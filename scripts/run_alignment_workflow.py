import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

from backend.processing.alignment.input_validator import validate_cross_date_rasters, validate_raster_file
from backend.processing.alignment.metrics import report_metrics
from backend.processing.alignment.overlap import calculate_overlap, class_mask
from backend.processing.alignment.provenance import write_alignment_provenance
from backend.processing.alignment.registration import estimate_translation
from backend.processing.alignment.signal_builder import build_registration_signal
from backend.processing.alignment.transform_validator import validate_transformation
from backend.processing.alignment.warp import apply_translation
from backend.settings import settings

logger = logging.getLogger("alignment_workflow")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def locate_phase_outputs() -> dict[str, Path]:
    phase4_root = settings.processed_data_directory / "sentinel"
    phase5_root = settings.processed_data_directory / "quality"
    reference_dir = None
    moving_dir = None
    for date_dir in sorted(phase4_root.iterdir()):
        if date_dir.is_dir():
            if reference_dir is None:
                reference_dir = date_dir
            else:
                moving_dir = date_dir
    if not reference_dir or not moving_dir:
        raise FileNotFoundError(f"Expected two Phase 4 dates under {phase4_root}")
    ref_date = reference_dir.name
    mov_date = moving_dir.name
    ref_quality = phase5_root / ref_date / "quality_mask.tif"
    mov_quality = phase5_root / mov_date / "quality_mask.tif"
    band_names = ["blue", "green", "red", "nir", "swir16"]
    reference = {band: reference_dir / f"{band}.tif" for band in band_names}
    moving = {band: moving_dir / f"{band}.tif" for band in band_names}
    return {
        "reference_date": ref_date,
        "moving_date": mov_date,
        "reference_dir": reference_dir,
        "moving_dir": moving_dir,
        "reference": reference,
        "moving": moving,
        "reference_quality": ref_quality,
        "moving_quality": mov_quality,
    }


def load_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(1).astype(np.uint8)


def build_valid_mask(quality: np.ndarray) -> np.ndarray:
    value = np.asarray(quality, dtype=np.uint8)
    return class_mask(value, {settings.quality_mask_valid_value})


def estimate_registration(reference_data: np.ndarray, moving_data: np.ndarray, reference_valid: np.ndarray, moving_valid: np.ndarray) -> dict[str, object]:
    ref_signal = build_registration_signal(reference_data, reference_valid)
    mov_signal = build_registration_signal(moving_data, moving_valid)
    metrics = estimate_translation(ref_signal, mov_signal, reference_valid, moving_valid, max_shift=32)
    metrics["method"] = "translation_assessment"
    metrics["signal"] = "gradient_magnitude"
    return metrics


