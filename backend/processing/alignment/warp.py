from __future__ import annotations

import numpy as np


def apply_translation(array: np.ndarray, *, dx: int = 0, dy: int = 0, nodata_value: float | int = 0, categorical: bool = False) -> np.ndarray:
    data = np.asarray(array)
    if data.ndim != 2:
        raise ValueError("Warp input must be a 2D array")
    if dx == 0 and dy == 0:
        return data.copy()

    shifted = np.roll(data, shift=(-dx, -dy), axis=(1, 0))
    if dx > 0:
        shifted[:, -dx:] = nodata_value
    elif dx < 0:
        shifted[:, : -dx] = nodata_value
    if dy > 0:
        shifted[-dy:, :] = nodata_value
    elif dy < 0:
        shifted[: -dy, :] = nodata_value
    return shifted.astype(data.dtype)
