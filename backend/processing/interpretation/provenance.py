from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_provenance_record(region_id: str, retrieval_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_3_source_scenes": ["data/raw/sentinel"],
        "phase_4_prepared_grid": "data/processed/sentinel",
        "phase_5_1_quality_masks": "data/masks",
        "phase_6_alignment": "data/aligned",
        "phase_7_normalization": "data/normalized",
        "phase_8_change_evidence": "data/change",
        "phase_9_region_path": "data/processed/regions/regions.json",
        "phase_9_geojson_path": "data/processed/regions/regions.geojson",
        "phase_10_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "phase_10_qdrant_collection": "phase10_region_embeddings",
        "phase_11_query": retrieval_result.get("query", "") if retrieval_result.get("query") else "",
        "phase_11_result_rank": int(retrieval_result.get("rank", 1)),
        "phase_11_result_score": float(retrieval_result.get("similarity_score", 0.0)),
        "phase_11_retrieval_report": "data/retrieval/retrieval_report.json",
        "region_id": region_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifact_paths": {
            "region_json": str(Path("data/processed/regions/regions.json")),
            "region_geojson": str(Path("data/processed/regions/regions.geojson")),
        },
    }
