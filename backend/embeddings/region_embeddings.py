from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_region_text(region: dict[str, Any]) -> str:
    region_id = str(region.get("region_id", "unknown"))
    pixel_count = int(region.get("pixel_count", 0))
    area_m2 = float(region.get("area_m2", pixel_count * 100.0))
    reference_date = str(region.get("reference_date", "reference-date"))
    moving_date = str(region.get("moving_date", "moving-date"))
    mean_change = float(region.get("mean_change_magnitude", 0.0))
    median_change = float(region.get("median_change_magnitude", 0.0))

    band_summary = region.get("band_summary") or {}
    dominant_parts: list[str] = []
    for band in ("nir", "swir16", "red", "green", "blue"):
        info = band_summary.get(band, {}) if isinstance(band_summary, dict) else {}
        if not isinstance(info, dict):
            continue
        mean_diff = info.get("mean_difference")
        if mean_diff is None:
            continue
        label = {
            "nir": "NIR",
            "swir16": "SWIR16",
            "red": "RED",
            "green": "GREEN",
            "blue": "BLUE",
        }.get(str(band).lower(), str(band).upper())
        if float(mean_diff) < 0:
            dominant_parts.append(f"{label} negative")
        elif float(mean_diff) > 0:
            dominant_parts.append(f"{label} positive")

    if not dominant_parts:
        dominant_parts = ["mixed spectral direction"]

    direction_text = ", ".join(dominant_parts)
    return (
        f"Region {region_id} covers approximately {area_m2:.0f} square meters "
        f"and contains {pixel_count} changed pixels between {reference_date} and {moving_date}. "
        f"Mean change magnitude is {mean_change:.2f}; median change magnitude is {median_change:.2f}. "
        f"Dominant spectral direction patterns: {direction_text}. This is a technical description of a "
        "Sentinel-2 change region and should not be interpreted as a land-cover label or verified real-world event."
    )


def generate_embedding_vectors(regions: Sequence[dict[str, Any]], *, model_name: str = DEFAULT_MODEL_NAME, batch_size: int = 32) -> tuple[np.ndarray, SentenceTransformer]:
    if not regions:
        raise ValueError("No regions were provided for embedding generation")

    texts = [build_region_text(region) for region in regions]
    model = SentenceTransformer(model_name, device="cpu")
    embeddings = model.encode(texts, batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=False)
    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim != 2:
        raise ValueError("Generated embeddings are not 2D")
    return embeddings, model


def region_id_to_qdrant_id(region_id: str) -> int:
    cleaned = str(region_id).strip()
    digits = ''.join(ch for ch in cleaned if ch.isdigit())
    if not digits:
        raise ValueError(f"Region ID '{region_id}' does not contain a numeric suffix for Qdrant indexing")
    return int(digits)


def prepare_embedding_records(regions: Sequence[dict[str, Any]], vectors: np.ndarray) -> list[dict[str, Any]]:
    if len(regions) != len(vectors):
        raise ValueError("Regions and vectors must have matching lengths")

    prepared: list[dict[str, Any]] = []
    for region, vector in zip(regions, vectors):
        payload = dict(region)
        payload["embedding_text"] = build_region_text(region)
        prepared.append(
            {
                "id": region_id_to_qdrant_id(region.get("region_id", "")),
                "vector": [float(value) for value in np.asarray(vector, dtype=np.float32).tolist()],
                "payload": payload,
            }
        )
    return prepared


def load_region_payload(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    region_path = Path(path)
    document = json.loads(region_path.read_text(encoding="utf-8"))
    if "regions" not in document:
        raise ValueError(f"Region document at {region_path} does not contain a 'regions' list")

    regions = document["regions"]
    report_path = region_path.parent / "region_report.json"
    report_payload: dict[str, Any] = {}
    if report_path.exists():
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    for region in regions:
        if "reference_date" not in region:
            region["reference_date"] = report_payload.get("reference_date", "reference-date")
        if "moving_date" not in region:
            region["moving_date"] = report_payload.get("moving_date", "moving-date")

    return regions, report_payload


def dump_embedding_artifacts(output_dir: str | Path, regions: Sequence[dict[str, Any]], vectors: np.ndarray) -> dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    vector_path = out_dir / "region_embeddings.npy"
    np.save(vector_path, np.asarray(vectors, dtype=np.float32))

    metadata_path = out_dir / "region_embeddings_metadata.json"
    metadata = {
        "region_count": len(regions),
        "vector_dimension": int(np.asarray(vectors).shape[1]),
        "embedding_model": DEFAULT_MODEL_NAME,
        "regions": [
            {
                "region_id": region.get("region_id"),
                "pixel_count": int(region.get("pixel_count", 0)),
                "area_m2": float(region.get("area_m2", 0.0)),
                "mean_change_magnitude": float(region.get("mean_change_magnitude", 0.0)),
                "text": build_region_text(region),
            }
            for region in regions
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return {"vectors": str(vector_path), "metadata": str(metadata_path)}
