"""Controlled integer-pixel displacement test for reference-guided BB localization.

Put this file in the repository root, next to test_bb_refinement.py.

Example (PowerShell):
    python test_bb_displacement.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"

The target's held-out manual center is used ONLY for reporting absolute distance;
no tested algorithm receives manual labels or the artificial displacement.
Integer image shifts are applied without interpolation so pixel intensity/noise
statistics within the translated BB are unchanged.

Research-only diagnostic. Not validated for clinical QA.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

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

# Include two directions and displacements beyond the Gaussian model's +/-7px limit.
SHIFTS = [(0, 0), (2, 0), (0, 2), (-2, 0), (5, 3), (-5, -3), (8, 0), (10, 5)]
METHODS = ["Fixed reference", "DoG (v1)", "Corrected centroid", "Gaussian + plane"]


def get_unique_row(df: pd.DataFrame, filename: str) -> pd.Series:
    matched = df[df["File"].astype(str) == filename]
    if len(matched) != 1:
        raise ValueError(f"Found {len(matched)} manual ROI records for {filename!r}; expected exactly 1")
    return matched.iloc[0]


def translate_integer(image: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Translate pixels by (dx right, dy down), with no interpolation."""
    h, w = image.shape
    if abs(dx) >= w or abs(dy) >= h:
        raise ValueError("Shift exceeds image dimensions")
    # Border fill affects only newly exposed edges, far away from the BB.
    background_fill = float(np.median(image))
    translated = np.full(image.shape, background_fill, dtype=np.float64)
    src_x1, src_x2 = max(0, -dx), min(w, w - dx)
    src_y1, src_y2 = max(0, -dy), min(h, h - dy)
    translated[src_y1 + dy:src_y2 + dy, src_x1 + dx:src_x2 + dx] = (
        image[src_y1:src_y2, src_x1:src_x2]
    )
    return translated


def locate(method: str, image: np.ndarray, expected: tuple[float, float]) -> tuple[float, float]:
    if method == "Fixed reference":
        return expected
    funcs = {
        "DoG (v1)": detect_bb,
        "Corrected centroid": centroid_refinement,
        "Gaussian + plane": gaussian_refinement,
    }
    pred = funcs[method](image, expected)
    return float(pred["center_x"]), float(pred["center_y"])


def run(image: np.ndarray, expected: tuple[float, float], manual: tuple[float, float], shifts=SHIFTS):
    if image.ndim != 2 or not np.isfinite(image).all():
        raise ValueError("Expected finite grayscale DICOM image")
    if not (np.isfinite(expected).all() and np.isfinite(manual).all()):
        raise ValueError("Invalid manually supplied ROI coordinates")
    baseline = {}
    rows = []
    for dx, dy in shifts:
        shifted = translate_integer(image, dx, dy)
        target = (manual[0] + dx, manual[1] + dy)
        for method in METHODS:
            item = {"Method": method, "Shift X (px)": dx, "Shift Y (px)": dy,
                    "Expected X from manual (px)": target[0],
                    "Expected Y from manual (px)": target[1],
                    "Status": "ok"}
            try:
                center = locate(method, shifted, expected)
                if not np.isfinite(center).all():
                    raise ValueError("Non-finite estimated center")
                item.update({"Predicted X (px)": center[0], "Predicted Y (px)": center[1],
                             "Distance to shifted manual (px)": math.dist(center, target)})
                if dx == 0 and dy == 0:
                    baseline[method] = center
                if method in baseline:
                    baseline_center = baseline[method]
                    measured_shift = (center[0] - baseline_center[0], center[1] - baseline_center[1])
                    item.update({"Recovered shift X (px)": measured_shift[0],
                                 "Recovered shift Y (px)": measured_shift[1],
                                 "Shift recovery error (px)": math.dist(measured_shift, (dx, dy))})
            except (ValueError, RuntimeError, OverflowError) as exc:
                item.update({"Status": "failed", "Failure reason": str(exc)})
            rows.append(item)
    return pd.DataFrame(rows)


def write_plot(df: pd.DataFrame, filename: Path):
    fig, ax = plt.subplots(figsize=(9, 5))
    for method in METHODS:
        sub = df[(df["Method"] == method) & (df["Status"] == "ok")].copy()
        sub["shift_magnitude"] = np.hypot(sub["Shift X (px)"], sub["Shift Y (px)"])
        sub = sub.sort_values("shift_magnitude")
        ax.plot(sub["shift_magnitude"], sub["Shift recovery error (px)"],
                marker="o", label=method)
    ax.set(xlabel="Applied translation magnitude (pixels)",
           ylabel="Shift recovery error (pixels)",
           title="Controlled displacement: recovered vs known translation")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(filename, dpi=175)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="Manual ROI reference DICOM filename")
    parser.add_argument("--test", required=True, help="DICOM filename under test_data/")
    args = parser.parse_args()
    if args.reference == args.test:
        parser.error("Use different reference and test files")
    table = pd.read_csv(ROOT / "output" / "batch_phantom_results.csv")
    ref = get_unique_row(table, args.reference)
    tst = get_unique_row(table, args.test)
    expected = (float(ref["Target Center X"]), float(ref["Target Center Y"]))
    manual = (float(tst["Target Center X"]), float(tst["Target Center Y"]))
    _, pixels = load_dicom(ROOT / "test_data" / args.test)
    df = run(np.asarray(pixels, dtype=float), expected, manual)
    out = ROOT / "output"
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.test).stem
    results_path = out / f"bb_displacement_{stem}.csv"
    plot_path = out / f"bb_displacement_{stem}.png"
    df.to_csv(results_path, index=False)
    write_plot(df, plot_path)
    print(f"\nControlled displacement experiment: {args.test}")
    print("No algorithm was given the known translation or held-out manual test center.")
    for method in METHODS:
        group = df[df["Method"] == method]
        ok = group[group["Status"] == "ok"]
        shift_errors = ok["Shift recovery error (px)"].dropna()
        msg = (f"{method:<21} {len(ok)}/{len(group)} ran; "
               f"mean shift recovery error: {shift_errors.mean():.3f} px" if len(shift_errors) else
               f"{method:<21} no valid estimates")
        print(msg)
    print("Saved:", results_path, "and", plot_path)
    print("IMPORTANT: shift recovery is relative to each algorithm's own unshifted output.")
    print("Absolute localization still depends on an imperfect manual mark.")


if __name__ == "__main__":
    main()
