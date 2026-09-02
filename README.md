# Radiotherapy Image Quality Toolkit

A Python-based toolkit for quantitative analysis and visualization of DICOM images, with a focus on radiotherapy and phantom image-quality assessment.

The project provides reusable tools for DICOM loading, ROI-based image analysis, interactive circular ROI selection, image windowing, batch phantom analysis, and automated result export.

---

## Features

### DICOM Processing

- Load DICOM images using `pydicom`
- Extract image pixel data for quantitative analysis
- Support DICOM intensity rescaling when applicable
- Inspect radiotherapy and phantom imaging data

### Image Visualization

- Display grayscale DICOM images
- Apply Window Level (WL) and Window Width (WW) for visualization
- Keep visualization windowing separate from quantitative pixel analysis

### ROI Analysis

- Rectangular ROI analysis
- Interactive circular ROI selection
- Target and background ROI selection
- ROI visualization on DICOM images

### Quantitative Image-Quality Metrics

- ROI mean
- ROI standard deviation
- Signal difference
- Background-subtracted SNR
- Contrast-to-noise ratio (CNR)

### Batch Phantom Analysis

- Process multiple phantom DICOM images
- Manually select target and background circular ROIs for each image
- Automatically calculate image-quality metrics
- Export quantitative results to CSV
- Automatically save annotated ROI figures

---

## Project Structure

```text
radiotherapy-image-quality-toolkit/
│
├── notebooks/
│   └── image_quality_demo.ipynb
│
├── src/
│   ├── dicom_reader.py
│   ├── roi_analysis.py
│   ├── roi_selector.py
│   ├── visualization.py
│   └── batch_analysis.py
│
├── output/
│   ├── batch_phantom_results.csv
│   └── batch_roi_figures/
│
├── test_data/
│
├── test_roi_selector.py
├── batch_manual_roi_analysis.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Technologies

- Python
- NumPy
- pandas
- matplotlib
- pydicom
- Jupyter Notebook

---

## Installation

Clone the repository and install the required packages:

```bash
pip install -r requirements.txt
```

Current dependencies include:

```text
pydicom
numpy
matplotlib
pandas
```

---

## Basic DICOM Workflow

### Load a DICOM Image

```python
from dicom_reader import load_dicom

ds, image = load_dicom("example.dcm")
```

### Display the Image

```python
from visualization import show_dicom_image

show_dicom_image(
    image,
    title="Example DICOM Image"
)
```

---

## Window Level and Window Width

Window Level and Window Width can be applied to improve image visualization.

```python
show_dicom_image(
    image,
    title="Windowed Phantom Image",
    window_level=65480,
    window_width=200
)
```

Windowing is used for visualization only.

The original image values are preserved for quantitative analysis.

This separation ensures that changing display contrast does not change measured ROI statistics.

---

## Rectangular ROI Analysis

The toolkit supports basic rectangular ROI analysis.

```python
from roi_analysis import (
    calculate_roi_statistics,
    calculate_snr
)

x1, x2 = 40, 80
y1, y2 = 40, 80

roi_mean, roi_std = calculate_roi_statistics(
    image,
    x1,
    x2,
    y1,
    y2
)

snr = calculate_snr(
    image,
    x1,
    x2,
    y1,
    y2
)

print("ROI Mean:", roi_mean)
print("ROI SD:", roi_std)
print("SNR:", snr)
```

---

## Interactive Circular ROI Selection

The toolkit supports interactive selection of circular target and background ROIs.

Each circular ROI is defined using two mouse clicks:

1. Click the ROI center.
2. Click a point on the ROI boundary.

The radius is then calculated automatically.

Example:

```python
from roi_selector import select_two_circular_rois

target_circle, background_circle = select_two_circular_rois(
    image,
    window_level=65480,
    window_width=200
)
```

The target ROI is displayed in red and the background ROI in blue.

---

## Circular ROI Statistics

Circular ROI statistics are calculated using the original image pixel values.

```python
from roi_analysis import calculate_circular_roi_statistics

target_mean, target_std = calculate_circular_roi_statistics(
    image,
    target_circle["center_x"],
    target_circle["center_y"],
    target_circle["radius"]
)

background_mean, background_std = calculate_circular_roi_statistics(
    image,
    background_circle["center_x"],
    background_circle["center_y"],
    background_circle["radius"]
)
```

The analysis returns:

- ROI mean
- ROI standard deviation

---

## Image-Quality Metrics

Some radiotherapy and phantom images may contain a substantial baseline intensity offset.

In these cases, a conventional metric such as:

```text
SNR = Mean / Standard Deviation
```

may produce misleadingly large values because the image baseline contributes strongly to the mean.

For this reason, the phantom workflow uses background-subtracted metrics.

### Signal Difference

```text
Signal Difference =
| Target Mean - Background Mean |
```

### Background-Subtracted SNR

```text
Background-Subtracted SNR =
| Target Mean - Background Mean |
---------------------------------
            Target SD
```

### Contrast-to-Noise Ratio

```text
CNR =
| Target Mean - Background Mean |
---------------------------------
         Background SD
