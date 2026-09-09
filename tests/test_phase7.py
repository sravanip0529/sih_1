from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.processing.normalization import compute_band_scale, normalize_band, raster_statistics, valid_mask_from_quality


def test_valid_mask_from_quality_excludes_cloud_and_nodata() -> None:
    quality = np.array([[0, 1, 2], [0, 0, 1]], dtype="uint8")
    valid = valid_mask_from_quality(quality, valid_value=0)
    assert valid.tolist() == [[True, False, False], [True, True, False]]


def test_compute_band_scale_matches_reference_median() -> None:
    reference = np.array([[10.0, 20.0], [30.0, 40.0]], dtype="float32")
    moving = np.array([[5.0, 10.0], [15.0, 20.0]], dtype="float32")
    ref_valid = np.array([[True, True], [True, True]])
    mov_valid = np.array([[True, True], [True, True]])
    scale = compute_band_scale(reference, moving, ref_valid, mov_valid)
    assert scale == pytest.approx(2.0)


def test_normalize_band_preserves_shape_and_geometry(tmp_path: Path) -> None:
    ref = np.full((3, 4), 100.0, dtype="float32")
    moving = np.full((3, 4), 50.0, dtype="float32")
    ref_valid = np.ones_like(ref, dtype=bool)
    mov_valid = np.ones_like(moving, dtype=bool)
    normalized = normalize_band(ref, moving, ref_valid, mov_valid)
    assert normalized.shape == ref.shape
    assert np.allclose(normalized, 100.0)


def test_raster_statistics_ignores_nodata_and_records_counts() -> None:
    values = np.array([[1.0, 0.0], [0.0, 3.0]], dtype="float32")
    stats = raster_statistics(values, nodata=0.0)
    assert stats["valid_pixel_count"] == 2
    assert stats["nodata_pixel_count"] == 2
    assert stats["mean"] == pytest.approx(2.0)


def test_normalize_band_rejects_nonpositive_reference_median() -> None:
    reference = np.array([[0.0, 0.0], [0.0, 0.0]], dtype="float32")
    moving = np.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32")
    ref_valid = np.ones_like(reference, dtype=bool)
    mov_valid = np.ones_like(moving, dtype=bool)
    with pytest.raises(ValueError, match="positive"):
        normalize_band(reference, moving, ref_valid, mov_valid)
