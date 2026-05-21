"""
Flask application for the Deepfake Verification Platform.

Exposes REST endpoints for media upload, forensic analysis, report
retrieval, and analysis status tracking.
"""

from __future__ import annotations

import logging
import os
import traceback
import tempfile
import shutil
import requests
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required

from extensions import db, bcrypt, jwt
from auth import auth_bp

from config import (
    ALL_ALLOWED_EXTENSIONS,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MODULE_WEIGHTS,
    OUTPUT_DIR,
    UPLOAD_DIR,
)
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
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_BYTES

# Auth & Database config
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", 
    "postgresql://deepfake_db_4z2x_user:H0zTJuCboGc5ER6ZYZAKKUKf3Ak3RMks@dpg-d8735sq8qa3s73cu1bl0-a.singapore-postgres.render.com/deepfake_db_4z2x"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-deepfake-key-change-in-prod"

db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)

with app.app_context():
    db.create_all()

app.register_blueprint(auth_bp)

# Cloudinary config
cloudinary.config(
    cloud_name="dnhwswxav",
    api_key="796264911316469",
    api_secret="M1yepEiUfTg3cFFGRROOsFNkwgU",
    secure=True
)

CORS(app)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory stores (swap for a DB in production)
# ---------------------------------------------------------------------------

# file_id  → {file_id, original_filename, saved_path, media_type, uploaded_at}
_uploads: dict[str, dict[str, Any]] = {}

# analysis_id → full results dict
_analyses: dict[str, dict[str, Any]] = {}

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
def upload_file():
    """Accept a multipart file upload.

    Validates the file extension against the allow-list, saves it under a
    UUID-based filename in the uploads directory, and returns metadata.

    **Request**: ``multipart/form-data`` with a ``file`` field.

    **Response** (201):

    .. code-block:: json

        {
            "file_id": "...",
            "filename": "original.jpg",
            "media_type": "image"
        }
    """
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

    # Upload to Cloudinary directly
    try:
        upload_result = cloudinary.uploader.upload(
            file,
            resource_type="auto"
        )
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        return jsonify({"error": "Failed to upload to cloud storage."}), 500

    file_id = upload_result["public_id"]
    secure_url = upload_result["secure_url"]

    _uploads[file_id] = {
        "file_id": file_id,
        "original_filename": original_filename,
        "secure_url": secure_url,
        "media_type": media_type,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

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
def analyze_file():
    """Run the full forensic pipeline on a previously uploaded file.

    **Request** (JSON):

    .. code-block:: json

        {"file_id": "..."}

    **Response** (200): Full analysis results including per-module scores,
    fused score, tier classification, verdict, and a link to the PDF
    report.
    """
    data = request.get_json(silent=True)
    if not data or "file_id" not in data:
        return jsonify({"error": "Missing 'file_id' in request body."}), 400

    file_id: str = data["file_id"]

    if file_id not in _uploads:
        return jsonify({"error": f"Unknown file_id: {file_id}"}), 404

    upload_info = _uploads[file_id]
    media_type: str = upload_info["media_type"]
    secure_url: str = upload_info["secure_url"]
    original_filename: str = upload_info["original_filename"]

    analysis_id: str = uuid4().hex

    # Mark as in-progress.
    _analyses[analysis_id] = {
        "analysis_id": analysis_id,
        "file_id": file_id,
        "status": "processing",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Download from Cloudinary to a temporary file
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, original_filename)
        logger.info(f"Downloading from {secure_url} to {temp_file_path}")
        
        r = requests.get(secure_url, stream=True)
        r.raise_for_status()
        with open(temp_file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                
        results = _execute_pipeline(analysis_id, temp_file_path, media_type)
        
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
            
    except Exception:
        tb = traceback.format_exc()
        logger.error("Pipeline failed for analysis %s:\n%s", analysis_id, tb)
        _analyses[analysis_id]["status"] = "failed"
        _analyses[analysis_id]["error"] = tb
        return jsonify({"error": "Analysis pipeline failed.", "analysis_id": analysis_id}), 500

    return jsonify(results), 200


@app.route("/api/report/<report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id: str):
    """Serve a generated PDF report by its ID.

    The report file is expected at ``<OUTPUT_DIR>/<report_id>.pdf``.
    """
    report_path = os.path.join(OUTPUT_DIR, f"{report_id}.pdf")

    if not os.path.isfile(report_path):
        return jsonify({"error": f"Report not found: {report_id}"}), 404

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
    if analysis_id not in _analyses:
        return jsonify({"error": f"Unknown analysis_id: {analysis_id}"}), 404

    entry = _analyses[analysis_id]

    # Return a slim status view when the analysis is still running.
    if entry.get("status") in ("processing", "failed"):
        return jsonify({
            "analysis_id": analysis_id,
            "status": entry["status"],
            "error": entry.get("error"),
        }), 200

    return jsonify(entry), 200


# ── pipeline orchestration ──────────────────────────────────────────────────


def _execute_pipeline(
    analysis_id: str,
    file_path: str,
    media_type: str,
) -> dict[str, Any]:
    """Orchestrate preprocessing → forensic modules → scoring → reporting.

    Args:
        analysis_id: Unique identifier for this analysis run.
        file_path: Absolute path to the uploaded file.
        media_type: One of ``'image'``, ``'video'``, ``'audio'``.

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
        # Normalise but we pass the original path to modules; they can
        # call normalize_image themselves if they need it.
        _ = normalize_image(file_path)

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
                "file_path": file_path,
                "media_type": media_type,
                "module_results": {
                    k: v for k, v in module_results.items() if v is not None
                },
                "fused_score": fused_score,
                "tier": tier_info,
                "verdict": verdict,
            }
            report_path = report_gen_fn(analysis_payload, analysis_output_dir)
            if report_path and os.path.isfile(report_path):
                report_id = analysis_id
                
                # Upload the PDF to Cloudinary
                try:
                    pdf_upload_res = cloudinary.uploader.upload(
                        report_path,
                        resource_type="raw",
                        public_id=f"reports/{report_id}"
                    )
                    report_url = pdf_upload_res["secure_url"]
                    logger.info("Report generated and uploaded to Cloudinary: %s", report_url)
                except Exception as e:
                    logger.error("Failed to upload report to Cloudinary: %s", e)
                    report_url = None
        except Exception:
            logger.exception("Report generation failed.")

    # ── 5. Assemble response ────────────────────────────────────────────
    response: dict[str, Any] = {
        "analysis_id": analysis_id,
        "file_id": _uploads_file_id_for(file_path),
        "media_type": media_type,
        "status": "completed",
        "modules": {},
        "fused_score": fused_score,
        "tier": tier_info,
        "verdict": verdict,
        "report_id": None,
        "report_url": report_url,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    for name, result in module_results.items():
        if result is not None:
            response["modules"][name] = {
                "score": result.get("score"),
                "details": result.get("details", {}),
                "evidence": result.get("evidence", []),
            }
        else:
            response["modules"][name] = {
                "score": None,
                "details": {},
                "evidence": [],
                "error": "Module did not return results.",
            }

    # Persist full results for the status endpoint.
    _analyses[analysis_id] = response

    return response


# ── internal helpers ────────────────────────────────────────────────────────


def _uploads_file_id_for(file_path: str) -> str | None:
    """Look up the file_id that corresponds to *file_path*."""
    # file_path is now a temp path, so we can't match it this way easily.
    # Since we don't strictly need file_id in the _execute_pipeline return (it's injected in /analyze),
    # let's just return a placeholder, or we could pass file_id down.
    return None


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
