import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.telegram_dispatcher import format_telegram_message, send_telegram_alert
from src.tasks.email_tasks import process_email_event
from src.models.user import User
from src.core.security import CredentialEncryptor
from src.core.ai_gateway import ClassificationResult, PlacementCategory
from sqlalchemy import select

@pytest.mark.parametrize(
    "category,expected_emoji",
    [
        ("Offer", "🔴"),
        ("Shortlist", "🟡"),
        ("Interview", "🔵"),
        ("Assessment", "🟢"),
        ("Opportunity", "⚪"),
        ("other", "⚪"),
    ]
)
def test_telegram_message_formatting(category, expected_emoji):
    """Verify HTML message formatting and proper emoji mapping for each category."""
    text = format_telegram_message(
        company="Microsoft",
        category=category,
        role="SDE",
        package="50 LPA",
        deadline="June 20",
        application_links=["https://microsoft.com/apply"]
    )
    
    assert f"Placement Update: Microsoft" in text
    assert expected_emoji in text
    assert "<b>Category:</b>" in text
    assert "<b>Role:</b> SDE" in text
    assert "<b>Package:</b> 50 LPA" in text
    assert "<b>Deadline:</b> June 20" in text
    assert "href=\"https://microsoft.com/apply\"" in text

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_send_telegram_alert_success(mock_post):
    """Verify that send_telegram_alert delivers HTTP requests with correct payload and silent flag."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    success = await send_telegram_alert(
        telegram_id=987654321,
        text="Hello Student!",
        bot_token="test_bot_token"
    )
    
    assert success is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.telegram.org/bottest_bot_token/sendMessage"
    payload = kwargs["json"]
    assert payload["chat_id"] == 987654321
    assert payload["text"] == "Hello Student!"
    assert payload["parse_mode"] == "HTML"
    assert payload["disable_notification"] is True  # Verify silent delivery

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.AIGateway.classify_email", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_integration_success(
    mock_send_tg, mock_classify, mock_parse, mock_fetch, mock_refresh, db_session
):
    """Verify end-to-end processing pipeline triggers TG alerts upon successful AI classification."""
    # 1. Seed user in db
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=123456,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("mock_refresh_token"),
        encrypted_register_number=encryptor.encrypt("21BCE0001"),
        encrypted_neopat_id=encryptor.encrypt("NP001")
    )
    db_session.add(user)
    await db_session.commit()
    
    # 2. Setup mocks
    mock_refresh.return_value = "mock_access_token"
    mock_fetch.return_value = {"id": "msg_99"}
    mock_parse.return_value = ("Placement Drive", "VIT Placement Office", "Details for Microsoft. 21BCE0001 Selected.")
    
    mock_classify.return_value = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.OFFER,
        company="Microsoft",
        role="SDE",
        package="45 LPA",
        deadline="ASAP",
        application_links=["https://microsoft.com/apply"],
        confidence=0.99
    )
    
    # Run the worker task
    process_email_event(email="student@vitstudent.ac.in", history_id=1001, message_id="msg_99")
    
    # Verify TG alert was sent with correct structured HTML content
    mock_send_tg.assert_called_once()
    tg_id, text = mock_send_tg.call_args[0]
    assert tg_id == 123456
    assert "🔴 Placement Update: Microsoft" in text
    assert "<b>Role:</b> SDE" in text
    assert "<b>Package:</b> 45 LPA" in text

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.AIGateway.classify_email", side_effect=Exception("AI Failure"))
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_integration_ai_failure_fallback_matched(
    mock_send_tg, mock_classify, mock_parse, mock_fetch, mock_refresh, db_session
):
    """Verify that when AI fails, the pipeline falls back to pre-checks and dispatches a high-priority match warning."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=123456,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("mock_refresh_token"),
        encrypted_register_number=encryptor.encrypt("21BCE0001"),
        encrypted_neopat_id=encryptor.encrypt("NP001")
    )
    db_session.add(user)
    await db_session.commit()
    
    mock_refresh.return_value = "mock_access_token"
    mock_fetch.return_value = {"id": "msg_99"}
    # Plaintext body contains student's register number (deterministic match)
    mock_parse.return_value = ("Shortlist PDF", "VIT Office", "Shortlisted students: 21BCE0001 details.")
    
    # Run the worker task
    process_email_event(email="student@vitstudent.ac.in", history_id=1001, message_id="msg_99")
    
    # Verify fallback TG alert was sent
    mock_send_tg.assert_called_once()
    tg_id, text = mock_send_tg.call_args[0]
    assert tg_id == 123456
    assert "🔴 High Priority Match (Fallback)" in text
    assert "verified locally" in text

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.AIGateway.classify_email", side_effect=Exception("AI Failure"))
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_integration_ai_failure_fallback_unmatched(
    mock_send_tg, mock_classify, mock_parse, mock_fetch, mock_refresh, db_session
):
    """Verify that when AI fails and pre-check is negative, the pipeline sends a generic placement warning notification."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=123456,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("mock_refresh_token"),
        encrypted_register_number=encryptor.encrypt("21BCE0001"),
        encrypted_neopat_id=encryptor.encrypt("NP001")
    )
    db_session.add(user)
    await db_session.commit()
    
    mock_refresh.return_value = "mock_access_token"
    mock_fetch.return_value = {"id": "msg_99"}
    # Plaintext body does NOT contain student's identifiers
    mock_parse.return_value = ("General Info", "VIT Office", "Dear all, placement registration details.")
    
    # Run the worker task
    process_email_event(email="student@vitstudent.ac.in", history_id=1001, message_id="msg_99")
    
    # Verify generic fallback TG alert was sent
    mock_send_tg.assert_called_once()
    tg_id, text = mock_send_tg.call_args[0]
    assert tg_id == 123456
    assert "⚠️ Placement Update" in text
    assert "Placement-related email detected" in text
