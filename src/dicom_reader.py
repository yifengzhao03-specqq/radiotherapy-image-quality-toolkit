import pydicom


def load_dicom(file_path):
    """
    Load a DICOM file and return both the dataset
    and its pixel array.
    """
    ds = pydicom.dcmread(file_path)
    image = ds.pixel_array

    return ds, image