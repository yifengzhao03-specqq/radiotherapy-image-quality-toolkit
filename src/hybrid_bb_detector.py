"""Experimental coarse-to-fine BB localization for 2D DICOM pixel arrays.

Stage 1: reference-guided DoG response peak, from ``bb_detector.detect_bb``.
Stage 2: 2D Gaussian + sloping background fitted near that DoG candidate,
         from ``bb_center_refinement.gaussian_refinement``.
Stage 3: heuristic QC; NO results are clinically validated or auto-approved.

Expected coordinates (x, y) are an approximate same-phantom, same-geometry
reference and are NOT the held-out test-image manual labels.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from bb_detector import detect_bb
from bb_center_refinement import gaussian_refinement


def detect_bb_hybrid(
    image: np.ndarray,
    expected_center: tuple[float, float],
    search_radius: int = 18,
    *,
    expected_polarity: str | None = None,
    max_relative_fit_rms: float = 0.25,
    min_sigma: float = 2.5,
    max_sigma: float = 10.0,
    max_coarse_refined_gap: float = 7.2,
) -> dict[str, Any]:
    """Detect a local BB candidate and refine its center via Gaussian fitting.

    Returns a structured result with ``status``:
      * candidate_requires_review: passed *heuristic* QC, NOT validated/approved
      * low_confidence_requires_review: localized, but one or more flags raised
      * detection_failed: no reliable estimate could be calculated

    ``expected_polarity`` may be 'bright', 'dark', or None. When supplied,
    mismatching polarity is flagged instead of automatically accepted.
    The heuristic limits were chosen for initial research tests; they must be
    recalibrated before use on other phantoms / imaging systems.
    """
    if expected_polarity not in (None, "bright", "dark"):
        raise ValueError("expected_polarity must be None, 'bright', or 'dark'")
    if not (0 < max_relative_fit_rms < 10):
        raise ValueError("max_relative_fit_rms must be positive")
    if not (1.5 < min_sigma < max_sigma < 13.0):
        raise ValueError("sigma QC bounds must satisfy 1.5 < min < max < 13")
    if not (0 < max_coarse_refined_gap <= 10):
        raise ValueError("invalid max_coarse_refined_gap")

    output: dict[str, Any] = {
        "method": "dog_plus_gaussian_v3",
        "status": "detection_failed",
        "qc_flags": [],
        "coarse_x": None, "coarse_y": None,
        "center_x": None, "center_y": None,
        "dog_polarity": None, "dog_score": None,
        "gaussian_polarity": None, "gaussian_sigma": None,
        "gaussian_amplitude": None, "fit_rms": None,
        "relative_fit_rms": None, "coarse_refined_gap": None,
    }
    expected = (float(expected_center[0]), float(expected_center[1]))
    array = np.asarray(image, dtype=np.float64)
    if array.ndim != 2 or not np.isfinite(array).all():
        output["qc_flags"].append("invalid_image")
        return output
    if not all(math.isfinite(v) for v in expected):
        output["qc_flags"].append("invalid_reference_center")
        return output

    try:
        coarse = detect_bb(array, expected, search_radius=search_radius)
        cx = float(coarse["center_x"])
        cy = float(coarse["center_y"])
        output.update({
            "coarse_x": cx, "coarse_y": cy,
            "dog_polarity": coarse["polarity"],
            "dog_score": float(coarse["contrast_score"]),
        })
    except (ValueError, RuntimeError, OverflowError) as exc:
        output["qc_flags"].append(f"coarse_detection_failed:{exc}")
        return output

    flags: list[str] = []
    if coarse["status"] != "candidate_requires_review":
        flags.append("weak_dog_response")
    if expected_polarity is not None and coarse["polarity"] != expected_polarity:
        flags.append("unexpected_dog_polarity")

    # The coarse peak can be ~5 px away from the true BB center on this data.
    # Thus, re-center the Gaussian's *entire fit region* on the new candidate,
    # instead of fitting around the unchanged original reference coordinates.
    try:
        refined = gaussian_refinement(array, (cx, cy))
        rx = float(refined["center_x"])
        ry = float(refined["center_y"])
        sigma = float(refined["sigma"])
        amplitude = float(refined["amplitude"])
        rms = float(refined["fit_rms"])
        relative_rms = rms / max(abs(amplitude), 1e-12)
        gap = math.hypot(rx - cx, ry - cy)
        output.update({
            "center_x": rx, "center_y": ry,
            "gaussian_polarity": refined["polarity"],
            "gaussian_sigma": sigma, "gaussian_amplitude": amplitude,
            "fit_rms": rms, "relative_fit_rms": relative_rms,
            "coarse_refined_gap": gap,
        })
    except (ValueError, RuntimeError, OverflowError) as exc:
        output["qc_flags"].append(f"gaussian_refinement_failed:{exc}")
        return output

    if not all(math.isfinite(v) for v in (rx, ry, sigma, amplitude, rms, relative_rms, gap)):
        output["qc_flags"].append("nonfinite_gaussian_result")
        output["center_x"] = output["center_y"] = None
        return output
    if refined["polarity"] != coarse["polarity"]:
        flags.append("coarse_refined_polarity_mismatch")
    if expected_polarity is not None and refined["polarity"] != expected_polarity:
        flags.append("unexpected_gaussian_polarity")
    if not min_sigma <= sigma <= max_sigma:
        flags.append("sigma_out_of_expected_range")
    if relative_rms > max_relative_fit_rms:
        flags.append("high_relative_fit_residual")
    if gap > max_coarse_refined_gap:
        flags.append("large_coarse_refined_disagreement")
    # Candidates extremely close to a hard search boundary may be clipped.
    if math.hypot(cx - expected[0], cy - expected[1]) > search_radius - 1.0:
        flags.append("coarse_at_search_boundary")

    output["qc_flags"] = flags
    output["status"] = (
        "low_confidence_requires_review" if flags else "candidate_requires_review"
    )
    return output
