from __future__ import annotations

import numpy as np


def build_registration_signal(data: np.ndarray, valid_mask: np.ndarray | None = None) -> np.ndarray:
    array = np.asarray(data, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError("Registration signal must be a 2D raster")
    if valid_mask is not None:
        valid_mask = np.asarray(valid_mask, dtype=bool)
        if valid_mask.shape != array.shape:
            raise ValueError("Valid mask shape does not match signal array")
        array = np.where(valid_mask, array, 0.0)

    gradient_x, gradient_y = np.gradient(array)
    signal = np.hypot(np.abs(gradient_x), np.abs(gradient_y))
    return signal.astype(np.float32)
