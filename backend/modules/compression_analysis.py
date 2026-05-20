"""
compression_analysis.py — JPEG Quantization & DCT Forensic Analysis Module.

Extracts JPEG quantization tables, compares them against the standard IJG
(Independent JPEG Group) luminance and chrominance tables, detects
double-compression artefacts, and computes a normalised deviation score.

Typical usage::

    result = analyze("photo.jpg")
    print(result["score"], result["details"])
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ── Standard IJG quantization tables (quality = 50) ─────────────────────────
# These are the baseline tables defined in the JPEG specification (Annex K).
# Cameras and honest encoders scale these uniformly; manipulated images often
# show irregular patterns or evidence of re-quantization.

IJG_LUMINANCE_Q50: np.ndarray = np.array([
    [16, 11, 10, 16,  24,  40,  51,  61],
    [12, 12, 14, 19,  26,  58,  60,  55],
    [14, 13, 16, 24,  40,  57,  69,  56],
    [14, 17, 22, 29,  51,  87,  80,  62],
    [18, 22, 37, 56,  68, 109, 103,  77],
    [24, 35, 55, 64,  81, 104, 113,  92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103,  99],
], dtype=np.float64)

IJG_CHROMINANCE_Q50: np.ndarray = np.array([
    [17, 18, 24, 47, 99, 99, 99, 99],
    [18, 21, 26, 66, 99, 99, 99, 99],
    [24, 26, 56, 99, 99, 99, 99, 99],
    [47, 66, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
    [99, 99, 99, 99, 99, 99, 99, 99],
], dtype=np.float64)

JPEG_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".jfif"}
IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp", ".heic",
}


def _extract_quantization_tables(image: Image.Image) -> List[np.ndarray]:
    """Extract quantization tables from a Pillow ``JpegImageFile``.

    Returns a list of 8×8 ``np.ndarray`` tables (typically 2: luma + chroma).
    """
    qtables_raw = image.quantization  # dict[int, tuple/list of 64 ints]
    tables: List[np.ndarray] = []
    if not qtables_raw:
        return tables
    for _idx in sorted(qtables_raw.keys()):
        flat = list(qtables_raw[_idx])
        if len(flat) == 64:
            tables.append(np.array(flat, dtype=np.float64).reshape(8, 8))
    return tables


def _compute_quality_factor(qtable: np.ndarray, standard: np.ndarray) -> float:
    """Estimate the JPEG quality factor by reversing the IJG scaling formula.

    The IJG encoder scales the standard table by::

        q_scaled = max(floor((standard * S + 50) / 100), 1)

    where ``S`` is derived from quality.  We invert this per-element and
    return the *median* estimated quality (0-100).
    """
    # Avoid division by zero
    safe_std = np.where(standard == 0, 1, standard)
    # S_est per element
    s_estimates = (qtable * 100.0 - 50.0) / safe_std
    # quality from S
    s_median = float(np.median(s_estimates))
    if s_median < 50:
        quality = 5000.0 / max(s_median, 0.01)
    else:
        quality = 200.0 - 2.0 * s_median
    return float(np.clip(quality, 1.0, 100.0))


def _table_deviation(qtable: np.ndarray, standard: np.ndarray) -> float:
    """Normalised root-mean-square deviation between *qtable* and a scaled
    version of *standard*.

    We first scale the standard table to the estimated quality, then
    measure the residual.  A perfectly honest encode will have deviation ≈ 0.
    """
    quality = _compute_quality_factor(qtable, standard)
    if quality < 50:
        s = 5000.0 / max(quality, 1)
    else:
        s = 200.0 - 2.0 * quality
    scaled_std = np.floor((standard * s + 50.0) / 100.0)
    scaled_std = np.clip(scaled_std, 1, 255)
    diff = np.abs(qtable - scaled_std)
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    # Normalise to [0, 1] — an RMSE of ~20 is already very unusual
    return float(np.clip(rmse / 20.0, 0.0, 1.0))


def _detect_double_compression(tables: List[np.ndarray]) -> tuple[bool, str]:
    """Heuristic: double-compressed JPEGs often have quantization tables
    whose entries are *multiples* of common small primes that do not match
    any single quality factor scaling.

    We also flag tables where the high-frequency coefficients are
    disproportionately large relative to the low-frequency ones —
    a tell-tale sign of re-quantization at a higher quality after an
    initial low-quality save.
    """
    if not tables:
        return False, "No quantization tables available"

    luma = tables[0]

    # Check 1: ratio of DC coeff to median AC coeff
    dc = luma[0, 0]
    ac_median = float(np.median(luma[1:, 1:]))
    if ac_median > 0:
        ratio = dc / ac_median
        # In natural single-compression, DC is usually ≤ AC median
        if ratio < 0.3:
            return True, (
                f"DC/AC-median ratio unusually low ({ratio:.2f}); "
                "consistent with re-quantization at higher quality"
            )

    # Check 2: periodicity in table values (ghosting of original Q-table)
    flat = luma.flatten()
    # Count how many entries are exact multiples of a small base (2-4)
    for base in (2, 3, 4):
        multiples = np.sum(flat % base == 0)
        frac = multiples / 64.0
        if frac > 0.85 and base > 2:
            return True, (
                f"{frac*100:.0f}% of Q-table entries are multiples of {base}; "
                "suggests double compression"
            )

    # Check 3: unusually flat Q-table (all-ones or near-uniform)
    unique_count = len(np.unique(luma))
    if unique_count <= 3:
        return True, (
            f"Q-table has only {unique_count} unique values; "
            "highly unusual — possible synthetic generation"
        )

    return False, "No double-compression artefacts detected"


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(file_path: str, **kwargs: Any) -> Dict[str, Any]:
    """Analyse JPEG compression artefacts of the file at *file_path*.

    Parameters
    ----------
    file_path : str
        Path to the media file.

    Returns
    -------
    dict
        ``{"score": float, "details": dict, "evidence": list}``
    """
    logger.info("compression_analysis: analysing %s", file_path)

    result: Dict[str, Any] = {
        "score": 0.0,
        "details": {},
        "evidence": [],
    }

    # ── Guard: file existence ────────────────────────────────────────────
    if not os.path.isfile(file_path):
        logger.warning("compression_analysis: file not found — %s", file_path)
        result["score"] = 0.5
        result["details"]["error"] = "File not found"
        return result

    ext = Path(file_path).suffix.lower()

    # ── Guard: non-image ─────────────────────────────────────────────────
    if ext not in IMAGE_EXTENSIONS:
        result["score"] = 0.5
        result["details"]["note"] = (
            f"Non-image extension '{ext}'; compression analysis not applicable"
        )
        return result

    # ── Guard: non-JPEG images ───────────────────────────────────────────
    if ext not in JPEG_EXTENSIONS:
        result["score"] = 0.0
        result["details"]["note"] = (
            f"File is '{ext}', not JPEG; quantization analysis skipped. "
            "Non-JPEG formats do not use DCT-based compression."
        )
        return result

    # ── Open JPEG & extract Q-tables ─────────────────────────────────────
    try:
        image = Image.open(file_path)
    except Exception as exc:
        logger.error("compression_analysis: cannot open image — %s", exc)
        result["score"] = 0.5
        result["details"]["error"] = f"Cannot open image: {exc}"
        return result

    if not hasattr(image, "quantization") or image.quantization is None:
        result["score"] = 0.3
        result["details"]["note"] = "JPEG has no embedded quantization tables"
        return result

    tables = _extract_quantization_tables(image)
    if not tables:
        result["score"] = 0.3
        result["details"]["note"] = "Could not parse quantization tables"
        return result

    details: Dict[str, Any] = {"num_tables": len(tables)}

    # ── Luminance table analysis ─────────────────────────────────────────
    luma_dev = _table_deviation(tables[0], IJG_LUMINANCE_Q50)
    luma_quality = _compute_quality_factor(tables[0], IJG_LUMINANCE_Q50)
    details["luminance_deviation"] = round(luma_dev, 4)
    details["estimated_quality_luma"] = round(luma_quality, 1)
    details["luminance_table"] = tables[0].astype(int).tolist()

    # ── Chrominance table analysis (if present) ──────────────────────────
    chroma_dev: float = 0.0
    if len(tables) > 1:
        chroma_dev = _table_deviation(tables[1], IJG_CHROMINANCE_Q50)
        chroma_quality = _compute_quality_factor(tables[1], IJG_CHROMINANCE_Q50)
        details["chrominance_deviation"] = round(chroma_dev, 4)
        details["estimated_quality_chroma"] = round(chroma_quality, 1)
        details["chrominance_table"] = tables[1].astype(int).tolist()

    # ── Double-compression detection ─────────────────────────────────────
    is_double, double_desc = _detect_double_compression(tables)
    details["double_compression_detected"] = is_double
    details["double_compression_note"] = double_desc

    # ── Final score ──────────────────────────────────────────────────────
    #   deviation weight: 60 %
    #   double-compression weight: 40 %
    avg_dev = (luma_dev + chroma_dev) / max(len(tables), 1)
    double_weight = 0.4 if is_double else 0.0
    score = min(1.0, avg_dev * 0.6 + double_weight)

    result["score"] = round(score, 4)
    result["details"] = details
    logger.info(
        "compression_analysis: score=%.4f  est_quality=%.1f  double=%s",
        score, luma_quality, is_double,
    )
    return result
