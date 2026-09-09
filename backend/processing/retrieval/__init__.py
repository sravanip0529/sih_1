"""Semantic retrieval utilities for Phase 11."""

from .query import (
    QueryValidationError,
    build_retrieval_result,
    encode_query,
    validate_query,
    validate_top_k,
)

__all__ = [
    "QueryValidationError",
    "build_retrieval_result",
    "encode_query",
    "validate_query",
    "validate_top_k",
]
