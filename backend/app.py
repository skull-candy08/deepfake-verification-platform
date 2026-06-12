"""
Flask application for the Deepfake Verification Platform.

Exposes REST endpoints for media upload, forensic analysis, report
retrieval, and analysis status tracking.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import magic
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

import config
from config import (
    ALL_ALLOWED_EXTENSIONS,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MODULE_WEIGHTS,
    OUTPUT_DIR,
    UPLOAD_DIR,
)
from extensions import bcrypt, db, jwt, limiter
from models import Analysis, Upload, User, TokenBlocklist
from auth import auth_bp
from cleanup import run_cleanup
from utils.preprocessing import (
    detect_media_type,
    extract_audio,
    extract_frames,
    normalize_image,
)
from utils.scoring import (
    calculate_weighted_score,
    classify_tier,
    generate_verdict,
)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = config.JWT_ACCESS_TOKEN_EXPIRES
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = config.JWT_REFRESH_TOKEN_EXPIRES
app.config["JWT_TOKEN_LOCATION"] = getattr(config, "JWT_TOKEN_LOCATION", ["headers"])
app.config["JWT_COOKIE_SECURE"] = getattr(config, "JWT_COOKIE_SECURE", False)
app.config["JWT_COOKIE_CSRF_PROTECT"] = getattr(config, "JWT_COOKIE_CSRF_PROTECT", False)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = config.MAX_FILE_SIZE_BYTES

# Initialize extensions
db.init_app(app)
jwt.init_app(app)
bcrypt.init_app(app)
limiter.init_app(app)
CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

# Register auth blueprint
app.register_blueprint(auth_bp)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None

# Create tables
with app.app_context():
    db.create_all()

# Schedule background cleanup
def _cleanup_loop():
    import time
    while True:
        with app.app_context():
            try:
                run_cleanup(config.CLEANUP_MAX_AGE_HOURS)
            except Exception as e:
                app.logger.error(f"Cleanup task failed: {e}")
        time.sleep(3600)  # run once an hour

cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
cleanup_thread.start()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ensure required directories exist
# ---------------------------------------------------------------------------

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── helper ──────────────────────────────────────────────────────────────────


def _allowed_file(filename: str) -> bool:
    """Return *True* if *filename* has an allowed extension."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALL_ALLOWED_EXTENSIONS


