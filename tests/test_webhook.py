import json
import base64
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import settings
from src.core.database import get_db
from src.api.endpoints.webhook import get_redis
from src.tasks.email_tasks import process_email_event
from src.models.user import DeadLetterQueue
from sqlalchemy.future import select

client = TestClient(app)

# Mock token values
VALID_OIDC_TOKEN = "valid_gcp_pubsub_token"
INVALID_OIDC_TOKEN = "invalid_pubsub_token"

@pytest.fixture(autouse=True)
def override_dependencies(db_session, mock_redis):
    """Override database and Redis dependencies for testing."""
    async def _get_db_override():
        yield db_session

    async def _get_redis_override():
        yield mock_redis

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_redis] = _get_redis_override
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def mock_verify_oauth2():
    """Mock google-auth token verification check."""
    with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
        def side_effect(token, request, audience):
            if token == VALID_OIDC_TOKEN and audience == settings.WEBHOOK_AUDIENCE:
                return {
                    "iss": "accounts.google.com",
                    "aud": settings.WEBHOOK_AUDIENCE,
                    "email": "pubsub@google.com"
                }
            raise ValueError("Invalid credentials or audience")
        mock_verify.side_effect = side_effect
        yield mock_verify

def make_pubsub_payload(email: str, history_id: int, message_id: str) -> dict:
    """Helper to construct a base64 encoded Pub/Sub push notification payload."""
    data_dict = {"emailAddress": email, "historyId": history_id}
    encoded_data = base64.b64encode(json.dumps(data_dict).encode("utf-8")).decode("utf-8")
    return {
        "message": {
            "data": encoded_data,
            "messageId": message_id,
            "publishTime": "2026-06-09T12:00:00Z"
        },
        "subscription": "projects/vit-placement/subscriptions/sentinel-push"
    }

