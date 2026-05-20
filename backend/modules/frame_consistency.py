"""
frame_consistency.py — Temporal & Face Consistency Forensic Module.

Designed for video analysis. Accepts a list of extracted frame image paths
and analyses:

1. **Face-landmark jitter** — uses MediaPipe Face Mesh to extract 468
   normalised landmarks per frame, then computes the L2 distance between
   consecutive frames.  Deepfake faces often exhibit unnatural micro-jitter
   that is absent from real footage.

2. **Lighting / histogram shifts** — computes per-frame HSV histograms and
   measures discontinuities with ``cv2.compareHist`` (Bhattacharyya distance).
   Spliced or generated frames show abrupt lighting changes.

Typical usage::

    result = analyze(
        "dummy.mp4",
        frames=["frame001.png", "frame002.png", "frame003.png"],
    )
    print(result["score"], result["details"])
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────────────────────
JITTER_SCORE_UPPER: float = 0.015   # L2 jitter at/above this → score 1.0
JITTER_SCORE_LOWER: float = 0.002   # L2 jitter at/below this → score 0.0
HIST_SCORE_UPPER: float = 0.45      # Bhattacharyya distance → score 1.0
HIST_SCORE_LOWER: float = 0.05      # Bhattacharyya distance → score 0.0

# Lazy-loaded MediaPipe face mesh (heavy import)
_face_mesh = None


def _get_face_mesh():
    """Lazy-initialise the MediaPipe Face Mesh solution."""
    global _face_mesh
    if _face_mesh is None:
        import mediapipe as mp
        _face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
    return _face_mesh


def _extract_landmarks(image_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Return normalised (x, y, z) landmarks as an (N, 3) array, or *None*."""
    mesh = _get_face_mesh()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    results = mesh.process(rgb)
    if not results.multi_face_landmarks:
        return None
    face = results.multi_face_landmarks[0]
    landmarks = np.array(
        [[lm.x, lm.y, lm.z] for lm in face.landmark],
        dtype=np.float64,
    )
    return landmarks


def _compute_jitter(
    landmarks_seq: List[np.ndarray],
) -> tuple[List[float], float, float]:
    """Compute per-frame L2 jitter and return (jitters, mean, std).

    *jitters* contains ``len(landmarks_seq) - 1`` values.
    """
    jitters: List[float] = []
    for i in range(1, len(landmarks_seq)):
        diff = landmarks_seq[i] - landmarks_seq[i - 1]
        l2 = float(np.mean(np.linalg.norm(diff, axis=1)))
        jitters.append(l2)
    mean_j = float(np.mean(jitters)) if jitters else 0.0
    std_j = float(np.std(jitters)) if jitters else 0.0
    return jitters, mean_j, std_j


def _compute_histogram(image_bgr: np.ndarray) -> np.ndarray:
    """Compute a normalised HSV histogram (H: 50 bins, S: 60 bins)."""
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist(
        [hsv], [0, 1], None, [50, 60], [0, 180, 0, 256],
    )
    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return hist


