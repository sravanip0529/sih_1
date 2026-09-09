import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from backend.processing.change_detection import (
    build_joint_valid_mask,
    build_quality_exclusion_mask,
    classify_change,
    compute_change_magnitude,
    compute_robust_scale,
    compute_signed_difference,
    compute_summary,
    select_threshold,
    validate_geometry,
    validate_output_geometry,
    validate_quality_mask,
    write_raster,
)
from backend.settings import settings

BANDS = ("blue", "green", "red", "nir", "swir16")
REFERENCE_DATE = "2023-06-05"
MOVING_DATE = "2024-06-26"
OUTPUT_ROOT = Path("data/change")


def read_array(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(1).astype(np.float32)


def read_quality(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(1).astype(np.uint8)


def validate_inputs(reference_dir: Path, moving_dir: Path, ref_quality_path: Path, mov_quality_path: Path) -> dict[str, object]:
    for band in BANDS:
        validate_geometry(reference_dir / f"{band}.tif", moving_dir / f"{band}.tif")
    validate_quality_mask(ref_quality_path, reference_dir / "blue.tif", (settings.quality_mask_valid_value, settings.quality_mask_cloud_value, settings.quality_mask_nodata_value))
    validate_quality_mask(mov_quality_path, moving_dir / "blue.tif", (settings.quality_mask_valid_value, settings.quality_mask_cloud_value, settings.quality_mask_nodata_value))
    with rasterio.open(reference_dir / "blue.tif") as ref_ds, rasterio.open(moving_dir / "blue.tif") as mov_ds, rasterio.open(ref_quality_path) as ref_q, rasterio.open(mov_quality_path) as mov_q:
        checks = {
            "reference_crs": ref_ds.crs.to_string(),
            "moving_crs": mov_ds.crs.to_string(),
            "reference_shape": (ref_ds.width, ref_ds.height),
            "moving_shape": (mov_ds.width, mov_ds.height),
            "reference_transform": tuple(ref_ds.transform),
            "moving_transform": tuple(mov_ds.transform),
            "reference_quality_shape": (ref_q.width, ref_q.height),
            "moving_quality_shape": (mov_q.width, mov_q.height),
            "quality_classes": sorted({int(v) for v in np.unique(ref_q.read(1))} | {int(v) for v in np.unique(mov_q.read(1))}),
        }
        if ref_ds.crs != mov_ds.crs:
            raise ValueError("CRS mismatch")
        if ref_ds.res != mov_ds.res:
            raise ValueError("Resolution mismatch")
        if (ref_ds.width, ref_ds.height) != (mov_ds.width, mov_ds.height):
            raise ValueError("Raster dimensions mismatch")
        if ref_ds.transform != mov_ds.transform:
            raise ValueError("Raster transform mismatch")
    return checks


def compute_band_outputs(reference_dir: Path, moving_dir: Path, valid_mask: np.ndarray, threshold_k: float) -> tuple[dict[str, np.ndarray], dict[str, float], dict[str, np.ndarray], np.ndarray, float]:
    band_differences: dict[str, np.ndarray] = {}
    robust_scales: dict[str, float] = {}
    standardized: dict[str, np.ndarray] = {}
    for band in BANDS:
        ref = read_array(reference_dir / f"{band}.tif")
        mov = read_array(moving_dir / f"{band}.tif")
        difference = np.full(ref.shape, 0.0, dtype=np.float32)
        diff_valid = compute_signed_difference(ref, mov, valid_mask)
        difference[valid_mask] = diff_valid[valid_mask]
        band_differences[band] = difference
        scale = compute_robust_scale(diff_valid[valid_mask])
        robust_scales[band] = scale
        standardized[band] = np.zeros_like(diff_valid, dtype=np.float32)
        standardized[band][valid_mask] = diff_valid[valid_mask] / scale if scale > 0 else 0.0
    magnitude = compute_change_magnitude(standardized)
    threshold = select_threshold(magnitude[valid_mask], method="median_plus_k", k=threshold_k)
    return band_differences, robust_scales, standardized, magnitude, threshold


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute spectral change evidence between reference and normalized moving Sentinel-2 imagery.")
    parser.add_argument("--reference-date", default=REFERENCE_DATE)
    parser.add_argument("--moving-date", default=MOVING_DATE)
    parser.add_argument("--threshold-k", type=float, default=3.0)
    args = parser.parse_args()

    ref_date = args.reference_date
    mov_date = args.moving_date
    ref_dir = Path("data/normalized") / ref_date
    mov_dir = Path("data/normalized") / mov_date
    ref_quality_path = Path("data/processed/quality") / ref_date / "quality_mask.tif"
    mov_quality_path = Path("data/processed/quality") / mov_date / "quality_mask.tif"

    for path in [ref_dir / "blue.tif", mov_dir / "blue.tif", ref_quality_path, mov_quality_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    checks = validate_inputs(ref_dir, mov_dir, ref_quality_path, mov_quality_path)
    ref_quality = read_quality(ref_quality_path)
    mov_quality = read_quality(mov_quality_path)
    joint_valid = build_joint_valid_mask(ref_quality, mov_quality, valid_value=settings.quality_mask_valid_value, cloud_value=settings.quality_mask_cloud_value, nodata_value=settings.quality_mask_nodata_value)
    total_pixels = int(joint_valid.size)
    ref_valid_pixels = int(np.count_nonzero(ref_quality == settings.quality_mask_valid_value))
    mov_valid_pixels = int(np.count_nonzero(mov_quality == settings.quality_mask_valid_value))
    joint_valid_pixels = int(np.count_nonzero(joint_valid))
    excluded_cloud_pixels = int(np.count_nonzero((ref_quality == settings.quality_mask_cloud_value) | (mov_quality == settings.quality_mask_cloud_value)))
    excluded_nodata_pixels = int(np.count_nonzero((ref_quality == settings.quality_mask_nodata_value) | (mov_quality == settings.quality_mask_nodata_value)))
    other_invalid_pixels = int(total_pixels - ref_valid_pixels - mov_valid_pixels + joint_valid_pixels)
    joint_valid_fraction = joint_valid_pixels / total_pixels if total_pixels else 0.0

    valid_mask = joint_valid.copy()
    for band in BANDS:
        arr = read_array(ref_dir / f"{band}.tif")
        if not np.all(np.isfinite(arr[valid_mask])):
            raise ValueError(f"Non-finite reference values remain in valid pixels for {band}")
        arr_m = read_array(mov_dir / f"{band}.tif")
        if not np.all(np.isfinite(arr_m[valid_mask])):
            raise ValueError(f"Non-finite moving values remain in valid pixels for {band}")

    band_differences, robust_scales, _, magnitude, threshold = compute_band_outputs(ref_dir, mov_dir, valid_mask, args.threshold_k)

    output_dir = OUTPUT_ROOT / f"{ref_date}_to_{mov_date}"
    output_dir.mkdir(parents=True, exist_ok=True)

    for band, diff in band_differences.items():
        write_raster(output_dir / f"{band}_difference.tif", diff, ref_dir / "blue.tif", dtype="float32", nodata=0.0)
    write_raster(output_dir / "change_magnitude.tif", magnitude, ref_dir / "blue.tif", dtype="float32", nodata=0.0)
    exclusion_mask = build_quality_exclusion_mask(ref_quality, mov_quality, settings.quality_mask_valid_value, settings.quality_mask_cloud_value, settings.quality_mask_nodata_value)
    write_raster(output_dir / "quality_exclusion_mask.tif", exclusion_mask.astype(np.float32), ref_dir / "blue.tif", dtype="float32", nodata=0.0)
    change_mask = classify_change(magnitude, threshold, excluded=(~joint_valid))
    write_raster(output_dir / "change_mask.tif", change_mask.astype(np.float32), ref_dir / "blue.tif", dtype="float32", nodata=0.0)

    issue_counts = {
        "no_change_pixels": int(np.count_nonzero(change_mask == 0)),
        "change_pixels": int(np.count_nonzero(change_mask == 1)),
        "excluded_pixels": int(np.count_nonzero(change_mask == 2)),
        "change_fraction_valid": float(np.count_nonzero(change_mask == 1) / joint_valid_pixels) if joint_valid_pixels else 0.0,
        "change_fraction_total": float(np.count_nonzero(change_mask == 1) / total_pixels) if total_pixels else 0.0,
    }

    magnitude_stats = compute_summary(magnitude[joint_valid], valid_mask=None)
    band_stats = {band: compute_summary(band_differences[band][joint_valid], valid_mask=None) for band in BANDS}
    threshold_method = "median_plus_k"
    report = {
        "phase": 8,
        "status": "complete",
        "reference_date": ref_date,
        "moving_date": mov_date,
        "reference_imagery": str(ref_dir),
        "moving_imagery": str(mov_dir),
        "reference_quality_mask": str(ref_quality_path),
        "moving_quality_mask": str(mov_quality_path),
        "bands": list(BANDS),
        "input_geometry_validation": checks,
        "quality_mask_semantics": {"valid": settings.quality_mask_valid_value, "cloud": settings.quality_mask_cloud_value, "nodata": settings.quality_mask_nodata_value},
        "joint_valid_pixel_count": joint_valid_pixels,
        "joint_valid_pixel_fraction": joint_valid_fraction,
        "cloud_excluded_pixels": excluded_cloud_pixels,
        "nodata_excluded_pixels": excluded_nodata_pixels,
        "other_invalid_pixels": other_invalid_pixels,
        "per_band_difference_method": "moving_normalized - reference",
        "robust_standardization_method": "z = difference / (1.4826 * MAD) with STD fallback for degenerate cases",
        "robust_scale_values": {band: float(robust_scales[band]) for band in BANDS},
        "multi_band_change_magnitude": {
            "formula": "sqrt(sum(z_band^2))",
            "statistics": magnitude_stats,
        },
        "threshold_method": threshold_method,
        "threshold_configuration": {"k": args.threshold_k},
        "threshold_value": float(threshold),
        "change_mask_class_semantics": {"0": "NO_CHANGE", "1": "CHANGE", "2": "EXCLUDED"},
        "change_statistics": {
            **issue_counts,
            "total_pixels": total_pixels,
            "joint_valid_pixels": joint_valid_pixels,
            "excluded_pixels": int(total_pixels - joint_valid_pixels),
            "threshold_value": float(threshold),
            "threshold_method": threshold_method,
        },
        "per_band_difference_statistics": band_stats,
        "output_paths": {
            "band_differences": {band: str(output_dir / f"{band}_difference.tif") for band in BANDS},
            "change_magnitude": str(output_dir / "change_magnitude.tif"),
            "change_mask": str(output_dir / "change_mask.tif"),
            "quality_exclusion_mask": str(output_dir / "quality_exclusion_mask.tif"),
        },
        "provenance": {
            "phase": 8,
            "reference_date": ref_date,
            "moving_date": mov_date,
            "reference_source_paths": {band: str(ref_dir / f"{band}.tif") for band in BANDS},
            "moving_source_paths": {band: str(mov_dir / f"{band}.tif") for band in BANDS},
            "quality_masks": {"reference": str(ref_quality_path), "moving": str(mov_quality_path)},
            "quality_semantics": {"valid": settings.quality_mask_valid_value, "cloud": settings.quality_mask_cloud_value, "nodata": settings.quality_mask_nodata_value},
            "band_difference_method": "moving_normalized - reference",
            "robust_standardization_method": "z = difference / robust_scale",
            "combined_magnitude_formula": "sqrt(sum(z^2))",
            "threshold_method": threshold_method,
            "threshold_configuration": {"k": args.threshold_k},
            "threshold_value": float(threshold),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    validate_output_geometry([output_dir / f"{band}_difference.tif" for band in BANDS] + [output_dir / "change_magnitude.tif", output_dir / "change_mask.tif", output_dir / "quality_exclusion_mask.tif"], ref_dir / "blue.tif")

    report_path = OUTPUT_ROOT / "change_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "README.txt").write_text("Phase 8 spectral change evidence outputs for reference 2023-06-05 and moving 2024-06-26.\n", encoding="utf-8")

    print(json.dumps({
        "status": "complete",
        "reference_date": ref_date,
        "moving_date": mov_date,
        "joint_valid_pixels": joint_valid_pixels,
        "joint_valid_fraction": joint_valid_fraction,
        "threshold": float(threshold),
        "change_pixels": issue_counts["change_pixels"],
        "change_fraction_valid": issue_counts["change_fraction_valid"],
        "change_fraction_total": issue_counts["change_fraction_total"],
        "report": str(report_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
