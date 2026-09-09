"""Embeddings for region-level semantic descriptors."""

from .region_embeddings import (
    build_region_text,
    generate_embedding_vectors,
    prepare_embedding_records,
)

__all__ = [
    "build_region_text",
    "generate_embedding_vectors",
    "prepare_embedding_records",
]
