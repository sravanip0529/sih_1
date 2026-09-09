from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import box as shapely_box


def extract_regions(change_mask: np.ndarray, *, change_value: int = 1, excluded_value: int = 2, connectivity: int = 8) -> list[dict[str, object]]:
    mask = np.asarray(change_mask, dtype=np.uint8)
    if connectivity not in {4, 8}:
        raise ValueError("Connectivity must be 4 or 8")
    visited = np.zeros(mask.shape, dtype=bool)
    regions: list[dict[str, object]] = []
    height, width = mask.shape
    for row in range(height):
        for col in range(width):
            if visited[row, col] or mask[row, col] != change_value:
                continue
            stack = [(row, col)]
            visited[row, col] = True
            pixels: list[tuple[int, int]] = []
            while stack:
                r, c = stack.pop()
                pixels.append((r, c))
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        if connectivity == 4 and abs(dr) + abs(dc) != 1:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < height and 0 <= cc < width and not visited[rr, cc] and mask[rr, cc] == change_value:
                            visited[rr, cc] = True
                            stack.append((rr, cc))
            pixels = sorted(pixels)
            rows = [p[0] for p in pixels]
            cols = [p[1] for p in pixels]
            regions.append({
                "region_id": "",
                "pixels": pixels,
                "pixel_count": len(pixels),
                "bbox": (min(cols), min(rows), max(cols), max(rows)),
                "centroid": ((min(cols) + max(cols)) / 2.0, (min(rows) + max(rows)) / 2.0),
            })
    regions.sort(key=lambda item: (-int(item["pixel_count"]), int(item["bbox"][1]), int(item["bbox"][0])))
    for index, region in enumerate(regions, start=1):
        region["region_id"] = f"region_{index:04d}"
    return regions


def filter_regions(regions: list[dict[str, object]], *, min_pixels: int = 1, min_area_m2: float | None = None, pixel_area_m2: float = 100.0) -> list[dict[str, object]]:
    retained: list[dict[str, object]] = []
    for region in regions:
        pixel_count = int(region["pixel_count"])
        area_m2 = pixel_count * pixel_area_m2
        if min_area_m2 is not None and area_m2 < min_area_m2:
            continue
        if pixel_count < min_pixels:
            continue
        retained.append(region)
    return retained


def summarize_region_statistics(region: dict[str, object], *, magnitude: np.ndarray) -> dict[str, float | int | tuple[int, int, int, int]]:
    pixels = region["pixels"]
    values = np.asarray([magnitude[r, c] for r, c in pixels], dtype=np.float32)
    if values.size == 0:
        raise ValueError("Region contains no pixels")
    stats = {
        "mean_change_magnitude": float(np.mean(values)),
        "median_change_magnitude": float(np.median(values)),
        "max_change_magnitude": float(np.max(values)),
        "min_change_magnitude": float(np.min(values)),
        "std_change_magnitude": float(np.std(values)),
        "pixel_count": int(values.size),
        "bbox": region["bbox"],
    }
    return stats


def generate_semantic_description(region: dict[str, object]) -> str:
    region_id = region["region_id"]
    pixel_count = region["pixel_count"]
    area_m2 = region.get("area_m2", pixel_count * 100.0)
    reference_date = region.get("reference_date", "reference")
    moving_date = region.get("moving_date", "moving")
    magnitude = region.get("mean_change_magnitude", 0.0)
    band_summary = region.get("band_summary", {})
    dominant = []
    for band in ("nir", "swir16", "red", "green", "blue"):
        info = band_summary.get(band, {})
        mean_value = info.get("mean_difference")
        if mean_value is not None:
            if mean_value < 0:
                dominant.append(f"{band.upper()} negative")
            elif mean_value > 0:
                dominant.append(f"{band.upper()} positive")
    dominant_text = ", ".join(dominant) if dominant else "spectral change mixed"
    return (
        f"Region {region_id} covers approximately {area_m2:.0f} square meters and contains {pixel_count} changed pixels between "
        f"{reference_date} and {moving_date}. The region shows {magnitude:.2f} mean change magnitude. "
        f"Major spectral direction patterns: {dominant_text}. This description represents spectral change evidence and does not identify a verified real-world land-cover event."
    )


def _write_geojson(path: Path, regions: list[dict[str, object]], *, crs: str = "EPSG:32633") -> None:
    features = []
    for region in regions:
        min_col, min_row, max_col, max_row = region["bbox"]
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [min_col, min_row],
                [max_col, min_row],
                [max_col, max_row],
                [min_col, max_row],
                [min_col, min_row],
            ]],
        }
        properties = {
            "region_id": region["region_id"],
            "pixel_count": int(region["pixel_count"]),
            "area_m2": float(region.get("area_m2", int(region["pixel_count"]) * 100.0)),
            "centroid_x": float(region["centroid"][0]),
            "centroid_y": float(region["centroid"][1]),
        }
        features.append({"type": "Feature", "properties": properties, "geometry": geom})
    feature_collection = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": crs}}, "features": features}
    path.write_text(json.dumps(feature_collection, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, regions: list[dict[str, object]]) -> None:
    fieldnames = ["region_id", "pixel_count", "area_m2", "area_hectares", "centroid_x", "centroid_y", "bbox_min_x", "bbox_min_y", "bbox_max_x", "bbox_max_y", "mean_change_magnitude", "median_change_magnitude", "max_change_magnitude"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for region in regions:
            writer.writerow({
                "region_id": region["region_id"],
                "pixel_count": int(region["pixel_count"]),
                "area_m2": float(region.get("area_m2", int(region["pixel_count"]) * 100.0)),
                "area_hectares": float(region.get("area_m2", int(region["pixel_count"]) * 100.0) / 10000.0),
                "centroid_x": float(region["centroid"][0]),
                "centroid_y": float(region["centroid"][1]),
                "bbox_min_x": float(region["bbox"][0]),
                "bbox_min_y": float(region["bbox"][1]),
                "bbox_max_x": float(region["bbox"][2]),
                "bbox_max_y": float(region["bbox"][3]),
                "mean_change_magnitude": float(region.get("mean_change_magnitude", 0.0)),
                "median_change_magnitude": float(region.get("median_change_magnitude", 0.0)),
                "max_change_magnitude": float(region.get("max_change_magnitude", 0.0)),
            })


def build_region_preview(change_mask: np.ndarray, regions: list[dict[str, object]], *, excluded_value: int = 2) -> np.ndarray:
    preview = np.full(change_mask.shape, excluded_value, dtype=np.uint8)
    for region in regions:
        for row, col in region["pixels"]:
            preview[row, col] = int(region["region_id"].split("_")[-1])
    return preview


def write_region_outputs(output_dir: Path, regions: list[dict[str, object]], *, crs: str = "EPSG:32633", resolution_m: float = 10.0) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    regions_path = output_dir / "regions.json"
    geojson_path = output_dir / "regions.geojson"
    csv_path = output_dir / "region_features.csv"
    report_path = output_dir / "region_report.json"
    preview_path = output_dir / "region_preview.tif"
    _write_geojson(geojson_path, regions, crs=crs)
    _write_csv(csv_path, regions)
    regions_path.write_text(json.dumps({"regions": regions, "crs": crs, "resolution_m": resolution_m}, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps({"phase": "phase_9", "regions": len(regions), "crs": crs, "resolution_m": resolution_m, "timestamp": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n", encoding="utf-8")
    return {
        "regions": str(regions_path),
        "geojson": str(geojson_path),
        "csv": str(csv_path),
        "report": str(report_path),
        "preview": str(preview_path),
    }
