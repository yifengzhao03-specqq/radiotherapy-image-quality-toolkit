import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle


# --------------------------------------------------
# Project paths
# --------------------------------------------------

project_root = Path(__file__).parent
src_path = project_root / "src"

if str(src_path) not in sys.path:
    sys.path.insert(
        0,
        str(src_path)
    )


# --------------------------------------------------
# Project imports
# --------------------------------------------------

from dicom_reader import load_dicom

from roi_selector import (
    select_two_circular_rois
)

from roi_analysis import (
    calculate_circular_roi_statistics,
    calculate_background_subtracted_metrics
)

from visualization import apply_window


# --------------------------------------------------
# DISPLAY SETTINGS
# --------------------------------------------------

# Change these two values to adjust display contrast.

WINDOW_LEVEL = 262139
WINDOW_WIDTH = 2710


# --------------------------------------------------
# Input and output folders
# --------------------------------------------------

test_data_folder = (
    project_root
    / "test_data"
)

output_folder = (
    project_root
    / "output"
)

figure_folder = (
    output_folder
    / "batch_roi_figures"
)

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

figure_folder.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Find DICOM files
# --------------------------------------------------

dicom_files = sorted(
    test_data_folder.glob(
        "*.dcm"
    )
)

if not dicom_files:
    raise FileNotFoundError(
        "No DICOM files were found in test_data."
    )


print(
    "\nRadiotherapy Image Quality Toolkit"
)

print(
    "==================================="
)

print(
    f"Found {len(dicom_files)} DICOM files."
)

print(
    f"Window Level: {WINDOW_LEVEL}"
)

print(
    f"Window Width: {WINDOW_WIDTH}"
)

print(
    "\nEach image requires:"
)

print(
    "1. Target circular ROI"
)

print(
    "2. Background circular ROI"
)


# --------------------------------------------------
# Store results
# --------------------------------------------------

all_results = []


# --------------------------------------------------
# Analyze files
# --------------------------------------------------

for index, file_path in enumerate(
    dicom_files,
    start=1
):

    print(
        "\n==================================="
    )

    print(
        f"Image {index} of {len(dicom_files)}"
    )

    print(
        "File:",
        file_path.name
    )


    # --------------------------------------------------
    # Load DICOM
    # --------------------------------------------------

    ds, image = load_dicom(
        file_path
    )


    print(
        "Image min:",
        f"{image.min():.3f}"
    )

    print(
        "Image max:",
        f"{image.max():.3f}"
    )


    # --------------------------------------------------
    # Select circular ROIs
    # --------------------------------------------------

    print(
        "\nSelect TARGET ROI first, "
        "then BACKGROUND ROI."
    )

    (
        target_circle,
        background_circle
    ) = select_two_circular_rois(
        image,
        window_level=WINDOW_LEVEL,
        window_width=WINDOW_WIDTH
    )


    # --------------------------------------------------
    # Target ROI statistics
    # --------------------------------------------------

    (
        target_mean,
        target_std
    ) = calculate_circular_roi_statistics(
        image,
        target_circle["center_x"],
        target_circle["center_y"],
        target_circle["radius"]
    )


    # --------------------------------------------------
    # Background ROI statistics
    # --------------------------------------------------

    (
        background_mean,
        background_std
    ) = calculate_circular_roi_statistics(
        image,
        background_circle["center_x"],
        background_circle["center_y"],
        background_circle["radius"]
    )


    # --------------------------------------------------
    # Image-quality metrics
    # --------------------------------------------------

    (
        signal_difference,
        background_subtracted_snr,
        cnr
    ) = calculate_background_subtracted_metrics(
        target_mean,
        target_std,
        background_mean,
        background_std
    )


    # --------------------------------------------------
    # Store results
    # --------------------------------------------------

    result = {
        "File":
            file_path.name,

        "Window Level":
            WINDOW_LEVEL,

        "Window Width":
            WINDOW_WIDTH,

        "Target Center X":
            target_circle["center_x"],

        "Target Center Y":
            target_circle["center_y"],

        "Target Radius":
            target_circle["radius"],

        "Target Mean":
            target_mean,

        "Target SD":
            target_std,

        "Background Center X":
            background_circle["center_x"],

        "Background Center Y":
            background_circle["center_y"],

        "Background Radius":
            background_circle["radius"],

        "Background Mean":
            background_mean,

        "Background SD":
            background_std,

        "Signal Difference":
            signal_difference,

        "Background-Subtracted SNR":
            background_subtracted_snr,

        "CNR":
            cnr
    }

    all_results.append(
        result
    )


    # --------------------------------------------------
    # Prepare windowed image for saved figure
    # --------------------------------------------------

    display_image = apply_window(
        image,
        WINDOW_LEVEL,
        WINDOW_WIDTH
    )


    # --------------------------------------------------
    # Save annotated ROI figure
    # --------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(8, 8)
    )

    ax.imshow(
        display_image,
        cmap="gray"
    )


    target_patch = Circle(
        (
            target_circle["center_x"],
            target_circle["center_y"]
        ),
        target_circle["radius"],
        fill=False,
        linewidth=2,
        edgecolor="red"
    )


    background_patch = Circle(
        (
            background_circle["center_x"],
            background_circle["center_y"]
        ),
        background_circle["radius"],
        fill=False,
        linewidth=2,
        edgecolor="blue"
    )


    ax.add_patch(
        target_patch
    )

    ax.add_patch(
        background_patch
    )


    ax.text(
        target_circle["center_x"],
        target_circle["center_y"]
        - target_circle["radius"]
        - 5,
        "Target ROI",
        color="red",
        ha="center"
    )


    ax.text(
        background_circle["center_x"],
        background_circle["center_y"]
        - background_circle["radius"]
        - 5,
        "Background ROI",
        color="blue",
        ha="center"
    )


    ax.set_title(
        f"{file_path.name}\n"
        f"WL={WINDOW_LEVEL}, WW={WINDOW_WIDTH}"
    )

    ax.axis(
        "off"
    )


    figure_path = (
        figure_folder
        / f"{file_path.stem}_roi.png"
    )


    fig.savefig(
        figure_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(
        fig
    )


    # --------------------------------------------------
    # Print current result
    # --------------------------------------------------

    print(
        "\nSignal Difference:",
        f"{signal_difference:.3f}"
    )

    print(
        "Background-Subtracted SNR:",
        f"{background_subtracted_snr:.3f}"
    )

    print(
        "CNR:",
        f"{cnr:.3f}"
    )

    print(
        "Saved ROI figure:",
        figure_path.name
    )


# --------------------------------------------------
# Save all results
# --------------------------------------------------

results_df = pd.DataFrame(
    all_results
)


csv_path = (
    output_folder
    / "batch_phantom_results.csv"
)


results_df.to_csv(
    csv_path,
    index=False
)


# --------------------------------------------------
# Final summary
# --------------------------------------------------

print(
    "\n==================================="
)

print(
    "BATCH ANALYSIS COMPLETE"
)

print(
    "==================================="
)

print(
    f"Analyzed {len(results_df)} images."
)

print(
    "\nResults saved to:"
)

print(
    csv_path
)

print(
    "\nROI figures saved to:"
)

print(
    figure_folder
)