import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cscan_app.app_components import DEFAULT_COLORMAPS
from cscan_app.colormap_utils import build_custom_cmap
from cscan_app.data_processing import (
    build_jaguar_like_sheet,
    drop_excel_header_row_if_present,
    generate_mock_data,
    reshape_sheet_to_matrix,
)
from cscan_app.ui_layout import build_main_ui


class CScanViewerApp:
    COLORMAPS = DEFAULT_COLORMAPS

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("C-Scan 3 Frame Viewer (Tkinter)")
        self.root.geometry("1400x850")

        self.frames_data = []
        self.current_source = "No data"
        self.loaded_sheets = []
        self.sheet_names = []
        self.sheet_images = {}

        self.current_cmap = tk.StringVar(value="custom_gyr")
        self.active_frame_var = tk.StringVar(value="Frame A")
        self.scale_min_var = tk.StringVar()
        self.scale_max_var = tk.StringVar()
        self.g_threshold_var = tk.DoubleVar(value=62.0)
        self.y_threshold_var = tk.DoubleVar(value=82.0)
        self.r_threshold_var = tk.DoubleVar(value=93.0)
        self.frame_a_sheet_var = tk.StringVar(value="-")
        self.frame_b_sheet_var = tk.StringVar(value="-")
        self.frame_c_sheet_var = tk.StringVar(value="-")
        self.sheet_render_mode_var = tk.StringVar(value="N*M Matrix")
        self.status_var = tk.StringVar(value="Ready")
        self.info_var = tk.StringVar(value="")
        self._draw_job = None
        self._last_canvas_size = (None, None)
        self._is_drawing = False
        self._pending_draw = False
        self._preview_dragging = False
        self._preview_drag_mode = None
        self._preview_min_span = 0.02
        self._preview_first = 0.0
        self._preview_last = 1.0
        self.preview_visible = True
        self._threshold_drag_key = None

        self._build_ui()
        if hasattr(self, "source_label"):
            self.source_label.configure(text="Current Source: No data")
        if hasattr(self, "sheet_label"):
            self.sheet_label.configure(text="Loaded Sheets: -")
        self.status_var.set("No data loaded")
        self.scale_min_var.set("")
        self.scale_max_var.set("")
        self._request_draw(delay_ms=0)

    def _build_ui(self):
        build_main_ui(self)

    def _update_plot_scrollregion(self, _event=None):
        if hasattr(self, "plot_viewport"):
            bbox = self.plot_viewport.bbox("all")
            if bbox is not None:
                self.plot_viewport.configure(scrollregion=bbox)
                self._sync_preview_selector(self._preview_first, self._preview_last)

    def _on_plot_viewport_configure(self, event):
        if not hasattr(self, "plot_window_id"):
            return
        content_w = max(self.plot_content.winfo_reqwidth(), event.width)
        content_h = max(self.plot_content.winfo_reqheight(), event.height)
        self.plot_viewport.itemconfigure(self.plot_window_id, width=content_w, height=content_h)
        self._update_plot_scrollregion()

    def _on_plot_xview(self, first, last):
        self.plot_xscroll.set(first, last)
        self._sync_preview_selector(self._preview_first, self._preview_last)

    def _on_preview_configure(self, _event=None):
        self._draw_preview_strip()
        self._sync_preview_selector(self._preview_first, self._preview_last)

    def _set_preview_range(self, first: float, last: float, request_draw: bool = True):
        first = max(0.0, min(first, 1.0))
        last = max(0.0, min(last, 1.0))
        if last - first < self._preview_min_span:
            if first <= self._preview_first:
                last = min(1.0, first + self._preview_min_span)
            else:
                first = max(0.0, last - self._preview_min_span)
        self._preview_first, self._preview_last = first, last
        self._sync_preview_selector(first, last)
        if request_draw:
            self._request_draw(delay_ms=0)

    def _on_preview_press(self, event):
        if not hasattr(self, "preview_canvas"):
            return
        width = max(int(self.preview_canvas.winfo_width()), 1)
        x = min(max(event.x, 0), width)
        x1 = self._preview_first * width
        x2 = self._preview_last * width
        handle_px = 10

        if abs(x - x1) <= handle_px:
            self._preview_drag_mode = "left"
        elif abs(x - x2) <= handle_px:
            self._preview_drag_mode = "right"
        elif x1 <= x <= x2:
            self._preview_drag_mode = "move"
            self._preview_drag_offset = x - x1
        else:
            self._preview_drag_mode = "center"
            frac = x / width
            span = self._preview_last - self._preview_first
            new_first = min(max(frac - span / 2.0, 0.0), 1.0 - span)
            self._set_preview_range(new_first, new_first + span, request_draw=True)

    def _on_preview_drag(self, event):
        if not hasattr(self, "preview_canvas"):
            return
        if not self._preview_drag_mode:
            return

        width = max(int(self.preview_canvas.winfo_width()), 1)
        frac = min(max(event.x / width, 0.0), 1.0)
        first, last = self._preview_first, self._preview_last
        span = max(last - first, self._preview_min_span)

        if self._preview_drag_mode == "left":
            self._set_preview_range(frac, last, request_draw=True)
        elif self._preview_drag_mode == "right":
            self._set_preview_range(first, frac, request_draw=True)
        elif self._preview_drag_mode == "move":
            x = min(max(event.x, 0), width)
            offset = getattr(self, "_preview_drag_offset", 0)
            new_first = min(max((x - offset) / width, 0.0), 1.0 - span)
            self._set_preview_range(new_first, new_first + span, request_draw=True)
        else:
            new_first = min(max(frac - span / 2.0, 0.0), 1.0 - span)
            self._set_preview_range(new_first, new_first + span, request_draw=True)

    def _on_preview_release(self, _event=None):
        self._preview_drag_mode = None

    def _draw_preview_strip(self):
        if not hasattr(self, "preview_canvas"):
            return
        self.preview_canvas.delete("all")
        if not self.frames_data:
            return

        frame_index = {"Frame A": 0, "Frame B": 1, "Frame C": 2}.get(self.active_frame_var.get(), 0)
        frame = self.frames_data[frame_index]
        if frame.size == 0:
            return

        width = max(int(self.preview_canvas.winfo_width()), 2)
        height = max(int(self.preview_canvas.winfo_height()), 2)
        parsed = self._parse_scale()
        if parsed:
            vmin, vmax = parsed
        else:
            vmin, vmax = self._global_min_max()
        denom = (vmax - vmin) if (vmax - vmin) > 0 else 1.0

        col_vals = np.nanmean(frame, axis=0)
        idx = np.linspace(0, len(col_vals) - 1, width).astype(int)
        sampled = col_vals[idx]
        norm = np.clip((sampled - vmin) / denom, 0.0, 1.0)

        cmap_name = self.current_cmap.get()
        cmap = self._build_custom_cmap() if cmap_name == "custom_gyr" else plt.get_cmap(cmap_name)

        for x, t in enumerate(norm):
            rgba = cmap(float(t))
            color = "#{:02x}{:02x}{:02x}".format(
                int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255)
            )
            self.preview_canvas.create_line(x, 0, x, height, fill=color)

    def _sync_preview_selector_from_view(self):
        self._sync_preview_selector(self._preview_first, self._preview_last)

    def _sync_preview_selector(self, first: float, last: float):
        if not hasattr(self, "preview_canvas"):
            return
        width = max(int(self.preview_canvas.winfo_width()), 1)
        height = max(int(self.preview_canvas.winfo_height()), 1)
        x1 = int(first * width)
        x2 = int(last * width)
        self.preview_canvas.delete("__selector__")
        self.preview_canvas.create_rectangle(
            x1,
            1,
            max(x2, x1 + 2),
            height - 1,
            outline="#38bdf8",
            width=2,
            tags="__selector__",
        )
        # draggable handles
        handle_w = 6
        self.preview_canvas.create_rectangle(
            max(x1 - handle_w // 2, 0),
            1,
            min(x1 + handle_w // 2, width),
            height - 1,
            fill="#38bdf8",
            outline="#38bdf8",
            tags="__selector__",
        )
        self.preview_canvas.create_rectangle(
            max(x2 - handle_w // 2, 0),
            1,
            min(x2 + handle_w // 2, width),
            height - 1,
            fill="#38bdf8",
            outline="#38bdf8",
            tags="__selector__",
        )

    def toggle_preview(self):
        if not hasattr(self, "viewer_split") or not hasattr(self, "preview_canvas"):
            return

        if self.preview_visible:
            self.viewer_split.sashpos(0, max(40, self.viewer_split.winfo_height() - 22))
            self.preview_canvas.configure(height=1)
            if hasattr(self, "preview_toggle_btn"):
                self.preview_toggle_btn.configure(text="Show Preview")
            self.preview_visible = False
        else:
            self.preview_canvas.configure(height=36)
            self.viewer_split.sashpos(0, int(self.viewer_split.winfo_height() * 0.88))
            if hasattr(self, "preview_toggle_btn"):
                self.preview_toggle_btn.configure(text="Hide Preview")
            self.preview_visible = True
            self._draw_preview_strip()
            self._sync_preview_selector_from_view()

    def _thresholds_normalized(self):
        g = self.g_threshold_var.get() / 100.0
        y = self.y_threshold_var.get() / 100.0
        r = self.r_threshold_var.get() / 100.0
        return g, y, r

    def _build_custom_cmap(self):
        return build_custom_cmap(
            self.g_threshold_var.get(),
            self.y_threshold_var.get(),
            self.r_threshold_var.get(),
        )

    def _on_threshold_preview_configure(self, _event=None):
        self._draw_threshold_preview()

    def _threshold_key_at_x(self, x: float, width: int):
        g_x = (self.g_threshold_var.get() / 100.0) * width
        y_x = (self.y_threshold_var.get() / 100.0) * width
        r_x = (self.r_threshold_var.get() / 100.0) * width
        candidates = [("g", g_x), ("y", y_x), ("r", r_x)]
        nearest = min(candidates, key=lambda item: abs(item[1] - x))
        return nearest[0] if abs(nearest[1] - x) <= 14 else None

    def _on_threshold_preview_press(self, event):
        if not hasattr(self, "threshold_preview"):
            return
        width = max(int(self.threshold_preview.winfo_width()), 1)
        x = min(max(event.x, 0), width)
        self._threshold_drag_key = self._threshold_key_at_x(x, width)

    def _on_threshold_preview_drag(self, event):
        if not hasattr(self, "threshold_preview"):
            return
        if not self._threshold_drag_key:
            return

        width = max(int(self.threshold_preview.winfo_width()), 1)
        x = min(max(event.x, 0), width)
        pct = (x / width) * 100.0

        g = self.g_threshold_var.get()
        y = self.y_threshold_var.get()
        r = self.r_threshold_var.get()

        if self._threshold_drag_key == "g":
            self.g_threshold_var.set(max(0.0, min(pct, y - 1.0)))
        elif self._threshold_drag_key == "y":
            self.y_threshold_var.set(max(g + 1.0, min(pct, r - 1.0)))
        elif self._threshold_drag_key == "r":
            self.r_threshold_var.set(max(y + 1.0, min(pct, 100.0)))

        self._draw_threshold_preview()
        self._request_draw(delay_ms=40)

    def _on_threshold_preview_release(self, _event=None):
        self._threshold_drag_key = None

    def _draw_threshold_handle(self, canvas, x: float, center_y: float, height: float, color: str, label: str):
        half_w = 6
        radius = half_w
        top = center_y - height / 2.0
        bottom = center_y + height / 2.0

        canvas.create_oval(x - radius, top, x + radius, top + 2 * radius, fill=color, outline="#f8fafc", width=1)
        canvas.create_rectangle(
            x - half_w,
            top + radius,
            x + half_w,
            bottom - radius,
            fill=color,
            outline="#f8fafc",
            width=1,
        )
        canvas.create_oval(
            x - radius,
            bottom - 2 * radius,
            x + radius,
            bottom,
            fill=color,
            outline="#f8fafc",
            width=1,
        )
        canvas.create_text(x, top - 7, text=label, fill="#e2e8f0", font=("Helvetica", 8, "bold"))

    def _draw_threshold_preview(self):
        if not hasattr(self, "threshold_preview"):
            return

        canvas = self.threshold_preview
        canvas.delete("all")
        width = int(canvas.winfo_width() or 250)
        height = int(canvas.winfo_height() or 56)
        cmap = self._build_custom_cmap()

        top = 24
        bottom = max(top + 6, height - 12)
        bar_h = max(bottom - top, 6)

        for x in range(width):
            t = x / max(width - 1, 1)
            rgba = cmap(t)
            color = "#{:02x}{:02x}{:02x}".format(
                int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255)
            )
            canvas.create_line(x, top, x, bottom, fill=color)

        canvas.create_rectangle(0, top, width, bottom, outline="#334155", width=1)

        for label, pos, marker_color in (
            ("G", self.g_threshold_var.get() / 100.0, "#22c55e"),
            ("Y", self.y_threshold_var.get() / 100.0, "#f59e0b"),
            ("R", self.r_threshold_var.get() / 100.0, "#ef4444"),
        ):
            x = pos * width
            self._draw_threshold_handle(
                canvas=canvas,
                x=x,
                center_y=top + bar_h / 2.0,
                height=bar_h + 18,
                color=marker_color,
                label=label,
            )

        self.threshold_text.configure(
            text=(
                f"G={self.g_threshold_var.get():.1f}% | "
                f"Y={self.y_threshold_var.get():.1f}% | "
                f"R={self.r_threshold_var.get():.1f}%"
            )
        )

    def _on_g_threshold_change(self, _value):
        g = self.g_threshold_var.get()
        y = self.y_threshold_var.get()
        if g >= y:
            self.g_threshold_var.set(max(0.0, y - 1.0))
        self._draw_threshold_preview()
        self._request_draw(delay_ms=40)

    def _on_y_threshold_change(self, _value):
        g = self.g_threshold_var.get()
        y = self.y_threshold_var.get()
        r = self.r_threshold_var.get()
        if y <= g:
            self.y_threshold_var.set(min(100.0, g + 1.0))
        elif y >= r:
            self.y_threshold_var.set(max(0.0, r - 1.0))
        self._draw_threshold_preview()
        self._request_draw(delay_ms=40)

    def _on_r_threshold_change(self, _value):
        y = self.y_threshold_var.get()
        r = self.r_threshold_var.get()
        if r <= y:
            self.r_threshold_var.set(min(100.0, y + 1.0))
        self._draw_threshold_preview()
        self._request_draw(delay_ms=40)

    def _request_draw(self, delay_ms: int = 0):
        if self._draw_job is not None:
            try:
                self.root.after_cancel(self._draw_job)
            except Exception:
                pass
            self._draw_job = None

        def _run():
            self._draw_job = None
            self._draw_all()

        self._draw_job = self.root.after(max(delay_ms, 0), _run)

    def _parse_scale(self):
        try:
            vmin = float(self.scale_min_var.get())
            vmax = float(self.scale_max_var.get())
        except ValueError:
            return None

        if vmin >= vmax:
            return None
        return vmin, vmax

    def _refresh_sheet_selectors(self):
        has_sheets = bool(self.sheet_names)
        values = self.sheet_names if has_sheets else ["-"]
        state = "readonly" if has_sheets else "disabled"

        for combo, var in (
            (self.frame_a_sheet_combo, self.frame_a_sheet_var),
            (self.frame_b_sheet_combo, self.frame_b_sheet_var),
            (self.frame_c_sheet_combo, self.frame_c_sheet_var),
        ):
            combo.configure(values=values, state=state)
            if var.get() not in values:
                var.set(values[0])

    def _sync_frames_from_sheet_selection(self):
        if not self.sheet_images or not self.sheet_names:
            return

        selected = [
            self.frame_a_sheet_var.get(),
            self.frame_b_sheet_var.get(),
            self.frame_c_sheet_var.get(),
        ]
        selected = [name if name in self.sheet_images else self.sheet_names[0] for name in selected]

        self.frame_a_sheet_var.set(selected[0])
        self.frame_b_sheet_var.set(selected[1])
        self.frame_c_sheet_var.set(selected[2])

        self.frames_data = [self.sheet_images[name] for name in selected]
        self.loaded_sheets = selected
        self.sheet_label.configure(text=f"Loaded Sheets: {', '.join(selected)}")

    def _on_sheet_mapping_change(self, _event=None):
        if not self.sheet_images:
            return

        self._sync_frames_from_sheet_selection()
        self.auto_scale(update_plot=False)
        self.status_var.set("Updated frame-sheet mapping")
        self._request_draw(delay_ms=0)

    def _global_min_max(self):
        if not self.frames_data:
            return 0.0, 1.0
        arr_min = min(float(np.nanmin(frame)) for frame in self.frames_data)
        arr_max = max(float(np.nanmax(frame)) for frame in self.frames_data)
        return arr_min, arr_max

    def apply_manual_scale(self):
        if not self.frames_data:
            self.status_var.set("No data to scale")
            return

        parsed = self._parse_scale()
        if not parsed:
            self.status_var.set("Invalid scale: require numeric values and min < max")
            return

        self.status_var.set("Manual scale applied")
        self._request_draw(delay_ms=0)

    def auto_scale(self, update_plot: bool = True):
        if not self.frames_data:
            self.scale_min_var.set("")
            self.scale_max_var.set("")
            self.status_var.set("No data loaded")
            if update_plot:
                self._request_draw(delay_ms=0)
            return

        vmin, vmax = self._global_min_max()
        self.scale_min_var.set(f"{vmin:.6f}")
        self.scale_max_var.set(f"{vmax:.6f}")
        self.status_var.set("Auto scale updated from current data")
        if update_plot:
            self._request_draw(delay_ms=0)

    def _draw_all(self):
        if self._is_drawing:
            self._pending_draw = True
            return
        self._is_drawing = True

        try:
            if not self.frames_data:
                self.ax.clear()
                self.ax.text(
                    0.5,
                    0.5,
                    "No data loaded\nImport Excel to display",
                    ha="center",
                    va="center",
                    transform=self.ax.transAxes,
                    fontsize=12,
                )
                self.ax.set_axis_off()
                self.cax.clear()
                self.info_var.set("No data")
                self.canvas.draw_idle()
                self._draw_preview_strip()
                self._update_plot_scrollregion()
                return

            parsed = self._parse_scale()
            if parsed:
                vmin, vmax = parsed
            else:
                vmin, vmax = self._global_min_max()

            cmap_name = self.current_cmap.get()
            cmap = self._build_custom_cmap() if cmap_name == "custom_gyr" else cmap_name
            frame_index = {"Frame A": 0, "Frame B": 1, "Frame C": 2}.get(self.active_frame_var.get(), 0)
            frame = self.frames_data[frame_index]

            # Dynamically size plot canvas from data shape so very wide sheets
            # (e.g. 10 x 10000) render as wide horizontal images.
            rows, cols = frame.shape
            viewport_w = int(self.plot_viewport.winfo_width()) if hasattr(self, "plot_viewport") else 0
            width_px = max(max(viewport_w, 900), min(5000, int(cols * 0.25)))
            height_px = max(420, min(760, int(rows * 22)))
            if (width_px, height_px) != self._last_canvas_size:
                self.fig.set_size_inches(width_px / self.fig.dpi, height_px / self.fig.dpi, forward=True)
                self.canvas_widget.configure(width=width_px, height=height_px)
                self._last_canvas_size = (width_px, height_px)

            self.ax.clear()
            im = self.ax.imshow(
                frame,
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
                aspect="auto",
                interpolation="nearest",
                resample=False,
            )
            self.ax.set_title(f"C-Scan {self.active_frame_var.get()}")
            self.ax.set_xlabel("X")
            self.ax.set_ylabel("Y")

            # Zoom by selected preview range
            x_first, x_last = self._preview_first, self._preview_last
            cols = frame.shape[1]
            x0 = x_first * max(cols - 1, 1)
            x1 = x_last * max(cols - 1, 1)
            if x1 - x0 >= 1:
                self.ax.set_xlim(x0, x1)

            self.cax.clear()
            self.fig.colorbar(im, cax=self.cax)

            self.info_var.set(
                (
                    f"shape={frame.shape}, min={vmin:.4f}, max={vmax:.4f}, cmap={cmap_name}, "
                    f"G={self.g_threshold_var.get():.1f}%, Y={self.y_threshold_var.get():.1f}%, R={self.r_threshold_var.get():.1f}%"
                )
            )
            self.canvas.draw_idle()
            self._draw_preview_strip()
            self._update_plot_scrollregion()
        finally:
            self._is_drawing = False
            if self._pending_draw:
                self._pending_draw = False
                self._request_draw(delay_ms=10)

    def _reshape_sheet_to_image(self, df: pd.DataFrame) -> np.ndarray:
        return reshape_sheet_to_matrix(df)

    def _drop_excel_header_row_if_present(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_excel_header_row_if_present(df)

    def _build_jaguar_like_sheet(self, frame: np.ndarray, low: float, high: float, rows: int = 10) -> pd.DataFrame:
        return build_jaguar_like_sheet(frame, low=low, high=high, rows=rows)

    def export_mock_excel(self):
        if not self.frames_data:
            self.status_var.set("No data to export")
            messagebox.showwarning("Export", "No data to export")
            return

        default_name = "export_current_frames_nm.xlsx"
        path = filedialog.asksaveasfilename(
            title="Save current frames as Excel (N*M)",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not path:
            return

        try:
            frames = [np.asarray(frame, dtype=float) for frame in self.frames_data]

            if self.loaded_sheets and len(self.loaded_sheets) >= 3:
                sheet_names = [str(self.loaded_sheets[0]), str(self.loaded_sheets[1]), str(self.loaded_sheets[2])]
            else:
                sheet_names = ["Frame A", "Frame B", "Frame C"]

            with pd.ExcelWriter(path) as writer:
                for sheet_name, frame in zip(sheet_names, frames):
                    df = pd.DataFrame(np.nan_to_num(frame, nan=0.0))
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)

            shape_text = ", ".join(str(tuple(frame.shape)) for frame in frames)
            self.status_var.set(f"Exported N*M Excel: {os.path.basename(path)} | {shape_text}")
        except Exception as exc:
            self.status_var.set("Failed to export mock Excel")
            messagebox.showerror("Export Error", f"Cannot export Excel file:\n{exc}")

    def import_excel(self):
        path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        if not path:
            return

        self._load_excel_path(path)

    def _load_excel_path(self, path: str):
        if not path:
            return

        try:
            xls = pd.ExcelFile(path)
            sheets = xls.sheet_names
            if not sheets:
                raise ValueError("No sheets found")

            parsed_sheets = {}
            for name in sheets:
                # Read as raw rows first so 1x10000 headerless sheets are preserved
                # during import; then strip synthetic 0..N-1 header rows if present.
                df = pd.read_excel(path, sheet_name=name, header=None)
                df = drop_excel_header_row_if_present(df)
                parsed_sheets[name] = self._reshape_sheet_to_image(df)

            self.sheet_names = sheets
            self.sheet_images = parsed_sheets

            default_selection = sheets[:3]
            while len(default_selection) < 3:
                default_selection.append(default_selection[-1])

            self.frame_a_sheet_var.set(default_selection[0])
            self.frame_b_sheet_var.set(default_selection[1])
            self.frame_c_sheet_var.set(default_selection[2])

            self._refresh_sheet_selectors()
            self._sync_frames_from_sheet_selection()
            self.current_source = path

            self.source_label.configure(text=f"Current Source: {path}")

            self.auto_scale(update_plot=False)
            self.status_var.set(f"Loaded Excel: {path.split('/')[-1]} ({len(sheets)} sheets)")
            self._request_draw(delay_ms=0)
        except Exception as exc:
            self.status_var.set("Failed to load Excel")
            messagebox.showerror("Import Error", f"Cannot import Excel file:\n{exc}")

    def reset_mock_data(self):
        self.frames_data = generate_mock_data()
        self.current_source = "Mock data"
        self.loaded_sheets = []
        self.sheet_names = []
        self.sheet_images = {}
        self.frame_a_sheet_var.set("-")
        self.frame_b_sheet_var.set("-")
        self.frame_c_sheet_var.set("-")
        self._refresh_sheet_selectors()
        self.source_label.configure(text="Current Source: Mock data")
        self.sheet_label.configure(text="Loaded Sheets: -")
        self.auto_scale(update_plot=False)
        self.status_var.set("Reset to mock data")
        self._request_draw(delay_ms=0)


def main():
    root = tk.Tk()
    app = CScanViewerApp(root)

    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
        if not os.path.isabs(excel_path):
            excel_path = os.path.join(os.getcwd(), excel_path)
        if os.path.exists(excel_path):
            app._load_excel_path(excel_path)
        else:
            app.status_var.set(f"Excel file not found: {excel_path}")

    root.mainloop()


if __name__ == "__main__":
    main()
