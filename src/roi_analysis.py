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
def summarize_analysis(
    image,
    target_coords,
    background_coords
):
    """
    Return a summary of target/background ROI statistics,
    SNR, and CNR.
    """

    tx1, tx2, ty1, ty2 = target_coords
    bx1, bx2, by1, by2 = background_coords

    target_mean, target_std = calculate_roi_statistics(
        image, tx1, tx2, ty1, ty2
    )

    background_mean, background_std = calculate_roi_statistics(
        image, bx1, bx2, by1, by2
    )

    snr = calculate_snr(
        image, tx1, tx2, ty1, ty2
    )

    cnr = calculate_cnr(
        image,
        target_coords,
        background_coords
    )

    return {
        "Target Mean": target_mean,
        "Target SD": target_std,
        "Background Mean": background_mean,
        "Background SD": background_std,
        "SNR": snr,
        "CNR": cnr
    }

def calculate_circular_roi_statistics(
    image,
    center_x,
    center_y,
    radius
):
    """
    Calculate mean and standard deviation inside a circular ROI.
    """

    y, x = np.ogrid[
        :image.shape[0],
        :image.shape[1]
    ]

    mask = (
        (x - center_x) ** 2
        + (y - center_y) ** 2
    ) <= radius ** 2

    roi_pixels = image[mask]

    mean = np.mean(roi_pixels)
    std = np.std(roi_pixels)

    return mean, std

def calculate_background_subtracted_metrics(
    target_mean,
    target_std,
    background_mean,
    background_std
):
    """
    Calculate signal difference, background-subtracted SNR,
    and CNR.

    Background-subtracted SNR:
        |target_mean - background_mean| / target_std

    CNR:
        |target_mean - background_mean| / background_std
    """

    signal_difference = abs(
        target_mean - background_mean
    )

    if target_std != 0:
        background_subtracted_snr = (
            signal_difference / target_std
        )
    else:
        background_subtracted_snr = float("nan")

    if background_std != 0:
        cnr = (
            signal_difference / background_std
        )
    else:
        cnr = float("nan")

    return (
        signal_difference,
        background_subtracted_snr,
        cnr
    )