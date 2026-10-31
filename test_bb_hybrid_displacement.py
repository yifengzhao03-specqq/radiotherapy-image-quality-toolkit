"""Controlled translation comparison: fixed, DoG, v2 Gaussian, and hybrid v3.

PowerShell:
    python test_bb_hybrid_displacement.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"

All translated images are generated in memory; no source DICOM is modified.
The held-out test-image manual point and known shifts are used ONLY to score.
Only integer-pixel translation is assessed here (not real scanner motion).
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
from bb_center_refinement import gaussian_refinement
from hybrid_bb_detector import detect_bb_hybrid

SHIFTS = [(0, 0), (2, 0), (0, 2), (-2, 0), (5, 3), (-5, -3), (8, 0), (10, 5)]
METHODS = ["Fixed reference", "DoG v1", "Gaussian v2", "Hybrid v3"]


def translate_integer(image: np.ndarray, dx: int, dy: int) -> np.ndarray:
    h, w = image.shape
    if abs(dx) >= w or abs(dy) >= h:
        raise ValueError("Shift exceeds image dimensions")
    result = np.full_like(image, float(np.median(image)), dtype=np.float64)
    x1, x2 = max(0, -dx), min(w, w - dx)
    y1, y2 = max(0, -dy), min(h, h - dy)
    result[y1 + dy:y2 + dy, x1 + dx:x2 + dx] = image[y1:y2, x1:x2]
    return result


def one_row(frame: pd.DataFrame, name: str) -> pd.Series:
    rows = frame[frame["File"].astype(str) == name]
    if len(rows) != 1:
        raise ValueError(f"Need one manual ROI record for {name}, found {len(rows)}")
    return rows.iloc[0]


def run(image: np.ndarray, ref_xy: tuple[float, float], manual_xy: tuple[float, float],
        *, search_radius: int = 18) -> pd.DataFrame:
    """The applied shift is NOT passed to any detector."""
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 2 or not np.isfinite(image).all():
        raise ValueError("Need a finite 2D image")
    first = detect_bb(image, ref_xy, search_radius=search_radius)
    reference_polarity = first["polarity"]
    zero = {}
    rows = []
    for dx, dy in SHIFTS:
        translated = translate_integer(image, dx, dy)
        manual_shifted = (manual_xy[0] + dx, manual_xy[1] + dy)
        for label in METHODS:
            record = {"Method": label, "Shift X (px)": dx, "Shift Y (px)": dy,
                      "Expected X (manual evaluation only)": manual_shifted[0],
                      "Expected Y (manual evaluation only)": manual_shifted[1],
                      "Status": "failed", "QC Flags": ""}
            try:
                if label == "Fixed reference":
                    p = {"center_x": ref_xy[0], "center_y": ref_xy[1], "status": "baseline"}
                elif label == "DoG v1":
                    p = detect_bb(translated, ref_xy, search_radius=search_radius)
                elif label == "Gaussian v2":
                    p = gaussian_refinement(translated, ref_xy)
                else:
                    p = detect_bb_hybrid(translated, ref_xy, search_radius=search_radius,
                                         expected_polarity=reference_polarity)
                record["Status"] = p.get("status", "failed")
                record["QC Flags"] = "; ".join(p.get("qc_flags", []))
                center = (p.get("center_x"), p.get("center_y"))
                if any(v is None for v in center) or not all(math.isfinite(v) for v in center):
                    raise ValueError("No valid center estimate returned")
                record["Predicted X (px)"] = center[0]
                record["Predicted Y (px)"] = center[1]
                record["Absolute error to manual (px)"] = math.dist(center, manual_shifted)
                if dx == 0 and dy == 0:
                    zero[label] = center
                if label in zero:
                    recovered = (center[0] - zero[label][0], center[1] - zero[label][1])
                    record["Recovered X shift (px)"] = recovered[0]
                    record["Recovered Y shift (px)"] = recovered[1]
                    record["Shift recovery error (px)"] = math.dist(recovered, (dx, dy))
            except (ValueError, RuntimeError, OverflowError) as exc:
                record["Status"] = "detection_failed"
                record["QC Flags"] += ("; " if record["QC Flags"] else "") + str(exc)
            rows.append(record)
    return pd.DataFrame(rows)


def plot(df: pd.DataFrame, filepath: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    for label in METHODS:
        subset = df[df["Method"] == label].copy()
        subset["Translation magnitude (px)"] = np.hypot(subset["Shift X (px)"], subset["Shift Y (px)"])
        subset = subset.sort_values("Translation magnitude (px)")
        ax.plot(subset["Translation magnitude (px)"], subset["Shift recovery error (px)"],
                marker="o", label=label)
        # Flag cases that a QC heuristic would recommend for review.
        if label == "Hybrid v3":
            bad = subset[subset["Status"] != "candidate_requires_review"]
            ax.scatter(bad["Translation magnitude (px)"], bad["Shift recovery error (px)"],
                       s=130, facecolors="none", edgecolors="black", linewidths=1.8,
                       label="Hybrid: QC flagged")
    ax.set(xlabel="Applied translation magnitude (px)",
           ylabel="Shift recovery error (px)",
           title="BB localization: controlled integer-pixel translations (diagnostic only)")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(filepath, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--search-radius", type=int, default=18)
    args = parser.parse_args()
    if args.reference == args.test:
        parser.error("Reference and test images must be different")
    if args.search_radius < 3:
        parser.error("--search-radius must be at least 3 pixels")
    manual_data = pd.read_csv(ROOT / "output" / "batch_phantom_results.csv")
    ref = one_row(manual_data, args.reference)
    test = one_row(manual_data, args.test)
    ref_xy = (float(ref["Target Center X"]), float(ref["Target Center Y"]))
    manual_xy = (float(test["Target Center X"]), float(test["Target Center Y"]))
    _, image = load_dicom(ROOT / "test_data" / args.test)
    results = run(image, ref_xy, manual_xy, search_radius=args.search_radius)
    output = ROOT / "output"
    output.mkdir(parents=True, exist_ok=True)
    stem = Path(args.test).stem
    csv_path = output / f"bb_hybrid_displacement_{stem}.csv"
    png_path = output / f"bb_hybrid_displacement_{stem}.png"
    results.to_csv(csv_path, index=False)
    plot(results, png_path)
    print("\nHybrid v3 controlled displacement test — experimental")
    for label in METHODS:
        data = results[results["Method"] == label]
        errors = data["Shift recovery error (px)"].dropna()
        print(f"{label:<18} {errors.mean():.3f} px mean shift error; "
              f"{(data['Status'] == 'detection_failed').sum()} failed; "
              f"{(data['Status'] == 'low_confidence_requires_review').sum()} flagged")
    print(f"Saved: {csv_path}\nSaved: {png_path}")
    print("IMPORTANT: zero shift error alone does not prove accurate BB center localization.")

if __name__ == "__main__":
    main()
