from datetime import datetime, timezone
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from backend.ingestion.aoi import AOIError, from_bbox, from_geojson
from backend.ingestion.asset_resolver import resolve_assets
from backend.ingestion.downloader import download_asset
from backend.ingestion.scene_selection import select_scene
from backend.ingestion.stac_service import Scene


def scene(scene_id: str, cloud: float, day: int, assets: tuple[str, ...] = ("blue", "green", "red", "nir", "swir16")) -> Scene:
    return Scene(
        scene_id=scene_id,
        collection="sentinel-2-l2a",
        datetime=datetime(2023, 6, day, tzinfo=timezone.utc),
        bbox=(13.3, 52.4, 13.5, 52.6),
        geometry={"type": "Polygon", "coordinates": [[[13.3, 52.4], [13.5, 52.4], [13.5, 52.6], [13.3, 52.6], [13.3, 52.4]]]},
        cloud_cover=cloud,
        platform="sentinel-2a",
        assets={asset: f"https://example.test/{asset}.tif" for asset in assets},
        source_url=f"https://example.test/{scene_id}",
        provider="test",
    )


def test_aoi_bbox_and_geojson_validation() -> None:
    assert from_bbox([13.3, 52.4, 13.4, 52.5]).bbox == (13.3, 52.4, 13.4, 52.5)
    assert from_geojson({"type": "Polygon", "coordinates": [[[13.3, 52.4], [13.4, 52.4], [13.4, 52.5], [13.3, 52.4]]]}).geometry.is_valid
    with pytest.raises(AOIError):
        from_bbox([13.4, 52.5, 13.3, 52.4])
    with pytest.raises(AOIError):
        from_geojson({"type": "Point", "coordinates": [13.3, 52.4]})


def test_asset_validation_reports_missing_assets() -> None:
    selection = resolve_assets(scene("incomplete", 5, 10, ("blue", "green", "red")))
    assert selection.complete is False
    assert selection.missing == ("nir", "swir16")


def test_selection_is_deterministic_by_cloud_then_date_then_id() -> None:
    result = select_scene([scene("later", 5, 20), scene("best", 5, 15), scene("cloudy", 10, 15)], datetime(2023, 6, 15, tzinfo=timezone.utc).date())
    assert result.scene.scene_id == "best"


def test_download_uses_existing_file_without_network(tmp_path: Path) -> None:
    destination = tmp_path / "assets" / "red.tif"
    destination.parent.mkdir()
    destination.write_bytes(b"sample")
    assert download_asset("https://invalid.example/red.tif", destination) == 6
    assert destination.read_bytes() == b"sample"
