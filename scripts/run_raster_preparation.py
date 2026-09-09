import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml
from shapely.geometry import box

from backend.ingestion.aoi import from_bbox
from backend.processing.grid import build_grid
from backend.processing.raster_harmonizer import prepare_band
from backend.processing.raster_inspector import inspect_raster
from backend.processing.rgb_preview import create_rgb_preview
from backend.processing.statistics import raster_statistics
from backend.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("raster_preparation")


def source_path(metadata_path: Path, band: str) -> Path:
    path = metadata_path.parent / "assets" / f"{band}.tif"
    if not path.exists():
        raise FileNotFoundError(f"Missing source asset for {band}: {path}")
    return path


def prepare_scene(metadata_path: Path, aoi, grid, bands: tuple[str, ...], output_root: Path, dry_run: bool) -> dict[str, object]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    scene_id = metadata["scene_id"]
    date_key = metadata["acquisition_datetime"][:10]
    scene_output = output_root / date_key
    records: dict[str, object] = {"scene_id": scene_id, "acquisition_datetime": metadata["acquisition_datetime"], "bands": {}}
    for band in bands:
        path = source_path(metadata_path, band)
        source_info = inspect_raster(path).to_dict()
        if not dry_run:
            destination = scene_output / f"{band}.tif"
            nodata_info = prepare_band(path, aoi, grid, destination, settings.continuous_resampling_method, settings.output_nodata)
            stats = raster_statistics(destination, settings.output_nodata)
            records["bands"][band] = {"source": source_info, "output_path": str(destination), "statistics": stats, **nodata_info}
        else:
            records["bands"][band] = {"source": source_info}
    if not dry_run and settings.rgb_preview_enabled:
        preview = scene_output / "rgb_preview.tif"
        create_rgb_preview(scene_output / "red.tif", scene_output / "green.tif", scene_output / "blue.tif", preview, settings.rgb_preview_percentile_low, settings.rgb_preview_percentile_high)
        records["rgb_preview"] = {"path": str(preview), "percentile_low": settings.rgb_preview_percentile_low, "percentile_high": settings.rgb_preview_percentile_high}
    records["source_metadata"] = str(metadata_path)
    return records


def validate_common_grid(report: dict[str, object], bands: tuple[str, ...]) -> None:
    signatures = []
    for scene in (report["date_a"], report["date_b"]):
        for band in bands:
            import rasterio
            with rasterio.open(scene["bands"][band]["output_path"]) as dataset:
                signatures.append((dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height, tuple(dataset.res), tuple(dataset.bounds)))
    if len(set(signatures)) != 1:
        raise ValueError("Prepared bands do not share one common CRS, transform, dimensions, resolution, and bounds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase 3 Sentinel-2 COGs on one common AOI grid.")
    parser.add_argument("--config", default="configs/sample_sentinel.yaml")
    parser.add_argument("--metadata-only", action="store_true", help="Inspect sources and grid without writing prepared rasters")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    aoi = from_bbox(config["aoi"]["bbox"]).geometry
    grid = build_grid(aoi, settings.processing_target_crs, settings.processing_resolution_m, settings.aoi_buffer_meters)
    raw_root = settings.sentinel_data_directory
    metadata_paths = sorted(raw_root.glob("*/**/metadata.json"))
    if len(metadata_paths) != 2:
        raise RuntimeError(f"Expected two Phase 3 metadata sidecars, found {len(metadata_paths)}")
    bands = tuple(config["required_assets"])
    output_root = settings.processed_data_directory / "sentinel"
    report: dict[str, object] = {
        "phase": 4,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "aoi": config["aoi"],
        "aoi_buffer_meters": settings.aoi_buffer_meters,
        "target_grid": grid.to_dict(),
        "resampling_method": settings.continuous_resampling_method,
        "output_nodata": settings.output_nodata,
        "bands": list(bands),
    }
    records = [prepare_scene(path, aoi, grid, bands, output_root, args.metadata_only) for path in metadata_paths]
    records.sort(key=lambda record: record["acquisition_datetime"])
    report["date_a"], report["date_b"] = records
    if not args.metadata_only:
        validate_common_grid(report, bands)
        report["cross_date_grid_validation"] = "passed"
        report_path = output_root / "preparation_report.json"
    else:
        report["cross_date_grid_validation"] = "not_run_metadata_only"
        report_path = output_root / "preparation_report_dry_run.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not args.metadata_only:
        for record in records:
            date_metadata = {
                "phase": 4,
                "source_scene_id": record["scene_id"],
                "source_metadata": record["source_metadata"],
                "source_acquisition_datetime": record["acquisition_datetime"],
                "aoi": config["aoi"],
                "aoi_buffer_meters": settings.aoi_buffer_meters,
                "target_grid": grid.to_dict(),
                "resampling_method": settings.continuous_resampling_method,
                "output_nodata": settings.output_nodata,
                "bands": record["bands"],
                "rgb_preview": record.get("rgb_preview"),
                "processing_timestamp": report["created_at"],
                "cloud_masking": "not_implemented",
                "registration": "not_implemented",
                "radiometric_normalization": "not_implemented",
            }
            date_dir = output_root / record["acquisition_datetime"][:10]
            (date_dir / "metadata.json").write_text(json.dumps(date_metadata, indent=2, default=str) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "target_grid": grid.to_dict(), "cross_date_grid_validation": report["cross_date_grid_validation"]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
