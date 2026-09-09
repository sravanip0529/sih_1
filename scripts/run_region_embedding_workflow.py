from __future__ import annotations

import json
from pathlib import Path

from qdrant_client import models

from backend.database.qdrant_client import create_client, create_collection, upsert_points
from backend.embeddings.region_embeddings import (
    DEFAULT_MODEL_NAME,
    dump_embedding_artifacts,
    generate_embedding_vectors,
    load_region_payload,
    prepare_embedding_records,
)
from backend.settings import settings


OUTPUT_DIR = Path("data/embeddings")
COLLECTION_NAME = "phase10_region_embeddings"


def main() -> dict[str, object]:
    regions_path = Path("data/processed/regions/regions.json")
    regions, report = load_region_payload(regions_path)
    if not regions:
        raise ValueError("Region payload is empty")

    vectors, model = generate_embedding_vectors(regions)
    records = prepare_embedding_records(regions, vectors)
    artifacts = dump_embedding_artifacts(OUTPUT_DIR, regions, vectors)

    client = create_client()
    count = 0
    try:
        try:
            existing = client.get_collection(COLLECTION_NAME)
            vector_size = int(existing.config.params.vectors.size)
            if vector_size != int(vectors.shape[1]):
                raise ValueError(
                    f"Collection {COLLECTION_NAME} has vector size {vector_size}, expected {vectors.shape[1]}"
                )
        except Exception:
            create_collection(client, COLLECTION_NAME, vector_size=int(vectors.shape[1]))

        points = [
            models.PointStruct(
                id=int(record["id"]),
                vector=record["vector"],
                payload={
                    **record["payload"],
                    "embedding_model": getattr(model, "_model_card_name", None) or getattr(model, "_model_card_vars", {}).get("name", DEFAULT_MODEL_NAME),
                    "reference_date": record["payload"].get("reference_date", report.get("reference_date", "reference-date")),
                    "moving_date": record["payload"].get("moving_date", report.get("moving_date", "moving-date")),
                    "embedding_text": record["payload"].get("embedding_text", ""),
                },
            )
            for record in records
        ]
        upsert_points(client, COLLECTION_NAME, points)
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.points_count
    finally:
        client.close()

    report_payload = {
        "phase": "phase_10",
        "status": "complete",
        "collection_name": COLLECTION_NAME,
        "vector_dimension": int(vectors.shape[1]),
        "region_count": len(regions),
        "reference_date": report.get("reference_date", "reference-date"),
        "moving_date": report.get("moving_date", "moving-date"),
        "vector_store": settings.qdrant_url,
        "embedding_model": getattr(model, "_model_card_name", None) or getattr(model, "_model_card_vars", {}).get("name", DEFAULT_MODEL_NAME),
        "indexed_points": int(count),
        "artifacts": artifacts,
    }
    report_path = OUTPUT_DIR / "phase10_report.json"
    report_path.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")
    return report_payload


if __name__ == "__main__":
    main()
