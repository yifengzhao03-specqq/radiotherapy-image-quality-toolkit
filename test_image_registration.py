"""Run first registration test after finishing manual ROI annotation.

Usage:
    python test_image_registration.py
    python test_image_registration.py --reference image_01.dcm --moving image_02.dcm

Inputs: test_data/*.dcm, optional output/batch_phantom_results.csv
Output: output/registration_preview.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from dicom_reader import load_dicom
from image_registration import estimate_translation


def add_circle(ax, x, y, radius, *, color, linestyle="-"):
    if not all(np.isfinite(v) for v in (x, y, radius)):
        return
    ax.add_patch(Circle((x, y), radius, facecolor="none",
                        edgecolor=color, linewidth=2, linestyle=linestyle))


def configure_image(ax, image, title):
    low, high = np.percentile(image, [1, 99])
    if high <= low:
        low, high = float(np.min(image)), float(np.max(image))
    if high <= low:
        high = low + 1
    ax.imshow(image, cmap="gray", vmin=low, vmax=high)
    ax.set_title(title, fontsize=10)
    ax.set_axis_off()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", help="Name of .dcm file in test_data")
    parser.add_argument("--moving", help="Name of .dcm file in test_data")
    args = parser.parse_args()
    folder = ROOT / "test_data"
    files = sorted(folder.glob("*.dcm"))
    if len(files) < 2:
        raise SystemExit("Put at least TWO .dcm files in test_data/ first.")

    reference_path = folder / args.reference if args.reference else files[0]
    moving_path = folder / args.moving if args.moving else files[1]
    if not reference_path.is_file() or not moving_path.is_file():
        raise SystemExit("One or both specified DICOM files were not found in test_data/.")
    if reference_path.resolve() == moving_path.resolve():
        raise SystemExit("Choose TWO different DICOM files.")

    _, reference = load_dicom(reference_path)
    _, moving = load_dicom(moving_path)
    dx, dy = estimate_translation(reference, moving)
    print("\n=== First image-registration test ===")
    print(f"Reference: {reference_path.name}")
    print(f"Moving:    {moving_path.name}")
    print(f"Reference ROI -> moving ROI: dx = {dx:+.2f} px, dy = {dy:+.2f} px")
    print("Positive dx means right, positive dy means down.")
    print("IMPORTANT: visually check the preview before trusting these shifts.")

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), constrained_layout=True)
    configure_image(axes[0], reference, f"Reference: {reference_path.name}")
    configure_image(axes[1], moving, f"Moving: {moving_path.name}\ndx={dx:+.1f}, dy={dy:+.1f} px")

    csv_path = ROOT / "output" / "batch_phantom_results.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        ref_matches = df.loc[df["File"] == reference_path.name]
        moving_matches = df.loc[df["File"] == moving_path.name]
        if not ref_matches.empty:
            r = ref_matches.iloc[0]
            for prefix, color in (("Target", "red"), ("Background", "cyan")):
                x = float(r[f"{prefix} Center X"])
                y = float(r[f"{prefix} Center Y"])
                radius = float(r[f"{prefix} Radius"])
                add_circle(axes[0], x, y, radius, color=color)
                add_circle(axes[1], x + dx, y + dy, radius, color=color)
                if not moving_matches.empty:
                    m = moving_matches.iloc[0]
                    mx, my = float(m[f"{prefix} Center X"]), float(m[f"{prefix} Center Y"])
                    error = np.hypot(x + dx - mx, y + dy - my)
                    print(f"{prefix} center difference vs manual moving ROI: {error:.2f} px")
                    # White dashed circle indicates the user's manual annotation.
                    add_circle(axes[1], mx, my, float(m[f"{prefix} Radius"]),
                               color="white", linestyle="--")
            print("Preview: red/cyan = propagated ROIs; white dashed = manually drawn ROIs.")
        else:
            print("No matching reference row in CSV; generating image-only preview.")
    else:
        print("Manual ROI CSV not found; generating image-only preview.")

    output = ROOT / "output" / "registration_preview.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160)
    plt.close(fig)
    print(f"Saved preview: {output}")


if __name__ == "__main__":
    main()
