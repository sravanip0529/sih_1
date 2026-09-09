from dataclasses import dataclass, asdict
from math import ceil, floor

from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.ops import transform
from affine import Affine


@dataclass(frozen=True)
class TargetGrid:
    crs: str
    resolution: float
    transform: Affine
    width: int
    height: int
    bounds: tuple[float, float, float, float]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["transform"] = tuple(self.transform)
        return value


def transform_aoi(aoi: Polygon, source_crs: str, target_crs: str) -> Polygon:
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transform(transformer.transform, aoi)


def build_grid(aoi: Polygon, target_crs: str, resolution: float, buffer_meters: float = 0.0) -> TargetGrid:
    if resolution <= 0:
        raise ValueError("Target resolution must be positive")
    if buffer_meters < 0:
        raise ValueError("AOI buffer must not be negative")
    projected = transform_aoi(aoi, "EPSG:4326", target_crs)
    if buffer_meters:
        projected = projected.buffer(buffer_meters)
    min_x, min_y, max_x, max_y = projected.bounds
    left = floor(min_x / resolution) * resolution
    bottom = floor(min_y / resolution) * resolution
    right = ceil(max_x / resolution) * resolution
    top = ceil(max_y / resolution) * resolution
    width = int(round((right - left) / resolution))
    height = int(round((top - bottom) / resolution))
    if width <= 0 or height <= 0:
        raise ValueError("AOI produces an empty target grid")
    return TargetGrid(
        crs=CRS.from_user_input(target_crs).to_string(),
        resolution=resolution,
        transform=Affine(resolution, 0, left, 0, -resolution, top),
        width=width,
        height=height,
        bounds=(left, bottom, right, top),
    )