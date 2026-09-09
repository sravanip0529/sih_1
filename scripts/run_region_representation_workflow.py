import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from backend.processing.regions import (
    build_region_preview,
    extract_regions,
    filter_regions,
    generate_semantic_description,
    summarize_region_statistics,
    write_region_outputs,
)
from backend.settings import settings

REFERENCE_DATE = "2023-06-05"
MOVING_DATE = "2024-06-26"


def read_raster(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(1).astype(np.float32)


def validate_phase8_inputs(change_root: Path) -> dict[str, object]:
    required = [
        "blue_difference.tif",
        "green_difference.tif",
        "red_difference.tif",
        "nir_difference.tif",
        "swir16_difference.tif",
        "change_magnitude.tif",
        "change_mask.tif",
        "quality_exclusion_mask.tif",
    ]
    missing = [name for name in required if not (change_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing Phase 8 inputs: {missing}")
    change_report = Path("data/change/change_report.json")
    if not change_report.exists():
        raise FileNotFoundError("Missing Phase 8 provenance report: data/change/change_report.json")
    with rasterio.open(change_root / "change_mask.tif") as mask_ds, rasterio.open(change_root / "change_magnitude.tif") as mag_ds:
        if mask_ds.crs != mag_ds.crs:
            raise ValueError("Phase 8 raster CRS mismatch")
        if (mask_ds.width, mask_ds.height) != (mag_ds.width, mag_ds.height):
            raise ValueError("Phase 8 raster dimensions mismatch")
        if mask_ds.transform != mag_ds.transform:
            raise ValueError("Phase 8 raster transform mismatch")
    return {"required_files": required, "provenance_report": str(change_report), "status": "validated"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract change regions from Phase 8 change evidence")
    parser.add_argument("--reference-date", default=REFERENCE_DATE)
    parser.add_argument("--moving-date", default=MOVING_DATE)
    parser.add_argument("--min-pixels", type=int, default=3)
    args = parser.parse_args()

    change_root = Path("data/change") / f"{args.reference_date}_to_{args.moving_date}"
    validate_phase8_inputs(change_root)
    change_report = Path("data/change/change_report.json")
    change_mask = read_raster(change_root / "change_mask.tif")
    change_magnitude = read_raster(change_root / "change_magnitude.tif")
    exclusion_mask = read_raster(change_root / "quality_exclusion_mask.tif")
    candidate_regions = extract_regions(change_mask.astype(np.uint8), change_value=1, excluded_value=2, connectivity=8)
    retained_regions = filter_regions(candidate_regions, min_pixels=args.min_pixels)

    region_metadata = []
    for region in retained_regions:
        pixels = region["pixels"]
        rows = [p[0] for p in pixels]
        cols = [p[1] for p in pixels]
        area_m2 = len(pixels) * settings.processing_resolution_m * settings.processing_resolution_m
        band_summary = {}
        for band in ("blue", "green", "red", "nir", "swir16"):
            band_arr = read_raster(change_root / f"{band}_difference.tif")
            values = np.asarray([band_arr[r, c] for r, c in pixels], dtype=np.float32)
            band_summary[band] = {
                "mean_difference": float(np.mean(values)) if values.size else 0.0,
                "median_difference": float(np.median(values)) if values.size else 0.0,
                "max_difference": float(np.max(values)) if values.size else 0.0,
                "min_difference": float(np.min(values)) if values.size else 0.0,
            }
        region_stats = summarize_region_statistics(region, magnitude=change_magnitude)
        region_entry = {
            **region,
            "reference_date": args.reference_date,
            "moving_date": args.moving_date,
            "pixel_count": int(region["pixel_count"]),
            "area_m2": float(area_m2),
            "area_hectares": float(area_m2 / 10000.0),
            "bbox": region["bbox"],
            "centroid": region["centroid"],
            "mean_change_magnitude": region_stats["mean_change_magnitude"],
            "median_change_magnitude": region_stats["median_change_magnitude"],
            "max_change_magnitude": region_stats["max_change_magnitude"],
            "min_change_magnitude": region_stats["min_change_magnitude"],
            "std_change_magnitude": region_stats["std_change_magnitude"],
            "band_summary": band_summary,
            "semantic_description": "",
        }
        region_entry["semantic_description"] = generate_semantic_description(region_entry)
        region_metadata.append(region_entry)

    for region in region_metadata:
        region["area_m2"] = float(region["area_m2"])
        region["area_hectares"] = float(region["area_hectares"])

    total_retained_area_m2 = sum(float(region["area_m2"]) for region in region_metadata)
    with rasterio.open(change_root / "change_mask.tif") as template:
        preview = build_region_preview(change_mask, region_metadata)
        with rasterio.open(change_root / "region_preview.tif", "w", driver="GTiff", width=template.width, height=template.height, count=1, dtype="uint16", crs=template.crs, transform=template.transform, nodata=0) as out:
            out.write(preview.astype(np.uint16), 1)

    outputs = write_region_outputs(Path("data/processed/regions"), region_metadata, crs=str(template.crs), resolution_m=settings.processing_resolution_m)
    report = {
        "phase": "phase_9",
        "status": "complete",
        "reference_date": args.reference_date,
        "moving_date": args.moving_date,
        "input_locations": {
            "change_mask": str(change_root / "change_mask.tif"),
            "change_magnitude": str(change_root / "change_magnitude.tif"),
            "quality_exclusion_mask": str(change_root / "quality_exclusion_mask.tif"),
            "change_report": str(change_root / "change_report.json"),
        },
        "crs": str(template.crs),
        "resolution_m": settings.processing_resolution_m,
        "connectivity": "8-connectivity",
        "change_value": 1,
        "excluded_value": 2,
        "candidate_region_count": len(candidate_regions),
        "filtered_region_count": len(candidate_regions) - len(retained_regions),
        "retained_region_count": len(retained_regions),
        "minimum_region_pixels": args.min_pixels,
        "total_retained_changed_area_m2": float(total_retained_area_m2),
        "largest_region_size": max((int(region["pixel_count"]) for region in region_metadata), default=0),
        "smallest_region_size": min((int(region["pixel_count"]) for region in region_metadata), default=0),
        "output_locations": outputs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    output_report = Path("data/processed/regions/region_report.json")
    output_report.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "candidate_regions": len(candidate_regions),
        "retained_regions": len(retained_regions),
        "filtered_regions": len(candidate_regions) - len(retained_regions),
        "largest_region": max((int(region["pixel_count"]) for region in region_metadata), default=0),
        "smallest_region": min((int(region["pixel_count"]) for region in region_metadata), default=0),
        "total_retained_area_m2": float(total_retained_area_m2),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
