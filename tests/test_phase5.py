from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.processing.cloud.input_builder import S2CLOUDLESS_BANDS, build_model_input
from backend.processing.cloud.quality_mask import create_masks, statistics
from backend.processing.cloud.s2cloudless_service import generate_probability


def make_band(path: Path, value: float, nodata: float = 0) -> None:
    with rasterio.open(path, "w", driver="GTiff", width=4, height=3, count=1, dtype="float32", crs="EPSG:32633", transform=from_origin(0, 30, 10, 10), nodata=nodata) as dataset:
        dataset.write(np.full((3, 4), value, dtype="float32"), 1)


def test_input_builder_requires_exact_ten_bands(tmp_path: Path) -> None:
    paths = {band: tmp_path / f"{band}.tif" for band in S2CLOUDLESS_BANDS}
    for path in paths.values():
        make_band(path, 1000)
    model_input, nodata, info = build_model_input(paths)
    assert model_input.shape == (1, 3, 4, 10)
    assert np.isclose(model_input[0, 0, 0, 0], 0.1)
    assert nodata.sum() == 0
    assert info["scale_factor"] == 10000.0


def test_input_builder_rejects_grid_mismatch(tmp_path: Path) -> None:
    paths = {band: tmp_path / f"{band}.tif" for band in S2CLOUDLESS_BANDS}
    for path in paths.values():
        make_band(path, 1000)
    with rasterio.open(paths["B12"], "r+") as dataset:
        dataset.transform = from_origin(1, 30, 10, 10)
    with pytest.raises(ValueError, match="grid mismatch"):
        build_model_input(paths)


def test_quality_classes_preserve_nodata() -> None:
    probability = np.array([[0.1, 0.4, 0.9], [0.2, 0.8, 0.0]], dtype="float32")
    nodata = np.array([[False, False, False], [True, False, False]])
    cloud, quality = create_masks(probability, nodata, 0.4)
    assert quality.tolist() == [[0, 1, 1], [2, 1, 0]]
    stats = statistics(quality, probability)
    assert stats["total_pixels"] == 6
    assert stats["valid_pixels"] + stats["cloud_pixels"] + stats["nodata_pixels"] == 6


def test_s2cloudless_probability_shape_and_range(tmp_path: Path) -> None:
    paths = {band: tmp_path / f"{band}.tif" for band in S2CLOUDLESS_BANDS}
    for path in paths.values():
        make_band(path, 1000)
    model_input, _, _ = build_model_input(paths)
    probability, info = generate_probability(model_input, 0.4)
    assert probability.shape == (3, 4)
    assert probability.min() >= 0
    assert probability.max() <= 1
    assert info["model"] == "s2cloudless"


def test_l2a_cloud_input_requires_b10() -> None:
    from scripts.run_cloud_mask_workflow import EARTH_SEARCH_L2A_ASSET_KEYS

    assert EARTH_SEARCH_L2A_ASSET_KEYS["B10"] == "cirrus"
    assert "B10" in S2CLOUDLESS_BANDS


def test_cloud_configuration_rejects_invalid_threshold(monkeypatch) -> None:
    from backend.settings import Settings

    monkeypatch.setenv("CLOUD_PROBABILITY_THRESHOLD", "1.5")
    with pytest.raises(ValueError, match="between 0 and 1"):
        Settings()
