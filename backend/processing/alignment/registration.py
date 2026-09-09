from __future__ import annotations

import numpy as np


def estimate_translation(reference: np.ndarray, moving: np.ndarray, reference_valid: np.ndarray | None = None, moving_valid: np.ndarray | None = None, max_shift: int = 32) -> dict[str, float | int | bool]:
    ref = np.asarray(reference, dtype=np.float32)
    mov = np.asarray(moving, dtype=np.float32)
    if ref.shape != mov.shape:
        raise ValueError("Reference and moving arrays must share the same shape")
    if reference_valid is None:
        reference_valid = np.ones_like(ref, dtype=bool)
    else:
        reference_valid = np.asarray(reference_valid, dtype=bool)
    if moving_valid is None:
        moving_valid = np.ones_like(ref, dtype=bool)
    else:
        moving_valid = np.asarray(moving_valid, dtype=bool)

    valid = np.logical_and(reference_valid, moving_valid)
    if not np.any(valid):
        return {"dx": 0.0, "dy": 0.0, "accepted": False, "status": "insufficient_overlap"}

    ref_signal = ref.copy()
    mov_signal = mov.copy()
    ref_signal[~valid] = 0
    mov_signal[~valid] = 0
    best = None
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            moved = np.roll(mov_signal, shift=(dy, dx), axis=(0, 1))
            overlap = valid & np.ones_like(valid)
            if overlap.size == 0:
                continue
            corr = float(np.corrcoef(ref_signal[valid].ravel(), moved[valid].ravel())[0, 1]) if np.std(ref_signal[valid]) > 0 and np.std(moved[valid]) > 0 else 0.0
            if best is None or corr > best[0]:
                best = (corr, dx, dy)
    if best is None:
        return {"dx": 0.0, "dy": 0.0, "accepted": False, "status": "failed"}
    corr, dx, dy = best
    return {"dx": int(-dx), "dy": int(-dy), "ncc": float(corr), "accepted": True, "status": "ok"}
