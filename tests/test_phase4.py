from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from backend.ingestion.aoi import from_bbox
from backend.processing.grid import build_grid
from backend.processing.raster_harmonizer import prepare_band
from backend.processing.raster_inspector import inspect_raster
from backend.processing.rgb_preview import create_rgb_preview
from backend.processing.statistics import raster_statistics


def make_raster(path: Path, crs: str = "EPSG:32633", resolution: float = 20) -> None:
    transform = from_origin(500000, 6000000, resolution, resolution)
    with rasterio.open(path, "w", driver="GTiff", width=100, height=100, count=1, dtype="uint16", crs=crs, transform=transform, nodata=0) as dataset:
        dataset.write(np.ones((100, 100), dtype="uint16") * 1000, 1)


def test_raster_inspection_and_statistics(tmp_path: Path) -> None:
    path = tmp_path / "source.tif"
    make_raster(path)
    metadata = inspect_raster(path)
    assert metadata.crs == "EPSG:32633"
    assert metadata.resolution == (20.0, 20.0)
    assert raster_statistics(path, 0)["valid_pixel_count"] == 10000


def test_common_grid_is_deterministic_and_reprojects_20m(tmp_path: Path) -> None:
    source = tmp_path / "source.tif"
    make_raster(source, resolution=20)
    aoi = from_bbox(list(transform_bounds("EPSG:32633", "EPSG:4326", 500000, 5998000, 502000, 6000000))).geometry
    grid = build_grid(aoi, "EPSG:32633", 10)
    output = tmp_path / "prepared.tif"
    prepare_band(source, aoi, grid, output, "bilinear", 0)
    with rasterio.open(output) as dataset:
        assert dataset.crs.to_string() == "EPSG:32633"
        assert dataset.res == (10.0, 10.0)
        assert (dataset.width, dataset.height) == (grid.width, grid.height)


def test_rgb_preview_is_three_band_uint8(tmp_path: Path) -> None:
    paths = []
    for name, value in (("red", 100), ("green", 200), ("blue", 300)):
        path = tmp_path / f"{name}.tif"
        make_raster(path)
        paths.append(path)
    preview = tmp_path / "preview.tif"
    create_rgb_preview(paths[0], paths[1], paths[2], preview)
    with rasterio.open(preview) as dataset:
        assert dataset.count == 3
        assert dataset.dtypes == ("uint8", "uint8", "uint8")