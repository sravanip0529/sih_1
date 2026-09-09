import logging

from qdrant_client import QdrantClient, models

from backend.settings import settings

logger = logging.getLogger(__name__)


def create_client() -> QdrantClient:
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=settings.service_timeout_seconds,
        check_compatibility=False,
    )


def check_connection() -> tuple[str, str | None]:
    client = None
    try:
        client = create_client()
        client.get_collections()
        return "up", None
    except Exception as error:
        logger.exception("Qdrant connectivity check failed")
        return "down", str(error)
    finally:
        if client is not None:
            client.close()


def create_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )


def upsert_points(client: QdrantClient, collection_name: str, points: list[models.PointStruct]) -> None:
    client.upsert(collection_name=collection_name, points=points, wait=True)


def delete_points(client: QdrantClient, collection_name: str, point_ids: list[str]) -> None:
    client.delete(collection_name=collection_name, points_selector=models.PointIdsList(points=point_ids), wait=True)


def search_points(
    client: QdrantClient,
    collection_name: str,
    query_vector: list[float],
    limit: int = 20,
) -> list[models.ScoredPoint]:
    return client.search(collection_name=collection_name, query_vector=query_vector, limit=limit)
