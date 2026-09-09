from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

VALID_CLASSES = (0,)
CLOUD_CLASS = 1
NODATA_CLASS = 2


def build_joint_valid_mask(reference_quality: np.ndarray, moving_quality: np.ndarray, valid_value: int = 0, cloud_value: int = 1, nodata_value: int = 2) -> np.ndarray:
    ref = np.asarray(reference_quality, dtype=np.uint8)
    mov = np.asarray(moving_quality, dtype=np.uint8)
    if ref.shape != mov.shape:
        raise ValueError("Quality masks must share the same shape")
    ref_valid = ref == valid_value
    mov_valid = mov == valid_value
    return np.logical_and(ref_valid, mov_valid)


def compute_signed_difference(reference: np.ndarray, moving: np.ndarray, valid: np.ndarray) -> np.ndarray:
    ref = np.asarray(reference, dtype=np.float32)
    mov = np.asarray(moving, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool)
    result = np.zeros_like(ref, dtype=np.float32)
    if ref.shape != mov.shape:
        raise ValueError("Reference and moving arrays must share the same shape")
    result[valid] = mov[valid] - ref[valid]
    return result


def compute_robust_scale(values: np.ndarray, *, floor: float = 1.0e-6) -> float:
    arr = np.asarray(values, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return 1.0
    median = float(np.median(finite))
    mad = float(np.median(np.abs(finite - median)))
    scale = 1.4826 * mad
    if not np.isfinite(scale) or scale <= floor:
        std = float(np.std(finite))
        if std > floor:
            return float(std)
        return 1.0
    return float(scale)


def compute_change_magnitude(band_differences: dict[str, np.ndarray]) -> np.ndarray:
    if not band_differences:
        raise ValueError("No band differences were provided")
    first = next(iter(band_differences.values()))
    magnitude = np.zeros_like(first, dtype=np.float32)
    for band_name, values in band_differences.items():
        if values.shape != first.shape:
            raise ValueError(f"Band {band_name} has mismatched shape")
        scale = compute_robust_scale(values[np.isfinite(values)])
        if scale <= 0:
            scale = 1.0
        z = values / scale
        magnitude = np.hypot(magnitude, z)
    return magnitude.astype(np.float32)


def select_threshold(values: np.ndarray, method: str = "median_plus_k", k: float = 1.0) -> float:
    arr = np.asarray(values, dtype=np.float32)
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return 0.0
    if method == "median_plus_k":
        median = float(np.median(valid))
        scale = compute_robust_scale(valid)
        return float(median + k * scale)
    raise ValueError(f"Unsupported threshold method: {method}")


def classify_change(magnitude: np.ndarray, threshold: float, excluded: np.ndarray | None = None) -> np.ndarray:
    mag = np.asarray(magnitude, dtype=np.float32)
    excluded_mask = np.zeros_like(mag, dtype=bool) if excluded is None else np.asarray(excluded, dtype=bool)
    result = np.zeros_like(mag, dtype=np.uint8)
    valid = ~excluded_mask & np.isfinite(mag)
    result[valid & (mag >= threshold)] = 1
    result[excluded_mask] = 2
    return result.astype(np.uint8)


def validate_geometry(reference_path: Path, moving_path: Path) -> None:
    if not reference_path.exists() or not moving_path.exists():
        raise FileNotFoundError("Reference or moving raster missing")
    try:
        with rasterio.open(reference_path) as ref, rasterio.open(moving_path) as mov:
            if ref.crs != mov.crs:
                raise ValueError("CRS mismatch between reference and moving rasters")
            if (ref.width, ref.height) != (mov.width, mov.height):
                raise ValueError("Reference and moving rasters do not have matching dimensions")
            if ref.transform != mov.transform:
                raise ValueError("Reference and moving rasters do not share the same transform")
            if ref.res != mov.res:
                raise ValueError("Reference and moving rasters do not share the same resolution")
    except (rasterio.errors.RasterioIOError, OSError, ValueError):
        raise ValueError(f"Invalid geometry for rasters: {reference_path} and {moving_path}")


def validate_quality_mask(mask_path: Path, reference_path: Path, valid_values: tuple[int, ...] = (0, 1, 2)) -> None:
    if not mask_path.exists():
        raise FileNotFoundError(f"Missing quality mask: {mask_path}")
    with rasterio.open(mask_path) as mask_ds, rasterio.open(reference_path) as ref_ds:
        if mask_ds.crs != ref_ds.crs:
            raise ValueError("Quality mask CRS mismatch")
        if (mask_ds.width, mask_ds.height) != (ref_ds.width, ref_ds.height):
            raise ValueError("Quality mask dimensions mismatch")
        if mask_ds.transform != ref_ds.transform:
            raise ValueError("Quality mask transform mismatch")
        unique = set(np.unique(mask_ds.read(1)).tolist())
        if not set(valid_values).issuperset(unique):
            raise ValueError(f"Unexpected quality classes present: {sorted(unique)}")


def validate_output_geometry(paths: list[Path], template: Path) -> None:
    with rasterio.open(template) as ref:
        for path in paths:
            with rasterio.open(path) as dataset:
                if dataset.crs != ref.crs:
                    raise ValueError(f"Output CRS mismatch for {path.name}")
                if (dataset.width, dataset.height) != (ref.width, ref.height):
                    raise ValueError(f"Output dimension mismatch for {path.name}")
                if dataset.transform != ref.transform:
                    raise ValueError(f"Output transform mismatch for {path.name}")


def build_quality_exclusion_mask(reference_quality: np.ndarray, moving_quality: np.ndarray, valid_value: int = 0, cloud_value: int = 1, nodata_value: int = 2) -> np.ndarray:
    ref = np.asarray(reference_quality, dtype=np.uint8)
    mov = np.asarray(moving_quality, dtype=np.uint8)
    excluded = np.zeros_like(ref, dtype=np.uint8)
    excluded[(ref == cloud_value) | (mov == cloud_value)] = 1
    excluded[(ref == nodata_value) | (mov == nodata_value)] = 2
    return excluded.astype(np.uint8)


def write_raster(path: Path, array: np.ndarray, template_path: Path, *, dtype: str = "float32", nodata: float | int = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as template:
        profile = template.profile.copy()
        profile.update(driver="GTiff", dtype=dtype, count=1, nodata=nodata, compress="deflate")
        with rasterio.open(path, "w", **profile) as target:
            target.write(np.asarray(array, dtype=dtype), 1)


def compute_summary(values: np.ndarray, *, valid_mask: np.ndarray | None = None) -> dict[str, float | int | None]:
    arr = np.asarray(values, dtype=np.float32)
    if valid_mask is not None:
        arr = arr[valid_mask]
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"minimum": None, "maximum": None, "mean": None, "median": None, "stddev": None, "valid_pixels": 0}
    return {
        "minimum": float(finite.min()),
        "maximum": float(finite.max()),
        "mean": float(finite.mean()),
        "median": float(np.median(finite)),
        "stddev": float(finite.std()),
        "valid_pixels": int(finite.size),
    }
