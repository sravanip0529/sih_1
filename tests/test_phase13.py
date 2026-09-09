import pytest
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_retrieval_api_accepts_valid_query() -> None:
    response = client.post(
        "/api/retrieval/search",
        json={"query": "Find regions with strong vegetation-related spectral change", "top_k": 3, "include_interpretation": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Find regions with strong vegetation-related spectral change"
    assert payload["top_k"] == 3
    assert payload["result_count"] <= 3
    assert len(payload["results"]) == payload["result_count"]
    assert payload["results"][0]["region_id"].startswith("region_")
    assert payload["scientific_limitations"]


def test_retrieval_api_rejects_empty_query() -> None:
    response = client.post(
        "/api/retrieval/search",
        json={"query": "   ", "top_k": 2, "include_interpretation": True},
    )
    assert response.status_code == 422


def test_retrieval_api_rejects_invalid_top_k() -> None:
    response = client.post(
        "/api/retrieval/search",
        json={"query": "Find vegetation-related change", "top_k": 0, "include_interpretation": True},
    )
    assert response.status_code == 422


def test_retrieval_api_can_disable_interpretation() -> None:
    response = client.post(
        "/api/retrieval/search",
        json={"query": "Find vegetation-related change", "top_k": 2, "include_interpretation": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["include_interpretation"] is False
    assert payload["results"][0]["region_id"].startswith("region_")
    assert "scientific_limitations" in payload
