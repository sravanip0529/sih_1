from __future__ import annotations

import numpy as np


def _normalize_classes(classes):
    if classes is None:
        return None
    if isinstance(classes, (set, tuple, list)):
        return [int(value) for value in classes]
    return [int(classes)]


def class_mask(values, valid_classes=None):
    arr = np.asarray(values)
    if arr.dtype == bool:
        return arr.astype(bool, copy=True)
    classes = _normalize_classes(valid_classes)
    if classes is None:
        return np.ones(arr.shape, dtype=bool)
    return np.isin(arr, classes)


def _as_bool_mask(values, valid_classes=None, cloud_classes=None, nodata_classes=None):
    arr = np.asarray(values)
    if arr.dtype == bool:
        return arr
    if valid_classes is not None:
        return class_mask(arr, valid_classes)
    return np.ones(arr.shape, dtype=bool)


def calculate_overlap(
    reference_valid: np.ndarray,
    moving_valid: np.ndarray,
    valid_classes: set[int] | tuple[int, ...] | None = None,
    cloud_classes: set[int] | tuple[int, ...] | None = None,
    nodata_classes: set[int] | tuple[int, ...] | None = None,
) -> dict[str, float | int]:
    ref_array = np.asarray(reference_valid)
    mov_array = np.asarray(moving_valid)
    if ref_array.shape != mov_array.shape:
        raise ValueError("Reference and moving valid masks must share the same shape")

    ref_valid = class_mask(ref_array, valid_classes or {1})
    mov_valid = class_mask(mov_array, valid_classes or {1})

    if valid_classes is not None and ref_array.dtype != bool and mov_array.dtype != bool:
        ref_valid = class_mask(ref_array, valid_classes)
        mov_valid = class_mask(mov_array, valid_classes)

    valid_overlap = np.logical_and(ref_valid, mov_valid)
    valid_overlap_count = int(np.count_nonzero(valid_overlap))
    total_pixels = int(ref_valid.size)
    valid_overlap_fraction = valid_overlap_count / total_pixels if total_pixels else 0.0

    cloud_excluded_pixels = 0
    nodata_excluded_pixels = 0
    if cloud_classes is not None and ref_array.dtype != bool and mov_array.dtype != bool:
        cloud_excluded_pixels = int(np.count_nonzero(np.isin(ref_array, list(cloud_classes)) | np.isin(mov_array, list(cloud_classes))))
    if nodata_classes is not None and ref_array.dtype != bool and mov_array.dtype != bool:
        nodata_excluded_pixels = int(np.count_nonzero(np.isin(ref_array, list(nodata_classes)) | np.isin(mov_array, list(nodata_classes))))

    return {
        "total_pixels": total_pixels,
        "valid_overlap_count": valid_overlap_count,
        "valid_overlap_fraction": float(valid_overlap_fraction),
        "cloud_excluded_pixels": int(cloud_excluded_pixels),
        "nodata_excluded_pixels": int(nodata_excluded_pixels),
    }
