import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from prometheus_client import CONTENT_TYPE_LATEST
import datetime
from datetime import timezone

from src.main import app
from src.core.database import get_db
from src.models.user import User, AuditLog

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_db_dependency(db_session):
    """Automatically override get_db dependency for tests to use the in-memory SQLite session."""
    async def _get_db_override():
        yield db_session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()

def test_metrics_endpoint(db_session):
    """Verify that GET /metrics endpoint returns prometheus format text."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "active_watches_total" in response.text
    assert "celery_pending_tasks_total" in response.text


@pytest.mark.asyncio
@patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
@patch("src.api.endpoints.monitoring.check_celery_workers")
async def test_health_endpoint_all_healthy(mock_check_celery, mock_redis_ping, db_session):
    """Verify health endpoint returns 200 healthy when all systems are functional."""
    # 1. Setup Postgres (add an active user and a successful renewal log within 24h)
    user = User(
        telegram_id=9876,
        gmail_address="user@vit.edu",
        encrypted_refresh_token="enc"
    )
    db_session.add(user)
    await db_session.commit()

    log = AuditLog(
        user_id=user.id,
        event_type="watch_renew",
        status="success",
        created_at=datetime.datetime.now(timezone.utc)
    )
    db_session.add(log)
    await db_session.commit()

    # 2. Mock Redis ping
    mock_redis_ping.return_value = True

    # 3. Mock Celery worker active
    mock_check_celery.return_value = True

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["postgresql"] == "healthy"
    assert data["redis"] == "healthy"
    assert data["celery"] == "healthy"
    assert data["watch_renewal"] == "healthy"


@pytest.mark.asyncio
@patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
@patch("src.api.endpoints.monitoring.check_celery_workers")
async def test_health_endpoint_pg_down(mock_check_celery, mock_redis_ping, db_session):
    """Verify health endpoint returns 503 unhealthy when Postgres fails."""
    # Mock db execute to fail
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Connection Lost")

    # Override get_db for this test specifically
    async def _get_db_fail():
        yield mock_db
    app.dependency_overrides[get_db] = _get_db_fail

    mock_redis_ping.return_value = True
    mock_check_celery.return_value = True

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["postgresql"] == "unhealthy"
    assert data["redis"] == "healthy"
    assert data["celery"] == "healthy"


@pytest.mark.asyncio
@patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
@patch("src.api.endpoints.monitoring.check_celery_workers")
async def test_health_endpoint_redis_down(mock_check_celery, mock_redis_ping, db_session):
    """Verify health endpoint returns 503 unhealthy when Redis is offline."""
    mock_redis_ping.side_effect = Exception("Redis Connection Refused")
    mock_check_celery.return_value = True

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["redis"] == "unhealthy"
    assert data["postgresql"] == "healthy"


@pytest.mark.asyncio
@patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
@patch("src.api.endpoints.monitoring.check_celery_workers")
async def test_health_endpoint_celery_down(mock_check_celery, mock_redis_ping, db_session):
    """Verify health endpoint returns 503 unhealthy when no active Celery workers exist."""
    mock_redis_ping.return_value = True
    mock_check_celery.return_value = False

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["celery"] == "unhealthy"


@pytest.mark.asyncio
@patch("redis.asyncio.Redis.ping", new_callable=AsyncMock)
@patch("src.api.endpoints.monitoring.check_celery_workers")
async def test_health_endpoint_watch_renewal_stale(mock_check_celery, mock_redis_ping, db_session):
    """Verify health endpoint returns 503 unhealthy when watch renewal log is stale."""
    # Setup active user in DB
    user = User(
        telegram_id=9876,
        gmail_address="user@vit.edu",
        encrypted_refresh_token="enc"
    )
    db_session.add(user)
    await db_session.commit()

    # Log is old (>24h)
    log = AuditLog(
        user_id=user.id,
        event_type="watch_renew",
        status="success",
        created_at=datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=25)
    )
    db_session.add(log)
    await db_session.commit()

    mock_redis_ping.return_value = True
    mock_check_celery.return_value = True

    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["watch_renewal"] == "unhealthy"
