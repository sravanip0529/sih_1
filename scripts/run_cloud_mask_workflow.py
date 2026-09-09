import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import rasterio
import yaml

from backend.ingestion.downloader import download_asset
from backend.ingestion.aoi import from_bbox
from backend.processing.cloud.input_builder import LOGICAL_BANDS, S2CLOUDLESS_BANDS, build_model_input
from backend.processing.cloud.quality_mask import create_masks, statistics
from backend.processing.cloud.s2cloudless_service import generate_probability
from backend.processing.grid import build_grid
from backend.processing.raster_harmonizer import prepare_band
from backend.processing.cloud.mask_validator import validate_probability, validate_quality
from backend.processing.cloud.mask_validator import validate_scl
from backend.processing.cloud.scl_provider import prepare_scl, quality_from_scl
from backend.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("cloud_mask_workflow")

EARTH_SEARCH_L2A_ASSET_KEYS = {
    "B01": "coastal",
    "B02": "blue",
    "B04": "red",
    "B05": "rededge1",
    "B08": "nir",
    "B8A": "nir08",
    "B09": "nir09",
    "B10": "cirrus",
    "B11": "swir16",
    "B12": "swir22",
}


def item_assets(metadata_path: Path) -> dict[str, str]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with httpx.Client(timeout=settings.stac_search_timeout_seconds) as client:
        response = client.get(metadata["stac_item_url"])
        response.raise_for_status()
    assets = response.json().get("assets", {})
    return {
        band: assets[asset_key]["href"]
        for band, asset_key in EARTH_SEARCH_L2A_ASSET_KEYS.items()
        if asset_key in assets and assets[asset_key].get("href")
    }


def prepare_inputs(metadata_path: Path, aoi, grid, output_dir: Path) -> tuple[dict[str, Path], dict[str, object]]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw_assets = metadata_path.parent / "assets"
    phase4_dir = settings.processed_data_directory / "sentinel" / metadata["acquisition_datetime"][:10]
    urls = None
    paths: dict[str, Path] = {}
    missing_raw = [
        band for band in S2CLOUDLESS_BANDS
        if not (phase4_dir / f"{LOGICAL_BANDS[band]}.tif").exists()
        and not (raw_assets / f"{LOGICAL_BANDS[band]}.tif").exists()
    ]
    if missing_raw:
        urls = item_assets(metadata_path)
        unavailable = [band for band in missing_raw if band not in urls]
        if unavailable:
            raise RuntimeError(
                f"Configured STAC item cannot provide required s2cloudless bands: {unavailable}. "
                "The current Earth Search L2A item has no usable B10 asset; do not substitute another band. "
                "Use a provider/product exposing valid B10 L1C data."
            )
    for band in S2CLOUDLESS_BANDS:
        logical = LOGICAL_BANDS[band]
        phase4_path = phase4_dir / f"{logical}.tif"
        if phase4_path.exists():
            paths[band] = phase4_path
            continue
        raw_path = raw_assets / f"{logical}.tif"
        if not raw_path.exists():
            if urls is None:
                urls = item_assets(metadata_path)
            logger.info("Downloading required cloud input %s for %s", band, metadata["scene_id"])
            download_asset(urls[band], raw_path)
        prepared_path = output_dir / "inputs" / f"{logical}.tif"
        prepare_band(raw_path, aoi, grid, prepared_path, settings.continuous_resampling_method, settings.output_nodata)
        paths[band] = prepared_path
    return paths, {"additional_bands": [band for band in S2CLOUDLESS_BANDS if not (phase4_dir / f"{LOGICAL_BANDS[band]}.tif").exists()]}


def write_raster(path: Path, array: np.ndarray, template: Path, dtype: str, nodata: float | int) -> None:
    with rasterio.open(template) as source:
        profile = source.profile.copy()
        profile.update(driver="GTiff", dtype=dtype, count=1, nodata=nodata, compress="deflate")
        path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(path, "w", **profile) as target:
            target.write(array.astype(dtype), 1)


