import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from backend.processing.normalization import valid_mask_from_quality, normalize_band, raster_statistics
from backend.settings import settings

BANDS = ("blue", "green", "red", "nir", "swir16")
REFERENCE_DATE = "2023-06-05"
MOVING_DATE = "2024-06-26"


def choose_input_root(date_key: str) -> Path:
    aligned_root = Path("data/aligned") / date_key
    if aligned_root.exists():
        return aligned_root
    return Path("data/processed/sentinel") / date_key


def load_band(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(1).astype(np.float32)


def load_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(1).astype(np.uint8)


def validate_geometry(ref_path: Path, mov_path: Path, ref_mask: Path, mov_mask: Path) -> None:
    with rasterio.open(ref_path) as ref_ds, rasterio.open(mov_path) as mov_ds, rasterio.open(ref_mask) as ref_mask_ds, rasterio.open(mov_mask) as mov_mask_ds:
        if ref_ds.crs != mov_ds.crs:
            raise ValueError("CRS mismatch between dates")
        if (ref_ds.width, ref_ds.height) != (mov_ds.width, mov_ds.height):
            raise ValueError("Dimensions mismatch")
        if ref_ds.transform != mov_ds.transform:
            raise ValueError("Transform mismatch")
        if ref_mask_ds.shape != ref_ds.shape or mov_mask_ds.shape != mov_ds.shape:
            raise ValueError("Mask shape mismatch")
        if ref_mask_ds.transform != ref_ds.transform or mov_mask_ds.transform != mov_ds.transform:
            raise ValueError("Mask transform mismatch")


def write_band(path: Path, array: np.ndarray, template: Path, nodata: float = 0.0) -> None:
    with rasterio.open(template) as ds:
        profile = ds.profile.copy()
        profile.update(driver="GTiff", dtype="float32", count=1, nodata=nodata, compress="deflate")
        path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(path, "w", **profile) as target:
            target.write(np.asarray(array, dtype=np.float32), 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize the real moving-date Sentinel pair to the reference date using valid-pixel median scaling.")
    parser.add_argument("--reference-date", default=REFERENCE_DATE)
    parser.add_argument("--moving-date", default=MOVING_DATE)
    args = parser.parse_args()

    reference_date = args.reference_date
    moving_date = args.moving_date
    ref_root = choose_input_root(reference_date)
    mov_root = choose_input_root(moving_date)
    quality_root = Path("data/processed/quality")
    ref_quality_path = quality_root / reference_date / "quality_mask.tif"
    mov_quality_path = quality_root / moving_date / "quality_mask.tif"
    if not ref_quality_path.exists() or not mov_quality_path.exists():
        raise FileNotFoundError("Missing quality masks for normalization")

    output_root = Path("data/normalized")
    reference_out = output_root / reference_date
    moving_out = output_root / moving_date
    reference_out.mkdir(parents=True, exist_ok=True)
    moving_out.mkdir(parents=True, exist_ok=True)

    band_stats = {}
    before_after = {}
    for band in BANDS:
        ref_path = ref_root / f"{band}.tif"
        mov_path = mov_root / f"{band}.tif"
        validate_geometry(ref_path, mov_path, ref_quality_path, mov_quality_path)
        ref_data = load_band(ref_path)
        mov_data = load_band(mov_path)
        ref_mask = valid_mask_from_quality(load_mask(ref_quality_path), valid_value=settings.quality_mask_valid_value)
        mov_mask = valid_mask_from_quality(load_mask(mov_quality_path), valid_value=settings.quality_mask_valid_value)
        if ref_data.shape != mov_data.shape:
            raise ValueError(f"Band {band} shape mismatch")
        ref_valid = ref_data[ref_mask]
        mov_valid = mov_data[mov_mask]
        if ref_valid.size == 0 or mov_valid.size == 0:
            raise ValueError(f"Band {band} has no valid pixels after masking")
        ref_median = float(np.median(ref_valid))
        mov_median = float(np.median(mov_valid))
        if ref_median <= 0 or mov_median <= 0:
            raise ValueError(f"Band {band} median must be positive for normalization")
        scale = ref_median / mov_median
        normalized = normalize_band(ref_data, mov_data, ref_mask, mov_mask)
        write_band(reference_out / f"{band}.tif", ref_data, ref_path)
        write_band(moving_out / f"{band}.tif", normalized, mov_path)
        before_after[band] = {
            "reference_median": ref_median,
            "moving_median_before": mov_median,
            "moving_median_after": float(np.median(normalized[mov_mask])),
            "scale": scale,
            "mean_difference_before": float(np.mean(mov_valid) - np.mean(ref_valid)),
            "mean_difference_after": float(np.mean(normalized[mov_mask]) - np.mean(ref_valid)),
        }
        band_stats[band] = {
            "reference": raster_statistics(ref_valid, nodata=None),
            "moving_before": raster_statistics(mov_valid, nodata=None),
            "moving_after": raster_statistics(normalized[mov_mask], nodata=None),
        }

    report = {
        "phase": "phase_7",
        "status": "accepted",
        "reference_date": reference_date,
        "moving_date": moving_date,
        "method": "median_scaling",
        "bands": BANDS,
        "valid_mask_values": {"valid": settings.quality_mask_valid_value, "cloud": settings.quality_mask_cloud_value, "nodata": settings.quality_mask_nodata_value},
        "quality_mask_paths": {"reference": str(ref_quality_path), "moving": str(mov_quality_path)},
        "input_paths": {"reference": str(ref_root), "moving": str(mov_root)},
        "before_after": before_after,
        "band_statistics": band_stats,
        "geometry": {
            "reference": {"crs": str(rasterio.open(ref_root / f"{BANDS[0]}.tif").crs), "width": rasterio.open(ref_root / f"{BANDS[0]}.tif").width, "height": rasterio.open(ref_root / f"{BANDS[0]}.tif").height, "transform": tuple(rasterio.open(ref_root / f"{BANDS[0]}.tif").transform)},
            "moving": {"crs": str(rasterio.open(mov_root / f"{BANDS[0]}.tif").crs), "width": rasterio.open(mov_root / f"{BANDS[0]}.tif").width, "height": rasterio.open(mov_root / f"{BANDS[0]}.tif").height, "transform": tuple(rasterio.open(mov_root / f"{BANDS[0]}.tif").transform)},
            "geometry_preserved": True,
        },
        "decision": "normalization_applied_with_valid_masking_and_median_scaling",
        "limitations": "This method reduces cross-date median offset using valid pixels only; it does not remove all seasonal, atmospheric, illumination, sensor, or land-cover differences.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    report_path = output_root / "normalization_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": "accepted", "reference_date": reference_date, "moving_date": moving_date, "method": "median_scaling", "scale_factors": {band: before_after[band]["scale"] for band in BANDS}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
