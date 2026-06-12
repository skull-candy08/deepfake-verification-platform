"""
ela_analysis.py — Error Level Analysis (ELA) Forensic Module.

Implements the core ELA algorithm::

    ELA(x, y) = |I_original(x, y) − I_recompressed(x, y)|

Regions that have been manipulated typically show *different* error levels
compared to the rest of the image, because they have been through a
different number of compression cycles.

This module:
1. Loads the original image with Pillow.
2. Re-saves it as JPEG at ``quality=95`` to a temporary file.
3. Computes the per-pixel absolute difference.
4. Generates a colour-mapped heatmap (``cv2.COLORMAP_JET``) and saves it
   as an evidence image.
5. Scores the image based on the normalised standard deviation of ELA
   values — high localised variance implies selective editing.

Typical usage::

    result = analyze("suspect.jpg")
    print(result["score"])
    print(result["evidence"])  # path(s) to heatmap PNG(s)
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
ELA_RECOMPRESSION_QUALITY: int = 95
ELA_SCALE_FACTOR: int = 20          # Amplification for visibility
SCORE_STDDEV_UPPER: float = 40.0    # Stddev at or above → score = 1.0
SCORE_STDDEV_LOWER: float = 5.0     # Stddev at or below → score = 0.0

IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp", ".heic",
}


def _compute_ela(original_path: str, quality: int = ELA_RECOMPRESSION_QUALITY) -> np.ndarray:
    """Compute the raw ELA difference array.

    Parameters
    ----------
    original_path : str
        Path to the source image.
    quality : int
        JPEG quality level used for re-compression (default 95).

    Returns
    -------
    np.ndarray
        Grayscale ELA image (uint8) after amplification.
    """
    original = Image.open(original_path).convert("RGB")

    # Re-compress to a temporary JPEG
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(tmp_fd)  # Close FD so Pillow can open it on Windows
    try:
        original.save(tmp_path, "JPEG", quality=quality)
        recompressed = Image.open(tmp_path).convert("RGB")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    orig_arr = np.array(original, dtype=np.float64)
    recomp_arr = np.array(recompressed, dtype=np.float64)

    # Per-pixel absolute difference across channels → single channel mean
    diff = np.abs(orig_arr - recomp_arr)
    ela_gray = np.mean(diff, axis=2)  # average across R, G, B

    # Amplify for visibility and clip
    ela_scaled = np.clip(ela_gray * ELA_SCALE_FACTOR, 0, 255).astype(np.uint8)
    return ela_scaled


def _generate_heatmap(
    ela_gray: np.ndarray,
    output_path: str,
) -> str:
    """Apply ``COLORMAP_JET`` to the ELA image and save as PNG.

    Returns the absolute path to the saved heatmap.
    """
    heatmap = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)
    cv2.imwrite(output_path, heatmap)
    logger.info("ela_analysis: heatmap saved → %s", output_path)
    return output_path


def _score_from_ela(ela_gray: np.ndarray) -> tuple[float, Dict[str, Any]]:
    """Derive a suspicion score from the ELA array.

    The scoring logic looks at:
    * **Global std-dev**: high std-dev across the whole image means uneven
      error levels → likely manipulation.
    * **Block-level variance**: we tile the image into 64×64 blocks and
      look at how much variance there is *between* blocks.

    Returns
    -------
    tuple[float, dict]
        ``(score, stats_dict)``
    """
    ela_f = ela_gray.astype(np.float64)
    global_mean = float(np.mean(ela_f))
    global_std = float(np.std(ela_f))
    global_max = float(np.max(ela_f))

    # Block-level analysis (64×64 tiles)
    h, w = ela_f.shape
    block_size = 64
    block_means: List[float] = []
    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            block = ela_f[y : y + block_size, x : x + block_size]
            block_means.append(float(np.mean(block)))

    block_std = float(np.std(block_means)) if len(block_means) > 1 else 0.0

    # Normalise global std to [0, 1]
    norm_std = (global_std - SCORE_STDDEV_LOWER) / (SCORE_STDDEV_UPPER - SCORE_STDDEV_LOWER)
    norm_std = float(np.clip(norm_std, 0.0, 1.0))

    # Normalise block std (inter-block variance above ~15 is suspicious)
    norm_block = float(np.clip(block_std / 30.0, 0.0, 1.0))

    # Weighted combination: global 60 %, block 40 %
    score = 0.60 * norm_std + 0.40 * norm_block
    score = float(np.clip(score, 0.0, 1.0))

    stats = {
        "global_mean": round(global_mean, 2),
        "global_std": round(global_std, 2),
        "global_max": round(global_max, 2),
        "block_count": len(block_means),
        "block_std": round(block_std, 2),
        "norm_global_std": round(norm_std, 4),
        "norm_block_std": round(norm_block, 4),
    }
    return score, stats


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(file_path: str, **kwargs: Any) -> Dict[str, Any]:
    """Perform Error Level Analysis on *file_path*.

    Parameters
    ----------
    file_path : str
        Path to the image file.
    **kwargs
        ``output_dir`` (str): directory for evidence images (default: same
        directory as *file_path*).

    Returns
    -------
    dict
        ``{"score": float, "details": dict, "evidence": list}``
    """
    logger.info("ela_analysis: analysing %s", file_path)

    result: Dict[str, Any] = {
        "score": 0.0,
        "details": {},
        "evidence": [],
    }

    # ── Guard: file existence ────────────────────────────────────────────
    if not os.path.isfile(file_path):
        logger.warning("ela_analysis: file not found — %s", file_path)
        result["score"] = 0.5
        result["details"]["error"] = "File not found"
        return result

    # ── Guard: non-image file ────────────────────────────────────────────
    ext = Path(file_path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        result["score"] = 0.5
        result["details"]["note"] = (
            f"Non-image extension '{ext}'; ELA not applicable"
        )
        return result

    # ── Compute ELA ──────────────────────────────────────────────────────
    try:
        ela_gray = _compute_ela(file_path, quality=ELA_RECOMPRESSION_QUALITY)
    except Exception as exc:
        logger.error("ela_analysis: ELA computation failed — %s", exc)
        result["score"] = 0.5
        result["details"]["error"] = f"ELA computation failed: {exc}"
        return result

    # ── Score ─────────────────────────────────────────────────────────────
    score, stats = _score_from_ela(ela_gray)
    result["score"] = round(score, 4)
    result["details"] = stats
    result["details"]["recompression_quality"] = ELA_RECOMPRESSION_QUALITY
    result["details"]["scale_factor"] = ELA_SCALE_FACTOR

    # ── Generate heatmap evidence ────────────────────────────────────────
    try:
        output_dir = kwargs.get("output_dir", str(Path(file_path).parent))
        os.makedirs(output_dir, exist_ok=True)
        stem = Path(file_path).stem
        heatmap_filename = f"{stem}_ela_heatmap.png"
        heatmap_path = os.path.join(output_dir, heatmap_filename)
        _generate_heatmap(ela_gray, heatmap_path)
        result["evidence"].append(heatmap_path)
    except Exception as exc:
        logger.error("ela_analysis: heatmap generation failed — %s", exc)
        result["details"]["heatmap_error"] = str(exc)

    logger.info("ela_analysis: score=%.4f", score)
    return result
