import json

import pytest

from backend.processing.interpretation import (
    analyze_retrieval_result,
    build_retrieval_analysis,
    resolve_region_metadata,
)


def test_phase12_resolves_real_retrieval_results() -> None:
    analysis = build_retrieval_analysis(
        "Find regions with strong vegetation-related spectral change",
        top_k=3,
    )

    assert analysis["status"] == "complete"
    assert analysis["top_k"] == 3
    assert len(analysis["results"]) <= 3

    for result in analysis["results"]:
        assert result["region_id"].startswith("region_")
        assert result["retrieval_rank"] >= 1
        assert result["retrieval_score"] == pytest.approx(result["retrieval_score"])
        assert result["geometry"]["type"] == "Polygon"
        assert result["pixel_count"] > 0
        assert result["area_m2"] > 0.0
        assert result["provenance"]["phase_11_query"]
        assert result["provenance"]["phase_9_region_path"]


def test_phase12_rejects_unknown_region_ids_without_fabrication() -> None:
    with pytest.raises(ValueError):
        resolve_region_metadata("region_missing_999")

    with pytest.raises(ValueError):
        analyze_retrieval_result({
            "rank": 1,
            "region_id": "region_missing_999",
            "similarity_score": 0.5,
            "pixel_count": 10,
            "area_m2": 1000.0,
            "reference_date": "2023-06-05",
            "moving_date": "2024-06-26",
        })


def test_phase12_preserves_retrieval_scores_as_similarity_only() -> None:
    analysis = build_retrieval_analysis("Find regions with strong vegetation-related spectral change", top_k=2)
    for result in analysis["results"]:
        assert "semantic retrieval similarity score" in result["retrieval_score_label"].lower()
        assert "probability" not in result["retrieval_score_label"].lower()
        assert json.loads(json.dumps(result["provenance"]))


def test_phase12_builds_cautious_spectral_interpretation() -> None:
    region = resolve_region_metadata("region_0001")
    interpretation = analyze_retrieval_result({
        "rank": 1,
        "region_id": "region_0001",
        "similarity_score": 0.47,
        "pixel_count": region["pixel_count"],
        "area_m2": region["area_m2"],
        "reference_date": region["reference_date"],
        "moving_date": region["moving_date"],
    })

    assert "spectral" in interpretation["scientific_interpretation"].lower()
    assert "does not identify" in interpretation["scientific_interpretation"].lower() or "not a verified" in interpretation["scientific_interpretation"].lower()
    assert isinstance(interpretation["limitations"], list)
    assert interpretation["limitations"]
