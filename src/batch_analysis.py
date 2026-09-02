from pathlib import Path
import pandas as pd

from dicom_reader import load_dicom
from roi_analysis import summarize_analysis


def analyze_dicom_folder(
    folder_path,
    target_coords,
    background_coords
):
    """
    Analyze all DICOM files in a folder and return
    the results as a pandas DataFrame.
    """

    folder = Path(folder_path)

    results_list = []

    for file_path in folder.glob("*.dcm"):
        ds, image = load_dicom(file_path)

        results = summarize_analysis(
            image,
            target_coords,
            background_coords
        )

        results["File"] = file_path.name

        results_list.append(results)

    results_df = pd.DataFrame(results_list)

    return results_df