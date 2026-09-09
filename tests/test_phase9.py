from pathlib import Path

import numpy as np
import pytest

from backend.processing.regions import (
    extract_regions,
    filter_regions,
    generate_semantic_description,
    summarize_region_statistics,
)


def test_extract_regions_detects_connected_components() -> None:
    change_mask = np.array([
        [0, 1, 1, 0],
        [0, 1, 0, 0],
        [2, 0, 1, 1],
        [0, 0, 0, 1],
    ], dtype="uint8")
    regions = extract_regions(change_mask, change_value=1, excluded_value=2, connectivity=8)
    assert len(regions) == 1
    assert {region["pixel_count"] for region in regions} == {6}
    assert all(region["region_id"] for region in regions)


def test_filter_regions_uses_minimum_pixels() -> None:
    regions = [
        {"region_id": "region_0001", "pixel_count": 10, "bbox": (0, 0, 2, 2)},
        {"region_id": "region_0002", "pixel_count": 2, "bbox": (5, 5, 6, 6)},
    ]
    retained = filter_regions(regions, min_pixels=3)
    assert [r["region_id"] for r in retained] == ["region_0001"]


def test_region_summary_statistics_are_finite() -> None:
    region = {
        "pixel_count": 4,
        "pixels": [(0, 0), (0, 1), (1, 0), (1, 1)],
        "bbox": (0, 0, 1, 1),
    }
    stats = summarize_region_statistics(region, magnitude=np.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32"))
    assert stats["mean_change_magnitude"] == pytest.approx(2.5)
    assert stats["median_change_magnitude"] == pytest.approx(2.5)
    assert np.isfinite(stats["max_change_magnitude"])


def test_semantic_description_is_deterministic() -> None:
    region = {
        "region_id": "region_0001",
        "pixel_count": 5,
        "area_m2": 500.0,
        "reference_date": "2023-06-05",
        "moving_date": "2024-06-26",
        "mean_change_magnitude": 7.5,
        "band_summary": {"nir": {"mean_difference": -40.0}, "swir16": {"mean_difference": 25.0}},
    }
    description = generate_semantic_description(region)
    assert "region_0001" in description
    assert "2023-06-05" in description and "2024-06-26" in description
    assert description == generate_semantic_description(region)
