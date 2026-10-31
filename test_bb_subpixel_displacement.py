"""Research-only subpixel displacement test for reference-guided BB localization.

The test image is shifted by known *fractional* pixel amounts using SciPy
interpolation. Known shifts and held-out manual test centers are used only for
SCORING, never for detection/refinement. The input DICOM is NOT modified.

Run from the project root (PowerShell):
  python test_bb_subpixel_displacement.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"

Outputs (under output/):
  bb_subpixel_<test_stem>.csv
  bb_subpixel_summary_<test_stem>.csv
  bb_subpixel_<test_stem>_linear.png
  bb_subpixel_<test_stem>_cubic.png

Important: This tests simulated image-domain shifts, not real-world physical
BB position accuracy. Interpolation changes image noise/texture; compare
interpolation orders separately and do not interpret tiny errors as clinical
localization accuracy.
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
from scipy.ndimage import shift as ndimage_shift

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from dicom_reader import load_dicom
from bb_detector import detect_bb
from bb_center_refinement import gaussian_refinement
from hybrid_bb_detector import detect_bb_hybrid

# Predeclared: do not tune based on the held-out test labels.
# X displacement is positive to the right; Y displacement is positive down.
SHIFTS_XY = [
    (0.0, 0.0),
    (+0.25, 0.0),
    (+0.50, 0.0),
    (0.0, +0.75),
    (+1.25, -0.50),
    (+2.50, +1.75),
    (-2.25, +1.50),
    (+5.50, -3.25),
    (+8.25, +0.50),
]
INTERPOLATION = {1: "linear", 3: "cubic"}
METHODS = ["Fixed reference", "DoG v1", "Gaussian v2", "Hybrid v3"]


def manual_row(frame: pd.DataFrame, filename: str) -> pd.Series:
    rows = frame.loc[frame["File"].astype(str) == filename]
    if len(rows) != 1:
        raise ValueError(f"Expected one manual ROI row for {filename!r}; found {len(rows)}")
    return rows.iloc[0]


def fractional_translate(image: np.ndarray, dx: float, dy: float, order: int) -> np.ndarray:
    """Shift (x, y) as (dx, dy); scipy uses (row, col) = (dy, dx).

    We use constant padding at a robust background value to avoid wrapping
    an unrelated edge into the image. BB must be far from the image edges.
    Exactly zero shift returns an untouched copy, with no interpolation.
    """
    if dx == 0 and dy == 0:
        return image.copy()
    fill = float(np.median(image))
    return ndimage_shift(
        image, shift=(dy, dx), order=order, mode="constant", cval=fill,
        prefilter=(order > 1), output=np.float64,
    )


def run_test(
    pixels: np.ndarray,
    reference_xy: tuple[float, float],
    manual_test_xy: tuple[float, float],
    *,
    search_radius: int = 18,
    orders: tuple[int, ...] = (1, 3),
) -> pd.DataFrame:
    """Evaluate fractional shifts. Labels and shifts are NEVER passed to detectors."""
    image = np.asarray(pixels, dtype=np.float64)
    if image.ndim != 2 or not np.isfinite(image).all():
        raise ValueError("Expected a finite 2D DICOM image")
    if not all(map(math.isfinite, (*reference_xy, *manual_test_xy))):
        raise ValueError("Invalid reference/manual coordinates")

    # Hold polarity constant across all shifts, derived ONLY from test image pixels
    # and the reference coordinate (not from the manual held-out test center).
    initial_dog = detect_bb(image, reference_xy, search_radius=search_radius)
    expected_polarity = initial_dog["polarity"]

    data = []
    for order in orders:
        baselines: dict[str, tuple[float, float]] = {}
        for dx, dy in SHIFTS_XY:
            translated = fractional_translate(image, dx, dy, order=order)
            shifted_manual = (manual_test_xy[0] + dx, manual_test_xy[1] + dy)

            for method in METHODS:
                row = {
                    "Interpolation": INTERPOLATION[order],
                    "Interpolation order": order,
                    "Method": method,
                    "Applied X shift (px)": dx,
                    "Applied Y shift (px)": dy,
                    "Applied magnitude (px)": math.hypot(dx, dy),
                    "Status": "detection_failed",
                    "QC flags": "",
                    "Predicted X (px)": np.nan,
                    "Predicted Y (px)": np.nan,
                    "Expected X (manual evaluation only)": shifted_manual[0],
                    "Expected Y (manual evaluation only)": shifted_manual[1],
                    "Absolute error vs manual (px)": np.nan,
                    "Recovered X shift (px)": np.nan,
                    "Recovered Y shift (px)": np.nan,
                    "Shift recovery error (px)": np.nan,
                }
                try:
                    if method == "Fixed reference":
                        result = {"center_x": reference_xy[0],
                                  "center_y": reference_xy[1], "status": "baseline"}
                    elif method == "DoG v1":
                        result = detect_bb(translated, reference_xy,
                                           search_radius=search_radius)
                    elif method == "Gaussian v2":
                        result = gaussian_refinement(translated, reference_xy)
                    else:
                        result = detect_bb_hybrid(
                            translated, reference_xy,
                            search_radius=search_radius,
                            expected_polarity=expected_polarity,
                        )
                    row["Status"] = result.get("status", "candidate_requires_review")
                    row["QC flags"] = "; ".join(result.get("qc_flags", []))
                    x, y = result.get("center_x"), result.get("center_y")
                    if x is None or y is None or not all(map(math.isfinite, (x, y))):
                        raise ValueError("No finite center returned")
                    center = (float(x), float(y))
                    row["Predicted X (px)"], row["Predicted Y (px)"] = center
                    row["Absolute error vs manual (px)"] = math.dist(center, shifted_manual)
                    if dx == 0 and dy == 0:
                        baselines[method] = center
                    if method in baselines:
                        recovered_dx = center[0] - baselines[method][0]
                        recovered_dy = center[1] - baselines[method][1]
                        row["Recovered X shift (px)"] = recovered_dx
                        row["Recovered Y shift (px)"] = recovered_dy
                        row["Shift recovery error (px)"] = math.hypot(
                            recovered_dx - dx, recovered_dy - dy
                        )
                except (ValueError, RuntimeError, OverflowError, ArithmeticError) as exc:
                    row["Status"] = "detection_failed"
                    row["QC flags"] = (
                        row["QC flags"] + ("; " if row["QC flags"] else "") + str(exc)
                    )
                data.append(row)
    return pd.DataFrame(data)


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    results = []
    for (interp, method), group in frame.groupby(["Interpolation", "Method"], sort=False):
        shifted = group[group["Applied magnitude (px)"] > 0]
        errors = shifted["Shift recovery error (px)"].dropna()
        absolute = shifted["Absolute error vs manual (px)"].dropna()
        results.append({
            "Interpolation": interp,
            "Method": method,
            "Nonzero shifts tested": len(shifted),
            "Valid shifts": len(errors),
            "Detection failures": int((shifted["Status"] == "detection_failed").sum()),
            "QC low confidence": int((shifted["Status"] == "low_confidence_requires_review").sum()),
            "Mean shift recovery error (px)": float(errors.mean()) if len(errors) else np.nan,
            "Max shift recovery error (px)": float(errors.max()) if len(errors) else np.nan,
            "Mean absolute error vs manual (px)": float(absolute.mean()) if len(absolute) else np.nan,
        })
    return pd.DataFrame(results)


def plot_one(frame: pd.DataFrame, interp: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    filtered = frame[frame["Interpolation"] == interp]
    for method in METHODS:
        group = filtered[filtered["Method"] == method].sort_values("Applied magnitude (px)")
        ax.plot(group["Applied magnitude (px)"], group["Shift recovery error (px)"],
                "o-", label=method)
        if method == "Hybrid v3":
            flagged = group[group["Status"].isin(["low_confidence_requires_review", "detection_failed"])]
            if not flagged.empty:
                ax.scatter(flagged["Applied magnitude (px)"], flagged["Shift recovery error (px)"],
                           s=100, facecolors="none", edgecolors="black", linewidths=1.5,
                           label="Hybrid: QC flagged")
    ax.set(xlabel="Known subpixel translation magnitude (px)",
           ylabel="Shift recovery error (px)",
           title=f"Simulated subpixel translation — {interp} interpolation (research only)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="Reference DICOM filename")
    parser.add_argument("--test", required=True, help="Test DICOM filename")
    parser.add_argument("--search-radius", type=int, default=18,
                        help="Coarse DoG search radius in pixels (default: 18)")
    parser.add_argument("--orders", type=int, nargs="+", default=[1, 3], choices=[1, 3],
                        help="Interpolation orders to compare: 1=linear, 3=cubic")
    args = parser.parse_args()
    if args.reference == args.test:
        parser.error("Reference and test must be different DICOM files")
    if args.search_radius < 3:
        parser.error("--search-radius must be >= 3")

    csv_manual = ROOT / "output" / "batch_phantom_results.csv"
    dicom_test = ROOT / "test_data" / args.test
    if not csv_manual.exists():
        parser.error(f"Manual comparison CSV not found: {csv_manual}")
    if not dicom_test.exists():
        parser.error(f"Test DICOM not found: {dicom_test}")
    frame = pd.read_csv(csv_manual)
    reference = manual_row(frame, args.reference)
    manual_test = manual_row(frame, args.test)
    reference_xy = (float(reference["Target Center X"]), float(reference["Target Center Y"]))
    manual_xy = (float(manual_test["Target Center X"]), float(manual_test["Target Center Y"]))

    _, pixels = load_dicom(dicom_test)
    results = run_test(pixels, reference_xy, manual_xy,
                       search_radius=args.search_radius, orders=tuple(dict.fromkeys(args.orders)))

    out = ROOT / "output"
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.test).stem
    result_csv = out / f"bb_subpixel_{stem}.csv"
    summary_csv = out / f"bb_subpixel_summary_{stem}.csv"
    results.to_csv(result_csv, index=False)
    stats = summarize(results)
    stats.to_csv(summary_csv, index=False)
    for order in dict.fromkeys(args.orders):
        name = INTERPOLATION[order]
        plot_one(results, name, out / f"bb_subpixel_{stem}_{name}.png")

    print("\nSUBPIXEL TRANSLATION VALIDATION — SIMULATED (NOT CLINICAL)")
    print(f"Reference: {args.reference} | Test: {args.test}")
    print(f"Reference center: {reference_xy}; manual test center used ONLY for scoring")
    print(stats.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print(f"\nSaved: {result_csv}\nSaved: {summary_csv}")
    for order in dict.fromkeys(args.orders):
        print(f"Saved: {out / f'bb_subpixel_{stem}_{INTERPOLATION[order]}.png'}")
    print("WARNING: interpolation changes pixel statistics; tiny errors do NOT prove real-world BB accuracy.")

if __name__ == "__main__":
    main()
