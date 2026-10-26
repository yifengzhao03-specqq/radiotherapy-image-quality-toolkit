"""Interactive two-ROI selector with explicit draw modes and live WL/WW.

Place this file at src/interactive_roi_selector.py in the toolkit project.
All ROI coordinates refer to ORIGINAL image pixels. WL/WW affects display only.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.widgets import Button, Slider, TextBox


def select_two_circular_rois(image, window_level=None, window_width=None):
    """Pick target/background circles while allowing pan, zoom and live WL/WW.

    Returns
    -------
    (target_roi, background_roi): dicts with center_x, center_y, radius,
    window_level and window_width (extra fields are backward compatible).
    """
    data = np.asarray(image)
    if data.ndim != 2 or not np.issubdtype(data.dtype, np.number):
        raise ValueError("Expected a 2D numeric grayscale image.")
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        raise ValueError("Image does not contain finite pixel values.")

    data_min = float(np.min(finite))
    data_max = float(np.max(finite))
    data_span = max(data_max - data_min, 1e-6)
    p_low, p_high = np.percentile(finite, [1, 99])
    auto_width = max(float(p_high - p_low), data_span / 100, 1e-6)
    auto_level = float((p_high + p_low) / 2)

    # Add padding so users can explore outside the occupied intensity range.
    wl_min = data_min - 0.5 * data_span
    wl_max = data_max + 0.5 * data_span
    ww_min = max(data_span / 10000, 1e-6)
    ww_max = max(3 * data_span, auto_width, ww_min * 10)

    init_wl = (float(window_level) if window_level is not None
               else auto_level)
    init_ww = (float(window_width) if window_width is not None
               else auto_width)
    if not np.isfinite(init_wl) or not wl_min <= init_wl <= wl_max:
        init_wl = auto_level
    if not np.isfinite(init_ww) or not ww_min <= init_ww <= ww_max:
        init_ww = auto_width
    init_wl = float(np.clip(init_wl, wl_min, wl_max))
    init_ww = float(np.clip(init_ww, ww_min, ww_max))

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.91, bottom=0.34)
    view = ax.imshow(data, cmap="gray",
                     vmin=init_wl - init_ww / 2,
                     vmax=init_wl + init_ww / 2,
                     interpolation="nearest")
    ax.set_title("DICOM ROI Viewer — View mode")
    ax.set_axis_off()
    status = fig.text(0.5, 0.028,
                      "VIEW: zoom/pan freely. Click Target ROI or Background ROI to draw.",
                      ha="center", fontsize=9)

    slider_wl = Slider(fig.add_axes([0.17, 0.272, 0.56, 0.026]),
                       "WL", wl_min, wl_max, valinit=init_wl, valfmt="%.1f")
    slider_ww = Slider(fig.add_axes([0.17, 0.227, 0.56, 0.026]),
                       "WW", ww_min, ww_max, valinit=init_ww, valfmt="%.1f")
    text_wl = TextBox(fig.add_axes([0.78, 0.260, 0.15, 0.042]),
                      "", initial=f"{init_wl:.1f}")
    text_ww = TextBox(fig.add_axes([0.78, 0.213, 0.15, 0.042]),
                      "", initial=f"{init_ww:.1f}")

    button_target = Button(fig.add_axes([0.06, 0.116, 0.16, 0.051]), "Target ROI")
    button_background = Button(fig.add_axes([0.235, 0.116, 0.19, 0.051]), "Background ROI")
    button_clear = Button(fig.add_axes([0.445, 0.116, 0.12, 0.051]), "Clear")
    button_confirm = Button(fig.add_axes([0.590, 0.116, 0.17, 0.051]), "Confirm")
    button_cancel = Button(fig.add_axes([0.780, 0.116, 0.15, 0.051]), "Cancel")
    button_auto = Button(fig.add_axes([0.78, 0.170, 0.15, 0.034]), "Auto WL/WW")

    rois = {"target": None, "background": None}
    artists = {"target": None, "background": None}
    temporary_marker = {"artist": None}
    stage = {"mode": "view", "center": None}
    result = {"confirmed": False}
    syncing = {"active": False}

    def message(text):
        status.set_text(text)
        fig.canvas.draw_idle()

    def set_view_mode():
        stage["mode"] = "view"
        stage["center"] = None
        if temporary_marker["artist"] is not None:
            temporary_marker["artist"].remove()
            temporary_marker["artist"] = None
        ax.set_title("DICOM ROI Viewer — View mode")
        message("VIEW: change WL/WW, wheel zoom, toolbar pan/zoom; choose ROI to draw.")

    def on_slider(_value):
        wl = slider_wl.val
        ww = slider_ww.val
        view.set_clim(vmin=wl - ww / 2, vmax=wl + ww / 2)
        # Updating TextBoxes fires submit callbacks on some backends.
        if not syncing["active"]:
            syncing["active"] = True
            try:
                text_wl.set_val(f"{wl:.1f}")
                text_ww.set_val(f"{ww:.1f}")
            finally:
                syncing["active"] = False
        fig.canvas.draw_idle()

    def set_from_text(raw_text, target_slider, field):
        if syncing["active"]:
            return
        try:
            value = float(raw_text.strip())
        except ValueError:
            message(f"Invalid {field}: please enter a number.")
            return
        if not np.isfinite(value) or not target_slider.valmin <= value <= target_slider.valmax:
            message(f"{field} must be within {target_slider.valmin:.1f}–{target_slider.valmax:.1f}.")
            return
        target_slider.set_val(value)

    slider_wl.on_changed(on_slider)
    slider_ww.on_changed(on_slider)
    text_wl.on_submit(lambda value: set_from_text(value, slider_wl, "WL"))
    text_ww.on_submit(lambda value: set_from_text(value, slider_ww, "WW"))

    def on_auto(_event):
        slider_wl.set_val(auto_level)
        slider_ww.set_val(auto_width)
        message("Auto WL/WW set from 1st–99th percentiles. Raw pixels unchanged.")

    button_auto.on_clicked(on_auto)

    def arm(kind):
        # When toolbar pan/zoom is active, stop it before enabling drawing.
        toolbar = getattr(fig.canvas, "toolbar", None)
        if toolbar is not None and toolbar.mode:
            message("Turn off the toolbar Pan/Zoom tool before drawing a ROI.")
            return
        stage["mode"] = kind
        stage["center"] = None
        if temporary_marker["artist"] is not None:
            temporary_marker["artist"].remove()
            temporary_marker["artist"] = None
        ax.set_title(f"DICOM ROI Viewer — {kind.upper()} ROI")
        message(f"{kind.upper()}: click CENTER, then BOUNDARY. Other controls still work.")

    button_target.on_clicked(lambda event: arm("target"))
    button_background.on_clicked(lambda event: arm("background"))

    def clear(_event):
        for key in rois:
            rois[key] = None
            if artists[key] is not None:
                artists[key].remove()
                artists[key] = None
        set_view_mode()
        message("Cleared ROI selections. Click Target ROI to start again.")

    button_clear.on_clicked(clear)

    def on_click(event):
        if stage["mode"] == "view" or event.inaxes is not ax:
            return
        # Only left button; navigation toolbar interactions must not select ROIs.
        if event.button != 1 or event.xdata is None or event.ydata is None:
            return
        toolbar = getattr(fig.canvas, "toolbar", None)
        if toolbar is not None and toolbar.mode:
            return

        x, y = float(event.xdata), float(event.ydata)
        if not (0 <= x < data.shape[1] and 0 <= y < data.shape[0]):
            return
        kind = stage["mode"]
        if stage["center"] is None:
            stage["center"] = (x, y)
            temporary_marker["artist"], = ax.plot(x, y, marker="+",
                                                    markersize=12, mew=2,
                                                    color="red" if kind == "target" else "cyan")
            message(f"{kind.upper()}: now click ROI BOUNDARY (radius).")
        else:
            cx, cy = stage["center"]
            radius = float(np.hypot(x - cx, y - cy))
            if radius < 0.5:
                message("ROI radius is too small. Click a boundary farther from center.")
                return
            if cx - radius < 0 or cy - radius < 0 or cx + radius >= data.shape[1] or cy + radius >= data.shape[0]:
                message("ROI extends outside the image. Click a closer boundary.")
                return
            if artists[kind] is not None:
                artists[kind].remove()
            artists[kind] = Circle((cx, cy), radius,
                                   edgecolor="red" if kind == "target" else "cyan",
                                   linewidth=2, facecolor="none")
            ax.add_patch(artists[kind])
            rois[kind] = {"center_x": cx, "center_y": cy, "radius": radius}
            set_view_mode()
            other = "Background ROI" if kind == "target" else "Target ROI"
            message(f"{kind.upper()} saved (r={radius:.1f}px). Choose {other} or Confirm.")

    fig.canvas.mpl_connect("button_press_event", on_click)

    def on_scroll(event):
        if event.inaxes is not ax or event.xdata is None or event.ydata is None:
            return
        if event.button not in ("up", "down"):
            return
        # Zoom anchored to cursor, preserving axis orientation.
        scale = 1 / 1.2 if event.button == "up" else 1.2
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        ax.set_xlim(*(event.xdata + (bound - event.xdata) * scale for bound in xlim))
        ax.set_ylim(*(event.ydata + (bound - event.ydata) * scale for bound in ylim))
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("scroll_event", on_scroll)

    def on_confirm(_event):
        if rois["target"] is None or rois["background"] is None:
            message("Define BOTH Target ROI and Background ROI before confirming.")
            return
        a, b = rois["target"], rois["background"]
        if np.hypot(a["center_x"] - b["center_x"],
                    a["center_y"] - b["center_y"]) < (a["radius"] + b["radius"]):
            message("Target and Background ROI overlap. Please reselect one.")
            return
        result["confirmed"] = True
        plt.close(fig)

    def on_cancel(_event):
        plt.close(fig)

    button_confirm.on_clicked(on_confirm)
    button_cancel.on_clicked(on_cancel)

    plt.show(block=True)
    if not result["confirmed"]:
        raise RuntimeError("ROI selection canceled or viewer closed without Confirm.")

    wl, ww = float(slider_wl.val), float(slider_ww.val)
    # Return extended dictionaries so old ROI analysis code keeps working.
    target = {**rois["target"], "window_level": wl, "window_width": ww}
    background = {**rois["background"], "window_level": wl, "window_width": ww}
    return target, background
