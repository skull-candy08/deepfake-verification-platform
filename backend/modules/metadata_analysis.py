"""
metadata_analysis.py — EXIF / Metadata Forensic Inspection Module.

Extracts and analyzes image metadata (EXIF) to identify signs of
manipulation. Missing EXIF, editing-software watermarks, GPS anomalies,
and timestamp inconsistencies all contribute to a weighted suspicion score.

Typical usage::

    result = analyze("photo.jpg")
    print(result["score"], result["details"])
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)

# ── Known editing-software signatures (case-insensitive substrings) ──────────
EDITING_SOFTWARE_SIGNATURES: list[str] = [
    "photoshop", "gimp", "faceapp", "aftereffects", "lightroom",
    "snapseed", "pixlr", "canva", "affinity", "paintshop",
    "corel", "capture one", "darktable", "luminar", "fotor",
    "befunky", "prisma", "remini", "reface", "deepfacelab",
    "faceswap", "facetune", "meitu", "beauty plus", "youcam",
]

# ── Weight constants for scoring ─────────────────────────────────────────────
WEIGHT_NO_EXIF: float = 0.30
WEIGHT_EDITING_SOFTWARE: float = 0.50
WEIGHT_TIMESTAMP_MISMATCH: float = 0.40
WEIGHT_GPS_STRIPPED: float = 0.10
WEIGHT_THUMBNAIL_MISMATCH: float = 0.15

# ── Supported image extensions ───────────────────────────────────────────────
IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp", ".heic",
}


def _decode_exif(image: Image.Image) -> Dict[str, Any]:
    """Return a human-readable dict of all EXIF tags present in *image*."""
    raw_exif = image.getexif()
    decoded: Dict[str, Any] = {}
    if not raw_exif:
        return decoded

    for tag_id, value in raw_exif.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        decoded[tag_name] = value

    # Decode GPS sub-IFD when present
    gps_ifd = raw_exif.get_ifd(0x8825)
    if gps_ifd:
        gps_data: Dict[str, Any] = {}
        for gps_tag_id, gps_value in gps_ifd.items():
            gps_tag_name = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
            gps_data[gps_tag_name] = gps_value
        decoded["GPSInfo"] = gps_data

    return decoded


def _parse_exif_datetime(value: Any) -> datetime | None:
    """Try to parse an EXIF datetime string (``YYYY:MM:DD HH:MM:SS``)."""
    if not isinstance(value, str):
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _check_editing_software(exif: Dict[str, Any]) -> tuple[bool, str | None]:
    """Return ``(found, software_name)`` if an editing-software tag is detected."""
    software_value: str = str(exif.get("Software", "")).lower()
    processing_software: str = str(exif.get("ProcessingSoftware", "")).lower()
    combined = f"{software_value} {processing_software}"

    for sig in EDITING_SOFTWARE_SIGNATURES:
        if sig in combined:
            return True, sig.title()
    return False, None


def _check_timestamp_consistency(exif: Dict[str, Any]) -> tuple[bool, str]:
    """Check ``DateTimeOriginal`` vs ``DateTimeDigitized`` for mismatches.

    Returns ``(is_mismatch, description)``.
    """
    dt_original = _parse_exif_datetime(exif.get("DateTimeOriginal"))
    dt_digitized = _parse_exif_datetime(exif.get("DateTimeDigitized"))
    dt_modified = _parse_exif_datetime(exif.get("DateTime"))

    if dt_original is None and dt_digitized is None:
        return False, "No timestamp tags found"

    if dt_original and dt_digitized:
        delta = abs((dt_original - dt_digitized).total_seconds())
        if delta > 2:  # allow ≤ 2 s of camera-internal lag
            return True, (
                f"DateTimeOriginal ({dt_original}) differs from "
                f"DateTimeDigitized ({dt_digitized}) by {delta:.0f}s"
            )

    if dt_original and dt_modified:
        delta = abs((dt_original - dt_modified).total_seconds())
        if delta > 86400:  # > 1 day apart
            return True, (
                f"DateTime ({dt_modified}) is >1 day from "
                f"DateTimeOriginal ({dt_original})"
            )

    return False, "Timestamps consistent"


def _check_gps_presence(exif: Dict[str, Any]) -> tuple[bool, str]:
    """Return ``(has_gps, description)``."""
    gps_info = exif.get("GPSInfo")
    if gps_info and isinstance(gps_info, dict) and len(gps_info) > 0:
        return True, "GPS data present"
    return False, "GPS data absent (may have been stripped)"


def _safe_serialize(value: Any) -> Any:
    """Convert EXIF value to a JSON-safe representation."""
    if isinstance(value, bytes):
        return value.hex()[:64] + ("..." if len(value) > 32 else "")
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_serialize(v) for k, v in value.items()}
    try:
        # IFDRational and similar
        return float(value)
    except (TypeError, ValueError):
        return str(value)


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(file_path: str, **kwargs: Any) -> Dict[str, Any]:
    """Analyse EXIF / metadata of the file at *file_path*.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the media file.

    Returns
    -------
    dict
        ``{"score": float, "details": dict, "evidence": list}``
        where *score* ∈ [0.0, 1.0] (0 = authentic, 1 = fake).
    """
    logger.info("metadata_analysis: analysing %s", file_path)

    result: Dict[str, Any] = {
        "score": 0.0,
        "details": {},
        "evidence": [],
    }

    # ── Guard: file existence ────────────────────────────────────────────
    if not os.path.isfile(file_path):
        logger.warning("metadata_analysis: file not found — %s", file_path)
        result["score"] = 0.5
        result["details"]["error"] = "File not found"
        return result

    # ── Guard: non-image files ───────────────────────────────────────────
    ext = Path(file_path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        logger.info("metadata_analysis: non-image file (%s)", ext)
        result["score"] = 0.5
        result["details"]["note"] = (
            f"Non-image extension '{ext}'; metadata analysis not applicable"
        )
        return result

    # ── Open image & extract EXIF ────────────────────────────────────────
    try:
        image = Image.open(file_path)
    except Exception as exc:
        logger.error("metadata_analysis: cannot open image — %s", exc)
        result["score"] = 0.5
        result["details"]["error"] = f"Cannot open image: {exc}"
        return result

    exif = _decode_exif(image)
    flags: Dict[str, float] = {}  # flag_name → weight
    details: Dict[str, Any] = {"exif_tag_count": len(exif)}

    # ── 1. Missing / stripped EXIF ───────────────────────────────────────
    if len(exif) == 0:
        flags["no_exif"] = WEIGHT_NO_EXIF
        details["no_exif"] = True
        logger.info("metadata_analysis: no EXIF data found — suspicious")
    else:
        details["no_exif"] = False
        # Store a serialisable summary of the raw EXIF
        details["exif_summary"] = {
            k: _safe_serialize(v)
            for k, v in list(exif.items())[:30]  # cap for report brevity
        }

    # ── 2. Editing-software detection ────────────────────────────────────
    has_editor, editor_name = _check_editing_software(exif)
    if has_editor:
        flags["editing_software"] = WEIGHT_EDITING_SOFTWARE
        details["editing_software_detected"] = editor_name
        logger.info("metadata_analysis: editing software detected — %s", editor_name)
    else:
        details["editing_software_detected"] = None

    # ── 3. GPS presence / absence ────────────────────────────────────────
    has_gps, gps_desc = _check_gps_presence(exif)
    details["gps_present"] = has_gps
    details["gps_note"] = gps_desc
    if not has_gps and len(exif) > 0:
        # GPS stripped from an otherwise-tagged image is mildly suspicious
        flags["gps_stripped"] = WEIGHT_GPS_STRIPPED

    # ── 4. Timestamp consistency ─────────────────────────────────────────
    ts_mismatch, ts_desc = _check_timestamp_consistency(exif)
    details["timestamp_mismatch"] = ts_mismatch
    details["timestamp_note"] = ts_desc
    if ts_mismatch:
        flags["timestamp_mismatch"] = WEIGHT_TIMESTAMP_MISMATCH
        logger.info("metadata_analysis: timestamp mismatch — %s", ts_desc)

    # ── 5. Thumbnail-size vs main-image-size sanity check ────────────────
    try:
        thumb_data = exif.get("JPEGThumbnail") or exif.get("TIFFThumbnail")
        if thumb_data and isinstance(thumb_data, bytes):
            import io
            thumb = Image.open(io.BytesIO(thumb_data))
            main_w, main_h = image.size
            thumb_w, thumb_h = thumb.size
            expected_ratio = main_w / max(main_h, 1)
            actual_ratio = thumb_w / max(thumb_h, 1)
            if abs(expected_ratio - actual_ratio) > 0.3:
                flags["thumbnail_mismatch"] = WEIGHT_THUMBNAIL_MISMATCH
                details["thumbnail_mismatch"] = True
                logger.info("metadata_analysis: thumbnail aspect ratio mismatch")
            else:
                details["thumbnail_mismatch"] = False
    except Exception:
        details["thumbnail_mismatch"] = "Unable to parse thumbnail"

    # ── Compute final score ──────────────────────────────────────────────
    if flags:
        score = min(1.0, sum(flags.values()))
    else:
        score = 0.0

    details["flags_triggered"] = list(flags.keys())
    details["flag_weights"] = flags

    result["score"] = round(score, 4)
    result["details"] = details
    logger.info("metadata_analysis: score=%.4f  flags=%s", score, list(flags.keys()))
    return result
