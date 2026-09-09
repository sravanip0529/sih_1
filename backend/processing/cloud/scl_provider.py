from pathlib import Path

import httpx
import numpy as np
import rasterio

from backend.ingestion.downloader import download_asset
from backend.processing.raster_harmonizer import prepare_band
from backend.settings import settings


SCL_CLASSES = {
    0: "no_data",
    1: "saturated_or_defective",
    2: "dark_area_or_shadow",
    3: "cloud_shadow",
    4: "vegetation",
    5: "bare_soils",
    6: "water",
    7: "unclassified",
    8: "cloud_medium_probability",
    9: "cloud_high_probability",
    10: "cirrus",
    11: "snow_or_ice",
}
NODATA_CLASSES = {0, 1}
CLOUD_EXCLUDED_CLASSES = {3, 8, 9, 10}


def resolve_scl_url(metadata_path: Path) -> str:
    import json

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with httpx.Client(timeout=settings.stac_search_timeout_seconds) as client:
        response = client.get(metadata["stac_item_url"])
        response.raise_for_status()
    href = response.json().get("assets", {}).get("scl", {}).get("href")
    if not href:
        raise RuntimeError(f"Selected scene has no SCL asset: {metadata['scene_id']}")
    return href


def prepare_scl(metadata_path: Path, aoi, grid, output_dir: Path) -> tuple[np.ndarray, Path, dict[str, object]]:
    metadata = __import__("json").loads(metadata_path.read_text(encoding="utf-8"))
    raw_path = metadata_path.parent / "assets" / "scl.tif"
    if not raw_path.exists():
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        download_asset(resolve_scl_url(metadata_path), raw_path)
    prepared_path = output_dir / "scl_prepared.tif"
    prepare_band(raw_path, aoi, grid, prepared_path, "nearest", settings.output_nodata)
    with rasterio.open(prepared_path) as dataset:
        values = dataset.read(1).round().astype("uint8")
    unknown = sorted(set(np.unique(values).tolist()) - set(SCL_CLASSES))
    if unknown:
        raise ValueError(f"Unexpected Sentinel-2 SCL classes: {unknown}")
    return values, prepared_path, {"provider": "sentinel_scl", "scl_classes": SCL_CLASSES, "source_asset": str(raw_path), "resampling": "nearest"}


def quality_from_scl(scl: np.ndarray) -> tuple[np.ndarray, dict[str, object]]:
    nodata = np.isin(scl, list(NODATA_CLASSES))
    excluded = np.isin(scl, list(CLOUD_EXCLUDED_CLASSES))
    quality = np.where(nodata, settings.quality_mask_nodata_value, np.where(excluded, settings.quality_mask_cloud_value, settings.quality_mask_valid_value)).astype("uint8")
    return quality, {"nodata_classes": sorted(NODATA_CLASSES), "cloud_excluded_classes": sorted(CLOUD_EXCLUDED_CLASSES), "cloud_shadow_handling": "SCL class 3 is included in the conservative cloud-excluded class 1"}