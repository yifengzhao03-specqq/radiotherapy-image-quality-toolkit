# Radiotherapy Image Quality Toolkit

A Python-based toolkit for basic quantitative analysis of radiotherapy imaging data.

## Features

- Read DICOM images
- Display DICOM pixel data
- Define rectangular regions of interest (ROIs)
- Calculate ROI mean and standard deviation
- Calculate signal-to-noise ratio (SNR)
- Calculate contrast-to-noise ratio (CNR)
- Visualize ROIs on medical images

## Project Structure

- `notebooks/image_quality_demo.ipynb`  
  Demonstrates the complete image-quality analysis workflow.

- `src/dicom_reader.py`  
  Contains functions for loading DICOM files and extracting pixel data.

- `src/roi_analysis.py`  
  Contains reusable functions for ROI statistics, SNR, and CNR calculations.

- `src/visualization.py`  
  Contains functions for displaying DICOM images and visualizing ROIs.

- `requirements.txt`  
  Lists the Python packages required to run the project.

## Technologies

- Python
- NumPy
- pydicom
- matplotlib
- Jupyter Notebook

## Example Workflow

1. Load a DICOM image
2. Extract the image pixel array
3. Define target and background ROIs
4. Calculate ROI statistics
5. Calculate SNR and CNR
6. Visualize the selected ROIs

## Data

The demonstration notebook uses sample DICOM data distributed with the pydicom package.

No patient-identifiable clinical data are included in this repository.

## Purpose

This project was developed as a computational medical physics portfolio project focused on quantitative medical image analysis.