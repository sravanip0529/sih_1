import logging

from fastapi import FastAPI

from backend.database.postgres_client import check_connection as check_postgres_connection
from backend.database.qdrant_client import check_connection as check_qdrant_connection
from backend.settings import settings


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Satellite Semantic Retrieval and Multi-Temporal Change Analysis System",
    version="0.1.0",
)


def check_postgres() -> tuple[str, str | None]:
    return check_postgres_connection()


def check_qdrant() -> tuple[str, str | None]:
    return check_qdrant_connection()


@app.on_event("startup")
def log_startup() -> None:
    logger.info("Starting API in %s environment", settings.app_env)
    postgres_status, _ = check_postgres()
    qdrant_status, _ = check_qdrant()
    logger.info("Database connection: %s", postgres_status)
    logger.info("Qdrant connection: %s", qdrant_status)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "qdrant": "not_checked",
        "postgres": "not_checked",
        "models_loaded": False,
    }


@app.get("/health/detailed")
def detailed_health() -> dict[str, object]:
    postgres_status, postgres_error = check_postgres()
    qdrant_status, qdrant_error = check_qdrant()
    overall_status = "ok" if postgres_status == "up" and qdrant_status == "up" else "degraded"
    return {
        "status": overall_status,
        "application_version": app.version,
        "environment": settings.app_env,
        "postgresql": {"status": postgres_status, "error": postgres_error},
        "qdrant": {"status": qdrant_status, "error": qdrant_error},
        "models_loaded": False,
    }
