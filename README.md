# Radiotherapy Image Quality Toolkit

**Experimental release: v0.3.0-alpha — Hybrid BB localization and quality-control prototypes**

**A Python toolkit for quantitative DICOM image analysis, interactive region-of-interest (ROI) selection, and experimental image-based ROI localization in radiotherapy phantom studies.**

The toolkit supports reproducible analysis of radiotherapy phantom images acquired under different imaging and irradiation conditions. It combines an interactive DICOM viewer, manual ROI statistics, batch reporting, and experimental, reference-guided BB localization with controlled validation scripts.

> **Development status:** Manual ROI analysis and interactive visualization are available. Translation-only registration, DoG candidate detection, background-corrected centroid / Gaussian center estimation, DoG-to-Gaussian hybrid localization (v3), and reference-calibrated width QC (v3.1) are **experimental prototypes**. Automatic target/background ROI generation and validated end-to-end analysis are **not yet implemented**.
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
| BB candidate localization (v1) | Local, reference-guided Difference-of-Gaussians (DoG) | Experimental; human review required |
| BB center refinement (v2) | Background-corrected centroid; Gaussian + background-plane fitting | Experimental |
| Hybrid BB localization (v3) | DoG coarse candidate followed by Gaussian + background-plane refinement | Experimental; human review required |
| Reference-width QC (v3.1) | Fit residual / polarity / candidate boundary checks plus reference-calibrated Gaussian sigma ratio | Experimental; no automatic pass |
| Research validation scripts | Integer/subpixel simulated translations, interpolation comparisons, synthetic degradation/negative-control stress tests | Experimental; not clinical validation |
| Fully automated ROI analysis | Automatically determine target **and** background ROIs for an image batch | Planned |

## Intended applications

The current workflows are being explored with phantom images, including:

- **Winston–Lutz phantom:** imaging of a ball-bearing target.
- **Alderson RANDO thorax phantom:** anthropomorphic thorax imaging with an externally placed metal BB as a target marker.

These phantoms have different backgrounds and target geometries. Select reference and test images **from the same phantom** and with compatible imaging geometry. The current software does not automatically identify the phantom type or establish a universally valid background ROI.

## Project layout

The layout below is the **intended release layout**. Confirm that each listed file exists in your working tree and is committed; documentation does not create or upload a file automatically.

```text
radiotherapy-image-quality-toolkit/
├── docs/images/                         # Only cleared, non-sensitive illustrations
├── notebook/                            # Existing notebook folder
├── src/
│   ├── dicom_reader.py
│   ├── roi_analysis.py
│   ├── roi_selector.py
│   ├── interactive_roi_selector.py
│   ├── visualization.py
│   ├── batch_analysis.py
│   ├── image_registration.py           # Experimental
│   ├── bb_detector.py                  # v1: DoG
│   ├── bb_center_refinement.py         # v2: centroid / Gaussian
│   ├── hybrid_bb_detector.py           # v3: DoG + Gaussian
│   └── hybrid_bb_detector_qc_v31.py    # v3.1: extra reference-width QC
├── batch_manual_roi_analysis.py
├── test_roi_selector.py
├── test_image_registration.py
├── test_bb_detection.py
├── test_bb_refinement.py
├── test_bb_displacement.py
├── test_bb_hybrid.py
├── test_bb_hybrid_displacement.py
├── test_bb_subpixel_displacement.py
├── test_bb_qc_validation.py
├── test_bb_qc_v31.py
├── install_roi_ui.py
├── test_data/                           # Local DICOM data; ignored by Git
├── output/                              # Generated figures/CSVs; ignored by Git
├── requirements.txt
├── .gitignore
└── README.md
```

The detector examples currently use **reference images and manual ROI metadata for initialization/evaluation**; they do not constitute completely autonomous full-image BB detection.

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

## Experimental workflow 3: BB center refinement and hybrid localization

The v2 module (`src/bb_center_refinement.py`) estimates a candidate BB center from the local signal using a background-corrected centroid and a 2D Gaussian plus a sloping background plane. The v3 hybrid (`src/hybrid_bb_detector.py`) uses a DoG candidate **only for coarse localization**, then refines its center with the Gaussian model. The test-image manual annotation is used for **evaluation only**, not to provide the test-image center.

