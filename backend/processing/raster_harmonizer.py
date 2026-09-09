from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import WindowError
from rasterio.enums import Resampling
from rasterio.windows import from_bounds, transform as window_transform
from rasterio.warp import reproject

from backend.processing.grid import TargetGrid, transform_aoi


RESAMPLING_METHODS = {"nearest": Resampling.nearest, "bilinear": Resampling.bilinear, "cubic": Resampling.cubic}


def prepare_band(source_path: Path, aoi, grid: TargetGrid, destination: Path, method: str, nodata: float) -> dict[str, object]:
    if method not in RESAMPLING_METHODS:
        raise ValueError(f"Unsupported resampling method: {method}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(source_path) as source:
        source_aoi = transform_aoi(aoi, "EPSG:4326", source.crs)
        min_x, min_y, max_x, max_y = source_aoi.bounds
        window = from_bounds(min_x, min_y, max_x, max_y, source.transform)
        window = window.round_offsets().round_lengths()
        try:
            window = window.intersection(rasterio.windows.Window(0, 0, source.width, source.height))
        except WindowError as error:
            raise ValueError(f"AOI does not overlap raster: {source_path}") from error
        if window.width <= 0 or window.height <= 0:
            raise ValueError(f"AOI does not overlap raster: {source_path}")
        source_array = source.read(1, window=window, boundless=False)
        source_transform = window_transform(window, source.transform)
        source_nodata = source.nodata
        output = np.full((grid.height, grid.width), nodata, dtype=np.float32)
        reproject(
            source=source_array,
            destination=output,
            src_transform=source_transform,
            src_crs=source.crs,
            src_nodata=source_nodata,
            dst_transform=grid.transform,
            dst_crs=grid.crs,
            dst_nodata=nodata,
            resampling=RESAMPLING_METHODS[method],
        )
        profile = source.profile.copy()
        profile.update(
            driver="GTiff", dtype="float32", count=1, width=grid.width, height=grid.height,
            crs=grid.crs, transform=grid.transform, nodata=nodata, compress="deflate",
        )
        if grid.width >= 256 and grid.height >= 256:
            profile.update(tiled=True, blockxsize=256, blockysize=256)
        else:
            profile.pop("tiled", None)
            profile.pop("blockxsize", None)
            profile.pop("blockysize", None)
        with rasterio.open(destination, "w", **profile) as target:
            target.write(output, 1)
    return {"source_nodata": source_nodata, "output_nodata": nodata, "source_dtype": source.dtypes[0]}