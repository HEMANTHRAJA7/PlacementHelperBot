import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.tasks.email_tasks import parse_deadline, check_and_send_reminders_async
from src.models.user import User, Reminder
from src.core.security import CredentialEncryptor

def test_parse_deadline():
    # Test None / empty
    assert parse_deadline(None) is None
    assert parse_deadline("") is None
    assert parse_deadline("   ") is None
    
    # Test non-date keywords
    assert parse_deadline("ASAP") is None
    assert parse_deadline("n/a") is None
    assert parse_deadline("none") is None
    assert parse_deadline("null") is None
    assert parse_deadline("immediate") is None
    
    # Test ISO formats
    parsed1 = parse_deadline("2026-06-12T18:00:00Z")
    assert parsed1 is not None
    assert parsed1.year == 2026
    assert parsed1.month == 6
    assert parsed1.day == 12
    assert parsed1.hour == 18
    assert parsed1.tzinfo == timezone.utc
    
    parsed2 = parse_deadline("2026-06-12 18:00:00")
    assert parsed2 is not None
    assert parsed2.tzinfo == timezone.utc
    
    parsed3 = parse_deadline("12-06-2026 18:00")
    assert parsed3 is not None
    assert parsed3.day == 12
    assert parsed3.month == 6
    assert parsed3.year == 2026
    assert parsed3.hour == 18
    
    parsed4 = parse_deadline("June 12, 2026 06:00 PM")
    assert parsed4 is not None
    assert parsed4.hour == 18
    assert parsed4.minute == 0
    
    parsed5 = parse_deadline("12 Jun 2026 18:00")
    assert parsed5 is not None
    assert parsed5.hour == 18

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_check_and_send_reminders_all_stages(mock_send_tg, db_session):
    # Setup test user
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=111111,
        gmail_address="student@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("refresh_token"),
        watch_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    now = datetime.now(timezone.utc)
    
    # 1. 24h reminder in the future (say, 23 hours in the future)
    reminder_24h = Reminder(
        user_id=user.id,
        company="Google",
        role="SWE Intern",
        category="Opportunity",
        deadline_at=now + timedelta(hours=23),
        status="ACTIVE",
        reminded_24h=False,
        reminded_6h=False,
        reminded_1h=False
    )
    
    # 2. 6h reminder in the future (say, 5 hours in the future)
    reminder_6h = Reminder(
        user_id=user.id,
        company="Microsoft",
        role="SDE",
        category="Assessment",
        deadline_at=now + timedelta(hours=5),
        status="ACTIVE",
        reminded_24h=True, # already sent 24h
        reminded_6h=False,
        reminded_1h=False
    )
    
    # 3. 1h reminder in the future (say, 45 minutes in the future)
    reminder_1h = Reminder(
        user_id=user.id,
        company="Apple",
        role="Hardware Engineer",
        category="Interview",
        deadline_at=now + timedelta(minutes=45),
        status="ACTIVE",
        reminded_24h=True,
        reminded_6h=True,
        reminded_1h=False
    )
    
    # 4. Expired reminder (deadline in the past)
    reminder_expired = Reminder(
        user_id=user.id,
        company="Netflix",
        role="Data Scientist",
        category="Opportunity",
        deadline_at=now - timedelta(minutes=10),
        status="ACTIVE",
        reminded_24h=True,
        reminded_6h=True,
        reminded_1h=True
    )
    
    db_session.add_all([reminder_24h, reminder_6h, reminder_1h, reminder_expired])
    await db_session.commit()
    
    # Run the reminder engine
    await check_and_send_reminders_async()
    
    # Refresh and assert status/fields
    await db_session.refresh(reminder_24h)
    await db_session.refresh(reminder_6h)
    await db_session.refresh(reminder_1h)
    await db_session.refresh(reminder_expired)
    
    assert reminder_24h.reminded_24h is True
    assert reminder_24h.status == "ACTIVE"
    
    assert reminder_6h.reminded_6h is True
    assert reminder_6h.status == "ACTIVE"
    
    assert reminder_1h.reminded_1h is True
    assert reminder_1h.status == "COMPLETED"
    
    assert reminder_expired.status == "EXPIRED"
    
    # 3 reminders should have been dispatched
    assert mock_send_tg.call_count == 3
    
    # Check messages contain company name and correct remaining time
    called_messages = [call[0][1] for call in mock_send_tg.call_args_list]
    
    assert any("Google" in m and "24 hours" in m for m in called_messages)
    assert any("Microsoft" in m and "6 hours" in m for m in called_messages)
    assert any("Apple" in m and "1 hour" in m for m in called_messages)

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_reminder_catch_up_policy(mock_send_tg, db_session):
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=222222,
        gmail_address="student2@vitstudent.ac.in",
        encrypted_refresh_token=encryptor.encrypt("refresh_token"),
        watch_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    now = datetime.now(timezone.utc)
    
    # Case A: Within 2 hours catch-up window
    # Deadline: 23 hours in the future
    # Trigger point was 1 hour ago (24 hours before deadline). Since 1 hour <= 2 hours, it should notify.
    reminder_within_catchup = Reminder(
        user_id=user.id,
        company="Amazon",
        category="Opportunity",
        deadline_at=now + timedelta(hours=23),
        status="ACTIVE",
        reminded_24h=False
    )
    
    # Case B: Exceeds 2 hours catch-up window
    # Deadline: 21 hours in the future
    # Trigger point was 3 hours ago. Since 3 hours > 2 hours, it should skip notification but mark reminded_24h=True.
    reminder_outside_catchup = Reminder(
        user_id=user.id,
        company="Meta",
        category="Opportunity",
        deadline_at=now + timedelta(hours=21),
        status="ACTIVE",
        reminded_24h=False
    )
    
    db_session.add_all([reminder_within_catchup, reminder_outside_catchup])
    await db_session.commit()
    
    await check_and_send_reminders_async()
    
    await db_session.refresh(reminder_within_catchup)
    await db_session.refresh(reminder_outside_catchup)
    
    # Both should be marked reminded_24h = True
    assert reminder_within_catchup.reminded_24h is True
    assert reminder_outside_catchup.reminded_24h is True
    
    # Only the Amazon reminder (within catch-up) should have triggered an alert
    assert mock_send_tg.call_count == 1
    called_messages = [call[0][1] for call in mock_send_tg.call_args_list]
    assert any("Amazon" in m for m in called_messages)
    assert not any("Meta" in m for m in called_messages)

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.fetch_gmail_message", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.parse_gmail_message")
@patch("src.tasks.email_tasks.AIGateway.classify_email", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_pipeline_creates_reminder(
    mock_send_tg, mock_classify, mock_parse, mock_fetch, mock_refresh, db_session
):
    from src.tasks.email_tasks import process_email_pipeline_async
    from src.core.ai_gateway import ClassificationResult, PlacementCategory
    from sqlalchemy import select

    # 1. Seed user in db
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=333333,
        gmail_address="student3@vitstudent.ac.in",
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
    
    # Deadline set in the future (ISO format)
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    
    mock_classify.return_value = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.OPPORTUNITY,
        company="Microsoft",
        role="SDE",
        package="45 LPA",
        deadline=future_deadline,
        application_links=["https://microsoft.com/apply"],
        confidence=0.99
    )
    
    # Run pipeline
    await process_email_pipeline_async("student3@vitstudent.ac.in", 1001, "msg_99")
    
    # Verify Reminder exists in DB
    result = await db_session.execute(select(Reminder).filter_by(user_id=user.id))
    reminders = result.scalars().all()
    
    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.company == "Microsoft"
    assert reminder.role == "SDE"
    assert reminder.category == "Opportunity"
    assert reminder.status == "ACTIVE"
    assert reminder.source_email_id == "msg_99"

    # Now let's try with non-eligible category 'Offer'
    mock_refresh.reset_mock()
    mock_fetch.reset_mock()
    mock_parse.reset_mock()
    mock_classify.reset_mock()
    
    mock_refresh.return_value = "mock_access_token"
    mock_fetch.return_value = {"id": "msg_100"}
    mock_parse.return_value = ("Placement Offer", "VIT Placement Office", "Offer details for Microsoft. 21BCE0001 Selected.")
    
    mock_classify.return_value = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.OFFER,
        company="Microsoft",
        role="SDE",
        package="45 LPA",
        deadline=future_deadline,
        application_links=["https://microsoft.com/apply"],
        confidence=0.99
    )
    
    await process_email_pipeline_async("student3@vitstudent.ac.in", 1002, "msg_100")
    
    result = await db_session.execute(select(Reminder).filter_by(source_email_id="msg_100"))
    assert len(result.scalars().all()) == 0

