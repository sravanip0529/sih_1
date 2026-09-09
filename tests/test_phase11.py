import pytest

from backend.processing.retrieval.query import QueryValidationError, encode_query, execute_query, validate_query, validate_top_k


def test_valid_query_is_accepted() -> None:
    assert validate_query("  Find regions with strong vegetation-related change  ") == "Find regions with strong vegetation-related change"


def test_empty_and_whitespace_queries_are_rejected() -> None:
    with pytest.raises(QueryValidationError):
        validate_query("")
    with pytest.raises(QueryValidationError):
        validate_query("   ")


def test_top_k_validation_and_limits() -> None:
    assert validate_top_k(5) == 5
    with pytest.raises(QueryValidationError):
        validate_top_k(0)
    with pytest.raises(QueryValidationError):
        validate_top_k(21)


def test_query_embedding_dimension_matches_expected() -> None:
    vector, model_name = encode_query("Find regions with strong NIR change", expected_dim=384)
    assert vector.shape == (384,)
    assert model_name


def test_query_embedding_rejects_incompatible_dimension() -> None:
    with pytest.raises(QueryValidationError):
        encode_query("Find regions with strong NIR change", expected_dim=123)


def test_execute_query_returns_structured_results() -> None:
    result = execute_query("Find regions with strong vegetation-related spectral change", top_k=3)

    assert result["status"] == "complete"
    assert result["top_k"] == 3
    assert len(result["results"]) <= 3
    assert all("similarity_score" in res for res in result["results"])
    assert all(res["region_id"].startswith("region_") for res in result["results"])
    assert all(res["rank"] >= 1 for res in result["results"])
