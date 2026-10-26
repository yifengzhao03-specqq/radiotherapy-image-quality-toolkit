"""Reference-guided metal ball-bearing (BB) localization for 2D phantom images.

This is an experimental *local* detector, not a full-image phantom detector.
A manually identified reference-image BB center supplies the approximate
search location. Detection is performed on quantitative DICOM pixel data,
not WL/WW-windowed display pixels.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter


def _parabolic_offset(y_minus: float, y_zero: float, y_plus: float) -> float:
    """Return subpixel peak offset, clipped to +/-0.5 px."""
    denom = y_minus - 2.0 * y_zero + y_plus
    if abs(denom) < 1e-12 or denom >= 0:
        return 0.0
    offset = 0.5 * (y_minus - y_plus) / denom
    return float(np.clip(offset, -0.5, 0.5))


def detect_bb(
    image: np.ndarray,
    expected_center: tuple[float, float],
    search_radius: int = 18,
    sigma_small: float = 1.8,
    sigma_large: float = 5.5,
) -> dict:
    """Find the strongest BB-like bright/dark blob near a reference center.

    Parameters
    ----------
    image:
        2D DICOM image pixel values, before display windowing.
    expected_center:
        Approximate (x, y) from a manually selected reference image.
    search_radius:
        Maximum displacement from the reference center in pixels.

    Returns
    -------
    Dictionary with predicted center, polarity, contrast score and review flag.

    Notes
    -----
    A difference-of-Gaussians favors compact structures over slow-varying
    tissue/bone intensity. The strongest response is only a *candidate*;
    bones and artifacts may also create bright/dark blobs. Always inspect the
    overlay and compare with held-out manual selections before batch analysis.
    """
    array = np.asarray(image, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"Expected a 2D image; got shape {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError("Image contains NaN/Inf. Review image before detection.")
    if search_radius < 3:
        raise ValueError("search_radius must be >= 3 pixels")
    if not (0 < sigma_small < sigma_large):
        raise ValueError("Require 0 < sigma_small < sigma_large")

    x0, y0 = (float(expected_center[0]), float(expected_center[1]))
    height, width = array.shape
    if not (0 <= x0 < width and 0 <= y0 < height):
        raise ValueError("Expected BB center is outside the DICOM image")

    # Filter a small crop to reduce computation and prevent distant structures
    # from affecting the candidate. Padding reduces Gaussian edge artifacts.
    pad = int(np.ceil(4 * sigma_large)) + 3
    x1 = max(0, int(np.floor(x0 - search_radius - pad)))
    x2 = min(width, int(np.ceil(x0 + search_radius + pad)) + 1)
    y1 = max(0, int(np.floor(y0 - search_radius - pad)))
    y2 = min(height, int(np.ceil(y0 + search_radius + pad)) + 1)
    crop = array[y1:y2, x1:x2]
    small = gaussian_filter(crop, sigma=sigma_small, mode="reflect")
    large = gaussian_filter(crop, sigma=sigma_large, mode="reflect")
    dog = small - large

    yy, xx = np.indices(crop.shape)
    search_mask = (xx + x1 - x0) ** 2 + (yy + y1 - y0) ** 2 <= search_radius ** 2
    # Require a one-pixel border for subpixel interpolation.
    search_mask[0, :] = False
    search_mask[-1, :] = False
    search_mask[:, 0] = False
    search_mask[:, -1] = False
    if not np.any(search_mask):
        raise ValueError("Search area is too close to the image boundary")

    response = np.abs(dog)
    response[~search_mask] = -np.inf
    py, px = np.unravel_index(int(np.argmax(response)), response.shape)
    polarity = "bright" if dog[py, px] >= 0 else "dark"
    sign = 1.0 if polarity == "bright" else -1.0
    signed_dog = dog * sign

    dx = _parabolic_offset(signed_dog[py, px - 1], signed_dog[py, px], signed_dog[py, px + 1])
    dy = _parabolic_offset(signed_dog[py - 1, px], signed_dog[py, px], signed_dog[py + 1, px])
    detected_x = float(x1 + px + dx)
    detected_y = float(y1 + py + dy)

    # A descriptive, local response/noise ratio; NOT a calibrated probability.
    valid = dog[search_mask]
    med = float(np.median(valid))
    robust_noise = 1.4826 * float(np.median(np.abs(valid - med)))
    score = float(abs(dog[py, px]) / max(robust_noise, 1e-9))
    # Even high-score detections require review on real images.
    status = "candidate_requires_review" if score >= 3.0 else "low_contrast_requires_review"

    return {
        "center_x": detected_x,
        "center_y": detected_y,
        "polarity": polarity,
        "contrast_score": score,
        "status": status,
        "expected_x": x0,
        "expected_y": y0,
        "search_radius": int(search_radius),
    }
