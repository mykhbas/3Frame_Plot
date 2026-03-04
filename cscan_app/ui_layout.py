import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def _apply_styles(app):
    style = ttk.Style(app.root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg_app = "#090f1d"
    bg_card = "#0f172a"
    bg_header = "#0b1222"
    fg_header = "#e6edf7"
    fg_title = "#f8fbff"
    fg_field = "#c4d2e6"
    muted = "#8da2bf"
    border = "#22314a"
    accent = "#4cc9f0"
    accent_soft = "#2f78c4"
    btn_bg = "#18243b"
    btn_active = "#223453"
    input_bg = "#101b2f"
    panel_soft = "#0b1426"

    app.root.configure(bg=bg_app)

    style.configure("App.TFrame", background=bg_app)
    style.configure("Card.TFrame", background=bg_card, relief="flat", borderwidth=0)
    style.configure("SoftCard.TFrame", background=panel_soft, relief="flat", borderwidth=0)
    style.configure("Header.TFrame", background=bg_header)
    style.configure("TPanedwindow", background=bg_card, sashwidth=8)

    style.configure("Title.TLabel", background=bg_header, foreground=fg_header, font=("Segoe UI", 15, "bold"))
    style.configure("Section.TLabel", background=bg_card, foreground=fg_title, font=("Segoe UI", 11, "bold"))
    style.configure("Field.TLabel", background=bg_card, foreground=fg_field, font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=bg_card, foreground=muted, font=("Segoe UI", 10))
    style.configure("Status.TLabel", background=bg_app, foreground=fg_field, font=("Segoe UI", 10))

    style.configure(
        "TButton",
        padding=(12, 9),
        font=("Segoe UI", 10, "bold"),
        background=btn_bg,
        foreground=fg_header,
        borderwidth=1,
        relief="flat",
        focusthickness=0,
        focuscolor=btn_bg,
    )
    style.map(
        "TButton",
        background=[("active", btn_active), ("pressed", btn_active)],
        foreground=[("disabled", muted), ("!disabled", fg_header)],
    )

    style.configure(
        "Primary.TButton",
        background=accent_soft,
        foreground="#f8fbff",
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("active", accent), ("pressed", accent)],
        foreground=[("disabled", muted), ("!disabled", "#f8fbff")],
    )

    style.configure(
        "TCombobox",
        padding=6,
        fieldbackground=input_bg,
        background=btn_bg,
        foreground=fg_header,
        arrowcolor=accent,
        bordercolor=border,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", input_bg)],
        foreground=[("readonly", fg_header), ("disabled", muted)],
        selectbackground=[("readonly", btn_active)],
        selectforeground=[("readonly", fg_header)],
    )

    style.configure(
        "TEntry",
        padding=6,
        fieldbackground=input_bg,
        foreground=fg_header,
        bordercolor=border,
    )
    style.configure("TSeparator", background=border)