```

These metrics reduce the influence of a large baseline offset and provide a more meaningful comparison between target and background regions.

Example:

```python
from roi_analysis import calculate_background_subtracted_metrics

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

print("Signal Difference:", signal_difference)
print(
    "Background-Subtracted SNR:",
    background_subtracted_snr
)
print("CNR:", cnr)
```

---

## Phantom DICOM Analysis

The toolkit can be used to analyze phantom DICOM images using manually selected circular ROIs.

A typical workflow is:

```text
Load Phantom DICOM
        ↓
Apply WL / WW for visualization
        ↓
Select Target Circular ROI
        ↓
Select Background Circular ROI
        ↓
Calculate ROI Statistics
        ↓
Calculate Signal Difference
        ↓
Calculate Background-Subtracted SNR
        ↓
Calculate CNR
        ↓
Save Annotated Figure
        ↓
Export Quantitative Results
```

---

## Batch Phantom Analysis

Multiple phantom DICOM images can be processed sequentially using:

```bash
python batch_manual_roi_analysis.py
```

For each image, the program:

1. Loads the DICOM image.
2. Applies the selected Window Level and Window Width for display.
3. Prompts the user to select a target circular ROI.
4. Prompts the user to select a background circular ROI.
5. Calculates target ROI mean and standard deviation.
6. Calculates background ROI mean and standard deviation.
7. Calculates signal difference.
8. Calculates background-subtracted SNR.
9. Calculates CNR.
10. Saves an annotated ROI figure.
11. Adds the quantitative results to the batch results table.

---

## Batch Analysis Output

The batch workflow automatically generates:

```text
output/
│
├── batch_phantom_results.csv
│
└── batch_roi_figures/
    ├── image_01_roi.png
    ├── image_02_roi.png
    ├── image_03_roi.png
    └── ...
```

The CSV file includes:

- File name
- Window Level
- Window Width
- Target ROI center coordinates
- Target ROI radius
- Target mean
- Target standard deviation
- Background ROI center coordinates
- Background ROI radius
- Background mean
- Background standard deviation
- Signal difference
- Background-subtracted SNR
- CNR

---

## Example Output

The figure below shows an example phantom image with manually selected circular ROIs.

- **Red circle:** Target ROI
- **Blue circle:** Background ROI
- Window level and window width are applied for visualization only.

![Example Phantom ROI Analysis](docs/images/phantom_roi_example.png)



## Notebook Demonstration

The repository also includes a Jupyter Notebook:

```text
notebooks/image_quality_demo.ipynb
```

The notebook demonstrates the basic workflow:

1. Load a sample DICOM image.
2. Display the image.
3. Define rectangular ROIs.
4. Calculate ROI statistics.
5. Calculate SNR and CNR.
6. Display target and background ROIs.
7. Load phantom DICOM test data.

The reusable analysis functions are stored in the `src/` directory rather than being implemented directly inside the notebook.

---

## Source Modules

### `dicom_reader.py`

Handles:

- DICOM loading
- Pixel array extraction
- Image intensity rescaling when applicable

### `roi_analysis.py`

Handles:

- Rectangular ROI statistics
- Circular ROI statistics
- SNR calculations
- Signal difference
- Background-subtracted SNR
- CNR

### `roi_selector.py`

Handles:

- Interactive circular ROI selection
- Target ROI selection
- Background ROI selection

### `visualization.py`

Handles:

- DICOM image display
- Window Level / Window Width
- ROI visualization
- Target/background ROI display

### `batch_analysis.py`

Provides reusable functionality for multi-image analysis.

---

## Data Privacy

DICOM files may contain sensitive metadata.

Clinical or patient-identifiable DICOM data should not be uploaded to a public GitHub repository.

The `test_data/` directory should contain only:

- appropriately de-identified data, or
- non-patient phantom data

Original clinical datasets are not required for the demonstration workflow.

It is recommended that raw DICOM test data remain excluded from version control.

Example `.gitignore` entries:

```gitignore
test_data/
__pycache__/
*.pyc
```

---

## Design Principles

This project separates image visualization from quantitative analysis.

Window Level and Window Width are used only to improve visual interpretation and ROI placement.

Quantitative calculations are performed using the underlying image pixel values rather than the windowed display image.

The project also separates:

```text
User interaction
        ↓
ROI selection
        ↓
Image analysis
        ↓
Visualization
        ↓
Batch processing
        ↓
Data export
```

into reusable Python modules.

---

## Purpose

This project was developed as an independent computational medical physics portfolio project.

The goal is to demonstrate practical programming skills relevant to medical physics, including:

- Python programming
- DICOM handling
- medical image processing
- quantitative image analysis
- ROI-based analysis
- interactive visualization
- modular software development
- automated batch processing
- CSV data export
- reproducible computational workflows

---

## Future Development

Potential future improvements include:

- Automated phantom ROI detection
- Additional image-quality metrics
- ROI position reuse across related image sets
- Automatic DICOM Window Center / Window Width detection
- Improved command-line interface
- Graphical user interface
- Automated quality-control reporting
- Additional radiotherapy imaging workflows
- Treatment-plan and RT DICOM analysis