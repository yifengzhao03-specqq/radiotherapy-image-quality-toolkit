# Radiotherapy Image Quality Toolkit

**A Python toolkit for quantitative DICOM image analysis, interactive region-of-interest (ROI) selection, and experimental image-based ROI localization in radiotherapy phantom studies.**

The toolkit was developed to support reproducible analysis of radiotherapy imaging data, particularly comparisons of image quality under different acquisition and irradiation conditions. It combines an interactive DICOM viewer, circular and rectangular ROI measurements, batch reporting, and early-stage computer-vision methods for phantom localization.

> **Development status:** Manual ROI analysis and interactive visualization are available. Translation-only image registration and reference-guided ball-bearing (BB) detection are **experimental prototypes**. Fully automatic, validated ROI selection is **not yet implemented**.
>
> **Research software only.** This toolkit has not been clinically validated and must not be used for patient-care or treatment decisions.

## Features and status

| Component | Capabilities | Status |
| --- | --- | --- |
| DICOM processing | Read DICOM pixel data; apply rescale slope/intercept when available | Implemented |
| Interactive image viewer | Grayscale display, live window level/width (WL/WW), zoom, pan | Implemented (upgraded viewer) |
| Manual ROI selection | Independently select circular target and background ROIs | Implemented |
| Quantitative analysis | ROI mean and SD, signal difference, background-subtracted SNR, CNR | Implemented |
| Batch analysis | Analyze multiple `.dcm` files, export CSV results and annotated figures | Implemented (manual ROIs) |
| Image registration | Estimate 2D translations between images using phase cross-correlation | Experimental |
| Automatic BB localization | Reference-guided, local Difference-of-Gaussians (DoG) candidate detection | Experimental; human review required |
| Fully automated ROI analysis | Automatically determine target **and** background ROIs for an image batch | Planned |

## Intended applications

The current workflows are being explored with phantom images, including:

- **Winston–Lutz phantom:** imaging of a ball-bearing target.
- **Alderson RANDO thorax phantom:** anthropomorphic thorax imaging with an externally placed metal BB as a target marker.

These phantoms have different backgrounds and target geometries. Select reference and test images **from the same phantom** and with compatible imaging geometry. The current software does not automatically identify the phantom type or establish a universally valid background ROI.

## Project layout

The structure below includes the original analysis code and the new experimental modules. Local input/output folders are created or populated when running the workflows.

```text
radiotherapy-image-quality-toolkit/
├── src/
│   ├── dicom_reader.py
│   ├── roi_analysis.py
│   ├── roi_selector.py                 # Legacy manual selector
│   ├── interactive_roi_selector.py     # Upgraded interactive viewer
│   ├── visualization.py
│   ├── batch_analysis.py
│   ├── image_registration.py          # Experimental
│   └── bb_detector.py                 # Experimental
├── batch_manual_roi_analysis.py
├── test_roi_selector.py
├── test_image_registration.py         # Experimental example
├── test_bb_detection.py               # Experimental example
├── install_roi_ui.py                  # One-time upgrade helper (if needed)
├── test_data/                         # Local DICOM files; excluded from Git
├── output/                            # Locally generated results; excluded from Git
├── docs/
├── requirements.txt
└── README.md
```

> This README describes the **upgraded working version**. Before publishing, include the new Python files listed above and the updated `batch_manual_roi_analysis.py` in the same commit. The published repository may not contain every file until you push your local changes.

## Requirements and installation

- Python **3.10+** recommended
- A Python environment with a working Matplotlib interactive GUI backend for the ROI viewer
- Windows, macOS, or Linux with desktop display support for interactive annotation

Clone the repository:

```bash
git clone https://github.com/yifengzhao03-specqq/radiotherapy-image-quality-toolkit.git
cd radiotherapy-image-quality-toolkit
```

Create a virtual environment (recommended):

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Core dependencies are `pydicom`, `numpy`, `matplotlib`, `pandas`, `scipy`, and `scikit-image`. Some compressed DICOM transfer syntaxes may require additional pixel-data decoding packages.

> **Filename note:** The repository originally used the misspelled `requitements.txt`. Rename it to **`requirements.txt`** and include `scipy` and `scikit-image` before publishing this update.

## Quick start: manual ROI batch analysis

1. Place your locally permitted `.dcm` files directly in `test_data/` (not in a nested subfolder).
2. From the repository root, run:

```bash
python batch_manual_roi_analysis.py
```

3. For each image, use the viewer to inspect the target and background regions, then confirm both ROIs.
4. Review the resulting CSV and annotated images in `output/`.

### Using the upgraded interactive viewer

The upgraded viewer keeps image navigation separate from ROI drawing:

1. **View mode:** Zoom using the mouse wheel or use the Matplotlib toolbar to pan/zoom without placing ROI points.
2. **WL / WW controls:** Adjust the sliders, enter values, or use **Auto WL/WW** to set a display range from image intensities.
3. **Target ROI:** Click **Target ROI**, then click its center and boundary to define the radius.
4. **Background ROI:** Click **Background ROI**, then select its center and boundary.
5. **Confirm:** Review both circles and click **Confirm** to continue batch processing. **Clear** restarts selection, and **Cancel** exits without confirming.

If `batch_manual_roi_analysis.py` still imports `roi_selector` instead of `interactive_roi_selector`, the upgraded UI has not yet been connected. With `src/interactive_roi_selector.py` and `install_roi_ui.py` present, run the one-time helper:

```bash
python install_roi_ui.py
```

The helper makes a backup of the previous batch script. Review the changes before committing and keep backup files out of the public repository.

**Important:** WL and WW affect **display only**. All quantitative metrics are calculated from the DICOM pixel array (including DICOM rescale parameters when present), **not** from the windowed display image.

