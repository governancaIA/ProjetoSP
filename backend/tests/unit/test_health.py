"""
Tests for GET /health endpoint (EPIC 18)
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _patches(pg_ok=True, redis_ok=True, minio_ok=True):
    """Return context managers that patch the three health-check dependencies."""
    pg_session = MagicMock()
    if not pg_ok:
        pg_session.execute.side_effect = Exception("connection refused")

    redis_client = MagicMock()
    if not redis_ok:
        redis_client.ping.side_effect = Exception("Redis unavailable")

    minio_client = MagicMock()
    if not minio_ok:
        minio_client.list_buckets.side_effect = Exception("MinIO unreachable")

    return (
        patch("app.main.SessionLocal", return_value=pg_session),
        patch("app.main.redis_lib.from_url", return_value=redis_client),
        patch("app.main.Minio", return_value=minio_client),
    )


def test_health_all_healthy(client):
    """All dependencies up — returns 200 healthy"""
    p1, p2, p3 = _patches()
    with p1, p2, p3:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["checks"]["postgresql"] == "ok"
    assert body["checks"]["redis"] == "ok"
    assert body["checks"]["minio"] == "ok"


def test_health_postgres_down(client):
    """PostgreSQL down — returns 503 degraded"""
    p1, p2, p3 = _patches(pg_ok=False)
    with p1, p2, p3:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert "error" in body["checks"]["postgresql"]
    assert body["checks"]["redis"] == "ok"
    assert body["checks"]["minio"] == "ok"


def test_health_redis_down(client):
    """Redis down — returns 503 degraded"""
    p1, p2, p3 = _patches(redis_ok=False)
    with p1, p2, p3:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["postgresql"] == "ok"
    assert "error" in body["checks"]["redis"]
    assert body["checks"]["minio"] == "ok"


def test_health_minio_down(client):
    """MinIO down — returns 503 degraded"""
    p1, p2, p3 = _patches(minio_ok=False)
    with p1, p2, p3:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["postgresql"] == "ok"
    assert body["checks"]["redis"] == "ok"
    assert "error" in body["checks"]["minio"]


def test_health_multiple_down(client):
    """Multiple dependencies down — still 503 degraded (not 500)"""
    p1, p2, p3 = _patches(pg_ok=False, minio_ok=False)
    with p1, p2, p3:
        response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert "error" in body["checks"]["postgresql"]
    assert body["checks"]["redis"] == "ok"
    assert "error" in body["checks"]["minio"]