def _compute_hist_distances(
    frames_bgr: List[np.ndarray],
) -> tuple[List[float], float, float]:
    """Bhattacharyya distances between consecutive frames' histograms."""
    hists = [_compute_histogram(f) for f in frames_bgr]
    distances: List[float] = []
    for i in range(1, len(hists)):
        d = cv2.compareHist(hists[i - 1], hists[i], cv2.HISTCMP_BHATTACHARYYA)
        distances.append(float(d))
    mean_d = float(np.mean(distances)) if distances else 0.0
    std_d = float(np.std(distances)) if distances else 0.0
    return distances, mean_d, std_d


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(file_path: str, **kwargs: Any) -> Dict[str, Any]:
    """Analyse temporal / face consistency across video frames.

    Parameters
    ----------
    file_path : str
        Path to the video file (used for logging; actual analysis uses
        the frame images).
    **kwargs
        ``frames`` (list[str]): **required** — ordered list of frame image
        paths extracted from the video.

    Returns
    -------
    dict
        ``{"score": float, "details": dict, "evidence": list}``
    """
    logger.info("frame_consistency: analysing %s", file_path)

    result: Dict[str, Any] = {
        "score": 0.0,
        "details": {},
        "evidence": [],
    }

    frame_paths: List[str] = kwargs.get("frames", [])

    # ── Guard: no frames ─────────────────────────────────────────────────
    if not frame_paths:
        result["score"] = 0.5
        result["details"]["note"] = (
            "No frame paths provided; pass frames=[...] to enable analysis"
        )
        return result

    # ── Guard: single frame ──────────────────────────────────────────────
    if len(frame_paths) == 1:
        result["score"] = 0.0
        result["details"]["note"] = (
            "Only one frame provided; temporal analysis requires ≥ 2 frames"
        )
        return result

    # ── Load frames ──────────────────────────────────────────────────────
    frames_bgr: List[np.ndarray] = []
    valid_paths: List[str] = []
    for fp in frame_paths:
        if not os.path.isfile(fp):
            logger.warning("frame_consistency: frame not found — %s", fp)
            continue
        img = cv2.imread(fp)
        if img is None:
            logger.warning("frame_consistency: cannot read — %s", fp)
            continue
        frames_bgr.append(img)
        valid_paths.append(fp)

    if len(frames_bgr) < 2:
        result["score"] = 0.5
        result["details"]["note"] = "Fewer than 2 valid frames could be loaded"
        return result

    details: Dict[str, Any] = {"total_frames_loaded": len(frames_bgr)}

    # ── Face-landmark jitter analysis ────────────────────────────────────
    landmarks_seq: List[np.ndarray] = []
    frames_with_faces: int = 0
    for img in frames_bgr:
        try:
            lm = _extract_landmarks(img)
        except Exception as exc:
            logger.debug("frame_consistency: landmark extraction error — %s", exc)
            lm = None
        if lm is not None:
            landmarks_seq.append(lm)
            frames_with_faces += 1
        else:
            # Insert a copy of the last known landmarks to keep alignment
            if landmarks_seq:
                landmarks_seq.append(landmarks_seq[-1].copy())

    details["frames_with_faces"] = frames_with_faces

    jitter_score: float = 0.0
    if len(landmarks_seq) >= 2:
        jitters, jitter_mean, jitter_std = _compute_jitter(landmarks_seq)
        details["jitter_mean"] = round(jitter_mean, 6)
        details["jitter_std"] = round(jitter_std, 6)
        details["jitter_max"] = round(float(max(jitters)), 6) if jitters else 0.0
        details["jitter_values"] = [round(j, 6) for j in jitters[:50]]  # cap

        # Normalise
        norm_jitter = (jitter_mean - JITTER_SCORE_LOWER) / (
            JITTER_SCORE_UPPER - JITTER_SCORE_LOWER
        )
        jitter_score = float(np.clip(norm_jitter, 0.0, 1.0))
    else:
        details["jitter_note"] = "Insufficient faces detected for jitter analysis"
        jitter_score = 0.5  # indeterminate

    details["jitter_score"] = round(jitter_score, 4)

    # ── Histogram / lighting analysis ────────────────────────────────────
    hist_dists, hist_mean, hist_std = _compute_hist_distances(frames_bgr)
    details["hist_mean"] = round(hist_mean, 4)
    details["hist_std"] = round(hist_std, 4)
    details["hist_max"] = round(float(max(hist_dists)), 4) if hist_dists else 0.0
    details["hist_values"] = [round(d, 4) for d in hist_dists[:50]]

    # Detect spikes (> 2σ above mean) as potential splice points
    if hist_dists and hist_std > 0:
        threshold = hist_mean + 2.0 * hist_std
        spikes = [
            i for i, d in enumerate(hist_dists) if d > threshold
        ]
        details["lighting_spike_frames"] = spikes
    else:
        details["lighting_spike_frames"] = []

    norm_hist = (hist_mean - HIST_SCORE_LOWER) / (
        HIST_SCORE_UPPER - HIST_SCORE_LOWER
    )
    hist_score = float(np.clip(norm_hist, 0.0, 1.0))
    details["hist_score"] = round(hist_score, 4)

    # ── Final fused score ────────────────────────────────────────────────
    #   jitter weight: 60 %   |   histogram weight: 40 %
    score = 0.60 * jitter_score + 0.40 * hist_score
    score = float(np.clip(score, 0.0, 1.0))

    result["score"] = round(score, 4)
    result["details"] = details
    logger.info(
        "frame_consistency: score=%.4f (jitter=%.4f, hist=%.4f)",
        score, jitter_score, hist_score,
    )
    return result