def process_date(metadata_path: Path, aoi, grid, config: dict[str, object], output_root: Path) -> dict[str, object]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    date_key = metadata["acquisition_datetime"][:10]
    output_dir = output_root / date_key
    paths, asset_info = prepare_inputs(metadata_path, aoi, grid, output_dir)
    model_input, nodata_mask, input_info = build_model_input(paths)
    probability, model_info = generate_probability(model_input, settings.cloud_probability_threshold)
    cloud_mask, quality = create_masks(
        probability,
        nodata_mask,
        settings.cloud_probability_threshold,
        settings.quality_mask_valid_value,
        settings.quality_mask_cloud_value,
        settings.quality_mask_nodata_value,
    )
    probability_path = output_dir / "cloud_probability.tif"
    cloud_mask_path = output_dir / "cloud_mask.tif"
    quality_path = output_dir / "quality_mask.tif"
    template = paths["B02"]
    write_raster(probability_path, np.where(nodata_mask, -1.0, probability), template, "float32", -1.0)
    write_raster(cloud_mask_path, cloud_mask, template, "uint8", settings.quality_output_nodata)
    write_raster(quality_path, quality, template, "uint8", settings.quality_output_nodata)
    with rasterio.open(template) as dataset:
        signature = (dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height, tuple(dataset.res), tuple(dataset.bounds))
    validate_probability(probability_path, signature, -1.0)
    validate_quality(quality_path, signature, {settings.quality_mask_valid_value, settings.quality_mask_cloud_value, settings.quality_mask_nodata_value})
    quality_stats = statistics(quality, probability, settings.quality_mask_nodata_value)
    record = {
        "phase": "5.1",
        "source_scene_id": metadata.get("source_scene_id", metadata["scene_id"]),
        "source_acquisition_datetime": metadata.get("source_acquisition_datetime", metadata["acquisition_datetime"]),
        "phase4_metadata": str(phase4_dir_from_path(template)),
        "cloud_detector": model_info,
        "cloud_input": input_info,
        "additional_bands": asset_info["additional_bands"],
        "threshold": settings.cloud_probability_threshold,
        "mask_refinement": {"enabled": settings.cloud_mask_refinement_enabled, "dilation_pixels": 0, "erosion_pixels": 0},
        "mask_classes": {"valid": settings.quality_mask_valid_value, "cloud": settings.quality_mask_cloud_value, "nodata": settings.quality_mask_nodata_value},
        "nodata_policy": "Source nodata is authoritative; nodata is never classified as clear or cloud.",
        "outputs": {"cloud_probability": str(probability_path), "cloud_mask": str(cloud_mask_path), "quality_mask": str(quality_path)},
        "statistics": quality_stats,
        "grid": signature,
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        "cloud_shadow_detection": "not_implemented",
        "radiometric_normalization": "not_implemented",
    }
    (output_dir / "metadata.json").write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    return record