@patch("src.api.endpoints.webhook.process_email_event.delay")
def test_webhook_post_success(mock_delay, mock_verify_oauth2):
    """Verify POST /webhook successfully validates OIDC JWT and enqueues task."""
    payload = make_pubsub_payload("student@vitstudent.ac.in", 12345, "msg_001")
    headers = {"Authorization": f"Bearer {VALID_OIDC_TOKEN}"}
    
    response = client.post("/api/v1/webhook", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
    
    # Verify task was enqueued out-of-band
    mock_delay.assert_called_once_with("student@vitstudent.ac.in", 12345, "msg_001")

def test_webhook_reject_unauthorized(mock_verify_oauth2):
    """Verify POST /webhook rejects requests without authorization or with invalid signatures."""
    payload = make_pubsub_payload("student@vitstudent.ac.in", 12345, "msg_001")
    
    # Missing authorization header
    response = client.post("/api/v1/webhook", json=payload)
    assert response.status_code == 422 # FastAPI validation fails on missing header
    
    # Invalid Bearer structure
    response = client.post("/api/v1/webhook", json=payload, headers={"Authorization": "invalid_structure"})
    assert response.status_code == 401
    assert "bearer token structure" in response.json()["detail"].lower()

    # Invalid token signature
    response = client.post("/api/v1/webhook", json=payload, headers={"Authorization": f"Bearer {INVALID_OIDC_TOKEN}"})
    assert response.status_code == 401
    assert "google oidc verification failed" in response.json()["detail"].lower()

@patch("src.api.endpoints.webhook.process_email_event.delay")
def test_idempotency_msg_id(mock_delay, mock_verify_oauth2):
    """Verify webhook drops duplicate messageId requests and caches them for 24 hours."""
    payload = make_pubsub_payload("student@vitstudent.ac.in", 12345, "msg_duplicate")
    headers = {"Authorization": f"Bearer {VALID_OIDC_TOKEN}"}
    
    # First request
    response1 = client.post("/api/v1/webhook", json=payload, headers=headers)
    assert response1.status_code == 200
    assert response1.json() == {"status": "queued"}
    assert mock_delay.call_count == 1
    
    # Duplicate request
    response2 = client.post("/api/v1/webhook", json=payload, headers=headers)
    assert response2.status_code == 200
    assert response2.json()["status"] == "ignored"
    assert response2.json()["detail"] == "duplicate messageId"
    # Ensure Celery delay was NOT called a second time
    assert mock_delay.call_count == 1

@patch("src.api.endpoints.webhook.process_email_event.delay")
def test_idempotency_history_id(mock_delay, mock_verify_oauth2):
    """Verify webhook drops duplicate historyId notifications for the same email address."""
    headers = {"Authorization": f"Bearer {VALID_OIDC_TOKEN}"}
    
    # Message 1
    payload1 = make_pubsub_payload("student@vitstudent.ac.in", 77777, "msg_first")
    response1 = client.post("/api/v1/webhook", json=payload1, headers=headers)
    assert response1.status_code == 200
    assert response1.json() == {"status": "queued"}
    assert mock_delay.call_count == 1

    # Message 2 with different message_id but same history_id for same email
    payload2 = make_pubsub_payload("student@vitstudent.ac.in", 77777, "msg_second")
    response2 = client.post("/api/v1/webhook", json=payload2, headers=headers)
    assert response2.status_code == 200
    assert response2.json()["status"] == "ignored"
    assert response2.json()["detail"] == "duplicate historyId"
    assert mock_delay.call_count == 1

class MockCeleryTask:
    """Mock context to simulate a bound Celery task and retry loops."""
    class MaxRetriesExceededError(Exception):
        pass

    def __init__(self):
        self.request = MagicMock()
        self.request.retries = 0
        self.default_retry_delay = 1

    def retry(self, exc, countdown):
        self.request.retries += 1
        if self.request.retries > 5:
            raise self.MaxRetriesExceededError("Max retries exceeded")
        raise Exception("Retry task execution")

@patch("src.tasks.email_tasks.process_email_pipeline_async")
def test_dlq_routing(mock_pipeline, db_engine):
    """Verify task errors that exceed max retries are saved to the PostgreSQL Dead-Letter Queue."""
    mock_task = MockCeleryTask()
    
    async def pipeline_side_effect(email, history_id, message_id):
        if email == "fail@vit.edu":
            raise ValueError("Simulated processing failure for email event")
        return None
    mock_pipeline.side_effect = pipeline_side_effect
    
    # 1. Verify successful processing returns correct status
    res = process_email_event.__wrapped__.__func__(mock_task, "student@vitstudent.ac.in", 12345, "msg_success")
    assert res == {"status": "success", "email": "student@vitstudent.ac.in", "history_id": 12345}
    
    # 2. Verify failed processing runs retry loop
    # First attempt raises standard retry exception
    with pytest.raises(Exception, match="Retry task execution"):
        process_email_event.__wrapped__.__func__(mock_task, "fail@vit.edu", 99999, "msg_fail_001")
    assert mock_task.request.retries == 1

    # Simulate 5 retries already executed; next failure triggers DLQ routing
    mock_task.request.retries = 5
    with pytest.raises(MockCeleryTask.MaxRetriesExceededError):
        process_email_event.__wrapped__.__func__(mock_task, "fail@vit.edu", 99999, "msg_fail_001")
        
    # Query DLQ table to check if task details were successfully saved
    async def get_dlq_entry():
        from src.core import database
        from sqlalchemy.future import select
        async with database.SessionLocal() as session:
            result = await session.execute(select(DeadLetterQueue).filter_by(message_id="msg_fail_001"))
            return result.scalar_one_or_none()

    import asyncio
    dlq_entry = asyncio.run(get_dlq_entry())
    assert dlq_entry is not None
    assert dlq_entry.payload == {"emailAddress": "fail@vit.edu", "historyId": 99999}
    assert "Simulated processing failure" in dlq_entry.error_reason



