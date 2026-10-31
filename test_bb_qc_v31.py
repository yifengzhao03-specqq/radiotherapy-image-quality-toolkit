"""Compare original v3 QC against reference-width-assisted v3.1 QC.

Run from the repository root (PowerShell):
    python test_bb_qc_v31.py --reference "10FFF_0_RI.dcm" --test "6FFF_RI.dcm"

Prerequisites: original test_bb_qc_validation.py and original v3 modules.
Synthetic case generator re-used unchanged to allow paired comparison.
The manual center of the test image is ONLY used to build synthetic cases
and score diagnostics, not to locate BB in v3/v3.1. Research use only.
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
from dicom_reader import load_dicom  # noqa: E402
from hybrid_bb_detector import detect_bb_hybrid  # noqa: E402
from hybrid_bb_detector_qc_v31 import calibrate_reference, detect_bb_hybrid_qc_v31  # noqa: E402
from test_bb_qc_validation import build_scenarios, manual_row, DIAGNOSTIC_LARGE_ERROR_PX  # noqa: E402


def is_warned(result: dict) -> bool:
    return result.get("status") in ("low_confidence_requires_review", "detection_failed") or bool(result.get("qc_flags"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", required=True)
    p.add_argument("--test", required=True)
    p.add_argument("--search-radius", type=int, default=18)
    p.add_argument("--seed", type=int, default=20261031)
    p.add_argument("--min-sigma-ratio", type=float, default=0.70)
    p.add_argument("--max-sigma-ratio", type=float, default=1.40)
    args = p.parse_args()
    if args.reference == args.test:
        p.error("Reference and test image must differ for this comparison")
    manual_path = ROOT / "output" / "batch_phantom_results.csv"
    ref_path = ROOT / "test_data" / args.reference
    test_path = ROOT / "test_data" / args.test
    for path in (manual_path, ref_path, test_path):
        if not path.is_file():
            p.error(f"Missing required file: {path}")
    manual = pd.read_csv(manual_path)
    ref_row, test_row = manual_row(manual, args.reference), manual_row(manual, args.test)
    ref_xy = float(ref_row["Target Center X"]), float(ref_row["Target Center Y"])
    test_xy = float(test_row["Target Center X"]), float(test_row["Target Center Y"])
    _, ref_image = load_dicom(ref_path)
    _, test_image = load_dicom(test_path)
    ref_image = np.asarray(ref_image, dtype=np.float64)
    test_image = np.asarray(test_image, dtype=np.float64)
    if ref_image.shape != test_image.shape:
        p.error("Reference/test images must have compatible geometry")
    try:
        calibration = calibrate_reference(ref_image, ref_xy, search_radius=args.search_radius)
    except ValueError as e:
        p.error(str(e))

    # Test-derived labels are confined to synthetic scenario creation/evaluation.
    scenarios = build_scenarios(test_image, test_xy, args.seed)
    rows = []
    for name, truth, altered, description in scenarios:
        old = detect_bb_hybrid(
            altered, ref_xy, search_radius=args.search_radius,
            expected_polarity=calibration["reference_polarity"],
        )
        new = detect_bb_hybrid_qc_v31(
            altered, ref_xy, calibration=calibration, search_radius=args.search_radius,
            min_sigma_ratio=args.min_sigma_ratio, max_sigma_ratio=args.max_sigma_ratio,
        )
        x, y = new.get("center_x"), new.get("center_y")
        has_estimate = x is not None and y is not None and np.isfinite([x, y]).all()
        distance = math.dist((float(x), float(y)), test_xy) if has_estimate and truth == "present" else np.nan
        # >2 pixels is ONLY a synthetic diagnostic label, not a BB QC threshold.
        issue = (truth == "absent" or (truth == "present" and (not has_estimate or distance > DIAGNOSTIC_LARGE_ERROR_PX)))
        rows.append({
            "Case": name, "BB truth (synthetic)": truth,
            "v3 status": old["status"], "v3 flags": ";".join(old["qc_flags"]),
            "v3.1 status": new["status"], "v3.1 flags": ";".join(new["qc_flags"]),
            "Reference fitted sigma": new["reference_sigma"],
            "Test fitted sigma": new.get("gaussian_sigma"),
            "Sigma ratio to trusted reference": new["sigma_ratio_to_reference"],
            "Distance to manually marked BB (px; if present)": distance,
            "Diagnostic issue present": issue,
            "v3 missed specific warning": issue and not is_warned(old),
            "v3.1 missed specific warning": issue and not is_warned(new),
            "v3.1 warned": is_warned(new),
        })
    frame = pd.DataFrame(rows)
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    stem = Path(args.test).stem
    csv_path = out_dir / f"bb_qc_v31_{stem}.csv"
    fig_path = out_dir / f"bb_qc_v31_{stem}.png"
    frame.to_csv(csv_path, index=False)

    # A compact overview of actual heuristic warning behavior.
    fig, ax = plt.subplots(figsize=(11.5, 5))
    for idx, (label, column) in enumerate([
        ("Original v3", "v3 missed specific warning"),
        ("Reference-width QC v3.1", "v3.1 missed specific warning"),
    ]):
        warnings = []
        for _, row in frame.iterrows():
            if row[column]:
                mark = "MISS"
            elif row["Diagnostic issue present"]:
                mark = "FLAGGED"
            else:
                mark = "NO DIAGNOSTIC ISSUE"
            warnings.append(mark)
        for col, mark in enumerate(warnings):
            ax.text(col, idx, mark.replace("NO DIAGNOSTIC ISSUE", "NO ISSUE"),
                    ha="center", va="center", rotation=55, fontsize=8)
    ax.set_xlim(-0.6, len(frame)-0.4)
    ax.set_ylim(-0.7, 1.7)
    ax.set_xticks(range(len(frame)), frame["Case"], rotation=35, ha="right", fontsize=9)
    ax.set_yticks([0, 1], ["Original v3", "v3.1 reference-width"])
    ax.grid(axis="x", alpha=0.15)
    fig.suptitle("Synthetic QC stress test: warning gaps (research only)")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    print("\nResearch-only synthetic QC comparison; neither version auto-approves BBs")
    print(f"Reference width sigma: {calibration['reference_sigma']:.3f} px")
    print(frame[["Case", "v3 status", "v3.1 status", "Sigma ratio to trusted reference", "v3 missed specific warning", "v3.1 missed specific warning"]].to_string(index=False))
    print("\nMissed-specific-warning counts (synthetic diagnostic only):",
          int(frame["v3 missed specific warning"].sum()), "->",
          int(frame["v3.1 missed specific warning"].sum()))
    print("Files:", csv_path, fig_path, sep="\n  ")


if __name__ == "__main__":
    main()
