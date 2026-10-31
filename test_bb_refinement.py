"""Compare DoG, plane-corrected centroid, and Gaussian center fitting.

Example (PowerShell, run from repository root):
  python test_bb_refinement.py --reference "10FFF_0_RI.dcm" --test "10x_0_RI.dcm"

Uses test_data DICOMs and output/batch_phantom_results.csv from existing tools.
The test image's manual center is used ONLY for post-hoc evaluation.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from dicom_reader import load_dicom
from bb_detector import detect_bb
from bb_center_refinement import centroid_refinement, gaussian_refinement


def _one_row(df, filename):
    rows = df[df["File"].astype(str) == filename]
    if len(rows) != 1:
        raise ValueError(f"Expected one ROI row for {filename!r}; found {len(rows)}")
    return rows.iloc[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="Reference DICOM filename in manual ROI CSV")
    parser.add_argument("--test", required=True, help="Test DICOM filename in test_data/")
    args = parser.parse_args()
    if args.reference == args.test:
        parser.error("Reference and test must be different images")
    data = pd.read_csv(ROOT / "output" / "batch_phantom_results.csv")
    ref, tst = _one_row(data, args.reference), _one_row(data, args.test)
    _, image = load_dicom(ROOT / "test_data" / args.test)
    expected = (float(ref["Target Center X"]), float(ref["Target Center Y"]))
    manual = (float(tst["Target Center X"]), float(tst["Target Center Y"]))

    predictions = {"Fixed reference": {"center_x": expected[0], "center_y": expected[1]}}
    for name, method in [
        ("DoG (v1)", lambda: detect_bb(image, expected)),
        ("Corrected centroid", lambda: centroid_refinement(image, expected)),
        ("Gaussian + plane", lambda: gaussian_refinement(image, expected)),
    ]:
        try:
            predictions[name] = method()
        except (ValueError, RuntimeError, OverflowError) as exc:
            predictions[name] = {"error": str(exc), "status": "failed"}

    rows = []
    print("\n=== BB localization: exploratory comparison (NOT validated) ===")
    for name, result in predictions.items():
        if "error" in result:
            print(f"{name:<21} failed: {result['error']}")
            rows.append({"Method": name, "QC Status": "failed", "Error": result["error"]})
            continue
        loc = (float(result["center_x"]), float(result["center_y"]))
        err = math.dist(loc, manual)
        print(f"{name:<21} center=({loc[0]:.2f}, {loc[1]:.2f}), "
              f"distance to manual={err:.2f} px")
        rows.append({"Method": name, "Center X": loc[0], "Center Y": loc[1],
                     "Manual Center X": manual[0], "Manual Center Y": manual[1],
                     "Distance to Manual (px)": err,
                     "QC Status": result.get("status", "baseline")})

    out = ROOT / "output"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "bb_v2_comparison.csv", index=False)
    wl, ww = float(tst["Window Level"]), float(tst["Window Width"])
    if not np.isfinite(wl) or not np.isfinite(ww) or ww <= 0:
        wl, ww = float(np.median(image)), float(np.percentile(image,99)-np.percentile(image,1))
    fig, ax = plt.subplots(figsize=(7,6.5))
    ax.imshow(image, cmap="gray", origin="upper", vmin=wl-ww/2, vmax=wl+ww/2)
    styles = {
        "Fixed reference": ("o", "orange"),
        "DoG (v1)": ("+", "lime"),
        "Corrected centroid": ("x", "cyan"),
        "Gaussian + plane": ("*", "yellow"),
    }
    for name, result in predictions.items():
        if "error" in result:
            continue
        marker, color = styles[name]
        ax.plot(result["center_x"], result["center_y"], marker=marker,
                color=color, ms=12, mew=2, linestyle="None", label=name)
    ax.plot(*manual, marker="P", color="magenta", markersize=10,
            linestyle="None", label="Manual test mark (evaluation only)")
    ax.set_xlim(expected[0]-22, expected[0]+22)
    ax.set_ylim(expected[1]+22, expected[1]-22)
    ax.set_xlabel("X (pixel)")
    ax.set_ylabel("Y (pixel)")
    ax.set_title(f"BB center estimates — {args.test}\nReference-guided; diagnostic only")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "bb_v2_comparison.png", dpi=180)
    plt.close(fig)
    print("Saved:", out / "bb_v2_comparison.png", "and bb_v2_comparison.csv")
    print("Note: one image and one manual mark do not validate any method.")

if __name__ == "__main__":
    main()
