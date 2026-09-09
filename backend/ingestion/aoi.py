from dataclasses import dataclass

from shapely.geometry import Polygon, shape


class AOIError(ValueError):
    """Raised when an area of interest is invalid or too large."""


@dataclass(frozen=True)
class AOI:
    geometry: Polygon

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return tuple(self.geometry.bounds)

    def intersects(self, geometry: object) -> bool:
        return self.geometry.intersects(geometry)

    def to_geojson(self) -> dict[str, object]:
        return {"type": "Polygon", "coordinates": [list(self.geometry.exterior.coords)]}


def from_bbox(bbox: list[float] | tuple[float, ...]) -> AOI:
    if len(bbox) != 4:
        raise AOIError("AOI bbox must contain [min_lon, min_lat, max_lon, max_lat]")
    min_lon, min_lat, max_lon, max_lat = bbox
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise AOIError("AOI bbox coordinates are outside valid ranges or have zero area")
    if (max_lon - min_lon) > 1 or (max_lat - min_lat) > 1:
        raise AOIError("AOI is too large for the Phase 3 development workflow")
    return AOI(Polygon([(min_lon, min_lat), (max_lon, min_lat), (max_lon, max_lat), (min_lon, max_lat)]))


def from_geojson(geojson: dict[str, object]) -> AOI:
    geometry = shape(geojson)
    if not isinstance(geometry, Polygon) or geometry.is_empty or not geometry.is_valid:
        raise AOIError("AOI GeoJSON must be a valid non-empty Polygon")
    min_lon, min_lat, max_lon, max_lat = geometry.bounds
    if not (-180 <= min_lon and max_lon <= 180 and -90 <= min_lat and max_lat <= 90):
        raise AOIError("AOI GeoJSON coordinates are outside valid ranges")
    if (max_lon - min_lon) > 1 or (max_lat - min_lat) > 1:
        raise AOIError("AOI is too large for the Phase 3 development workflow")
    return AOI(geometry)