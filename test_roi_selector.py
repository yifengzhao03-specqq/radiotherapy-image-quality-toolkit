import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd


# --------------------------------------------------
# Project paths
# --------------------------------------------------

project_root = Path(__file__).parent
src_path = project_root / "src"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# --------------------------------------------------
# Project imports
# --------------------------------------------------

from dicom_reader import load_dicom

from roi_selector import select_two_circular_rois

from roi_analysis import (
    calculate_circular_roi_statistics,
    calculate_background_subtracted_metrics
)

from visualization import apply_window


# --------------------------------------------------
# Display settings
# --------------------------------------------------

WINDOW_LEVEL = 262139
WINDOW_WIDTH = 2710


# --------------------------------------------------
# Locate phantom DICOM files
# --------------------------------------------------

test_data_folder = project_root / "test_data"

dicom_files = sorted(
    test_data_folder.glob("*.dcm")
)

if not dicom_files:
    raise FileNotFoundError(
        "No DICOM files were found in test_data."
    )


# --------------------------------------------------
# Load first phantom DICOM
# --------------------------------------------------

example_file = dicom_files[0]

print("\nRadiotherapy Image Quality Toolkit")
print("----------------------------------")
print("Loading:", example_file.name)

ds, image = load_dicom(
    example_file
)


# --------------------------------------------------
# Print DICOM intensity information
# --------------------------------------------------

print("\nDICOM Intensity Information")
print("-----------------------------------")

print(
    "Modality:",
    getattr(ds, "Modality", "Unknown")
)

print(
    "Rescale Slope:",
    getattr(ds, "RescaleSlope", "Not present")
)

print(
    "Rescale Intercept:",
    getattr(ds, "RescaleIntercept", "Not present")
)

print(
    "Bits Stored:",
    getattr(ds, "BitsStored", "Unknown")
)

print(
    "Pixel Representation:",
    getattr(ds, "PixelRepresentation", "Unknown")
)

print(
    "Image Min:",
    image.min()
)

print(
    "Image Max:",
    image.max()
)


# --------------------------------------------------
# Print display settings
# --------------------------------------------------

print("\nDisplay Settings")
print("-----------------------------------")

print(
    "Window Level:",
    WINDOW_LEVEL
)

print(
    "Window Width:",
    WINDOW_WIDTH
)


# --------------------------------------------------
# Select Target + Background ROIs
# --------------------------------------------------

print(
    "\nSelect TARGET ROI first, "
    "then BACKGROUND ROI."
)

target_circle, background_circle = (
    select_two_circular_rois(
        image,
        window_level=WINDOW_LEVEL,
        window_width=WINDOW_WIDTH
    )
)


# --------------------------------------------------
# Calculate Target ROI statistics
# --------------------------------------------------

target_mean, target_std = (
    calculate_circular_roi_statistics(
        image,
        target_circle["center_x"],
        target_circle["center_y"],
        target_circle["radius"]
    )
)


# --------------------------------------------------
# Calculate Background ROI statistics
# --------------------------------------------------

background_mean, background_std = (
    calculate_circular_roi_statistics(
        image,
        background_circle["center_x"],
        background_circle["center_y"],
        background_circle["radius"]
    )
)


# --------------------------------------------------
# Calculate image-quality metrics
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
# Print results
# --------------------------------------------------

print("\n===================================")
print("CIRCULAR ROI ANALYSIS RESULTS")
print("===================================")


print("\nTarget ROI")
print("-----------------------------------")

print(
    "Center:",
    f"({target_circle['center_x']:.2f}, "
    f"{target_circle['center_y']:.2f})"
)

print(
    "Radius:",
    f"{target_circle['radius']:.2f} px"
)

print(
    "Mean:",
    f"{target_mean:.3f}"
)

print(
    "SD:",
    f"{target_std:.3f}"
)


print("\nBackground ROI")
print("-----------------------------------")

print(
    "Center:",
    f"({background_circle['center_x']:.2f}, "
    f"{background_circle['center_y']:.2f})"
)

print(
    "Radius:",
    f"{background_circle['radius']:.2f} px"
)

print(
    "Mean:",
    f"{background_mean:.3f}"
)

print(
    "SD:",
    f"{background_std:.3f}"
)


print("\nImage Quality Metrics")
print("-----------------------------------")

print(
    "Signal Difference:",
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


# --------------------------------------------------
# Create output folder
# --------------------------------------------------

output_folder = project_root / "output"

output_folder.mkdir(
    parents=True,
    exist_ok=True
)

print("\nOutput folder:")
print(output_folder)


# --------------------------------------------------
# Apply WL / WW for exported figure
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
    f"Phantom Circular ROI Analysis\n"
    f"WL={WINDOW_LEVEL}, WW={WINDOW_WIDTH}"
)

ax.axis(
    "off"
)


figure_path = (
    output_folder
    / "phantom_roi_analysis.png"
)


fig.savefig(
    figure_path,
    dpi=300,
    bbox_inches="tight"
)

plt.close(
    fig
)


print("\nSaved ROI figure:")
print(figure_path)


# --------------------------------------------------
# Save analysis results to CSV
# --------------------------------------------------

results = {
    "File":
        example_file.name,

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


results_df = pd.DataFrame(
    [results]
)


csv_path = (
    output_folder
    / "phantom_roi_results.csv"
)


results_df.to_csv(
    csv_path,
    index=False
)


print("\nSaved CSV results:")
print(csv_path)

print(
    "\nAnalysis and file export complete."
)