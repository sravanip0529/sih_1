from fastapi.testclient import TestClient

from backend.main import app
from backend.settings import Settings


def test_settings_have_cpu_safe_defaults() -> None:
    configured = Settings()

    assert configured.processing_resolution_m == 10
    assert configured.cloud_coverage_threshold == 20.0
    assert configured.stac_collection == "sentinel-2-l2a"
    assert configured.model_directory.name == "models"


def test_settings_read_environment(monkeypatch) -> None:
    monkeypatch.setenv("STAC_API_URL", "https://example.test/stac")
    monkeypatch.setenv("CLOUD_PROBABILITY_THRESHOLD", "0.25")

    configured = Settings()

    assert configured.stac_api_url == "https://example.test/stac"
    assert configured.cloud_probability_threshold == 0.25


def test_health_response_shape(monkeypatch) -> None:
    monkeypatch.setattr("backend.main.check_postgres", lambda: ("up", None))
    monkeypatch.setattr("backend.main.check_qdrant", lambda: ("up", None))

    response = TestClient(app).get("/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["postgresql"]["status"] == "up"
    assert body["qdrant"]["status"] == "up"


def test_qdrant_client_factory_uses_configured_url(monkeypatch) -> None:
    from backend.database import qdrant_client

    monkeypatch.setattr(qdrant_client.settings, "qdrant_url", "http://qdrant:6333")
    client = qdrant_client.create_client()

    try:
        assert client is not None
    finally:
        client.close()
