from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.processing.interpretation.evidence_builder import build_evidence_summary
from backend.processing.interpretation.provenance import build_provenance_record
from backend.processing.interpretation.spectral_interpreter import build_scientific_interpretation
from backend.processing.retrieval.query import execute_query


def resolve_region_metadata(region_id: str) -> dict[str, Any]:
    region_path = Path("data/processed/regions/regions.json")
    if not region_path.exists():
        raise ValueError(f"Phase 9 regions metadata not found at {region_path}")

    try:
        with region_path.open("r", encoding="utf-8") as handle:
            regions = json.load(handle)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Phase 9 region metadata is not valid JSON: {region_path}") from exc

    if isinstance(regions, dict):
        region_list = regions.get("regions", [])
    else:
        region_list = regions

    for region in region_list:
        if str(region.get("region_id")) == str(region_id):
            return region

    raise ValueError(f"Unknown region_id '{region_id}' in Phase 9 metadata")


def analyze_retrieval_result(retrieval_result: dict[str, Any], *, query: str | None = None) -> dict[str, Any]:
    region_id = str(retrieval_result.get("region_id", "")).strip()
    if not region_id:
        raise ValueError("retrieval_result.region_id is required")

    region = resolve_region_metadata(region_id)
    rank = int(retrieval_result.get("rank", 1))
    score = float(retrieval_result.get("similarity_score", 0.0))
    if score != score or score in (float("inf"), float("-inf")):
        raise ValueError(f"Retrieval score for region '{region_id}' must be finite")

    geometry_path = Path("data/processed/regions/regions.geojson")
    geometry = {}
    if geometry_path.exists():
        try:
            with geometry_path.open("r", encoding="utf-8") as handle:
                feature_collection = json.load(handle)
            for feature in feature_collection.get("features", []):
                if str(feature.get("properties", {}).get("region_id")) == region_id:
                    geometry = feature.get("geometry", {})
                    break
        except json.JSONDecodeError:  # pragma: no cover - defensive
            geometry = {}

    evidence = build_evidence_summary(region, retrieval_result)
    interpretation = build_scientific_interpretation(region, score)

    record = {
        "region_id": region_id,
        "retrieval_rank": rank,
        "retrieval_score": score,
        "retrieval_score_label": "semantic retrieval similarity score",
        "query_timestamp": datetime.now(timezone.utc).isoformat(),
        "reference_date": str(region.get("reference_date", retrieval_result.get("reference_date", ""))),
        "moving_date": str(region.get("moving_date", retrieval_result.get("moving_date", ""))),
        "pixel_count": int(region.get("pixel_count", retrieval_result.get("pixel_count", 0))),
        "area_m2": float(region.get("area_m2", retrieval_result.get("area_m2", 0.0))),
        "geometry": geometry,
        "mean_change_magnitude": float(region.get("mean_change_magnitude", evidence["change_evidence"].get("mean_magnitude", 0.0))),
        "median_change_magnitude": float(region.get("median_change_magnitude", evidence["change_evidence"].get("median_magnitude", 0.0))),
        "max_change_magnitude": float(region.get("max_change_magnitude", evidence["change_evidence"].get("max_magnitude", 0.0))),
        "spectral_summary": evidence["spectral_summary"],
        "evidence_summary": evidence["evidence_summary"],
        "scientific_interpretation": interpretation["interpretation"],
        "limitations": interpretation["limitations"],
        "provenance": build_provenance_record(region_id, {**retrieval_result, "query": query or retrieval_result.get("query", "")}),
    }
    return record


def build_retrieval_analysis(query: str, *, top_k: int = 5, collection_name: str = "phase10_region_embeddings") -> dict[str, Any]:
    retrieval = execute_query(query, top_k=top_k, collection_name=collection_name)
    if retrieval.get("status") != "complete":
        raise ValueError(f"Phase 11 retrieval failed: {retrieval}")

    analysis = {
        "status": "complete",
        "query": retrieval.get("query", query),
        "query_timestamp": datetime.now(timezone.utc).isoformat(),
        "reference_date": retrieval.get("reference_date", ""),
        "moving_date": retrieval.get("moving_date", ""),
        "top_k": int(retrieval.get("top_k", top_k)),
        "collection_name": collection_name,
        "embedding_model": retrieval.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        "results": [],
    }

    for result in retrieval.get("results", []):
        analysis["results"].append(analyze_retrieval_result(result, query=analysis["query"]))

    return analysis
