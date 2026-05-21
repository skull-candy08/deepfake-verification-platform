"""
Scoring and classification utilities for the Deepfake Verification Platform.

Implements weighted score fusion, tier classification, and verdict
generation based on the thresholds defined in :pymod:`config`.
"""

from __future__ import annotations

import logging
from typing import Optional

from config import MODULE_WEIGHTS, TIER_THRESHOLDS

logger = logging.getLogger(__name__)


def calculate_weighted_score(
    module_scores: dict[str, Optional[float]],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Compute a fused deepfake-likelihood score via weighted linear combination.

    Only modules whose score is not ``None`` participate.  When one or
    more modules are skipped the remaining weights are **re-normalised**
    so the result still lies in [0, 1].

    Args:
        module_scores: Mapping of module name → score (0-1) or ``None``
            when the module was not applicable / did not run.
        weights: Optional custom weight mapping.  Falls back to
            :data:`config.MODULE_WEIGHTS`.

    Returns:
        A float in [0.0, 1.0] representing the overall manipulation
        likelihood.  Returns ``0.0`` when no modules provided scores.

    Example::

        >>> calculate_weighted_score(
        ...     {"metadata": 0.3, "compression": 0.5, "ela": None},
        ... )
        0.411...
    """
    if weights is None:
        weights = MODULE_WEIGHTS

    # Filter to modules that actually produced a score.
    active: dict[str, float] = {
        name: score
        for name, score in module_scores.items()
        if score is not None and name in weights
    }

    if not active:
        logger.warning(
            "No module scores available – returning 0.0 as the fused score."
        )
        return 0.0

    total_weight: float = sum(weights[name] for name in active)

    if total_weight <= 0:
        logger.warning("Total active weight is zero – returning 0.0.")
        return 0.0

    # Weighted sum with re-normalised weights.
    fused_score: float = sum(
        (weights[name] / total_weight) * score
        for name, score in active.items()
    )

    # Clamp to [0, 1] to guard against floating-point drift.
    fused_score = max(0.0, min(1.0, fused_score))

    logger.info(
        "Fused score: %.4f  (active modules: %s, total_weight: %.2f)",
        fused_score,
        list(active.keys()),
        total_weight,
    )
    return round(fused_score, 4)


def classify_tier(score: float) -> dict:
    """Map a fused score to a classification tier.

    The tier boundaries are defined in
    :data:`config.TIER_THRESHOLDS`.

    Args:
        score: A float in [0, 1].

    Returns:
        A dict with keys ``tier`` (int), ``label`` (str), and
        ``description`` (str).
    """
    for tier_info in TIER_THRESHOLDS:
        if score < tier_info["max_score"]:
            result = {
                "tier": tier_info["tier"],
                "label": tier_info["label"],
                "description": tier_info["description"],
            }
            logger.debug("Score %.4f → %s", score, result)
            return result

    # Fallback: score == 1.0 (or rounding edge-case) → highest tier.
    highest = TIER_THRESHOLDS[-1]
    return {
        "tier": highest["tier"],
        "label": highest["label"],
        "description": highest["description"],
    }


def generate_verdict(score: float) -> str:
    """Return a human-readable verdict string for the given score.

    Verdict bands:
        * ``score < 0.3``  → *Likely Authentic*
        * ``0.3 ≤ score < 0.5`` → *Suspicious*
        * ``0.5 ≤ score < 0.7`` → *Likely Manipulated*
        * ``score ≥ 0.7``  → *High Confidence Forgery*

    Args:
        score: A float in [0, 1].

    Returns:
        A verdict string.
    """
    if score < 0.3:
        verdict = "Likely Authentic"
    elif score < 0.5:
        verdict = "Suspicious"
    elif score < 0.7:
        verdict = "Likely Manipulated"
    else:
        verdict = "High Confidence Forgery"

    logger.info("Score %.4f → verdict: %s", score, verdict)
    return verdict
