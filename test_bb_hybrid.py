"""Compare reference-guided DoG and Gaussian v2 with the new hybrid v3.

PowerShell:
    python test_bb_hybrid.py --reference "10FFF_0_RI.dcm" --test "10x_RI.dcm"

Requires manual-ROI CSV from your previous runs for *evaluation only*.
DO NOT use the test image's manual mark to perform detection.
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


def one_row(frame: pd.DataFrame, filename: str) -> pd.Series:
    subset = frame[frame["File"].astype(str) == filename]
    if len(subset) != 1:
        raise ValueError(f"Expected one row for {filename!r}; found {len(subset)}")
    return subset.iloc[0]


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

    frame = pd.read_csv(ROOT / "output" / "batch_phantom_results.csv")
    ref = one_row(frame, args.reference)
    test = one_row(frame, args.test)
    ref_xy = (float(ref["Target Center X"]), float(ref["Target Center Y"]))
    test_manual = (float(test["Target Center X"]), float(test["Target Center Y"]))
    _, pixels = load_dicom(ROOT / "test_data" / args.test)
    pixels = np.asarray(pixels, dtype=np.float64)

    predictions = {}
    predictions["Fixed reference"] = {"center_x": ref_xy[0], "center_y": ref_xy[1], "status": "baseline"}
    try:
        dog = detect_bb(pixels, ref_xy, search_radius=args.search_radius)
        predictions["DoG v1"] = dog
        predictions["Gaussian v2"] = gaussian_refinement(pixels, ref_xy)
        predictions["Hybrid v3"] = detect_bb_hybrid(
            pixels, ref_xy, search_radius=args.search_radius,
            expected_polarity=dog["polarity"],
        )
    except (ValueError, RuntimeError, OverflowError) as exc:
        raise SystemExit(f"Unable to run baseline detector: {exc}") from exc

    rows = []
    print("\nBB localization comparison — research prototype")
    for label, result in predictions.items():
        pos = (result.get("center_x"), result.get("center_y"))
        if any(value is None for value in pos):
            distance = float("nan")
        else:
            distance = math.dist(pos, test_manual)
        row = {"File": args.test, "Method": label,
               "Center X": pos[0], "Center Y": pos[1],
               "Manual X (evaluation only)": test_manual[0],
               "Manual Y (evaluation only)": test_manual[1],
               "Distance to manual (px)": distance,
               "QC Status": result.get("status"),
               "QC Flags": "; ".join(result.get("qc_flags", [])),
               "DoG score": result.get("dog_score", result.get("contrast_score")),
               "Gaussian sigma": result.get("gaussian_sigma", result.get("sigma")),
               "Relative fit RMS": result.get("relative_fit_rms"),
               "Coarse X": result.get("coarse_x"),
               "Coarse Y": result.get("coarse_y")}
        rows.append(row)
        print(f"{label:17} distance={distance:.3f} px  "
              f"status={result.get('status')}  flags={row['QC Flags']}")

    stem = Path(args.test).stem
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"bb_hybrid_{stem}.csv"
    png_path = output_dir / f"bb_hybrid_{stem}.png"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    wl, ww = float(test.get("Window Level", np.nan)), float(test.get("Window Width", np.nan))
    if not np.isfinite(wl) or not np.isfinite(ww) or ww <= 0:
        wl = float(np.median(pixels))
        ww = max(1.0, float(np.percentile(pixels, 99) - np.percentile(pixels, 1)))
    fig, ax = plt.subplots(figsize=(7.2, 6.6))
    ax.imshow(pixels, cmap="gray", origin="upper", vmin=wl - ww / 2, vmax=wl + ww / 2)
    styles = {"Fixed reference": ("o", "orange"),
              "DoG v1": ("+", "lime"),
              "Gaussian v2": ("*", "yellow"),
              "Hybrid v3": ("x", "cyan")}
    for label, result in predictions.items():
        if result.get("center_x") is None or result.get("center_y") is None:
            continue
        marker, color = styles[label]
        ax.plot(result["center_x"], result["center_y"], color=color, marker=marker,
                ms=13, mew=2.3, linestyle="None", label=label)
    ax.plot(*test_manual, marker="P", color="magenta", ms=10,
            linestyle="None", label="Manual (evaluation only)")
    ax.set_xlim(ref_xy[0] - 25, ref_xy[0] + 25)
    ax.set_ylim(ref_xy[1] + 25, ref_xy[1] - 25)
    ax.set(xlabel="X (px)", ylabel="Y (px)",
           title=f"Coarse-to-fine BB localization — {args.test}\nExperimental; manual label held out")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(png_path, dpi=170)
    plt.close(fig)
    print(f"Saved: {csv_path}\nSaved: {png_path}")
    print("All detections remain experimental; QC status is not clinical approval.")

if __name__ == "__main__":
    main()