def _run_module(
    module_name: str,
    analyze_fn: Any,
    file_path: str,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Safely invoke a forensic module's ``analyze`` function.

    Returns the module result dict on success, or ``None`` on import /
    runtime errors (the pipeline must not crash if a single module fails).
    """
    try:
        result = analyze_fn(file_path, **kwargs)
        logger.info("Module '%s' completed – score: %s", module_name, result.get("score"))
        return result
    except Exception:
        logger.exception("Module '%s' raised an exception.", module_name)
        return None


def _safe_import_module(module_path: str, func_name: str = "analyze"):
    """Dynamically import *func_name* from *module_path*.

    Returns the callable, or ``None`` if the module is not yet
    implemented.
    """
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, func_name, None)
    except (ImportError, ModuleNotFoundError):
        logger.warning("Module '%s' not found – skipping.", module_path)
        return None


# ── endpoints ───────────────────────────────────────────────────────────────


@app.route("/api/upload", methods=["POST"])
@jwt_required()
@limiter.limit("20/hour")
def upload_file():
    """Accept a multipart file upload.

    Validates the file extension against the allow-list, validates MIME type
    with python-magic, saves it under a UUID-based filename in the uploads
    directory, creates a database record, and returns metadata.

    **Request**: ``multipart/form-data`` with a ``file`` field.

    **Response** (201):

    .. code-block:: json

        {
            "file_id": "...",
            "filename": "original.jpg",
            "media_type": "image"
        }
    """
    current_user_id = int(get_jwt_identity())

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]

    if file.filename is None or file.filename.strip() == "":
        return jsonify({"error": "No file selected."}), 400

    original_filename: str = secure_filename(file.filename)

    if not _allowed_file(original_filename):
        return jsonify({
            "error": f"File type not allowed. Accepted extensions: "
                     f"{sorted(ALL_ALLOWED_EXTENSIONS)}",
        }), 400

    # Detect media type from the original filename.
    try:
        media_type = detect_media_type(original_filename)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Save locally to UPLOAD_DIR
    file_id = uuid4().hex
    # Preserve original extension
    ext = os.path.splitext(original_filename)[1]
    saved_filename = f"{file_id}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    try:
        file.save(saved_path)
    except Exception as e:
        logger.error("Local file save failed: %s", e)
        return jsonify({"error": "Failed to save file locally."}), 500

    # Validate MIME type with python-magic
    try:
        detected_mime = magic.from_file(saved_path, mime=True)
    except Exception:
        detected_mime = None
    if detected_mime:
        mime_map = {
            "image": ["image/"],
            "video": ["video/"],
            "audio": ["audio/"],
        }
        if not any(detected_mime.startswith(prefix) for prefix in mime_map.get(media_type, [])):
            os.remove(saved_path)
            return jsonify({"error": "File content does not match its extension."}), 400

    # Create database record
    upload_record = Upload(
        user_id=current_user_id,
        file_id=file_id,
        original_filename=original_filename,
        saved_path=saved_path,
        media_type=media_type,
    )
    db.session.add(upload_record)
    db.session.commit()

    logger.info(
        "Upload OK – file_id=%s  filename=%s  media_type=%s",
        file_id,
        original_filename,
        media_type,
    )

    return jsonify({
        "file_id": file_id,
        "filename": original_filename,
        "media_type": media_type,
    }), 201


@app.route("/api/analyze", methods=["POST"])
@jwt_required()
@limiter.limit("10/hour")
def analyze_file():
    """Run the full forensic pipeline on a previously uploaded file.

    **Request** (JSON):

    .. code-block:: json

        {"file_id": "..."}

    **Response** (202): ``{analysis_id, status: 'processing'}``
    """
    current_user_id = int(get_jwt_identity())

    data = request.get_json(silent=True)
    if not data or "file_id" not in data:
        return jsonify({"error": "Missing 'file_id' in request body."}), 400

    file_id: str = data["file_id"]

    # Look up upload from database and verify ownership
    upload_record = Upload.query.filter_by(file_id=file_id).first()
    if not upload_record:
        return jsonify({"error": "Unknown file_id."}), 404
    if upload_record.user_id != current_user_id:
        return jsonify({"error": "Access denied."}), 403

    media_type: str = upload_record.media_type
    saved_path: str = upload_record.saved_path
    original_filename: str = upload_record.original_filename

    analysis_id: str = uuid4().hex

    # Create Analysis record in database
    analysis_record = Analysis(
        user_id=current_user_id,
        upload_id=upload_record.id,
        analysis_id=analysis_id,
        status="processing",
    )
    db.session.add(analysis_record)
    db.session.commit()

    # Run pipeline in background thread
    thread = threading.Thread(
        target=_run_analysis_background,
        args=(app, analysis_id, saved_path, media_type, file_id, original_filename),
    )
    thread.daemon = True
    thread.start()

    return jsonify({"analysis_id": analysis_id, "status": "processing"}), 202


def _run_analysis_background(
    app_instance,
    analysis_id: str,
    file_path: str,
    media_type: str,
    file_id: str,
    original_filename: str,
):
    """Execute the forensic pipeline in a background thread."""
    with app_instance.app_context():
        try:
            results = _execute_pipeline(
                analysis_id, file_path, media_type, file_id, original_filename
            )
            analysis = Analysis.query.filter_by(analysis_id=analysis_id).first()
            if analysis:
                analysis.status = "completed"
                analysis.fused_score = results.get("fused_score")
                tier_info = results.get("tier", {})
                analysis.tier_label = tier_info.get("label") if isinstance(tier_info, dict) else str(tier_info)
                analysis.verdict = results.get("verdict")
                analysis.report_path = results.get("report_id")
                analysis.completed_at = datetime.now(timezone.utc)
                analysis.result_json = json.dumps(results, default=str)
                db.session.commit()
        except Exception:
            logger.exception("Pipeline failed for analysis %s", analysis_id)
            analysis = Analysis.query.filter_by(analysis_id=analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = "An internal error occurred during analysis."
                analysis.completed_at = datetime.now(timezone.utc)
                db.session.commit()


@app.route("/api/report/<report_id>", methods=["GET"])
@jwt_required()
@limiter.limit("30/minute")
def get_report(report_id: str):
    """Serve a generated PDF report by its ID.

    The report file is expected at ``<OUTPUT_DIR>/<report_id>.pdf``.
    """
    # Validate report_id format
    if not re.match(r'^[a-f0-9]{32}$', report_id):
        return jsonify({"error": "Invalid report ID format."}), 400

    current_user_id = int(get_jwt_identity())

    # Verify ownership
    analysis = Analysis.query.filter_by(analysis_id=report_id).first()
    if not analysis:
        return jsonify({"error": "Report not found."}), 404
    if analysis.user_id != current_user_id:
        return jsonify({"error": "Access denied."}), 403

    report_path = os.path.join(OUTPUT_DIR, f"{report_id}.pdf")

    # Path traversal protection
    resolved_path = os.path.realpath(report_path)
    resolved_output_dir = os.path.realpath(OUTPUT_DIR)
    if not resolved_path.startswith(resolved_output_dir):
        return jsonify({"error": "Invalid report path."}), 400

    if not os.path.isfile(report_path):
        return jsonify({"error": "Report file not found."}), 404

    return send_file(
        report_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"deepfake_report_{report_id}.pdf",
    )


@app.route("/api/status/<analysis_id>", methods=["GET"])
@jwt_required()
def analysis_status(analysis_id: str):
    """Return the current status of an analysis job.

    Possible statuses: ``processing``, ``completed``, ``failed``.
    """
    # Validate format
    if not re.match(r'^[a-f0-9]{32}$', analysis_id):
        return jsonify({"error": "Invalid analysis ID format."}), 400

    current_user_id = int(get_jwt_identity())

    analysis = Analysis.query.filter_by(analysis_id=analysis_id).first()
    if not analysis:
        return jsonify({"error": "Unknown analysis_id."}), 404
    if analysis.user_id != current_user_id:
        return jsonify({"error": "Access denied."}), 403

    # Return a slim status view when the analysis is still running or failed.
    if analysis.status in ("processing", "pending"):
        return jsonify({
            "analysis_id": analysis_id,
            "status": analysis.status,
        }), 200

    if analysis.status == "failed":
        return jsonify({
            "analysis_id": analysis_id,
            "status": "failed",
            "error": "An internal error occurred.",
        }), 200

    # Completed — return full results from result_json
    response: dict[str, Any] = {
        "analysis_id": analysis_id,
        "status": "completed",
        "fused_score": analysis.fused_score,
        "tier_label": analysis.tier_label,
        "verdict": analysis.verdict,
        "report_id": analysis.report_path,
        "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
    }

    if analysis.result_json:
        try:
            response["results"] = json.loads(analysis.result_json)
        except (json.JSONDecodeError, TypeError):
            response["results"] = None

    return jsonify(response), 200


# ── pipeline orchestration ──────────────────────────────────────────────────


def _execute_pipeline(
    analysis_id: str,
    file_path: str,
    media_type: str,
    file_id: str,
    original_filename: str,
) -> dict[str, Any]:
    """Orchestrate preprocessing → forensic modules → scoring → reporting.

    Args:
        analysis_id: Unique identifier for this analysis run.
        file_path: Absolute path to the uploaded file.
        media_type: One of ``'image'``, ``'video'``, ``'audio'``.
        file_id: The file_id of the upload.
        original_filename: Original filename as uploaded.

    Returns:
        A dict containing per-module results, fused score, tier,
        verdict, and report URL.
    """

    # ── 1. Preprocessing ────────────────────────────────────────────────
    analysis_output_dir: str = os.path.join(OUTPUT_DIR, analysis_id)
    os.makedirs(analysis_output_dir, exist_ok=True)

    frame_paths: list[str] = []
    audio_path: str | None = None

    if media_type == "video":
        frames_dir = os.path.join(analysis_output_dir, "frames")
        frame_paths = extract_frames(file_path, frames_dir, fps=1)

        audio_out = os.path.join(analysis_output_dir, "audio.wav")
        audio_path = extract_audio(file_path, audio_out)

    elif media_type == "image":
        # Normalise — the result is not used directly; modules call
        # normalize_image themselves if they need it.
        normalize_image(file_path)

    elif media_type == "audio":
        audio_path = file_path

    # ── 2. Run forensic modules ─────────────────────────────────────────
    module_results: dict[str, dict[str, Any] | None] = {}

    # Metadata analysis (image / video)
    if media_type in ("image", "video"):
        fn = _safe_import_module("modules.metadata_analysis")
        if fn:
            module_results["metadata"] = _run_module("metadata", fn, file_path)

    # Compression analysis (image / video)
    if media_type in ("image", "video"):
        fn = _safe_import_module("modules.compression_analysis")
        if fn:
            module_results["compression"] = _run_module("compression", fn, file_path)

    # ELA analysis (image; for video, run on first extracted frame)
    if media_type == "image":
        fn = _safe_import_module("modules.ela_analysis")
        if fn:
            module_results["ela"] = _run_module("ela", fn, file_path)
    elif media_type == "video" and frame_paths:
        fn = _safe_import_module("modules.ela_analysis")
        if fn:
            module_results["ela"] = _run_module(
                "ela", fn, frame_paths[0], frames=frame_paths
            )

    # Frame analysis (video only)
    if media_type == "video" and frame_paths:
        fn = _safe_import_module("modules.frame_consistency")
        if fn:
            module_results["frame"] = _run_module(
                "frame", fn, file_path, frames=frame_paths
            )

    # Audio analysis (video with audio / standalone audio)
    if audio_path:
        fn = _safe_import_module("modules.audio_forensics")
        if fn:
            module_results["audio"] = _run_module("audio", fn, audio_path)

    # ── 3. Scoring ──────────────────────────────────────────────────────
    # Build a {module_name: score_or_None} map for the scorer.
    score_map: dict[str, float | None] = {}
    for name, result in module_results.items():
        score_map[name] = result["score"] if result else None

    fused_score: float = calculate_weighted_score(score_map, MODULE_WEIGHTS)
    tier_info: dict = classify_tier(fused_score)
    verdict: str = generate_verdict(fused_score)

    # ── 4. Report generation ────────────────────────────────────────────
    report_url: str | None = None
    report_id: str | None = None

    report_gen_fn = _safe_import_module(
        "reports.generator", "generate_report"
    )
    if report_gen_fn:
        try:
            analysis_payload = {
                "analysis_id": analysis_id,
                "file_id": file_id,
                "filename": original_filename,
                "file_path": file_path,
                "media_type": media_type,
                "module_scores": {
                    k: v for k, v in module_results.items() if v is not None
                },
                "fused_score": fused_score,
                "tier": tier_info,
                "verdict": verdict,
            }
            report_path = report_gen_fn(analysis_payload, analysis_output_dir)
            if report_path and os.path.isfile(report_path):
                report_id = analysis_id
                # Copy report to OUTPUT_DIR root so /api/report/<id> can serve it
                final_report = os.path.join(OUTPUT_DIR, f"{report_id}.pdf")
                if os.path.abspath(report_path) != os.path.abspath(final_report):
                    shutil.copy2(report_path, final_report)
                logger.info("Report generated: %s", final_report)
        except Exception:
            logger.exception("Report generation failed.")

    # ── 5. Assemble response ────────────────────────────────────────────
    response: dict[str, Any] = {
        "analysis_id": analysis_id,
        "file_id": file_id,
        "media_type": media_type,
        "status": "completed",
        "modules": {},
        "fused_score": fused_score,
        "tier": tier_info,
        "verdict": verdict,
        "report_id": report_id,
        "report_url": None,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    for name, result in module_results.items():
        if result is not None:
            # Strip absolute paths from evidence array
            raw_evidence = result.get("evidence", [])
            sanitized_evidence = [os.path.basename(p) for p in raw_evidence if isinstance(p, str)]

            response["modules"][name] = {
                "score": result.get("score"),
                "details": result.get("details", {}),
                "evidence": sanitized_evidence,
            }
        else:
            response["modules"][name] = {
                "score": None,
                "details": {},
                "evidence": [],
                "error": "Module did not return results.",
            }

    return response


# ── global error handlers ───────────────────────────────────────────────────


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found."}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Unhandled exception")
    return jsonify({"error": "An internal server error occurred."}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception: %s", e)
    return jsonify({"error": "An unexpected error occurred."}), 500


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_ENV") == "development")
