import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector, EllipseSelector


def select_rectangular_roi(image):
    """
    Interactively select a rectangular ROI.

    Returns
    -------
    selected_rois : list
        List of ROI coordinate tuples in the form:
        (x1, x2, y1, y2)
    """

    selected_rois = []

    fig, ax = plt.subplots()
    ax.imshow(image, cmap="gray")
    ax.set_title("Draw a rectangular ROI")

    def onselect(eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        coords = (
            int(min(x1, x2)),
            int(max(x1, x2)),
            int(min(y1, y2)),
            int(max(y1, y2))
        )

        selected_rois.append(coords)

        print("Selected rectangular ROI:", coords)

    selector = RectangleSelector(
        ax,
        onselect,
        useblit=True,
        button=[1],
        interactive=True
    )

    plt.show()

    return selected_rois


def select_circular_roi(image):
    """
    Interactively select a circular ROI.

    Returns
    -------
    selected_circles : list
        Each circle is stored as a dictionary containing:
        center_x, center_y, and radius.
    """

    selected_circles = []

    fig, ax = plt.subplots()
    ax.imshow(image, cmap="gray")
    ax.set_title("Draw a circular ROI")

    def onselect(eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        radius_x = abs(x2 - x1) / 2
        radius_y = abs(y2 - y1) / 2

        radius = min(radius_x, radius_y)

        circle = {
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius
        }

        selected_circles.append(circle)

        print(
            f"Selected circular ROI: "
            f"center=({center_x:.1f}, {center_y:.1f}), "
            f"radius={radius:.1f}"
        )

    selector = EllipseSelector(
        ax,
        onselect,
        useblit=True,
        button=[1],
        interactive=True
    )

    plt.show()

    return selected_circles