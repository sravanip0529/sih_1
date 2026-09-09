from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.transform import from_origin

from backend.processing.alignment.input_validator import validate_cross_date_rasters, validate_raster_file
from backend.processing.alignment.metrics import report_metrics
from backend.processing.alignment.overlap import calculate_overlap, class_mask
from backend.processing.alignment.signal_builder import build_registration_signal
from backend.processing.alignment.registration import estimate_translation
from backend.processing.alignment.signal_builder import build_registration_signal
from backend.processing.alignment.transform_validator import validate_transformation
from backend.processing.alignment.warp import apply_translation


def make_raster(path: Path, *, width: int = 12, height: int = 10, value: float = 10.0, crs: str = "EPSG:32633") -> None:
    transform = from_origin(1000, 1000, 10, 10)
    with rasterio.open(path, "w", driver="GTiff", width=width, height=height, count=1, dtype="float32", crs=crs, transform=transform, nodata=-9999.0) as dataset:
        dataset.write(np.full((height, width), value, dtype="float32"), 1)


def test_input_validation_rejects_missing_and_incompatible_grids(tmp_path: Path) -> None:
    reference = tmp_path / "ref.tif"
    moving = tmp_path / "moving.tif"
    make_raster(reference, width=12, height=10)
    make_raster(moving, width=12, height=10)

    assert validate_raster_file(reference)["valid"] is True
    result = validate_cross_date_rasters(reference, moving)
    assert result["grid_compatible"] is True

    bad = tmp_path / "bad.tif"
    make_raster(bad, width=14, height=10)
    result_bad = validate_cross_date_rasters(reference, bad)
    assert result_bad["grid_compatible"] is False

    missing = tmp_path / "missing.tif"
    with pytest.raises(FileNotFoundError):
        validate_raster_file(missing)


def test_quality_mask_overlap_and_valid_overlap_fraction() -> None:
    ref_valid = np.array([[1, 1, 0, 1], [1, 1, 1, 1]], dtype=bool)
    mov_valid = np.array([[1, 1, 1, 0], [1, 1, 0, 1]], dtype=bool)
    overlap = calculate_overlap(ref_valid, mov_valid, valid_classes={0}, cloud_classes={1}, nodata_classes={2})
    assert overlap["valid_overlap_count"] == 5
    assert overlap["valid_overlap_fraction"] == pytest.approx(5 / 8)
    assert overlap["cloud_excluded_pixels"] == 0
    assert overlap["nodata_excluded_pixels"] == 0


def test_class_mask_handles_set_membership_for_uint8_quality_masks() -> None:
    quality = np.array([[0, 1, 2, 0], [1, 0, 2, 1]], dtype="uint8")
    valid = class_mask(quality, {0})
    assert np.array_equal(valid, np.array([[True, False, False, True], [False, True, False, False]]))


def test_registration_signal_preserves_shape_with_valid_mask() -> None:
    data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype="float32")
    valid = np.array([[True, True, False], [True, False, True]], dtype=bool)
    signal = build_registration_signal(data, valid)
    assert signal.shape == data.shape
    assert signal.dtype == np.float32


def test_registration_estimates_known_translation() -> None:
    reference = np.zeros((20, 20), dtype="float32")
    moving = np.zeros_like(reference)
    reference[5:15, 5:15] = 1.0
    moving[5:15, 7:17] = 1.0

    ref_valid = np.ones_like(reference, dtype=bool)
    mov_valid = np.ones_like(reference, dtype=bool)
    shift = estimate_translation(reference, moving, ref_valid, mov_valid, max_shift=8)

    assert shift["dx"] == 2
    assert shift["dy"] == 0
    assert shift["accepted"] is True


def test_transformation_validation_rejects_bad_values() -> None:
    valid = {
        "dx": 1.0,
        "dy": -1.0,
        "ncc": 0.8,
        "valid_overlap_fraction": 0.8,
        "valid_overlap_count": 100,
        "status": "ok",
    }
    assert validate_transformation(valid, max_allowed_shift_pixels=10, min_valid_overlap_fraction=0.3)["accepted"] is True

    invalid = {"dx": float("nan"), "dy": 0.0, "ncc": 0.8, "valid_overlap_fraction": 0.8, "valid_overlap_count": 100, "status": "ok"}
    assert validate_transformation(invalid, max_allowed_shift_pixels=10, min_valid_overlap_fraction=0.3)["accepted"] is False

    too_large = {"dx": 30.0, "dy": 0.0, "ncc": 0.8, "valid_overlap_fraction": 0.8, "valid_overlap_count": 100, "status": "ok"}
    assert validate_transformation(too_large, max_allowed_shift_pixels=10, min_valid_overlap_fraction=0.3)["accepted"] is False


def test_warping_preserves_shape_and_uses_nearest_for_masks() -> None:
    array = np.array([[0, 1], [2, 0]], dtype="uint8")
    warped = apply_translation(array, dx=1, dy=0, nodata_value=255, categorical=False)
    assert warped.shape == (2, 2)
    assert warped[0, 0] == 1
    assert warped[0, 1] == 255

    mask = np.array([[0, 1], [2, 2]], dtype="uint8")
    warped_mask = apply_translation(mask, dx=1, dy=0, nodata_value=255, categorical=True)
    assert warped_mask.shape == (2, 2)
    assert set(np.unique(warped_mask)).issubset({0, 1, 2, 255})


def test_metrics_are_generated_and_do_not_claim_fake_improvement() -> None:
    ref = np.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32")
    mov = np.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32")
    before = report_metrics(ref, mov)
    after = report_metrics(ref, mov)
    assert "ncc" in before
    assert before["ncc"] == pytest.approx(after["ncc"])
    assert before["rmse"] == pytest.approx(0.0)
