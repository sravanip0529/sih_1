import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.ingestion.aoi import AOI
from backend.ingestion.asset_resolver import AssetSelection
from backend.ingestion.stac_service import Scene
from backend.settings import settings


def write_provenance(
    scene: Scene,
    selection: AssetSelection,
    aoi: AOI,
    date_window: str,
    local_paths: dict[str, str],
    reason: str,
) -> Path:
    directory = settings.sentinel_data_directory / scene.datetime.strftime("%Y-%m-%d") / scene.scene_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "metadata.json"
    record: dict[str, Any] = {
        "scene_id": scene.scene_id,
        "collection": scene.collection,
        "provider": scene.provider,
        "stac_api_url": settings.stac_api_url,
        "stac_item_url": scene.source_url,
        "acquisition_datetime": scene.datetime.isoformat(),
        "cloud_cover": scene.cloud_cover,
        "platform": scene.platform,
        "aoi": aoi.to_geojson(),
        "bbox": list(scene.bbox),
        "date_window": date_window,
        "selected_assets": selection.assets,
        "local_paths": local_paths,
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "selection_reason": reason,
        "processing_configuration": "configs/processing.yaml",
        "cloud_filter_is_metadata_only": True,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path