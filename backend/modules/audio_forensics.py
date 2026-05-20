"""
audio_forensics.py — Audio Forensic Analysis Module.

Analyses audio tracks for signs of manipulation or synthesis:

1. **Noise-floor consistency** — splits the waveform into fixed-length
   segments, computes RMS energy per segment, and flags high variance
   (edits / splices produce discontinuous noise floors).

2. **Mel-spectrogram analysis** — computes a mel-spectrogram and checks
   for anomalous frequency-band gaps (entire bands dropping to silence)
   which are common in synthesised audio.

3. **Spectral-transition detection** — measures the cosine distance
   between consecutive segments' mean spectral vectors; abrupt jumps
   indicate splice points.

Typical usage::

    result = analyze("clip.wav")
    print(result["score"], result["details"])
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
SEGMENT_DURATION_S: float = 1.0     # seconds per analysis segment
MEL_N_MELS: int = 128
MEL_N_FFT: int = 2048
MEL_HOP_LENGTH: int = 512

# Scoring thresholds
RMS_VAR_UPPER: float = 0.04         # normalised RMS variance → score 1.0
RMS_VAR_LOWER: float = 0.002        # → score 0.0
SPECTRAL_DIST_UPPER: float = 0.35   # cosine distance → score 1.0
SPECTRAL_DIST_LOWER: float = 0.05   # → score 0.0
BAND_GAP_RATIO_UPPER: float = 0.25  # fraction of silent bands → score 1.0

AUDIO_EXTENSIONS: set[str] = {
    ".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".wma", ".opus",
}


def _load_audio(file_path: str) -> tuple[np.ndarray, int]:
    """Load audio via librosa.  Returns ``(y, sr)``."""
    import librosa
    y, sr = librosa.load(file_path, sr=None, mono=True)
    return y, sr


def _analyse_noise_floor(
    y: np.ndarray, sr: int, seg_dur: float = SEGMENT_DURATION_S,
) -> tuple[float, Dict[str, Any]]:
    """Compute per-segment RMS energy and return (normalised variance, details)."""
    import librosa

    seg_samples = int(seg_dur * sr)
    n_segments = max(1, len(y) // seg_samples)
    rms_values: List[float] = []

    for i in range(n_segments):
        start = i * seg_samples
        end = start + seg_samples
        segment = y[start:end]
        rms = float(np.sqrt(np.mean(segment ** 2)))
        rms_values.append(rms)

    rms_arr = np.array(rms_values)
    rms_mean = float(np.mean(rms_arr))
    rms_std = float(np.std(rms_arr))
    rms_var_norm = float(rms_std / max(rms_mean, 1e-8))  # coefficient of variation

    details = {
        "n_segments": n_segments,
        "rms_mean": round(rms_mean, 6),
        "rms_std": round(rms_std, 6),
        "rms_coeff_of_variation": round(rms_var_norm, 6),
        "rms_min": round(float(np.min(rms_arr)), 6),
        "rms_max": round(float(np.max(rms_arr)), 6),
    }
    return rms_var_norm, details


def _analyse_mel_spectrogram(
    y: np.ndarray, sr: int,
) -> tuple[float, Dict[str, Any]]:
    """Compute mel-spectrogram and detect anomalous frequency-band gaps.

    Returns ``(band_gap_ratio, details)`` where *band_gap_ratio* is the
    fraction of mel bands whose mean energy falls below a silence threshold.
    """
    import librosa

    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_mels=MEL_N_MELS, n_fft=MEL_N_FFT, hop_length=MEL_HOP_LENGTH,
    )
    S_db = librosa.power_to_db(S, ref=np.max)

    # Per-band mean energy
    band_means = np.mean(S_db, axis=1)  # shape: (n_mels,)
    silence_threshold = float(np.min(S_db)) + 3.0  # 3 dB above global min

    silent_bands = int(np.sum(band_means < silence_threshold))
    band_gap_ratio = silent_bands / max(len(band_means), 1)

    details = {
        "n_mel_bands": int(MEL_N_MELS),
        "silent_bands": silent_bands,
        "band_gap_ratio": round(band_gap_ratio, 4),
        "spectrogram_dynamic_range_db": round(
            float(np.max(S_db) - np.min(S_db)), 2
        ),
        "mean_energy_db": round(float(np.mean(S_db)), 2),
    }
    return band_gap_ratio, details


def _detect_spectral_transitions(
    y: np.ndarray, sr: int, seg_dur: float = SEGMENT_DURATION_S,
) -> tuple[float, List[int], Dict[str, Any]]:
    """Detect abrupt spectral transitions (potential splice points).

    Returns ``(mean_distance, splice_indices, details)``.
    """
    import librosa

    seg_samples = int(seg_dur * sr)
    n_segments = max(1, len(y) // seg_samples)

    # Mean MFCC vector per segment — captures timbral fingerprint
    segment_features: List[np.ndarray] = []
    for i in range(n_segments):
        start = i * seg_samples
        end = start + seg_samples
        segment = y[start:end]
        if len(segment) < MEL_N_FFT:
            continue
        mfccs = librosa.feature.mfcc(
            y=segment, sr=sr, n_mfcc=13, n_fft=MEL_N_FFT, hop_length=MEL_HOP_LENGTH,
        )
        segment_features.append(np.mean(mfccs, axis=1))

    if len(segment_features) < 2:
        return 0.0, [], {"n_segments_mfcc": len(segment_features)}

    # Cosine distances between consecutive segment feature vectors
    distances: List[float] = []
    for i in range(1, len(segment_features)):
        a = segment_features[i - 1]
        b = segment_features[i]
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            distances.append(1.0)
        else:
            cos_sim = float(np.dot(a, b) / (norm_a * norm_b))
            cos_dist = 1.0 - cos_sim
            distances.append(max(0.0, cos_dist))

    mean_dist = float(np.mean(distances))
    std_dist = float(np.std(distances))

    # Flag segments where the distance is > 2σ above the mean
    splice_indices: List[int] = []
    if std_dist > 0:
        threshold = mean_dist + 2.0 * std_dist
        splice_indices = [i for i, d in enumerate(distances) if d > threshold]

    details = {
        "n_segments_mfcc": len(segment_features),
        "spectral_dist_mean": round(mean_dist, 6),
        "spectral_dist_std": round(std_dist, 6),
        "spectral_dist_max": round(float(max(distances)), 6) if distances else 0.0,
        "potential_splice_points": splice_indices,
        "spectral_distances": [round(d, 6) for d in distances[:50]],
    }
    return mean_dist, splice_indices, details


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(file_path: str, **kwargs: Any) -> Dict[str, Any]:
    """Analyse audio forensics of the file at *file_path*.

    Parameters
    ----------
    file_path : str
        Path to an audio file.

    Returns
    -------
    dict
        ``{"score": float, "details": dict, "evidence": list}``
    """
    logger.info("audio_forensics: analysing %s", file_path)

    result: Dict[str, Any] = {
        "score": 0.0,
        "details": {},
        "evidence": [],
    }

    # ── Guard: file existence ────────────────────────────────────────────
    if not os.path.isfile(file_path):
        logger.warning("audio_forensics: file not found — %s", file_path)
        result["score"] = 0.5
        result["details"]["error"] = "File not found"
        return result

    # ── Guard: non-audio extension ───────────────────────────────────────
    ext = Path(file_path).suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        result["score"] = 0.5
        result["details"]["note"] = (
            f"Extension '{ext}' is not a recognised audio format; "
            "audio forensics not applicable"
        )
        return result

    # ── Load audio ───────────────────────────────────────────────────────
    try:
        y, sr = _load_audio(file_path)
    except Exception as exc:
        logger.error("audio_forensics: failed to load audio — %s", exc)
        result["score"] = 0.5
        result["details"]["error"] = f"Failed to load audio: {exc}"
        return result

    if len(y) == 0:
        result["score"] = 0.5
        result["details"]["error"] = "Audio file is empty"
        return result

    duration_s = len(y) / sr
    result["details"]["duration_s"] = round(duration_s, 2)
    result["details"]["sample_rate"] = sr

    # ── 1. Noise-floor consistency ───────────────────────────────────────
    try:
        rms_var, rms_details = _analyse_noise_floor(y, sr)
        result["details"]["noise_floor"] = rms_details
        norm_rms = float(np.clip(
            (rms_var - RMS_VAR_LOWER) / (RMS_VAR_UPPER - RMS_VAR_LOWER), 0.0, 1.0
        ))
    except Exception as exc:
        logger.error("audio_forensics: noise-floor analysis failed — %s", exc)
        rms_var = 0.0
        norm_rms = 0.0
        result["details"]["noise_floor"] = {"error": str(exc)}

    # ── 2. Mel-spectrogram band gaps ─────────────────────────────────────
    try:
        band_gap_ratio, mel_details = _analyse_mel_spectrogram(y, sr)
        result["details"]["mel_spectrogram"] = mel_details
        norm_gap = float(np.clip(band_gap_ratio / BAND_GAP_RATIO_UPPER, 0.0, 1.0))
    except Exception as exc:
        logger.error("audio_forensics: mel analysis failed — %s", exc)
        band_gap_ratio = 0.0
        norm_gap = 0.0
        result["details"]["mel_spectrogram"] = {"error": str(exc)}

    # ── 3. Spectral transitions ──────────────────────────────────────────
    try:
        mean_dist, splices, trans_details = _detect_spectral_transitions(y, sr)
        result["details"]["spectral_transitions"] = trans_details
        norm_trans = float(np.clip(
            (mean_dist - SPECTRAL_DIST_LOWER) / (SPECTRAL_DIST_UPPER - SPECTRAL_DIST_LOWER),
            0.0, 1.0,
        ))
    except Exception as exc:
        logger.error("audio_forensics: spectral transition analysis failed — %s", exc)
        mean_dist = 0.0
        splices = []
        norm_trans = 0.0
        result["details"]["spectral_transitions"] = {"error": str(exc)}

    # ── Final fused score ────────────────────────────────────────────────
    #   noise-floor variance  : 35 %
    #   band-gap ratio        : 25 %
    #   spectral transitions  : 40 %
    score = 0.35 * norm_rms + 0.25 * norm_gap + 0.40 * norm_trans
    score = float(np.clip(score, 0.0, 1.0))

    result["score"] = round(score, 4)
    result["details"]["component_scores"] = {
        "noise_floor_norm": round(norm_rms, 4),
        "band_gap_norm": round(norm_gap, 4),
        "spectral_transition_norm": round(norm_trans, 4),
    }

    logger.info(
        "audio_forensics: score=%.4f (rms=%.4f gap=%.4f trans=%.4f)",
        score, norm_rms, norm_gap, norm_trans,
    )
    return result
