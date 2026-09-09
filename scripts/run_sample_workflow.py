import argparse
import json
import logging
from datetime import date
from pathlib import Path

import yaml

from backend.ingestion.aoi import from_bbox
from backend.ingestion.asset_resolver import resolve_assets
from backend.ingestion.downloader import download_asset
from backend.ingestion.provenance import write_provenance
from backend.ingestion.scene_selection import select_scene
from backend.ingestion.stac_service import search_scenes
from backend.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("sample_workflow")


def run_period(aoi, period: dict, max_cloud: float, limit: int, required: tuple[str, ...], download: bool) -> dict[str, object]:
    logger.info("STAC search window=%s cloud_cover<=%s", period["window"], max_cloud)
    scenes = search_scenes(aoi, period["window"], max_cloud, limit)
    if not scenes:
        raise RuntimeError(f"No scenes found for window {period['window']} and AOI {aoi.bbox}")
    selected = select_scene(scenes, date.fromisoformat(period["requested_date"]), required)
    selected_assets = resolve_assets(selected.scene, required)
    if not selected_assets.complete:
        raise RuntimeError(f"Scene {selected.scene.scene_id} is missing assets: {selected_assets.missing}")
    local_paths: dict[str, str] = {}
    directory = settings.sentinel_data_directory / selected.scene.datetime.strftime("%Y-%m-%d") / selected.scene.scene_id / "assets"
    if download:
        for asset_name, url in selected.assets.assets.items():
            destination = directory / f"{asset_name}.tif"
            download_asset(url, destination)
            local_paths[asset_name] = str(destination)
    metadata_path = write_provenance(selected.scene, selected.assets, aoi, period["window"], local_paths, selected.reason)
    return {
        "requested_date": period["requested_date"],
        "window": period["window"],
        "candidate_count": len(scenes),
        "selected_scene_id": selected.scene.scene_id,
        "acquisition_datetime": selected.scene.datetime.isoformat(),
        "cloud_cover": selected.scene.cloud_cover,
        "selection_reason": selected.reason,
        "metadata_path": str(metadata_path),
        "local_paths": local_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover and optionally download a two-date Sentinel-2 sample.")
    parser.add_argument("--config", default="configs/sample_sentinel.yaml")
    parser.add_argument("--metadata-only", action="store_true", help="Search, validate, and record provenance without downloading COG assets")
    args = parser.parse_args()
    try:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        aoi = from_bbox(config["aoi"]["bbox"])
        required = tuple(config["required_assets"])
        results = {
            "provider": settings.stac_provider,
            "stac_api_url": settings.stac_api_url,
            "collection": settings.stac_collection,
            "aoi_bbox": aoi.bbox,
            "date_a": run_period(aoi, config["date_a"], config["max_cloud_cover"], config["search_limit"], required, config.get("download", True) and not args.metadata_only),
            "date_b": run_period(aoi, config["date_b"], config["max_cloud_cover"], config["search_limit"], required, config.get("download", True) and not args.metadata_only),
        }
        print(json.dumps(results, indent=2))
        return 0
    except Exception as error:
        logger.error("Phase 3 sample workflow failed: %s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
