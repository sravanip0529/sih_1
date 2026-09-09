from __future__ import annotations

import numpy as np


def report_metrics(reference: np.ndarray, moving: np.ndarray) -> dict[str, float]:
    ref = np.asarray(reference, dtype=np.float32)
    mov = np.asarray(moving, dtype=np.float32)
    if ref.shape != mov.shape:
        raise ValueError("Reference and moving arrays must share the same shape")
    diff = ref - mov
    rmse = float(np.sqrt(np.mean(np.square(diff))))
    ncc = float(np.corrcoef(ref.ravel(), mov.ravel())[0, 1]) if ref.size > 1 else 1.0
    return {"rmse": rmse, "ncc": ncc}
