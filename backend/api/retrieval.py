from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.processing.interpretation import build_retrieval_analysis
from backend.processing.retrieval.query import QueryValidationError, execute_query, validate_query, validate_top_k

router = APIRouter(prefix="/api")


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language semantic query")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of retrieved regions")
    include_interpretation: bool = Field(default=True, description="Whether to include Phase 12 evidence interpretation")

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError("Query must not be empty")
        return normalized


class RetrievalResult(BaseModel):
    rank: int
    region_id: str
    retrieval_score: float
    reference_date: str | None = None
    moving_date: str | None = None
    pixel_count: int | None = None
    area_m2: float | None = None
    mean_change_magnitude: float | None = None
    median_change_magnitude: float | None = None
    max_change_magnitude: float | None = None
    semantic_description: str | None = None
    spectral_summary: str | dict[str, Any] | None = None
    evidence_summary: str | None = None
    scientific_interpretation: str | None = None
    limitations: list[str] = []
    provenance: dict[str, Any] = {}


class RetrievalResponse(BaseModel):
    status: str
    query: str
    top_k: int
    result_count: int
    include_interpretation: bool
    collection_name: str
    embedding_model: str
    reference_date: str | None = None
    moving_date: str | None = None
    results: list[RetrievalResult]
    scientific_limitations: list[str]
    provenance: dict[str, Any]


@router.post("/retrieval/search", response_model=RetrievalResponse)
def search_retrieval(request: RetrievalRequest) -> RetrievalResponse:
    try:
        cleaned_query = validate_query(request.query)
        cleaned_top_k = validate_top_k(request.top_k)
    except QueryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    try:
        if request.include_interpretation:
            analysis = build_retrieval_analysis(cleaned_query, top_k=cleaned_top_k)
            results = []
            for item in analysis["results"]:
                results.append(
                    RetrievalResult(
                        rank=item["retrieval_rank"],
                        region_id=item["region_id"],
                        retrieval_score=float(item["retrieval_score"]),
                        reference_date=item.get("reference_date"),
                        moving_date=item.get("moving_date"),
                        pixel_count=int(item.get("pixel_count", 0)),
                        area_m2=float(item.get("area_m2", 0.0)),
                        mean_change_magnitude=item.get("mean_change_magnitude"),
                        median_change_magnitude=item.get("median_change_magnitude"),
                        max_change_magnitude=item.get("max_change_magnitude"),
                        semantic_description=item.get("evidence_summary"),
                        spectral_summary=item.get("spectral_summary"),
                        evidence_summary=item.get("evidence_summary"),
                        scientific_interpretation=item.get("scientific_interpretation"),
                        limitations=item.get("limitations", []),
                        provenance=item.get("provenance", {}),
                    )
                )
            scientific_limitations = [
                "Semantic retrieval is not ground-truth classification.",
                "Spectral change is not automatically a verified real-world event.",
                "Similarity scores are not probabilities.",
                "No external validation dataset was introduced in this phase.",
            ]
            provenance = {
                "phase_11_retrieval": "data/retrieval/retrieval_report.json",
                "phase_12_analysis": "data/retrieval_analysis/retrieval_analysis.json",
                "phase_9_regions": "data/processed/regions/regions.json",
                "phase_10_collection": "phase10_region_embeddings",
            }
        else:
            retrieval = execute_query(cleaned_query, top_k=cleaned_top_k)
            results = []
            for item in retrieval.get("results", []):
                results.append(
                    RetrievalResult(
                        rank=item["rank"],
                        region_id=item["region_id"],
                        retrieval_score=float(item["similarity_score"]),
                        reference_date=item.get("reference_date"),
                        moving_date=item.get("moving_date"),
                        pixel_count=int(item.get("pixel_count", 0)),
                        area_m2=float(item.get("area_m2", 0.0)),
                        mean_change_magnitude=item.get("spectral_attributes", {}).get("mean_change_magnitude"),
                        median_change_magnitude=item.get("spectral_attributes", {}).get("median_change_magnitude"),
                        max_change_magnitude=item.get("spectral_attributes", {}).get("max_change_magnitude"),
                        semantic_description=item.get("semantic_description"),
                        spectral_summary=item.get("change_attributes"),
                        evidence_summary=item.get("semantic_description"),
                        scientific_interpretation=None,
                        limitations=[],
                        provenance={
                            "phase_11_retrieval": "data/retrieval/retrieval_report.json",
                            "phase_9_regions": "data/processed/regions/regions.json",
                            "phase_10_collection": "phase10_region_embeddings",
                        },
                    )
                )
            scientific_limitations = [
                "Semantic retrieval is not ground-truth classification.",
                "Spectral change is not automatically a verified real-world event.",
                "Similarity scores are not probabilities.",
            ]
            provenance = {
                "phase_11_retrieval": "data/retrieval/retrieval_report.json",
                "phase_9_regions": "data/processed/regions/regions.json",
                "phase_10_collection": "phase10_region_embeddings",
            }

        return RetrievalResponse(
            status="complete",
            query=cleaned_query,
            top_k=cleaned_top_k,
            result_count=len(results),
            include_interpretation=request.include_interpretation,
            collection_name="phase10_region_embeddings",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            reference_date="2023-06-05",
            moving_date="2024-06-26",
            results=results,
            scientific_limitations=scientific_limitations,
            provenance=provenance,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Retrieval failed: {exc}") from exc


@router.get("/health")
def retrieval_health() -> dict[str, str]:
    return {"status": "ok", "service": "retrieval"}
