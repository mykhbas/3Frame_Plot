import math

import numpy as np
import pandas as pd


def generate_mock_data(size: int = 128):
    x = np.linspace(-3, 3, size)
    y = np.linspace(-3, 3, size)
    xx, yy = np.meshgrid(x, y)

    z1 = np.exp(-(xx**2 + yy**2))
    z2 = np.sin(3 * xx) * np.cos(3 * yy)
    z3 = np.exp(-((xx - 1.2) ** 2 + (yy + 0.8) ** 2)) - 0.6 * np.exp(
        -((xx + 1.1) ** 2 + (yy - 1.0) ** 2)
    )

    rng = np.random.default_rng(42)
    noise = rng.normal(0, 0.03, size=(size, size))

    return [z1 + noise, z2 + noise, z3 + noise]


def reshape_sheet_to_matrix(df: pd.DataFrame) -> np.ndarray:
    numeric_df = df.apply(pd.to_numeric, errors="coerce")
    arr = numeric_df.to_numpy(dtype=float)

    if arr.ndim != 2:
        return np.zeros((16, 16), dtype=float)

    valid_rows = ~np.all(np.isnan(arr), axis=1)
    valid_cols = ~np.all(np.isnan(arr), axis=0)
    arr = arr[valid_rows][:, valid_cols]

    if arr.size == 0:
        return np.zeros((16, 16), dtype=float)

    return np.nan_to_num(arr, nan=0.0)


def drop_excel_header_row_if_present(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    first_row = pd.to_numeric(df.iloc[0], errors="coerce").to_numpy(dtype=float)
    if first_row.size == 0 or np.isnan(first_row).any():
        return df

    expected = np.arange(first_row.size, dtype=float)
    if np.allclose(first_row, expected, rtol=0.0, atol=1e-9):
        return df.iloc[1:].reset_index(drop=True)
    return df


def _to_fixed_square(frame: np.ndarray, side: int = 100) -> np.ndarray:
    arr = np.asarray(frame, dtype=float)
    if arr.ndim != 2 or arr.size == 0:
        return np.zeros((side, side), dtype=float)

    h, w = arr.shape
    y_idx = np.linspace(0, h - 1, side).astype(int)
    x_idx = np.linspace(0, w - 1, side).astype(int)
    sampled = arr[np.ix_(y_idx, x_idx)]
    return np.nan_to_num(sampled, nan=0.0)


def _normalize_01(arr: np.ndarray) -> np.ndarray:
    a_min = float(np.nanmin(arr))
    a_max = float(np.nanmax(arr))
    if math.isclose(a_min, a_max):
        return np.zeros_like(arr, dtype=float)
    return (arr - a_min) / (a_max - a_min)


def build_jaguar_like_sheet(frame: np.ndarray, low: float, high: float, rows: int = 10) -> pd.DataFrame:
    base = _to_fixed_square(frame, side=100)
    base_norm = _normalize_01(base)
    scaled = low + base_norm * (high - low)
    flat = scaled.reshape(-1)

    rng = np.random.default_rng(123)
    stacked = []
    for _ in range(rows):
        jitter = rng.normal(0, 0.01 * (high - low), size=flat.shape)
        row = np.clip(flat + jitter, low, high)
        stacked.append(row)

    return pd.DataFrame(np.stack(stacked, axis=0))

