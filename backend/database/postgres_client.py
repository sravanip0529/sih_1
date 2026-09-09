import logging

import psycopg

from backend.settings import settings

logger = logging.getLogger(__name__)


def check_connection() -> tuple[str, str | None]:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as connection:
            connection.execute("SELECT 1")
        return "up", None
    except Exception as error:
        logger.exception("PostgreSQL connectivity check failed")
        return "down", str(error)


def check_postgis() -> tuple[str, str | None]:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as connection:
            result = connection.execute("SELECT PostGIS_Version()").fetchone()
        return "up" if result and result[0] else "down", None
    except Exception as error:
        logger.exception("PostGIS connectivity check failed")
        return "down", str(error)
