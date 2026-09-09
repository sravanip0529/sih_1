from pathlib import Path

import numpy as np

from backend.processing.cloud.scl_provider import quality_from_scl


def test_scl_quality_mapping_preserves_nodata_and_shadows() -> None:
    scl = np.array([[0, 3, 8, 4], [9, 10, 6, 11]], dtype="uint8")
    quality, mapping = quality_from_scl(scl)

    assert quality.tolist() == [[2, 1, 1, 0], [1, 1, 0, 0]]
    assert 3 in mapping["cloud_excluded_classes"]
    assert mapping["cloud_shadow_handling"]


def test_provider_output_does_not_require_probability() -> None:
    from backend.settings import Settings

    configured = Settings(cloud_provider="sentinel_scl")
    assert configured.cloud_provider == "sentinel_scl"
