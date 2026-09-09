from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pystac_client
from shapely.geometry import shape

from backend.ingestion.aoi import AOI
from backend.settings import settings


@dataclass(frozen=True)
class Scene:
    scene_id: str
    collection: str
    datetime: datetime
    bbox: tuple[float, ...]
    geometry: dict[str, Any]
    cloud_cover: float | None
    platform: str | None
    assets: dict[str, str]
    source_url: str
    provider: str


def open_catalog() -> pystac_client.Client:
    if not settings.stac_api_url:
        raise RuntimeError("STAC_API_URL is not configured")
    return pystac_client.Client.open(settings.stac_api_url)


def normalize_item(item: Any) -> Scene:
    if not item.id or not item.datetime or not item.bbox or not item.geometry:
        raise ValueError(f"STAC item {item.id!r} is missing required metadata")
    assets = {key: asset.href for key, asset in item.assets.items() if asset.href}
    return Scene(
        scene_id=item.id,
        collection=(item.collection_id or settings.stac_collection),
        datetime=item.datetime,
        bbox=tuple(item.bbox),
        geometry=item.geometry,
        cloud_cover=item.properties.get("eo:cloud_cover"),
        platform=item.properties.get("platform"),
        assets=assets,
        source_url=item.get_self_href() or "",
        provider=settings.stac_provider,
    )


def search_scenes(aoi: AOI, datetime_range: str, max_cloud_cover: float, limit: int = 20) -> list[Scene]:
    catalog = open_catalog()
    search = catalog.search(
        collections=[settings.stac_collection],
        intersects=aoi.to_geojson(),
        datetime=datetime_range,
        query={"eo:cloud_cover": {"lte": max_cloud_cover}},
        max_items=limit,
    )
    scenes: list[Scene] = []
    for item in search.items():
        try:
            scene = normalize_item(item)
            if aoi.intersects(shape(item.geometry)):
                scenes.append(scene)
        except ValueError:
            continue
    return scenes