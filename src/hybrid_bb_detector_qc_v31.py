"""Research-only reference-calibrated QC overlay for Hybrid BB v3.

Designed to detect unexpected changes of fitted BB width (e.g., partial
occlusion) that may not increase Gaussian fit residual. Unlike a simple
fixed sigma threshold, this compares with a *trusted reference* image of the
same BB, phantom, detector geometry and resolution.

This module deliberately does not overwrite/modify Hybrid v3; passing a
heuristic check NEVER means clinical validation or automated approval.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from hybrid_bb_detector import detect_bb_hybrid


def calibrate_reference(
    reference_image: np.ndarray,
    reference_center: tuple[float, float],
    *,
    search_radius: int = 18,
) -> dict[str, Any]:
    """Obtain the BB width and polarity from a trusted reference image.

    The reference BB must be confirmed by the operator. Calibration is not
    allowed to silently succeed on an unreliable reference detection.
    """
    result = detect_bb_hybrid(
        reference_image, reference_center, search_radius=search_radius
    )
    sigma = result.get("gaussian_sigma")
    polarity = result.get("gaussian_polarity")
    good = (
        result.get("status") == "candidate_requires_review"
        and not result.get("qc_flags")
        and sigma is not None
        and math.isfinite(float(sigma))
        and float(sigma) > 0
        and polarity in ("bright", "dark")
    )
    if not good:
        raise ValueError(
            "Reference BB calibration is unreliable. Inspect/confirm the BB "
            f"before proceeding. Reference status={result.get('status')}, "
            f"flags={result.get('qc_flags')}"
        )
    return {
        "reference_sigma": float(sigma),
        "reference_polarity": str(polarity),
        "reference_detection": result,
    }


def detect_bb_hybrid_qc_v31(
    image: np.ndarray,
    reference_center: tuple[float, float],
    *,
    calibration: dict[str, Any],
    search_radius: int = 18,
    min_sigma_ratio: float = 0.70,
    max_sigma_ratio: float = 1.40,
) -> dict[str, Any]:
    """Add a reference-relative Gaussian-width check to v3 flags.

    Ratios 0.70/1.40 are exploratory engineering alerts, NOT medical limits.
    Recalibrate and test on independent acquisitions before using as criteria.

    Returns the same v3 keys plus reference_sigma, sigma_ratio_to_reference,
    qc_version. Never auto-approves a detection.
    """
    if not (0 < min_sigma_ratio < 1 < max_sigma_ratio):
        raise ValueError("Require 0 < min_sigma_ratio < 1 < max_sigma_ratio")
    ref_sigma = float(calibration["reference_sigma"])
    ref_polarity = str(calibration["reference_polarity"])
    if not (math.isfinite(ref_sigma) and ref_sigma > 0):
        raise ValueError("Invalid reference Gaussian sigma")
    if ref_polarity not in ("bright", "dark"):
        raise ValueError("Invalid reference BB polarity")

    result = detect_bb_hybrid(
        image,
        reference_center,
        search_radius=search_radius,
        expected_polarity=ref_polarity,
    ).copy()
    result["qc_version"] = "v3.1_research_reference_width"
    result["reference_sigma"] = ref_sigma
    sigma = result.get("gaussian_sigma")
    result["sigma_ratio_to_reference"] = None
    if sigma is not None and math.isfinite(float(sigma)):
        ratio = float(sigma) / ref_sigma
        result["sigma_ratio_to_reference"] = ratio
        if ratio < min_sigma_ratio or ratio > max_sigma_ratio:
            flags = list(result.get("qc_flags", []))
            flags.append("gaussian_width_changed_vs_trusted_reference")
            result["qc_flags"] = flags
            if result.get("status") != "detection_failed":
                result["status"] = "low_confidence_requires_review"
    return result
