"""Initial translation-only registration for matched 2D phantom images.

All measurements should be computed on the original image arrays, not on
interpolated/resampled images. This module estimates ROI-coordinate shifts.
"""

import numpy as np
from skimage.registration import phase_cross_correlation


def _normalize(image):
    """Robust display-independent normalization for registration only."""
    array = np.asarray(image, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError("Only 2D images are supported in this first version.")
    if not np.isfinite(array).all():
        raise ValueError("Image contains NaN or infinite values.")
    low, high = np.percentile(array, [1, 99])
    if high <= low:
        raise ValueError("Image has insufficient intensity variation.")
    return np.clip((array - low) / (high - low), 0, 1)


def estimate_translation(reference_image, moving_image, upsample_factor=10):
    """Estimate reference -> moving ROI displacement in pixels.

    Returns (dx, dy), where positive dx is rightward and positive dy is
    downward in array/image coordinates. Both images must have the same
    shape and image orientation. This is translation-only registration.

    Important: phase_cross_correlation's native shift moves *moving* into
    *reference* coordinates, so we negate it to transfer reference ROIs
    into moving-image coordinates.
    """
    reference = _normalize(reference_image)
    moving = _normalize(moving_image)
    if reference.shape != moving.shape:
        raise ValueError(
            f"Images have different shapes: {reference.shape} vs {moving.shape}. "
            "Use same-size, same-geometry phantom images for this test."
        )
    shift_to_align, _, _ = phase_cross_correlation(
        reference, moving, upsample_factor=upsample_factor
    )
    dy, dx = -float(shift_to_align[0]), -float(shift_to_align[1])
    return dx, dy
