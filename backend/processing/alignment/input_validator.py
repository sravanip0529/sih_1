from __future__ import annotations

from pathlib import Path
from typing import Any

import rasterio


SUPPORTED_DTYPES = {"uint8", "int16", "uint16", "int32", "float32", "float64"}


def validate_raster_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Raster does not exist: {file_path}")
    try:
        with rasterio.open(file_path) as dataset:
            if dataset.width <= 0 or dataset.height <= 0:
                raise ValueError(f"Invalid raster dimensions for {file_path}: {dataset.width}x{dataset.height}")
            if dataset.crs is None:
                raise ValueError(f"Raster has no CRS: {file_path}")
            if dataset.transform is None:
                raise ValueError(f"Raster has no affine transform: {file_path}")
            if dataset.dtypes[0] not in SUPPORTED_DTYPES:
                raise ValueError(f"Unsupported raster dtype for {file_path}: {dataset.dtypes[0]}")
            if dataset.res[0] <= 0 or dataset.res[1] <= 0:
                raise ValueError(f"Invalid raster resolution for {file_path}: {dataset.res}")
            info = {
                "valid": True,
                "path": str(file_path),
                "width": dataset.width,
                "height": dataset.height,
                "count": dataset.count,
                "crs": dataset.crs.to_string(),
                "transform": tuple(dataset.transform),
                "bounds": tuple(dataset.bounds),
                "res": tuple(dataset.res),
                "dtype": dataset.dtypes[0],
                "nodata": dataset.nodata,
            }
            return info
    except rasterio.errors.RasterioIOError as error:
        raise ValueError(f"Raster is unreadable: {file_path}") from error


def validate_cross_date_rasters(reference_path: str | Path, moving_path: str | Path) -> dict[str, Any]:
    reference = validate_raster_file(reference_path)
    moving = validate_raster_file(moving_path)

    checks = {
        "same_crs": reference["crs"] == moving["crs"],
        "same_width": reference["width"] == moving["width"],
        "same_height": reference["height"] == moving["height"],
        "same_affine": reference["transform"] == moving["transform"],
        "same_resolution": reference["res"] == moving["res"],
        "same_bounds": reference["bounds"] == moving["bounds"],
    }
    grid_compatible = all(checks.values())
    return {
        "reference": reference,
        "moving": moving,
        "checks": checks,
        "grid_compatible": grid_compatible,
        "status": "grid compatibility = PASS" if grid_compatible else "grid compatibility = FAIL",
    }
