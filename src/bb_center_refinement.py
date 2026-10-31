"""Experimental, reference-guided BB-center refinement for 2D DICOM pixels.

This module deliberately does not require a manual mark on the test image.
Use only with same-phantom images with compatible imaging geometry.
No detection is automatically approved for quantitative/clinical use.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares


def _region(image: np.ndarray, expected_center: tuple[float, float], radius: float):
    arr = np.asarray(image, dtype=np.float64)
    if arr.ndim != 2 or not np.isfinite(arr).all():
        raise ValueError("Expected a finite, 2D image array")
    cx, cy = map(float, expected_center)
    r = float(radius)
    if not np.isfinite(cx + cy + r) or r <= 0:
        raise ValueError("Invalid expected center / radius")
    if cx - r - 2 < 0 or cy - r - 2 < 0 or cx + r + 2 >= arr.shape[1] or cy + r + 2 >= arr.shape[0]:
        raise ValueError("BB search region is too close to image boundary")
    x1, x2 = int(np.floor(cx-r-1)), int(np.ceil(cx+r+1))+1
    y1, y2 = int(np.floor(cy-r-1)), int(np.ceil(cy+r+1))+1
    yy, xx = np.mgrid[y1:y2, x1:x2]
    z = arr[y1:y2, x1:x2]
    d = np.hypot(xx-cx, yy-cy)
    return xx.astype(float), yy.astype(float), z, d, cx, cy


def _plane(z, xx, yy, cx, cy, mask):
    if np.count_nonzero(mask) < 30:
        raise ValueError("Not enough background pixels for a plane fit")
    a = np.column_stack((np.ones(mask.sum()), (xx-cx)[mask], (yy-cy)[mask]))
    coeff = np.linalg.lstsq(a, z[mask], rcond=None)[0]
    plane = coeff[0] + coeff[1]*(xx-cx) + coeff[2]*(yy-cy)
    return plane, coeff


def centroid_refinement(
    image: np.ndarray,
    expected_center: tuple[float, float],
    target_radius: float = 10.0,
    background_outer_radius: float = 18.0,
) -> dict:
    """Compute a local-background-corrected positive/negative blob centroid.

    A plane is fitted to an annulus [target_radius+2, background_outer_radius]
    around the *reference-image expected center*. The annulus MUST avoid
    nearby structures for this approximation to be meaningful.
    """
    if target_radius < 3 or background_outer_radius <= target_radius + 4:
        raise ValueError("Require target_radius >=3, outer_radius > target_radius+4")
    xx, yy, z, d, cx, cy = _region(image, expected_center, background_outer_radius)
    annulus = (d >= target_radius + 2) & (d <= background_outer_radius)
    plane, _ = _plane(z, xx, yy, cx, cy, annulus)
    residual = z - plane
    center_mask = d <= min(4.0, target_radius / 2.0)
    polarity_sign = 1.0 if float(np.median(residual[center_mask])) >= 0 else -1.0
    weights = np.where(d <= target_radius, np.maximum(polarity_sign*residual, 0.0), 0.0)
    total = float(weights.sum())
    if total <= 1e-10:
        raise ValueError("BB-like signal not detected in expected region")
    center_x = float((xx*weights).sum()/total)
    center_y = float((yy*weights).sum()/total)
    annulus_sigma = float(np.std(residual[annulus]))
    local_signal = float(np.median(polarity_sign*residual[center_mask]))
    return {
        "center_x": center_x, "center_y": center_y,
        "polarity": "bright" if polarity_sign > 0 else "dark",
        "local_signal": local_signal,
        "background_sd": annulus_sigma,
        "status": "candidate_requires_review",
        "method": "plane_corrected_centroid",
    }


def gaussian_refinement(
    image: np.ndarray,
    expected_center: tuple[float, float],
    fit_radius: float = 18.0,
) -> dict:
    """Fit circular 2D Gaussian + sloping background to nearby image data.

    Note: BB projections are not truly Gaussian; this is an empirical model.
    Report the fit residual and do not infer absolute center accuracy from it.
    """
    if fit_radius < 9:
        raise ValueError("fit_radius must be >= 9")
    xx, yy, z, d, cx, cy = _region(image, expected_center, fit_radius)
    m = d <= fit_radius
    x, y, values = xx[m], yy[m], z[m]
    border = (d[m] >= fit_radius - 3)
    background = float(np.median(values[border]))
    core = values[((x-cx)**2+(y-cy)**2) <= 9]
    amplitude = float(np.median(core) - background)
    if abs(amplitude) < 1e-8:
        raise ValueError("No obvious central signal above background")
    initial = [cx, cy, 5.0, np.clip(amplitude, -15000, 15000), background, 0.0, 0.0]
    lower = [cx-7, cy-7, 1.5, -15000, float(values.min())-20000, -1000, -1000]
    upper = [cx+7, cy+7, 13.0, 15000, float(values.max())+20000, 1000, 1000]
    def fitted(p):
        bx, by, sigma, amp, offset, slope_x, slope_y = p
        return offset + slope_x*(x-cx) + slope_y*(y-cy) + amp * np.exp(
            -0.5 * ((x-bx)**2 + (y-by)**2)/sigma**2
        )
    result = least_squares(lambda p: fitted(p)-values, initial,
                           bounds=(lower, upper), max_nfev=1500)
    if not result.success:
        raise ValueError(f"Gaussian optimizer failed: {result.message}")
    bx, by, sigma, amp, *_ = result.x
    rms = float(np.sqrt(np.mean(result.fun**2)))
    return {
        "center_x": float(bx), "center_y": float(by),
        "polarity": "bright" if amp > 0 else "dark",
        "sigma": float(sigma), "amplitude": float(amp),
        "fit_rms": rms,
        "status": "candidate_requires_review",
        "method": "gaussian_plus_plane",
    }
