from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.database.qdrant_client import create_client, search_points
from backend.embeddings.region_embeddings import DEFAULT_MODEL_NAME, load_region_payload

MAX_TOP_K = 20


class QueryValidationError(ValueError):
    """Raised when a natural-language query is invalid."""


def validate_query(query: str) -> str:
    if query is None:
        raise QueryValidationError("Query must not be None")
    normalized = str(query).strip()
    if not normalized:
        raise QueryValidationError("Query must not be empty")
    if re.sub(r"\s+", " ", normalized) == "":
        raise QueryValidationError("Query must contain meaningful text")
    return normalized


def validate_top_k(top_k: int, *, max_top_k: int = MAX_TOP_K) -> int:
    try:
        value = int(top_k)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise QueryValidationError("Top-K must be an integer") from exc
    if value <= 0:
        raise QueryValidationError("Top-K must be positive")
    if value > max_top_k:
        raise QueryValidationError(f"Top-K exceeds configured maximum of {max_top_k}")
    return value


def encode_query(query: str, *, model_name: str = DEFAULT_MODEL_NAME, expected_dim: int | None = None) -> tuple[np.ndarray, str]:
    text = validate_query(query)
    model = SentenceTransformer(model_name, device="cpu")
    vector = model.encode([text], convert_to_numpy=True, normalize_embeddings=False)[0].astype(np.float32)
    if not np.isfinite(vector).all():
        raise QueryValidationError("Generated query embedding contains non-finite values")
    if expected_dim is not None and vector.shape[0] != expected_dim:
        raise QueryValidationError(
            f"Expected query embedding dimension {expected_dim}, got {vector.shape[0]}"
        )
    model_label = getattr(model, "_model_card_name", None) or getattr(model, "_model_card_vars", {}).get("name", model_name)
    return vector, str(model_label)


def _score_to_float(score: Any) -> float:
    try:
        score_value = float(score)
    except (TypeError, ValueError):
        return float("nan")
    if math.isnan(score_value) or math.isinf(score_value):
        return float("nan")
    return score_value


def _resolve_region_metadata(region_id: str) -> dict[str, Any]:
    region_path = Path("data/processed/regions/regions.json")
    regions, _ = load_region_payload(region_path)
    by_id = {str(region.get("region_id")): region for region in regions}
    if region_id not in by_id:
        raise KeyError(f"Region {region_id} not found in Phase 9 metadata")
    return by_id[region_id]


def build_retrieval_result(query: str, *, top_k: int, results: Sequence[Any], model_name: str, collection_name: str, reference_date: str, moving_date: str) -> dict[str, Any]:
    structured = {
        "status": "complete",
        "query": validate_query(query),
        "top_k": validate_top_k(top_k),
        "embedding_model": model_name,
        "collection_name": collection_name,
        "reference_date": reference_date,
        "moving_date": moving_date,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [],
    }

    for index, result in enumerate(results, start=1):
        payload = getattr(result, "payload", None)
        if payload is None and isinstance(result, dict):
            payload = result.get("payload", {})
        if payload is None:
            raise ValueError("Qdrant result payload is missing")

        region_id = str(payload.get("region_id"))
        metadata = _resolve_region_metadata(region_id)
        score = _score_to_float(getattr(result, "score", None) if not isinstance(result, dict) else result.get("score"))
        if not math.isfinite(score):
            raise ValueError(f"Non-finite similarity score for region {region_id}")
        structured["results"].append(
            {
                "rank": index,
                "region_id": region_id,
                "vector_point_id": int(getattr(result, "id", None) if not isinstance(result, dict) else result.get("id", 0)),
                "similarity_score": score,
                "reference_date": str(metadata.get("reference_date", reference_date)),
                "moving_date": str(metadata.get("moving_date", moving_date)),
                "pixel_count": int(metadata.get("pixel_count", payload.get("pixel_count", 0))),
                "area_m2": float(metadata.get("area_m2", payload.get("area_m2", 0.0))),
                "semantic_description": str(metadata.get("semantic_description", payload.get("semantic_description", ""))),
                "change_attributes": metadata.get("band_summary", payload.get("band_summary", {})),
                "spectral_attributes": {
                    "mean_change_magnitude": metadata.get("mean_change_magnitude", payload.get("mean_change_magnitude", 0.0)),
                    "median_change_magnitude": metadata.get("median_change_magnitude", payload.get("median_change_magnitude", 0.0)),
                    "max_change_magnitude": metadata.get("max_change_magnitude", payload.get("max_change_magnitude", 0.0)),
                },
                "geometry_available": "bbox" in metadata or "centroid" in metadata,
            }
        )

    return structured


def execute_query(query: str, *, top_k: int = 5, collection_name: str = "phase10_region_embeddings", model_name: str = DEFAULT_MODEL_NAME) -> dict[str, Any]:
    validated_query = validate_query(query)
    validated_top_k = validate_top_k(top_k)
    with Path("data/processed/regions/regions.json").open("r", encoding="utf-8") as handle:
        metadata = __import__("json").load(handle)
    reference_date = metadata["regions"][0].get("reference_date", "2023-06-05") if metadata.get("regions") else "2023-06-05"
    moving_date = metadata["regions"][0].get("moving_date", "2024-06-26") if metadata.get("regions") else "2024-06-26"

    query_vector, model_id = encode_query(validated_query, model_name=model_name, expected_dim=384)
    client = create_client()
    try:
        response = search_points(client, collection_name, query_vector.tolist(), limit=validated_top_k)
        points = response.points
    finally:
        client.close()

    if not points:
        return {
            "status": "complete",
            "query": validated_query,
            "top_k": validated_top_k,
            "embedding_model": model_id,
            "collection_name": collection_name,
            "reference_date": reference_date,
            "moving_date": moving_date,
            "results": [],
        }

    structured = build_retrieval_result(
        validated_query,
        top_k=validated_top_k,
        results=list(points),
        model_name=model_id,
        collection_name=collection_name,
        reference_date=reference_date,
        moving_date=moving_date,
    )
    return structured
