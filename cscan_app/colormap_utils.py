from matplotlib.colors import LinearSegmentedColormap


def build_custom_cmap(g_pct: float, y_pct: float, r_pct: float):
    g = g_pct / 100.0
    y = y_pct / 100.0
    r = r_pct / 100.0
    return LinearSegmentedColormap.from_list(
        "custom_gyr",
        [
            (0.0, "#000000"),
            (g, "#4caf50"),
            (y, "#ffeb3b"),
            (r, "#f44336"),
            (1.0, "#000000"),
        ],
        N=512,
    )