def process_scl_date(metadata_path: Path, aoi, grid, output_root: Path) -> dict[str, object]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    date_key = metadata["acquisition_datetime"][:10]
    output_dir = output_root / date_key
    scl, prepared_scl, provider_info = prepare_scl(metadata_path, aoi, grid, output_dir)
    quality, mapping_info = quality_from_scl(scl)
    cloud_mask = np.where(quality == settings.quality_mask_nodata_value, settings.quality_mask_nodata_value, (quality == settings.quality_mask_cloud_value).astype("uint8"))
    with rasterio.open(prepared_scl) as template:
        signature = (template.crs.to_string(), tuple(template.transform), template.width, template.height, tuple(template.res), tuple(template.bounds))
    scl_path = output_dir / "scl_classification.tif"
    cloud_mask_path = output_dir / "cloud_mask.tif"
    quality_path = output_dir / "quality_mask.tif"
    write_raster(scl_path, scl, prepared_scl, "uint8", settings.quality_output_nodata)
    write_raster(cloud_mask_path, cloud_mask, prepared_scl, "uint8", settings.quality_output_nodata)
    write_raster(quality_path, quality, prepared_scl, "uint8", settings.quality_output_nodata)
    validate_scl(scl_path, signature)
    validate_quality(quality_path, signature, {settings.quality_mask_valid_value, settings.quality_mask_cloud_value, settings.quality_mask_nodata_value})
    quality_stats = {
        "total_pixels": int(quality.size),
        "valid_pixels": int(np.count_nonzero(quality == settings.quality_mask_valid_value)),
        "cloud_pixels": int(np.count_nonzero(quality == settings.quality_mask_cloud_value)),
        "nodata_pixels": int(np.count_nonzero(quality == settings.quality_mask_nodata_value)),
    }
    quality_stats.update({
        "valid_percentage": quality_stats["valid_pixels"] / quality_stats["total_pixels"] * 100,
        "cloud_percentage": quality_stats["cloud_pixels"] / quality_stats["total_pixels"] * 100,
        "nodata_percentage": quality_stats["nodata_pixels"] / quality_stats["total_pixels"] * 100,
    })
    record = {
        "phase": 5,
        "provider": "sentinel_scl",
        "output_type": "categorical_classification",
        "source_scene_id": metadata.get("source_scene_id", metadata["scene_id"]),
        "source_acquisition_datetime": metadata.get("source_acquisition_datetime", metadata["acquisition_datetime"]),
        "phase4_metadata": str(settings.processed_data_directory / "sentinel" / date_key / "metadata.json"),
        "provider_info": provider_info,
        "class_mapping": mapping_info,
        "mask_classes": {"valid": settings.quality_mask_valid_value, "cloud": settings.quality_mask_cloud_value, "nodata": settings.quality_mask_nodata_value},
        "outputs": {"scl_classification": str(scl_path), "cloud_mask": str(cloud_mask_path), "quality_mask": str(quality_path)},
        "statistics": quality_stats,
        "grid": signature,
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        "radiometric_normalization": "not_implemented",
    }
    (output_dir / "metadata.json").write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    return record


def phase4_dir_from_path(path: Path) -> Path:
    return path.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate s2cloudless probability and quality masks for Phase 4 AOI rasters.")
    parser.add_argument("--config", default="configs/sample_sentinel.yaml")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    aoi = from_bbox(config["aoi"]["bbox"]).geometry
    grid = build_grid(aoi, settings.processing_target_crs, settings.processing_resolution_m, settings.aoi_buffer_meters)
    metadata_paths = sorted(settings.sentinel_data_directory.glob("*/**/metadata.json"))
    if len(metadata_paths) != 2:
        raise RuntimeError(f"Expected two Phase 3 provenance sidecars, found {len(metadata_paths)}")
    output_root = settings.processed_data_directory / "quality"
    if settings.cloud_provider == "sentinel_scl":
        records = [process_scl_date(path, aoi, grid, output_root) for path in metadata_paths]
    else:
        records = [process_date(path, aoi, grid, config, output_root) for path in metadata_paths]
    records.sort(key=lambda record: record["source_acquisition_datetime"])
    signatures = [tuple(record["grid"]) for record in records]
    if signatures[0] != signatures[1]:
        raise RuntimeError("Date quality outputs do not share the Phase 4 common grid")
    report = {"phase": "5.1", "provider": settings.cloud_provider, "requested_provider": settings.cloud_provider, "fallback_used": False, "grid_validation": "passed", "dates": records, "created_at": datetime.now(timezone.utc).isoformat()}
    report_path = output_root / "quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "grid_validation": "passed", "dates": [record["source_scene_id"] for record in records]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logger.error("Phase 5 cloud workflow failed: %s", error)
        raise SystemExit(2) from error
