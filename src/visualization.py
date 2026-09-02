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
        fill=False
    )

    ax.add_patch(rect)
    ax.text(x1, y1 - 3, label)

    ax.set_title(f"DICOM Image with {label}")
    ax.axis("off")

    plt.show()