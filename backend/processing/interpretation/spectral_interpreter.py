from __future__ import annotations

from typing import Any


def build_scientific_interpretation(region: dict[str, Any], retrieval_score: float) -> dict[str, Any]:
    band_summary = region.get("band_summary", {}) or {}
    positive_bands = []
    negative_bands = []

    for band_name in ("blue", "green", "red", "nir", "swir16"):
        stats = band_summary.get(band_name, {})
        mean_difference = stats.get("mean_difference")
        if mean_difference is None:
            continue
        if mean_difference > 0:
            positive_bands.append(band_name.upper())
        elif mean_difference < 0:
            negative_bands.append(band_name.upper())

    if positive_bands or negative_bands:
        direction_text = (
            f"This region shows a spectral pattern with {', '.join(positive_bands[:3])} positive difference and {', '.join(negative_bands[:3])} negative difference. "
            if positive_bands and negative_bands
            else f"This region shows a spectral pattern with {' '.join(positive_bands[:3]) or ' '.join(negative_bands[:3])} differences."
        )
    else:
        direction_text = "This region shows a spectral change pattern without a clear dominant band direction in the available metadata."

    interpretation = (
        f"The retrieved region is associated with a semantic retrieval similarity score of {retrieval_score:.6f}. "
        f"{direction_text} This is a cautious spectral interpretation of the detected difference, not a verified real-world land-cover event or an external validation result."
    )

    limitations = [
        "Semantic retrieval is not ground-truth classification.",
        "Spectral change is not automatically a verified real-world event.",
        "Similarity scores are not probabilities.",
        "No external validation dataset was introduced in this phase.",
    ]

    return {
        "interpretation": interpretation,
        "limitations": limitations,
    }
