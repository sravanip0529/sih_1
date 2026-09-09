from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio


def valid_mask_from_quality(quality: np.ndarray, valid_value: int = 0) -> np.ndarray:
    arr = np.asarray(quality)
    return np.asarray(arr == valid_value, dtype=bool)


def raster_statistics(values: np.ndarray, nodata: float | int | None = None) -> dict[str, float | int | None]:
    arr = np.asarray(values, dtype=np.float64)
    if nodata is not None:
        arr = np.ma.masked_equal(arr, nodata)
    valid = arr.compressed() if isinstance(arr, np.ma.MaskedArray) else arr
    if valid.size == 0:
        return {"minimum": None, "maximum": None, "mean": None, "stddev": None, "valid_pixel_count": 0, "nodata_pixel_count": int(arr.size if not isinstance(arr, np.ma.MaskedArray) else arr.count() == 0 and arr.size)}
    return {
        "minimum": float(np.min(valid)),
        "maximum": float(np.max(valid)),
        "mean": float(np.mean(valid)),
        "stddev": float(np.std(valid)),
        "valid_pixel_count": int(valid.size),
        "nodata_pixel_count": int(arr.size - valid.size) if isinstance(arr, np.ma.MaskedArray) else 0,
    }


def compute_band_scale(reference: np.ndarray, moving: np.ndarray, reference_valid: np.ndarray, moving_valid: np.ndarray) -> float:
    ref = np.asarray(reference, dtype=np.float64)
    mov = np.asarray(moving, dtype=np.float64)
    ref_valid = np.asarray(reference_valid, dtype=bool)
    mov_valid = np.asarray(moving_valid, dtype=bool)
    valid = np.logical_and(ref_valid, mov_valid)
    if not np.any(valid):
        raise ValueError("No valid pixels remain for normalization")
    ref_valid_values = ref[valid]
    mov_valid_values = mov[valid]
    ref_median = np.median(ref_valid_values)
    mov_median = np.median(mov_valid_values)
    if ref_median <= 0 or mov_median <= 0:
        raise ValueError("Reference and moving medians must be positive for scaling normalization")
    return float(ref_median / mov_median)


def normalize_band(reference: np.ndarray, moving: np.ndarray, reference_valid: np.ndarray, moving_valid: np.ndarray) -> np.ndarray:
    scale = compute_band_scale(reference, moving, reference_valid, moving_valid)
    normalized = np.asarray(moving, dtype=np.float32).copy()
    mask = np.logical_and(np.asarray(reference_valid, dtype=bool), np.asarray(moving_valid, dtype=bool))
    normalized[mask] = normalized[mask] * scale
    return normalized.astype(np.float32)


def write_raster(path: Path, array: np.ndarray, template: rasterio.DatasetReader, dtype: str, nodata: float | int) -> None:
    profile = template.profile.copy()
    profile.update(driver="GTiff", dtype=dtype, count=1, nodata=nodata, compress="deflate")
    with rasterio.open(path, "w", **profile) as target:
        target.write(np.asarray(array, dtype=dtype), 1)
