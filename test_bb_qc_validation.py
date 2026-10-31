"""Stress-test the *existing* Hybrid v3 BB detector's heuristic QC.

Research/diagnostic tool only. Does not modify DICOMs or the detector.

Example (VS Code / PowerShell, from repository root):
    python test_bb_qc_validation.py --reference "10FFF_0_RI.dcm" --test "6FFF_RI.dcm"

Requires src/dicom_reader.py, src/bb_detector.py, src/bb_center_refinement.py,
src/hybrid_bb_detector.py; test_data/*.dcm; output/batch_phantom_results.csv.

The test-image manual BB location is held out from the detector but used to
construct controlled perturbations AND evaluate localization error. That
makes this a diagnostic stress test, NOT an unbiased validation dataset.
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
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from dicom_reader import load_dicom  # noqa: E402
from bb_detector import detect_bb  # noqa: E402
from hybrid_bb_detector import detect_bb_hybrid  # noqa: E402


# Arbitrary, illustrative engineering diagnostic; NOT a validated tolerance.
DIAGNOSTIC_LARGE_ERROR_PX = 2.0


def manual_row(frame: pd.DataFrame, filename: str) -> pd.Series:
    rows = frame.loc[frame["File"].astype(str) == filename]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one manual ROI row for {filename!r}; found {len(rows)}")
    return rows.iloc[0]


def background_model(image: np.ndarray, center: tuple[float, float],
                     radius: float = 29.0) -> tuple[np.ndarray, float]:
    """Local plane + high-frequency noise estimate from a BB-external annulus.

    This synthetic background is imperfect on a complex thorax phantom.
    The removed-BB scenario is an approximate negative control, NOT a true
    independent BB-free acquisition.
    """
    cx, cy = center
    h, w = image.shape
    x1 = max(0, math.floor(cx - radius - 2))
    x2 = min(w, math.ceil(cx + radius + 2) + 1)
    y1 = max(0, math.floor(cy - radius - 2))
    y2 = min(h, math.ceil(cy + radius + 2) + 1)
    yy, xx = np.mgrid[y1:y2, x1:x2]
    patch = image[y1:y2, x1:x2]
    d = np.hypot(xx - cx, yy - cy)
    annulus = (d >= 22.0) & (d <= radius)
    if annulus.sum() < 40:
        raise ValueError("Insufficient surrounding background pixels; BB too near image edge")
    A = np.column_stack((np.ones(annulus.sum()),
                         (xx - cx)[annulus], (yy - cy)[annulus]))
    b = patch[annulus]
    beta = np.linalg.lstsq(A, b, rcond=None)[0]
    # One robust reweighting pass prevents one strong linear structure from
    # overwhelming the low-order plane estimate.
    residual = b - A @ beta
    scale = max(float(1.4826 * np.median(np.abs(residual - np.median(residual)))), 1e-3)
    weights = np.minimum(1.0, 2.5 * scale / np.maximum(np.abs(residual), 1e-9))
    Aw = A * np.sqrt(weights)[:, None]
    bw = b * np.sqrt(weights)
    beta = np.linalg.lstsq(Aw, bw, rcond=None)[0]
    plane_patch = beta[0] + beta[1] * (xx - cx) + beta[2] * (yy - cy)
    # High-frequency variation from the neighboring BB-external annulus.
    highfreq = patch - gaussian_filter(patch, sigma=1.2, mode="reflect")
    hf = highfreq[annulus]
    noise_sd = max(float(1.4826 * np.median(np.abs(hf - np.median(hf)))), 1e-3)
    return (x1, x2, y1, y2, plane_patch), noise_sd


def synthetic_background(image: np.ndarray, center: tuple[float, float],
                         *, seed: int, inner: float = 16.0,
                         outer: float = 22.0) -> np.ndarray:
    """Replace BB with smooth blend to neighboring planar/noisy background."""
    array = np.asarray(image, dtype=np.float64)
    info, noise_sd = background_model(array, center)
    x1, x2, y1, y2, plane = info
    yy, xx = np.mgrid[y1:y2, x1:x2]
    d = np.hypot(xx - center[0], yy - center[1])
    weight = np.clip((outer - d) / (outer - inner), 0, 1)
    # Cosine taper avoids the sharp ring of naive cut-and-paste removal.
    weight = 0.5 - 0.5 * np.cos(np.pi * weight)
    rng = np.random.default_rng(seed)
    replacement = plane + rng.normal(0, noise_sd, size=plane.shape)
    out = array.copy()
    out[y1:y2, x1:x2] = ((1 - weight) * array[y1:y2, x1:x2]
                              + weight * replacement)
    return out


def reduce_bb_contrast(image: np.ndarray, center: tuple[float, float],
                       fraction: float, *, seed: int) -> np.ndarray:
    """Interpolate between the original and the synthetic no-BB image."""
    absent = synthetic_background(image, center, seed=seed)
    # This changes the BB region, not the surrounding DICOM pixel data.
    return fraction * image + (1.0 - fraction) * absent


def partial_occlusion(image: np.ndarray, center: tuple[float, float],
                      *, seed: int) -> np.ndarray:
    """Remove about half the marker via smooth synthetic background blending."""
    clean = synthetic_background(image, center, seed=seed)
    cx, cy = center
    y1, y2 = max(0, int(cy - 30)), min(image.shape[0], int(cy + 32))
    x1, x2 = max(0, int(cx - 30)), min(image.shape[1], int(cx + 32))
    yy, xx = np.mgrid[y1:y2, x1:x2]
    r = np.hypot(xx - cx, yy - cy)
    left_half = np.clip((xx - cx + 1.5) / 3.0, 0, 1)  # x >= cx gets replaced
    rad = np.clip((22.0 - r) / 6.0, 0, 1)
    weight = left_half * rad
    out = image.copy()
    out[y1:y2, x1:x2] = ((1 - weight) * image[y1:y2, x1:x2]
                              + weight * clean[y1:y2, x1:x2])
    return out


def add_decoy(image: np.ndarray, center: tuple[float, float],
              amplitude: float, offset: tuple[float, float] = (13.0, -11.0)) -> np.ndarray:
    """Add one synthetic bright BB-like spot within the approximate search area."""
    out = image.copy()
    cx, cy = center[0] + offset[0], center[1] + offset[1]
    x1, x2 = max(0, int(cx - 22)), min(out.shape[1], int(cx + 23))
    y1, y2 = max(0, int(cy - 22)), min(out.shape[0], int(cy + 23))
    yy, xx = np.mgrid[y1:y2, x1:x2]
    out[y1:y2, x1:x2] += amplitude * np.exp(-0.5 * ((xx - cx)**2 + (yy - cy)**2) / 3.0**2)
    return out


def build_scenarios(image: np.ndarray, manual_xy: tuple[float, float],
                    seed: int) -> list[tuple[str, str, np.ndarray, str]]:
    """Return name, truth label, altered image, test explanation.

    These use HELD-OUT manual coordinates ONLY for simulation, NEVER detection.
    """
    arr = np.asarray(image, dtype=np.float64)
    if arr.ndim != 2 or not np.all(np.isfinite(arr)):
        raise ValueError("Expected a finite 2D original DICOM image")
    cx, cy = manual_xy
    info, _ = background_model(arr, manual_xy)
    x1, x2, y1, y2, plane = info
    center_pixel = arr[int(round(cy)), int(round(cx))]
    background_center = float(plane[int(round(cy)) - y1, int(round(cx)) - x1])
    # Prefer local center contrast but guard against unstable tiny estimates.
    center_contrast = max(abs(float(center_pixel - background_center)),
                          float(np.std(arr[y1:y2, x1:x2])), 1.0)
    rng = np.random.default_rng(seed + 1234)
    absent = synthetic_background(arr, manual_xy, seed=seed + 20)
    # Correct for the sign of marker: actual test images here show a bright BB.
    sign = 1 if center_pixel >= background_center else -1

    return [
        ("normal", "present", arr.copy(), "Original unmodified test DICOM"),
        ("contrast_50pct", "present",
         reduce_bb_contrast(arr, manual_xy, 0.50, seed=seed+1), "Simulated BB contrast 50%"),
        ("contrast_15pct", "present",
         reduce_bb_contrast(arr, manual_xy, 0.15, seed=seed+2), "Simulated BB contrast 15%"),
        ("noise_moderate", "present",
         arr + rng.normal(0, 0.25*center_contrast, size=arr.shape), "Added Gaussian noise, sigma=0.25*contrast"),
        ("noise_high", "present",
         arr + rng.normal(0, 0.75*center_contrast, size=arr.shape), "Added Gaussian noise, sigma=0.75*contrast"),
        ("half_obscured", "present", partial_occlusion(arr, manual_xy, seed=seed+3), "Half of BB is smoothly masked"),
        ("bb_removed", "absent", absent, "Synthetic BB removal via fitted background"),
        ("bb_removed_decoy", "absent", add_decoy(absent, manual_xy, sign*1.8*center_contrast),
         "No BB; artificial Gaussian spot offset ~17 px from BB"),
        ("bb_present_decoy", "present", add_decoy(arr, manual_xy, sign*1.8*center_contrast),
         "Real BB plus artificial nearby Gaussian decoy"),
        ("flat_image", "absent", np.full_like(arr, float(np.median(arr))),
         "Uniform image; deliberately unrealistic negative control"),
    ]


def evaluate(pixels: np.ndarray, reference_xy: tuple[float, float],
             manual_xy: tuple[float, float], *, search_radius: int,
             seed: int, expected_polarity: str) -> tuple[pd.DataFrame, list[tuple[str, str, np.ndarray, str]]]:
    cases = build_scenarios(pixels, manual_xy, seed)
    rows = []
    for name, truth, altered, note in cases:
        try:
            result = detect_bb_hybrid(altered, reference_xy,
                                      search_radius=search_radius,
                                      expected_polarity=expected_polarity)
        except Exception as exc:
            result = {"status": "detection_failed", "qc_flags": [f"unhandled_exception:{type(exc).__name__}:{exc}"],
                      "center_x": None, "center_y": None}
        status = result.get("status", "detection_failed")
        flags = result.get("qc_flags", [])
        x, y = result.get("center_x"), result.get("center_y")
        has_center = (x is not None and y is not None and
                      math.isfinite(float(x)) and math.isfinite(float(y)))
        distance = math.dist((float(x), float(y)), manual_xy) if (has_center and truth == "present") else np.nan
        warning = (status in ("detection_failed", "low_confidence_requires_review") or bool(flags))
        # These events are DIAGNOSTIC. 'candidate_requires_review' is still NEVER approved.
        issue = truth == "absent" or (truth == "present" and has_center and distance > DIAGNOSTIC_LARGE_ERROR_PX)
        if truth == "present" and not has_center:
            issue = True
        missed_warning = issue and not warning
        rows.append({
            "Case": name,
            "BB truth (simulation)": truth,
            "Scenario": note,
            "Predicted X (px)": float(x) if has_center else np.nan,
            "Predicted Y (px)": float(y) if has_center else np.nan,
            "Distance to manually marked BB (px; if present)": distance,
            "QC status": status,
            "QC flags": ";".join(map(str, flags)),
            "DoG score": result.get("dog_score", np.nan),
            "Gaussian sigma": result.get("gaussian_sigma", np.nan),
            "Relative fit RMS": result.get("relative_fit_rms", np.nan),
            "Coarse-refined distance (px)": result.get("coarse_refined_gap", np.nan),
            "Specific QC warning triggered": bool(warning),
            "Diagnostic issue present": bool(issue),
            "Potential QC warning miss": bool(missed_warning),
        })
    return pd.DataFrame(rows), cases


def plot_cases(cases: list[tuple[str, str, np.ndarray, str]],
               frame: pd.DataFrame, center: tuple[float, float], path: Path) -> None:
    cx, cy = center
    half = 26
    x1, x2 = int(cx-half), int(cx+half)+1
    y1, y2 = int(cy-half), int(cy+half)+1
    a = cases[0][2][y1:y2, x1:x2]
    vmin, vmax = np.percentile(a, [5, 99.5])
    if vmax <= vmin:
        vmax = vmin + 1
    fig, axes = plt.subplots(2, 5, figsize=(16, 7.3), constrained_layout=True)
    for ax, (name, truth, arr, note) in zip(axes.flat, cases):
        row = frame.loc[frame["Case"] == name].iloc[0]
        ax.imshow(arr[y1:y2, x1:x2], cmap="gray", origin="upper",
                  extent=[x1-.5, x2-.5, y2-.5, y1-.5], vmin=vmin, vmax=vmax)
        if truth == "present":
            ax.plot(cx, cy, marker="+", color="magenta", markersize=11, markeredgewidth=2)
        if np.isfinite(row["Predicted X (px)"]):
            ax.plot(row["Predicted X (px)"], row["Predicted Y (px)"],
                    marker="x", color="cyan", markersize=10, markeredgewidth=2)
        status = row["QC status"]
        readable = {"candidate_requires_review":"candidate (review)",
                    "low_confidence_requires_review":"low confidence",
                    "detection_failed":"FAILED"}.get(status, status)
        ax.set_title(f"{name}\n{readable}", fontsize=9)
        ax.set_xlim(cx-24, cx+24)
        ax.set_ylim(cy+24, cy-24)
        ax.tick_params(labelsize=7)
    fig.suptitle("Hybrid v3 heuristic QC challenge (synthetic; NOT clinical validation)\n"
                 "magenta + = manual BB (if present); cyan x = predicted center",
                 fontsize=13)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, help="Reference DICOM basename in test_data/")
    parser.add_argument("--test", required=True, help="Test DICOM basename in test_data/")
    parser.add_argument("--search-radius", type=int, default=18)
    parser.add_argument("--seed", type=int, default=20261031, help="Deterministic random seed")
    args = parser.parse_args()
    if args.reference == args.test:
        parser.error("Reference and test should be different DICOM files")
    if args.search_radius < 3:
        parser.error("--search-radius must be >= 3")
    csv_path = ROOT / "output" / "batch_phantom_results.csv"
    ref_path = ROOT / "test_data" / args.reference
    test_path = ROOT / "test_data" / args.test
    for path in (csv_path, ref_path, test_path):
        if not path.is_file():
            parser.error(f"Missing file: {path}")

    frame = pd.read_csv(csv_path)
    ref = manual_row(frame, args.reference)
    test = manual_row(frame, args.test)
    reference_xy = (float(ref["Target Center X"]), float(ref["Target Center Y"]))
    manual_xy = (float(test["Target Center X"]), float(test["Target Center Y"]))
    _, ref_img = load_dicom(ref_path)
    _, pixels = load_dicom(test_path)
    ref_img = np.asarray(ref_img, dtype=np.float64)
    pixels = np.asarray(pixels, dtype=np.float64)
    if ref_img.shape != pixels.shape:
        parser.error(f"DICOM image shapes differ: {ref_img.shape} vs {pixels.shape}")

    # Expected BB polarity inferred from the REFERENCE DICOM, not the altered test.
    ref_dog = detect_bb(ref_img, reference_xy, search_radius=args.search_radius)
    expected_polarity = ref_dog["polarity"]
    frame_result, cases = evaluate(pixels, reference_xy, manual_xy,
                                  search_radius=args.search_radius,
                                  seed=args.seed, expected_polarity=expected_polarity)
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    stem = Path(args.test).stem
    csv_out = out / f"bb_qc_{stem}.csv"
    png_out = out / f"bb_qc_{stem}.png"
    frame_result.to_csv(csv_out, index=False)
    plot_cases(cases, frame_result, manual_xy, png_out)

    print("\nBB QC STRESS TEST — synthetic alterations, NOT a clinical validation")
    print(f"Test: {args.test}; reference: {args.reference}; seed={args.seed}")
    print(f"Reference polarity: {expected_polarity}")
    print(frame_result[["Case", "BB truth (simulation)", "QC status",
                        "Distance to manually marked BB (px; if present)",
                        "Potential QC warning miss"]].to_string(index=False,
                            float_format=lambda v: f"{v:.3f}"))
    missed = int(frame_result["Potential QC warning miss"].sum())
    absent_missed = int(frame_result.loc[frame_result["BB truth (simulation)"] == "absent",
                                         "Potential QC warning miss"].sum())
    print(f"\nPotential missed specific QC warnings: {missed} / {len(frame_result)} scenarios")
    print(f"Unflagged synthetic BB-absent cases: {absent_missed} / "
          f"{sum(frame_result['BB truth (simulation)'] == 'absent')}")
    print("IMPORTANT: even unflagged 'candidate_requires_review' still requires manual review.")
    print(f"Saved CSV: {csv_out}\nSaved PNG: {png_out}")
    if missed:
        print("Existing heuristics did NOT warn on all designed failures; do not auto-approve candidates.")


if __name__ == "__main__":
    main()