def apply_band_warp(data: np.ndarray, dx: int, dy: int, *, nodata_value: float) -> np.ndarray:
    return apply_translation(data, dx=dx, dy=dy, nodata_value=nodata_value, categorical=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess and optionally align sentinel Phase 4 dates.")
    parser.add_argument("--assessment-only", action="store_true", help="Assess registration without writing transformed outputs.")
    args = parser.parse_args()

    outputs = locate_phase_outputs()
    reference_paths = outputs["reference"]
    moving_paths = outputs["moving"]
    for path in [*reference_paths.values(), *moving_paths.values(), outputs["reference_quality"], outputs["moving_quality"]]:
        validate_raster_file(path)

    grid_report = validate_cross_date_rasters(reference_paths["blue"], moving_paths["blue"])
    if not grid_report["grid_compatible"]:
        raise RuntimeError(f"Grid compatibility failed: {grid_report['checks']}")

    ref_quality = load_mask(outputs["reference_quality"])
    mov_quality = load_mask(outputs["moving_quality"])
    ref_valid = build_valid_mask(ref_quality)
    mov_valid = build_valid_mask(mov_quality)

    common_overlap = calculate_overlap(ref_valid, mov_valid, valid_classes={settings.quality_mask_valid_value}, cloud_classes={settings.quality_mask_cloud_value}, nodata_classes={settings.quality_mask_nodata_value})
    if common_overlap["valid_overlap_fraction"] < 0.05:
        raise RuntimeError(f"Registration preflight failed: valid overlap fraction too low ({common_overlap['valid_overlap_fraction']:.3f})")

    reference_band = rasterio.open(reference_paths["nir"]).read(1).astype(np.float32)
    moving_band = rasterio.open(moving_paths["nir"]).read(1).astype(np.float32)
    pre_metrics = estimate_registration(reference_band, moving_band, ref_valid, mov_valid)
    validation = validate_transformation({
        "dx": pre_metrics.get("dx"),
        "dy": pre_metrics.get("dy"),
        "ncc": pre_metrics.get("ncc", 0.0),
        "valid_overlap_fraction": common_overlap["valid_overlap_fraction"],
        "valid_overlap_count": common_overlap["valid_overlap_count"],
    }, max_allowed_shift_pixels=10.0, min_valid_overlap_fraction=0.05)
    if not validation["accepted"]:
        raise RuntimeError(f"Registration assessment rejected: {validation['reason']}")

    dx = int(pre_metrics["dx"])
    dy = int(pre_metrics["dy"])
    if args.assessment_only:
        report = {
            "phase": "phase_6",
            "status": "assessment_only",
            "reference_date": outputs["reference_date"],
            "moving_date": outputs["moving_date"],
            "valid_overlap": common_overlap,
            "estimated_shift_pixels": {"x": dx, "y": dy},
            "pre_alignment_metrics": report_metrics(reference_band, moving_band),
            "validation": validation,
            "method": "translation_assessment",
            "signal": "gradient_magnitude",
        }
        out_path = Path("data/aligned") / "alignment_report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"status": "assessment_only", "reference_date": outputs["reference_date"], "moving_date": outputs["moving_date"], "shift_xy": [dx, dy]}, indent=2))
        return 0

    aligned_root = Path("data/aligned")
    aligned_root.mkdir(parents=True, exist_ok=True)
    for date_key, source_paths in [(outputs["reference_date"], reference_paths), (outputs["moving_date"], moving_paths)]:
        date_dir = aligned_root / date_key
        date_dir.mkdir(parents=True, exist_ok=True)
        for band_name, path in source_paths.items():
            with rasterio.open(path) as source:
                data = source.read(1).astype(np.float32)
                transformed = data if date_key == outputs["reference_date"] else apply_band_warp(data, dx=dx, dy=dy, nodata_value=settings.output_nodata)
                out_path = date_dir / f"{band_name}.tif"
                profile = source.profile.copy()
                profile.update(driver="GTiff", dtype="float32", count=1, crs=source.crs, transform=source.transform, nodata=settings.output_nodata)
                with rasterio.open(out_path, "w", **profile) as target:
                    target.write(transformed.astype(np.float32), 1)

        quality_source = outputs["reference_quality"] if date_key == outputs["reference_date"] else outputs["moving_quality"]
        quality = load_mask(quality_source)
        quality_warped = apply_translation(quality, dx=dx, dy=dy, nodata_value=settings.quality_mask_nodata_value, categorical=True) if date_key == outputs["moving_date"] else quality.copy()
        quality_path = date_dir / "quality_mask.tif"
        with rasterio.open(reference_paths["blue"]) as template:
            profile = template.profile.copy()
            profile.update(driver="GTiff", dtype="uint8", count=1, nodata=settings.quality_output_nodata, compress="deflate")
            with rasterio.open(quality_path, "w", **profile) as target:
                target.write(quality_warped.astype("uint8"), 1)

        metadata = {
            "phase": "phase_6",
            "reference_date": outputs["reference_date"],
            "moving_date": outputs["moving_date"],
            "alignment_status": "accepted" if date_key == outputs["moving_date"] else "reference",
            "reference_grid": {"crs": str(rasterio.open(reference_paths["blue"]).crs), "width": rasterio.open(reference_paths["blue"]).width, "height": rasterio.open(reference_paths["blue"]).height, "transform": tuple(rasterio.open(reference_paths["blue"]).transform)},
            "registration_method": "translation_assessment",
            "registration_signal": "gradient_magnitude",
            "quality_mask_used": True,
            "valid_quality_classes": [settings.quality_mask_valid_value],
            "estimated_shift_pixels": {"x": dx, "y": dy},
            "estimated_shift_meters": {"x": dx * settings.processing_resolution_m, "y": dy * settings.processing_resolution_m},
            "correction_applied": date_key == outputs["moving_date"],
            "pre_alignment_metrics": report_metrics(rasterio.open(reference_paths["nir"]).read(1).astype(np.float32), rasterio.open(moving_paths["nir"]).read(1).astype(np.float32)),
            "configuration_reference": "configs/processing.yaml",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        write_alignment_provenance(date_dir / "metadata.json", metadata=metadata)

    report = {
        "phase": "phase_6",
        "reference_date": outputs["reference_date"],
        "moving_date": outputs["moving_date"],
        "input_rasters": {"reference": {band: str(path) for band, path in reference_paths.items()}, "moving": {band: str(path) for band, path in moving_paths.items()}},
        "quality_masks": {"reference": str(outputs["reference_quality"]), "moving": str(outputs["moving_quality"])},
        "valid_overlap": common_overlap,
        "estimated_shift_pixels": {"x": dx, "y": dy},
        "estimated_shift_meters": {"x": dx * settings.processing_resolution_m, "y": dy * settings.processing_resolution_m},
        "registration_method": "translation_assessment",
        "registration_signal": "gradient_magnitude",
        "pre_alignment_metrics": report_metrics(reference_band, moving_band),
        "validation": validation,
        "transformation": {"applied": True, "interpolation": {"continuous_bands": settings.continuous_resampling_method, "quality_mask": "nearest"}, "grid": "reference_grid_preserved"},
        "final_status": "accepted",
        "limitations": "This workflow estimates integer-pixel translation on a common AOI grid and does not prove sub-pixel geometric perfection or radiometric comparability.",
    }
    (aligned_root / "alignment_report.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": "accepted", "reference_date": outputs["reference_date"], "moving_date": outputs["moving_date"], "shift_xy": [dx, dy]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
