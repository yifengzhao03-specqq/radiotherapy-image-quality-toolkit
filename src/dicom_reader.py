import pydicom
import numpy as np


def load_dicom(file_path):
    """
    Load a DICOM file and return the dataset and
    rescaled pixel data when rescale parameters are available.
    """

    ds = pydicom.dcmread(file_path)

    image = ds.pixel_array.astype(np.float32)

    slope = float(
        getattr(ds, "RescaleSlope", 1.0)
    )

    intercept = float(
        getattr(ds, "RescaleIntercept", 0.0)
    )

    image = image * slope + intercept

    return ds, image