import numpy as np
import pytest

from backend.embeddings.region_embeddings import (
    build_region_text,
    prepare_embedding_records,
)


def test_build_region_text_includes_scientific_summary() -> None:
    region = {
        "region_id": "region_0007",
        "pixel_count": 60,
        "area_m2": 6000.0,
        "reference_date": "2023-06-05",
        "moving_date": "2024-06-26",
        "mean_change_magnitude": 8.01,
        "median_change_magnitude": 7.97,
        "band_summary": {
            "nir": {"mean_difference": -40.0},
            "swir16": {"mean_difference": 25.0},
            "red": {"mean_difference": 10.0},
        },
    }

    text = build_region_text(region)

    assert "region_0007" in text
    assert "2023-06-05" in text and "2024-06-26" in text
    assert "60 changed pixels" in text
    assert "8.01" in text
    assert "NIR" in text and "SWIR16" in text


def test_prepare_embedding_records_keeps_region_ids_and_vectors() -> None:
    regions = [
        {
            "region_id": "region_0001",
            "pixel_count": 10,
            "area_m2": 1000.0,
            "reference_date": "2023-06-05",
            "moving_date": "2024-06-26",
            "mean_change_magnitude": 7.4,
        },
        {
            "region_id": "region_0002",
            "pixel_count": 8,
            "area_m2": 800.0,
            "reference_date": "2023-06-05",
            "moving_date": "2024-06-26",
            "mean_change_magnitude": 9.2,
        },
    ]

    vectors = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ], dtype="float32")

    points = prepare_embedding_records(regions, vectors)

    assert len(points) == 2
    assert points[0]["id"] == 1
    assert points[0]["vector"] == pytest.approx([1.0, 0.0, 0.0])
    assert points[0]["payload"]["region_id"] == "region_0001"
    assert points[0]["payload"]["pixel_count"] == 10
