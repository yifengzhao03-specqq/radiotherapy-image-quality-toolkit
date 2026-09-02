import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from visualization import apply_window


def select_circular_roi(
    image,
    window_level=None,
    window_width=None
):
    """
    Select one circular ROI using two mouse clicks.

    First click:
        ROI center

    Second click:
        ROI boundary

    Returns
    -------
    dict
        center_x, center_y, radius
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

    ax.set_title(
        "Circular ROI Selection\n"
        "Click ROI center, then click ROI boundary"
    )

    ax.axis(
        "off"
    )

    points = plt.ginput(
        2,
        timeout=-1
    )

    if len(points) != 2:
        plt.close(
            fig
        )

        raise RuntimeError(
            "Two points are required to define the circular ROI."
        )

    center_x, center_y = points[0]
    edge_x, edge_y = points[1]

    radius = np.sqrt(
        (edge_x - center_x) ** 2
        + (edge_y - center_y) ** 2
    )

    circle_patch = Circle(
        (center_x, center_y),
        radius,
        fill=False,
        linewidth=2,
        edgecolor="red"
    )

    ax.add_patch(
        circle_patch
    )

    ax.set_title(
        f"Circular ROI\n"
        f"Center = ({center_x:.1f}, {center_y:.1f}), "
        f"Radius = {radius:.1f} px"
    )

    fig.canvas.draw()

    plt.pause(
        1.5
    )

    plt.close(
        fig
    )

    return {
        "center_x": center_x,
        "center_y": center_y,
        "radius": radius
    }


def select_two_circular_rois(
    image,
    window_level=None,
    window_width=None
):
    """
    Select target and background circular ROIs
    on the same image.

    First:
        Target center + boundary

    Second:
        Background center + boundary

    Returns
    -------
    target_circle : dict
    background_circle : dict
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

    ax.axis(
        "off"
    )

    # --------------------------------------------------
    # Target ROI
    # --------------------------------------------------

    ax.set_title(
        "Select TARGET ROI\n"
        "Click center, then click boundary"
    )

    fig.canvas.draw()

    target_points = plt.ginput(
        2,
        timeout=-1
    )

    if len(target_points) != 2:
        plt.close(
            fig
        )

        raise RuntimeError(
            "Two points are required for the target ROI."
        )

    target_center_x, target_center_y = (
        target_points[0]
    )

    target_edge_x, target_edge_y = (
        target_points[1]
    )

    target_radius = np.sqrt(
        (
            target_edge_x
            - target_center_x
        ) ** 2
        +
        (
            target_edge_y
            - target_center_y
        ) ** 2
    )

    target_circle = {
        "center_x":
            target_center_x,

        "center_y":
            target_center_y,

        "radius":
            target_radius
    }

    target_patch = Circle(
        (
            target_center_x,
            target_center_y
        ),
        target_radius,
        fill=False,
        linewidth=2,
        edgecolor="red"
    )

    ax.add_patch(
        target_patch
    )

    ax.text(
        target_center_x,
        target_center_y
        - target_radius
        - 5,
        "Target ROI",
        color="red",
        ha="center"
    )

    fig.canvas.draw()


    # --------------------------------------------------
    # Background ROI
    # --------------------------------------------------

    ax.set_title(
        "Select BACKGROUND ROI\n"
        "Click center, then click boundary"
    )

    fig.canvas.draw()

    background_points = plt.ginput(
        2,
        timeout=-1
    )

    if len(background_points) != 2:
        plt.close(
            fig
        )

        raise RuntimeError(
            "Two points are required for the background ROI."
        )

    (
        background_center_x,
        background_center_y
    ) = background_points[0]

    (
        background_edge_x,
        background_edge_y
    ) = background_points[1]

    background_radius = np.sqrt(
        (
            background_edge_x
            - background_center_x
        ) ** 2
        +
        (
            background_edge_y
            - background_center_y
        ) ** 2
    )

    background_circle = {
        "center_x":
            background_center_x,

        "center_y":
            background_center_y,

        "radius":
            background_radius
    }

    background_patch = Circle(
        (
            background_center_x,
            background_center_y
        ),
        background_radius,
        fill=False,
        linewidth=2,
        edgecolor="blue"
    )

    ax.add_patch(
        background_patch
    )

    ax.text(
        background_center_x,
        background_center_y
        - background_radius
        - 5,
        "Background ROI",
        color="blue",
        ha="center"
    )

    ax.set_title(
        "Selected Circular ROIs"
    )

    fig.canvas.draw()

    plt.pause(
        2
    )

    plt.close(
        fig
    )

    return (
        target_circle,
        background_circle
    )