def build_main_ui(app):
    _apply_styles(app)

    app.root.columnconfigure(1, weight=1)
    app.root.columnconfigure(0, minsize=320)
    app.root.rowconfigure(1, weight=1)

    header = ttk.Frame(app.root, padding=(14, 12), style="Header.TFrame")
    header.grid(row=0, column=0, columnspan=2, sticky="ew")
    header.columnconfigure(0, weight=1)

    title = ttk.Label(header, text="C-Scan 3 Frame Viewer", style="Title.TLabel")
    title.grid(row=0, column=0, sticky="w")

    import_btn = ttk.Button(header, text="Import Excel", command=app.import_excel, style="Primary.TButton")
    import_btn.grid(row=0, column=1, padx=(8, 0))

    mock_btn = ttk.Button(header, text="Reset Mock Data", command=app.reset_mock_data)
    mock_btn.grid(row=0, column=2, padx=(8, 0))

    export_mock_btn = ttk.Button(header, text="Export Mock Excel", command=app.export_mock_excel)
    export_mock_btn.grid(row=0, column=3, padx=(8, 0))

    left_panel = ttk.Frame(app.root, padding=14, style="SoftCard.TFrame")
    left_panel.grid(row=1, column=0, sticky="ns", padx=(12, 8), pady=(10, 10))
    left_panel.columnconfigure(0, weight=1)

    color_lbl = ttk.Label(left_panel, text="Color & Scale", style="Section.TLabel")
    color_lbl.grid(row=0, column=0, sticky="w", pady=(0, 8))

    ttk.Label(left_panel, text="Colormap", style="Field.TLabel").grid(row=1, column=0, sticky="w")
    app.cmap_combo = ttk.Combobox(
        left_panel,
        textvariable=app.current_cmap,
        values=app.COLORMAPS,
        state="readonly",
        width=20,
    )
    app.cmap_combo.grid(row=2, column=0, sticky="ew", pady=(2, 8))
    app.cmap_combo.bind("<<ComboboxSelected>>", lambda _e: app._request_draw(delay_ms=0))

    ttk.Label(left_panel, text="Thresholds (for custom_gyr)", style="Field.TLabel").grid(row=3, column=0, sticky="w")
    app.threshold_preview = tk.Canvas(
        left_panel,
        width=250,
        height=56,
        bg="#0b1426",
        highlightthickness=1,
        highlightbackground="#2a3b58",
    )
    app.threshold_preview.grid(row=4, column=0, sticky="ew", pady=(2, 8))
    app.threshold_preview.bind("<Configure>", app._on_threshold_preview_configure)
    app.threshold_preview.bind("<Button-1>", app._on_threshold_preview_press)
    app.threshold_preview.bind("<B1-Motion>", app._on_threshold_preview_drag)
    app.threshold_preview.bind("<ButtonRelease-1>", app._on_threshold_preview_release)

    app.threshold_text = ttk.Label(left_panel, text="G=62.0% | Y=82.0% | R=93.0%", style="Field.TLabel")
    app.threshold_text.grid(row=5, column=0, sticky="w", pady=(0, 8))

    ttk.Label(left_panel, text="Display Frame", style="Field.TLabel").grid(row=9, column=0, sticky="w")
    app.frame_combo = ttk.Combobox(
        left_panel,
        textvariable=app.active_frame_var,
        values=["Frame A", "Frame B", "Frame C"],
        state="readonly",
        width=20,
    )
    app.frame_combo.grid(row=10, column=0, sticky="ew", pady=(2, 8))
    app.frame_combo.bind("<<ComboboxSelected>>", lambda _e: app._request_draw(delay_ms=0))

    ttk.Label(left_panel, text="Scale Min", style="Field.TLabel").grid(row=11, column=0, sticky="w")
    min_entry = ttk.Entry(left_panel, textvariable=app.scale_min_var)
    min_entry.grid(row=12, column=0, sticky="ew", pady=(2, 8))

    ttk.Label(left_panel, text="Scale Max", style="Field.TLabel").grid(row=13, column=0, sticky="w")
    max_entry = ttk.Entry(left_panel, textvariable=app.scale_max_var)
    max_entry.grid(row=14, column=0, sticky="ew", pady=(2, 8))

    apply_scale_btn = ttk.Button(left_panel, text="Apply Scale", command=app.apply_manual_scale)
    apply_scale_btn.grid(row=15, column=0, sticky="ew", pady=(0, 6))

    auto_scale_btn = ttk.Button(left_panel, text="Auto Scale", command=app.auto_scale)
    auto_scale_btn.grid(row=16, column=0, sticky="ew", pady=(0, 12))

    ttk.Separator(left_panel, orient="horizontal").grid(row=17, column=0, sticky="ew", pady=(4, 8))

    data_lbl = ttk.Label(left_panel, text="Data", style="Section.TLabel")
    data_lbl.grid(row=18, column=0, sticky="w", pady=(0, 6))

    app.source_label = ttk.Label(left_panel, text="Current Source: Mock data", wraplength=250, style="Muted.TLabel")
    app.source_label.grid(row=19, column=0, sticky="w", pady=(0, 6))

    app.sheet_label = ttk.Label(left_panel, text="Loaded Sheets: -", wraplength=250, style="Muted.TLabel")
    app.sheet_label.grid(row=20, column=0, sticky="w")

    ttk.Label(left_panel, text="Sheet Render Mode", style="Field.TLabel").grid(row=21, column=0, sticky="w", pady=(8, 0))
    app.sheet_render_mode_combo = ttk.Combobox(
        left_panel,
        textvariable=app.sheet_render_mode_var,
        values=["N*M Matrix"],
        state="disabled",
        width=20,
    )
    app.sheet_render_mode_combo.grid(row=22, column=0, sticky="ew", pady=(2, 0))

    ttk.Separator(left_panel, orient="horizontal").grid(row=23, column=0, sticky="ew", pady=(8, 8))
    ttk.Label(left_panel, text="Frame Sheet Mapping", style="Section.TLabel").grid(row=24, column=0, sticky="w", pady=(0, 6))

    ttk.Label(left_panel, text="Frame A Sheet", style="Field.TLabel").grid(row=25, column=0, sticky="w")
    app.frame_a_sheet_combo = ttk.Combobox(
        left_panel,
        textvariable=app.frame_a_sheet_var,
        values=["-"],
        state="disabled",
        width=20,
    )
    app.frame_a_sheet_combo.grid(row=26, column=0, sticky="ew", pady=(2, 6))
    app.frame_a_sheet_combo.bind("<<ComboboxSelected>>", app._on_sheet_mapping_change)

    ttk.Label(left_panel, text="Frame B Sheet", style="Field.TLabel").grid(row=27, column=0, sticky="w")
    app.frame_b_sheet_combo = ttk.Combobox(
        left_panel,
        textvariable=app.frame_b_sheet_var,
        values=["-"],
        state="disabled",
        width=20,
    )
    app.frame_b_sheet_combo.grid(row=28, column=0, sticky="ew", pady=(2, 6))
    app.frame_b_sheet_combo.bind("<<ComboboxSelected>>", app._on_sheet_mapping_change)

    ttk.Label(left_panel, text="Frame C Sheet", style="Field.TLabel").grid(row=29, column=0, sticky="w")
    app.frame_c_sheet_combo = ttk.Combobox(
        left_panel,
        textvariable=app.frame_c_sheet_var,
        values=["-"],
        state="disabled",
        width=20,
    )
    app.frame_c_sheet_combo.grid(row=30, column=0, sticky="ew", pady=(2, 0))
    app.frame_c_sheet_combo.bind("<<ComboboxSelected>>", app._on_sheet_mapping_change)

    viewer_panel = ttk.Frame(app.root, padding=(12, 12, 12, 12), style="SoftCard.TFrame")
    viewer_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 12), pady=(10, 10))
    viewer_panel.columnconfigure(0, weight=1)
    viewer_panel.rowconfigure(0, weight=1)

    app.viewer_split = ttk.Panedwindow(viewer_panel, orient=tk.VERTICAL)
    app.viewer_split.grid(row=0, column=0, sticky="nsew")

    plot_area = ttk.Frame(app.viewer_split, style="Card.TFrame")
    plot_area.columnconfigure(0, weight=1)
    plot_area.rowconfigure(0, weight=1)

    preview_area = ttk.Frame(app.viewer_split, style="Card.TFrame")
    preview_area.columnconfigure(0, weight=1)
    preview_area.rowconfigure(0, weight=1)

    app.viewer_split.add(plot_area, weight=9)
    app.viewer_split.add(preview_area, weight=1)

    app.plot_viewport = tk.Canvas(plot_area, highlightthickness=0, bg="#0b1426")
    app.plot_viewport.grid(row=0, column=0, sticky="nsew")

    app.plot_xscroll = ttk.Scrollbar(plot_area, orient="horizontal", command=app.plot_viewport.xview)
    app.plot_xscroll.grid(row=1, column=0, sticky="ew")
    app.plot_viewport.configure(xscrollcommand=app._on_plot_xview)

    app.preview_canvas = tk.Canvas(
        preview_area,
        height=36,
        bg="#0b1426",
        highlightthickness=1,
        highlightbackground="#2a3b58",
    )
    app.preview_canvas.grid(row=0, column=0, sticky="nsew", pady=(2, 2))
    app.preview_canvas.bind("<Configure>", app._on_preview_configure)
    app.preview_canvas.bind("<Button-1>", app._on_preview_press)
    app.preview_canvas.bind("<B1-Motion>", app._on_preview_drag)
    app.preview_canvas.bind("<ButtonRelease-1>", app._on_preview_release)

    toggle_preview_btn = ttk.Button(preview_area, text="Hide Preview", command=app.toggle_preview)
    toggle_preview_btn.grid(row=1, column=0, sticky="e", pady=(0, 2))
    app.preview_toggle_btn = toggle_preview_btn

    app.plot_content = ttk.Frame(app.plot_viewport, style="Card.TFrame")
    app.plot_window_id = app.plot_viewport.create_window((0, 0), window=app.plot_content, anchor="nw")
    app.plot_content.bind("<Configure>", app._update_plot_scrollregion)
    app.plot_viewport.bind("<Configure>", app._on_plot_viewport_configure)

    app.fig = plt.Figure(figsize=(10, 7), dpi=100)
    app.fig.patch.set_facecolor("#0f172a")
    gs = app.fig.add_gridspec(1, 2, width_ratios=[30, 1], wspace=0.15)
    app.ax = app.fig.add_subplot(gs[0, 0])
    app.cax = app.fig.add_subplot(gs[0, 1])
    app.ax.set_facecolor("#f8fafc")
    app.cax.set_facecolor("#f8fafc")
    app.canvas = FigureCanvasTkAgg(app.fig, master=app.plot_content)
    app.canvas_widget = app.canvas.get_tk_widget()
    pixel_w = int(app.fig.get_figwidth() * app.fig.dpi)
    pixel_h = int(app.fig.get_figheight() * app.fig.dpi)
    app.canvas_widget.configure(width=pixel_w, height=pixel_h, bd=0, highlightthickness=0)
    app.canvas_widget.pack(anchor="nw")

    status = ttk.Frame(app.root, padding=(12, 8), style="App.TFrame")
    status.grid(row=2, column=0, columnspan=2, sticky="ew")
    status.columnconfigure(0, weight=1)
    status.columnconfigure(1, weight=1)

    header.lift()
    left_panel.lift()
    status.lift()

    ttk.Label(status, textvariable=app.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(status, textvariable=app.info_var, style="Status.TLabel").grid(row=0, column=1, sticky="e")
    app._draw_threshold_preview()
