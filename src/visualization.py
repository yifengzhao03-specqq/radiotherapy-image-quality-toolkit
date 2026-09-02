import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def apply_window(
    image,
    window_level,
    window_width
):
    """
    Apply window level and window width for visualization only.

    Parameters
    ----------
    image : numpy.ndarray
        Original image used for quantitative analysis.

    window_level : float
        Center of the display window.

    window_width : float
        Width of the display window.

    Returns
    -------
    numpy.ndarray
        Windowed image for display.
    """

    if window_width <= 0:
        raise ValueError(
            "window_width must be greater than 0."
        )

    lower = window_level - window_width / 2
    upper = window_level + window_width / 2

    display_image = np.clip(
        image,
        lower,
        upper
    )

    return display_image


def show_dicom_image(
    image,
    title="DICOM Image",
    window_level=None,
    window_width=None
):
    """
    Display a grayscale DICOM image.

    Optional window level and window width are used
    for visualization only.
    """

    if (
        window_level is not None
        and window_width is not None
    ):
        display_image = apply_window(
            image,
            window_level,
            window_width
        )
    else:
        display_image = image

    plt.figure(
        figsize=(8, 8)
    )

    plt.imshow(
        display_image,
        cmap="gray"
    )

    plt.title(
        title
    )

    plt.axis(
        "off"
    )

    plt.show()


def show_roi(
    image,
    x1,
    x2,
    y1,
    y2,
    label="ROI",
    window_level=None,
    window_width=None
):
    """
    Display a rectangular ROI on a DICOM image.
    """

    if (
        window_level is not None
        and window_width is not None
    ):
        display_image = apply_window(
            image,
            window_level,
            window_width
        )
    else:
        display_image = image

    fig, ax = plt.subplots(
        figsize=(8, 8)
    )

    ax.imshow(
        display_image,
        cmap="gray"
    )

    rect = patches.Rectangle(
        (x1, y1),
        x2 - x1,
        y2 - y1,
        linewidth=2,
        edgecolor="red",
        facecolor="none"
    )

    ax.add_patch(
        rect
    )

    ax.text(
        x1,
        y1 - 3,
        label,
        color="red"
    )

    ax.set_title(
        f"DICOM Image with {label}"
    )

    ax.axis(
        "off"
    )

    plt.show()


def show_two_rois(
    image,
    target_coords,
    background_coords,
    window_level=None,
    window_width=None
):
    """
    Display target and background rectangular ROIs
    on the same image.
    """

    if (
        window_level is not None
        and window_width is not None
    ):
        display_image = apply_window(
            image,
            window_level,
            window_width
        )
    else:
        display_image = image

    fig, ax = plt.subplots(
        figsize=(8, 8)
    )

    ax.imshow(
        display_image,
        cmap="gray"
    )

    tx1, tx2, ty1, ty2 = target_coords
    bx1, bx2, by1, by2 = background_coords

    target_rect = patches.Rectangle(
        (tx1, ty1),
        tx2 - tx1,
        ty2 - ty1,
        linewidth=2,
        edgecolor="red",
        facecolor="none"
    )

    background_rect = patches.Rectangle(
        (bx1, by1),
        bx2 - bx1,
        by2 - by1,
        linewidth=2,
        edgecolor="blue",
        facecolor="none"
    )

    ax.add_patch(
        target_rect
    )

    ax.add_patch(
        background_rect
    )

    ax.text(
        tx1,
        ty1 - 3,
        "Target ROI",
        color="red"
    )

    ax.text(
        bx1,
        by1 - 3,
        "Background ROI",
        color="blue"
    )

    ax.set_title(
        "Target and Background ROIs"
    )

    ax.axis(
        "off"
    )

    plt.show()