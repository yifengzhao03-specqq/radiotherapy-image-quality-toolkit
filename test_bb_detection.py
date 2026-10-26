"""Run an initial automatic BB-localization test on existing manual-ROI data.

Example (PowerShell, from project root):
    python test_bb_detection.py --reference "kV_RI.dcm" --test "6x_0_RI.dcm"

IMPORTANT: reference and test must be from the SAME phantom and share
compatible image geometry. The held-out test ROI is used only for comparison.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Save figures; no popup window required.
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dicom_reader import load_dicom
from bb_detector import detect_bb


def get_row(df: pd.DataFrame, filename: str) -> pd.Series:
    matching = df[df["File"].astype(str) == filename]
    if len(matching) != 1:
        raise ValueError(
            f"Expected exactly one row named {filename!r} in manual ROI CSV; "
            f"found {len(matching)}. Check filename or CSV."
        )
    return matching.iloc[0]


def save_preview(image, result, target_row, reference_row, output_path, title):
    # Display windowing only; the BB detector uses raw/rescaled pixels.
    wl = float(target_row["Window Level"])
    ww = float(target_row["Window Width"])
    if np.isfinite(wl) and np.isfinite(ww) and ww > 0:
        vmin, vmax = wl - ww / 2, wl + ww / 2
    else:
        vmin, vmax = np.percentile(image, [1, 99])
    if vmin >= vmax:
        vmax = vmin + 1
    x, y = result["center_x"], result["center_y"]
    manual_x = float(target_row["Target Center X"])
    manual_y = float(target_row["Target Center Y"])
    ex, ey = result["expected_x"], result["expected_y"]
    radius = float(reference_row["Target Radius"])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), constrained_layout=True)
    for ax in axes:
        ax.imshow(image, cmap="gray", vmin=vmin, vmax=vmax, origin="upper")
        ax.plot(x, y, "+", color="lime", ms=13, mew=2, label="Automatic BB center")
        ax.plot(manual_x, manual_y, "x", color="magenta", ms=10, mew=2, label="Held-out manual center")
        ax.add_patch(Circle((x, y), radius, fill=False, edgecolor="lime", lw=1.5))
        ax.add_patch(Circle((ex, ey), result["search_radius"], fill=False, edgecolor="yellow", ls="--", lw=1))
        ax.set_xlabel("X (pixel)")
        ax.set_ylabel("Y (pixel)")
    axes[0].set_title("Full DICOM image (display window only)")
    axes[1].set_xlim(ex - 48, ex + 48)
    axes[1].set_ylim(ey + 48, ey - 48)
    axes[1].set_title("Enlarged local search (96 x 96 pixels)")
    axes[1].legend(loc="upper right", fontsize=7, framealpha=.85)
    fig.suptitle(title, fontsize=11)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Test reference-guided automatic BB localization")
    parser.add_argument("--reference", required=True, help="Reference DICOM filename with manually recorded ROI")
    parser.add_argument("--test", required=True, help="Different DICOM filename of the SAME phantom")
    parser.add_argument("--search-radius", type=int, default=18, help="Expected maximum shift, pixels (default: 18)")
    args = parser.parse_args()

    if args.reference == args.test:
        parser.error("Reference and test files must be different; use a held-out image.")
    csv_path = PROJECT_ROOT / "output" / "batch_phantom_results.csv"
    if not csv_path.is_file():
        parser.error(f"Missing manual results: {csv_path}")
    df = pd.read_csv(csv_path)
    ref_row = get_row(df, args.reference)
    test_row = get_row(df, args.test)
    img_path = PROJECT_ROOT / "test_data" / args.test
    if not img_path.is_file():
        parser.error(f"Missing DICOM image: {img_path}")

    _, image = load_dicom(img_path)
    prior = (float(ref_row["Target Center X"]), float(ref_row["Target Center Y"]))
    result = detect_bb(image, prior, search_radius=args.search_radius)
    manual = (float(test_row["Target Center X"]), float(test_row["Target Center Y"]))
    center_error = math.dist((result["center_x"], result["center_y"]), manual)
    print("\n=== Reference-guided BB detection (experimental) ===")
    print(f"Reference:        {args.reference}")
    print(f"Test image:       {args.test}")
    print(f"Reference center: ({prior[0]:.2f}, {prior[1]:.2f}) px")
    print(f"Auto BB center:   ({result['center_x']:.2f}, {result['center_y']:.2f}) px")
    print(f"Manual center:    ({manual[0]:.2f}, {manual[1]:.2f}) px")
    print(f"Auto-manual difference: {center_error:.2f} pixels")
    print(f"Signal polarity:  {result['polarity']}")
    print(f"Response score:   {result['contrast_score']:.2f} (not a probability)")
    print(f"QC:               {result['status']}")
    print("NOTE: Inspect the image! No result is considered validated yet.")

    out_dir = PROJECT_ROOT / "output"
    out_png = out_dir / "bb_detection_preview.png"
    out_csv = out_dir / "bb_detection_test_result.csv"
    save_preview(image, result, test_row, ref_row, out_png, args.test)
    pd.DataFrame([{
        "Reference File": args.reference,
        "Test File": args.test,
        "Auto Center X": result["center_x"],
        "Auto Center Y": result["center_y"],
        "Manual Center X": manual[0],
        "Manual Center Y": manual[1],
        "Center Error Pixels": center_error,
        "Polarity": result["polarity"],
        "Response Score": result["contrast_score"],
        "QC Status": result["status"],
    }]).to_csv(out_csv, index=False)
    print(f"\nSaved preview: {out_png}")
    print(f"Saved results: {out_csv}")


if __name__ == "__main__":
    main()
