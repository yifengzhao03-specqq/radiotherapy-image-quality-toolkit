import matplotlib.pyplot as plt
import matplotlib.patches as patches


def show_dicom_image(image, title="DICOM Image"):
    """
    Display a grayscale DICOM image.
    """
    plt.imshow(image, cmap="gray")
    plt.title(title)
    plt.axis("off")
    plt.show()


def show_roi(image, x1, x2, y1, y2, label="ROI"):
    """
    Display an image with a rectangular ROI.
    """
    fig, ax = plt.subplots()

    ax.imshow(image, cmap="gray")

    rect = patches.Rectangle(
        (x1, y1),
        x2 - x1,
        y2 - y1,
        linewidth=2,
        edgecolor="red",
        facecolor="none"
    )

    ax.add_patch(rect)
    ax.text(x1, y1 - 3, label, color="red")

    ax.set_title(f"DICOM Image with {label}")
    ax.axis("off")

    plt.show()


def show_two_rois(image, target_coords, background_coords):
    """
    Display target and background ROIs on the same image.
    """
    fig, ax = plt.subplots()

    ax.imshow(image, cmap="gray")

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

    ax.add_patch(target_rect)
    ax.add_patch(background_rect)

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

    ax.set_title("Target and Background ROIs")
    ax.axis("off")

    plt.show()