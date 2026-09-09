from pathlib import Path

import numpy as np
import rasterio


def validate_probability(path: Path, expected_signature: tuple[object, ...], nodata: float) -> None:
    with rasterio.open(path) as dataset:
        signature = (dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height, tuple(dataset.res), tuple(dataset.bounds))
        values = dataset.read(1, masked=True)
        if signature != expected_signature or values.count() and (values.compressed().min() < 0 or values.compressed().max() > 1):
            raise ValueError(f"Invalid cloud probability output: {path}")


def validate_quality(path: Path, expected_signature: tuple[object, ...], allowed: set[int]) -> None:
    with rasterio.open(path) as dataset:
        signature = (dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height, tuple(dataset.res), tuple(dataset.bounds))
        values = set(np.unique(dataset.read(1)).tolist())
        if signature != expected_signature or not values.issubset(allowed):
            raise ValueError(f"Invalid quality mask output: {path}")


def validate_scl(path: Path, expected_signature: tuple[object, ...]) -> None:
    with rasterio.open(path) as dataset:
        signature = (dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height, tuple(dataset.res), tuple(dataset.bounds))
        values = set(np.unique(dataset.read(1)).tolist())
        if signature != expected_signature or not values.issubset(set(range(12))):
            raise ValueError(f"Invalid Sentinel-2 SCL output: {path}")