## Quantitative image-quality metrics

Let the target ROI have mean intensity `μT` and standard deviation `σT`; let the background ROI have mean `μB` and standard deviation `σB`.

| Metric | Definition |
| --- | --- |
| Signal difference | `abs(μT − μB)` |
| Background-subtracted SNR | `abs(μT − μB) / σT` |
| Contrast-to-noise ratio (CNR) | `abs(μT − μB) / σB` |

For these definitions, a zero ROI standard deviation produces an undefined ratio (`NaN`) rather than a finite value. The toolkit also contains a basic rectangular-ROI SNR calculation (`mean / SD`).

**Interpretation caveat:** The SNR and CNR definitions above are the definitions implemented by this project; they are not universal across the medical-imaging literature. ROI size, placement, local anatomy, and background heterogeneity can affect the results. For controlled comparisons, establish consistent ROI selection rules within each phantom and acquisition protocol.

### Output files

```text
output/
├── batch_phantom_results.csv
└── batch_roi_figures/
    ├── <dicom_stem>_roi.png
    └── ...
```

The CSV records the source filename, selected WL/WW, ROI centers/radii, target and background mean/SD, signal difference, background-subtracted SNR, and CNR. Saved figures show the selected ROI locations.

## Experimental workflow 1: image registration

`src/image_registration.py` uses **phase cross-correlation** to estimate the translation between two 2D images. The demo transfers reference ROI coordinates into the moving-image coordinate system and optionally compares them with manual ROIs recorded in the CSV.

```bash
python test_image_registration.py --reference "10FFF_0_RI.dcm" --moving "10x_0_RI.dcm"
```

Replace the example filenames with your own compatible images. The script reads from `test_data/`, uses `output/batch_phantom_results.csv` when available, and saves:

```text
output/registration_preview.png
```

- Estimated shifts are reported as `(dx, dy)` in pixels: **positive `dx` = right; positive `dy` = down** for ROI movement from reference to moving image.
- The current method models **translation only**; it does not model rotation, scaling, or geometric distortion.
- Images must have matching dimensions and compatible orientation and geometry.
- Visually inspect the results; a reported shift is **not** proof of successful registration.
- ROI statistics should be calculated in the original moving-image pixels, avoiding unnecessary image interpolation.

## Experimental workflow 2: reference-guided BB detection

`src/bb_detector.py` uses a **Difference-of-Gaussians (DoG)** response to locate a bright or dark BB-like candidate **near a known reference center**. This is a *local, reference-guided detector*, **not** a whole-image BB finder.

**Prerequisites:**

- Two images acquired with the **same phantom** and compatible geometry in `test_data/`.
- An existing `output/batch_phantom_results.csv` with manually recorded ROI coordinates for **both** images. The reference coordinates guide detection; the test-image manual coordinates are held out for comparison.

Run:

```bash
python test_bb_detection.py --reference "10FFF_0_RI.dcm" --test "10x_0_RI.dcm"
```

To adjust the maximum local search displacement, for example:

```bash
python test_bb_detection.py --reference "10FFF_0_RI.dcm" --test "10x_0_RI.dcm" --search-radius 6
```

The script produces:

```text
output/
├── bb_detection_preview.png
└── bb_detection_test_result.csv
```

The preview overlays the automated BB candidate and held-out manual center. The CSV includes the predicted and manual coordinates, center difference (pixels), bright/dark polarity, response score, and QC status.

**Detection limitations:**

- The response score is **not** a probability of correct detection.
- A status such as `candidate_requires_review` means the candidate still needs **human inspection**, not that it passed validation.
- Bone structures, noise, artifacts, and changes in image contrast can generate misleading peaks.
- In one initial test, the candidate differed from the manual center by approximately **4.20 pixels**; this is a debugging observation, **not** a validated accuracy estimate.
- Automated **background ROI placement**, fully automatic target ROI generation, and batch SNR/CNR analysis based on detected centers are **not yet part of this prototype**.

## Validation roadmap

The next phase is to compare fixed-coordinate ROI propagation, translation-based registration, computer-vision BB detection, and a future hybrid method using the **same-phantom** image groups. Planned evaluations include:

1. **Localization error:** Difference from carefully reviewed reference labels, in pixels (and mm when pixel spacing is reliable).
2. **Measurement agreement:** Changes in ROI statistics, SNR, and CNR caused by localization method.
3. **Repeatability:** Agreement between repeated manual annotations and automated methods.
4. **Robustness:** Behavior under changes in scatter, noise, contrast, and controlled synthetic translations.
5. **Failure handling:** Explicit reporting and manual review of uncertain detections, rather than silently accepting them.

Planned development also includes standardized, phantom-specific background ROI rules, broader BB search strategies, and additional registration transforms if required by the imaging geometry.

## Data privacy and reproducibility

DICOM headers can contain identifying information even when images are acquired with a phantom. **Do not commit patient-identifiable data, unreviewed DICOM headers, restricted research data, or sensitive generated results.** Check institutional policies before publishing example images.

The local `.gitignore` should exclude at least:

```gitignore
test_data/
output/
.venv/
__pycache__/
*.pyc
*.bak
```

The repository's original `.gitignore` already excludes `test_data/` and `output/`; add the backup-file pattern if you keep the installer's `.bak` file locally. Ignore rules do not retroactively untrack previously committed files—verify with `git status` and `git ls-files` before pushing.

## Project purpose

This is an independently developed computational medical-physics software project focused on DICOM handling, quantitative image-quality assessment, interactive visualization, computer vision, and reproducible analysis workflows. Experimental modules are shared to document the development process and enable further algorithm evaluation, **not** to imply clinical readiness or established performance.