From the repository root, with same-phantom, compatible-geometry DICOM images in `test_data/` and the associated `output/batch_phantom_results.csv` locally available:

```bash
python test_bb_refinement.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"
python test_bb_hybrid.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"
```

These scripts write diagnostic CSV and figure outputs to the local `output/` folder. The coarse detection remains reference-guided, and success must be visually reviewed.

## Experimental workflow 4: controlled localization validation

Controlled translation tests are **software diagnostics**, not physical localization accuracy measurements:

```bash
# Integer-pixel translations of a single image
python test_bb_hybrid_displacement.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"

# Interpolated fractional-pixel translations (linear and cubic)
python test_bb_subpixel_displacement.py --reference "10FFF_0_RI.dcm" --test "6FFF_RI.dcm"
```

The subpixel script compares interpolation methods and reports **shift-recovery error** (error in predicted displacement relative to that method's unshifted estimate) separately from **distance to a shifted manual annotation**. Neither metric alone is an independently measured physical BB-center error. Synthetic translation reuses the same underlying image and does not simulate real changes in projection, scatter, motion, or detector behavior.

In a preliminary single-image subpixel test, the v3 hybrid produced mean shift-recovery discrepancies of approximately **0.0325 px (linear)** and **0.0423 px (cubic)** across eight non-zero simulated shifts. These values are **diagnostic, dataset-specific, and not validated accuracy claims**.

## Experimental workflow 5: QC stress testing (v3 and v3.1)

The core v3 detector provides heuristic warnings about polarity, fit residual, fitted width, and search-boundary candidates. The v3.1 **optional QC wrapper** (`src/hybrid_bb_detector_qc_v31.py`) adds a comparison of the fitted Gaussian width against an inspected, same-phantom, same-geometry trusted reference.

```bash
python test_bb_qc_validation.py --reference "10FFF_0_RI.dcm" --test "6FFF_RI.dcm"
python test_bb_qc_v31.py --reference "10FFF_0_RI.dcm" --test "6FFF_RI.dcm"
```

The exploratory v3.1 sigma-ratio range is **0.70 to 1.40** relative to the trusted reference fit. This was selected during iterative development to investigate a simulated half-obscured BB, **not** established as a clinical acceptance interval. Synthetic cases include contrast reduction, added noise, partial masking, artificial BB removal, decoys, and uniform-image negatives. They are not equivalent to genuine BB-free acquisitions.

- `candidate_requires_review`: A candidate was returned; **human review is still required**.
- `low_confidence_requires_review`: Specific problems were flagged; **do not use the candidate for unattended quantitative analysis**.
- `detection_failed`: The detector could not produce a usable candidate.

**No current status means automatic/clinical acceptance.** Existing QC is a research prototype; thresholds have not been independently calibrated or validated.

## Limitations and roadmap

**Not yet implemented:** automatic target ROI generation; standardized phantom-specific background ROI placement; end-to-end unattended SNR/CNR analysis; universal phantom classification; validated clinical use.

**Before considering broader use:** validate on held-out acquisitions and both phantom groups; test real repositioning, rotations and varying image quality; evaluate repeated blinded manual annotations; collect real BB-absent/decoy negatives; assess QC false alarms and missed detections; standardize ROI radius and background-placement rules; and verify agreement of downstream quantitative metrics.

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
*.backup
```

Ignore rules do **not** retroactively untrack committed files. This repository has previously shown a tracked `batch_manual_roi_analysis.py.before_roi_ui.bak`; review its contents and remove it from Git tracking before release if it is only a local backup. Check `git status` and `git ls-files` before pushing. Do not post unreviewed DICOM or restricted output data.

## Project purpose

This is an independently developed computational medical-physics software project focused on DICOM handling, quantitative image-quality assessment, interactive visualization, computer vision, and reproducible analysis workflows. Experimental modules are shared to document the development process and enable further algorithm evaluation, **not** to imply clinical readiness or established performance.
