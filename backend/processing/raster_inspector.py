from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import rasterio


@dataclass(frozen=True)
class RasterMetadata:
    path: str
    width: int
    height: int
    count: int
    crs: str
    transform: tuple[float, ...]
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    dtype: str
    nodata: float | int | None
    driver: str
    compression: str | None
    block_shapes: tuple[tuple[int, int], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_raster(path: Path) -> RasterMetadata:
    with rasterio.open(path) as dataset:
        if not dataset.crs or dataset.width <= 0 or dataset.height <= 0:
            raise ValueError(f"Invalid raster metadata: {path}")
        if dataset.res[0] <= 0 or dataset.res[1] <= 0:
            raise ValueError(f"Invalid raster resolution: {path}")
        return RasterMetadata(
            path=str(path),
            width=dataset.width,
            height=dataset.height,
            count=dataset.count,
            crs=dataset.crs.to_string(),
            transform=tuple(dataset.transform),
            bounds=tuple(dataset.bounds),
            resolution=tuple(dataset.res),
            dtype=dataset.dtypes[0],
            nodata=dataset.nodata,
            driver=dataset.driver,
            compression=dataset.compression.value if dataset.compression else None,
            block_shapes=tuple(dataset.block_shapes),
        )