import numpy as np


def calculate_roi_statistics(image, x1, x2, y1, y2):
    """
    Calculate mean and standard deviation within a rectangular ROI.
    """
    roi = image[y1:y2, x1:x2]

    mean = np.mean(roi)
    std = np.std(roi)

    return mean, std


def calculate_snr(image, x1, x2, y1, y2):
    """
    Calculate SNR using mean / standard deviation.
    """
    mean, std = calculate_roi_statistics(
        image, x1, x2, y1, y2
    )

    if std == 0:
        return np.nan

    return mean / std


def calculate_cnr(
    image,
    target_coords,
    background_coords
):
    """
    Calculate CNR between a target ROI and background ROI.
    """

    tx1, tx2, ty1, ty2 = target_coords
    bx1, bx2, by1, by2 = background_coords

    target_mean, _ = calculate_roi_statistics(
        image, tx1, tx2, ty1, ty2
    )

    background_mean, background_std = calculate_roi_statistics(
        image, bx1, bx2, by1, by2
    )

    if background_std == 0:
        return np.nan

    cnr = abs(target_mean - background_mean) / background_std

    return cnr