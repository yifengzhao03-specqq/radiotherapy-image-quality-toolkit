"""One-time installer for the optional interactive ROI viewer.

Extract both this file and src/interactive_roi_selector.py into the
radiotherapy-image-quality-toolkit root, then run: python install_roi_ui.py
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
BATCH = ROOT / "batch_manual_roi_analysis.py"
VIEWER = ROOT / "src" / "interactive_roi_selector.py"
BACKUP = ROOT / "batch_manual_roi_analysis.py.before_roi_ui.bak"

if not BATCH.exists() or not VIEWER.exists():
    raise SystemExit(
        "Files missing. Extract the ZIP into your project ROOT; you should see "
        "batch_manual_roi_analysis.py and src/interactive_roi_selector.py."
    )

original = BATCH.read_text(encoding="utf-8")
if "from interactive_roi_selector import" in original:
    print("Interactive ROI viewer is already installed; no changes made.")
    raise SystemExit(0)

replacements = [
    (
        "from roi_selector import (\n    select_two_circular_rois\n)",
        "from interactive_roi_selector import (\n    select_two_circular_rois\n)",
    ),
    (
        "    ) = select_two_circular_rois(\n"
        "        image,\n"
        "        window_level=WINDOW_LEVEL,\n"
        "        window_width=WINDOW_WIDTH\n"
        "    )",
        "    ) = select_two_circular_rois(\n"
        "        image,\n"
        "        window_level=WINDOW_LEVEL,\n"
        "        window_width=WINDOW_WIDTH\n"
        "    )\n\n"
        "    # Use the settings actually selected in the viewer.\n"
        "    wl_used = target_circle[\"window_level\"]\n"
        "    ww_used = target_circle[\"window_width\"]",
    ),
    (
        '        "Window Level":\n            WINDOW_LEVEL,',
        '        "Window Level":\n            wl_used,',
    ),
    (
        '        "Window Width":\n            WINDOW_WIDTH,',
        '        "Window Width":\n            ww_used,',
    ),
    (
        "from visualization import apply_window\n",
        "",
    ),
    (
        "    display_image = apply_window(\n"
        "        image,\n"
        "        WINDOW_LEVEL,\n"
        "        WINDOW_WIDTH\n"
        "    )",
        "    # Keep original pixel data; apply WL/WW only to rendering.\n"
        "    display_image = image",
    ),
    (
        "    ax.imshow(\n        display_image,\n        cmap=\"gray\"\n    )",
        "    ax.imshow(\n"
        "        display_image,\n"
        "        cmap=\"gray\",\n"
        "        vmin=wl_used - ww_used / 2,\n"
        "        vmax=wl_used + ww_used / 2\n"
        "    )",
    ),
    (
        'f"WL={WINDOW_LEVEL}, WW={WINDOW_WIDTH}"',
        'f"WL={wl_used:.1f}, WW={ww_used:.1f}"',
    ),
]

updated = original
for old, new in replacements:
    count = updated.count(old)
    if count != 1:
        raise SystemExit(
            f"Could not apply update safely (expected one match, found {count})\n"
            f"Missing code snippet: {old[:65]!r}\n"
            "Your local script may differ from the public main version; "
            "no files were changed."
        )
    updated = updated.replace(old, new, 1)

if not BACKUP.exists():
    shutil.copy2(BATCH, BACKUP)
BATCH.write_text(updated, encoding="utf-8")
print("Interactive ROI UI installed successfully.")
print("Backup:", BACKUP.name)
print("Run: python batch_manual_roi_analysis.py")
