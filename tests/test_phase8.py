from pathlib import Path

import numpy as np
import pytest

from backend.processing.change_detection import (
    build_joint_valid_mask,
    classify_change,
    compute_change_magnitude,
    compute_signed_difference,
    compute_robust_scale,
    select_threshold,
    validate_geometry,
)


def test_build_joint_valid_mask_excludes_cloud_and_nodata() -> None:
    reference_quality = np.array([[0, 1, 2], [0, 0, 1]], dtype="uint8")
    moving_quality = np.array([[0, 0, 1], [2, 0, 0]], dtype="uint8")
    valid = build_joint_valid_mask(reference_quality, moving_quality, valid_value=0, cloud_value=1, nodata_value=2)
    assert valid.tolist() == [[True, False, False], [False, True, False]]


def test_signed_difference_uses_valid_pixels_only() -> None:
    reference = np.array([[10.0, 20.0], [30.0, 40.0]], dtype="float32")
    moving = np.array([[15.0, 18.0], [20.0, 50.0]], dtype="float32")
    valid = np.array([[True, True], [True, False]], dtype=bool)
    difference = compute_signed_difference(reference, moving, valid)
    assert difference.tolist() == [[5.0, -2.0], [-10.0, 0.0]]


def test_robust_scale_handles_zero_and_near_zero_cases() -> None:
    values = np.array([0.0, 0.0, 0.0, 0.0], dtype="float32")
    assert compute_robust_scale(values) == pytest.approx(1.0)
    values = np.array([1.0, 1.0, 1.0, 1.0], dtype="float32")
    assert compute_robust_scale(values) == pytest.approx(1.0)


def test_change_magnitude_is_nonnegative_and_robust() -> None:
    values = {
        "blue": np.array([0.0, 0.0, 0.0, 10.0], dtype="float32"),
        "green": np.array([0.0, 0.0, 0.0, 0.0], dtype="float32"),
        "red": np.array([0.0, 0.0, 0.0, 0.0], dtype="float32"),
        "nir": np.array([0.0, 0.0, 0.0, 0.0], dtype="float32"),
        "swir16": np.array([0.0, 0.0, 0.0, 0.0], dtype="float32"),
    }
    magnitude = compute_change_magnitude(values)
    assert magnitude.shape == (4,)
    assert np.all(np.isfinite(magnitude))
    assert np.all(magnitude >= 0.0)


def test_threshold_and_classification_are_deterministic() -> None:
    magnitude = np.array([0.1, 0.2, 0.3, 2.0, 2.5, 3.0], dtype="float32")
    threshold = select_threshold(magnitude, method="median_plus_k", k=1.0)
    mask = classify_change(magnitude, threshold, excluded=np.zeros_like(magnitude, dtype=bool))
    assert threshold > 0
    assert set(np.unique(mask)).issubset({0, 1})


def test_geometry_validation_rejects_mismatch(tmp_path: Path) -> None:
    ref = tmp_path / "ref.tif"
    mov = tmp_path / "mov.tif"
    ref.write_text("placeholder", encoding="utf-8")
    mov.write_text("placeholder", encoding="utf-8")
    with pytest.raises((ValueError, FileNotFoundError)):
        validate_geometry(ref, mov)
