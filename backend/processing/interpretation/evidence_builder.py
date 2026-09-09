from __future__ import annotations

from typing import Any


def _band_direction_label(mean_difference: float | None) -> str:
    if mean_difference is None:
        return "mixed spectral direction"
    if mean_difference > 0:
        return "positive difference"
    if mean_difference < 0:
        return "negative difference"
    return "near-zero difference"


def build_evidence_summary(region: dict[str, Any], retrieval_result: dict[str, Any]) -> dict[str, Any]:
    band_summary = region.get("band_summary", {}) or {}
    spectral_summary = []
    for band_name in ("blue", "green", "red", "nir", "swir16"):
        band_stats = band_summary.get(band_name, {})
        mean_difference = band_stats.get("mean_difference")
        if mean_difference is not None:
            spectral_summary.append(f"{band_name.upper()}: {_band_direction_label(float(mean_difference))} ({float(mean_difference):.2f})")

    change = {
        "mean_magnitude": float(region.get("mean_change_magnitude", 0.0)),
        "median_magnitude": float(region.get("median_change_magnitude", 0.0)),
        "max_magnitude": float(region.get("max_change_magnitude", 0.0)),
    }

    evidence_summary = (
        f"Region {region.get('region_id', 'unknown')} spans {int(region.get('pixel_count', retrieval_result.get('pixel_count', 0)))} changed pixels "
        f"with area {float(region.get('area_m2', retrieval_result.get('area_m2', 0.0))):.1f} square meters between "
        f"{region.get('reference_date', retrieval_result.get('reference_date', 'unknown'))} and {region.get('moving_date', retrieval_result.get('moving_date', 'unknown'))}. "
        f"The observed change magnitude is mean {change['mean_magnitude']:.2f}, median {change['median_magnitude']:.2f}, maximum {change['max_magnitude']:.2f}."
    )

    return {
        "change_evidence": change,
        "spectral_summary": "; ".join(spectral_summary) if spectral_summary else "No spectral direction summary available from the current metadata.",
        "evidence_summary": evidence_summary,
    }
