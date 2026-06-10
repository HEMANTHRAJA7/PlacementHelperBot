import pytest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.future import select
from datetime import timezone

from src.models.user import User, AuditLog, DeadLetterQueue
from src.tasks.email_tasks import (
    renew_all_watches_task,
    renew_single_user_watch_task,
    cleanup_old_logs
)
from src.core.security import CredentialEncryptor

@pytest.fixture(autouse=True)
def override_db_dependency(db_session):
    """Automatically configure tests to use in-memory SQLite session."""
    yield

@pytest.mark.asyncio
@patch("src.tasks.email_tasks.renew_single_user_watch_task.delay")
async def test_renew_all_watches_task(mock_delay, db_session):
    """Verify that renew_all_watches_task enqueues renewals for all users."""
    encryptor = CredentialEncryptor()
    user1 = User(
        telegram_id=111,
        gmail_address="user1@vit.edu",
        encrypted_refresh_token=encryptor.encrypt("refresh1")
    )
    user2 = User(
        telegram_id=222,
        gmail_address="user2@vit.edu",
        encrypted_refresh_token=encryptor.encrypt("refresh2")
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    renew_all_watches_task()
    assert mock_delay.call_count == 2
    mock_delay.assert_any_call(user1.id)
    mock_delay.assert_any_call(user2.id)


@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.core.gmail.setup_gmail_watch", new_callable=AsyncMock)
async def test_renew_single_user_watch_success(mock_setup_watch, mock_refresh_token, db_session):
    """Verify successful Gmail watch renewal updates user columns and audit logs."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=12345,
        gmail_address="student@vit.edu",
        encrypted_refresh_token=encryptor.encrypt("my_refresh_token"),
        watch_active=False
    )
    db_session.add(user)
    await db_session.commit()

    mock_refresh_token.return_value = "new_access_token"
    mock_setup_watch.return_value = {
        "expiration": "1700000000000",
        "historyId": "999888"
    }

    res = renew_single_user_watch_task(user.id)
    assert res["status"] == "success"

    # Refresh user instance from DB
    await db_session.refresh(user)
    assert user.watch_active is True
    assert user.watch_resource_id == "999888"
    assert user.watch_expiration == 1700000000000

    # Verify audit log entry was written
    result = await db_session.execute(select(AuditLog).filter_by(user_id=user.id))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].event_type == "watch_renew"
    assert logs[0].status == "success"
    assert logs[0].resource_type == "gmail_api"


@pytest.mark.asyncio
@patch("src.tasks.email_tasks.refresh_access_token", new_callable=AsyncMock)
@patch("src.core.gmail.setup_gmail_watch", new_callable=AsyncMock)
@patch("src.tasks.email_tasks.send_telegram_alert", new_callable=AsyncMock)
async def test_renew_single_user_watch_failure_and_alert(
    mock_send_tg, mock_setup_watch, mock_refresh_token, db_session
):


    """Verify that permanent renewal failure marks watch inactive and alerts Telegram."""
    encryptor = CredentialEncryptor()
    user = User(
        telegram_id=1234567,
        gmail_address="fail_student@vit.edu",
        encrypted_refresh_token=encryptor.encrypt("bad_refresh_token"),
        watch_active=True
    )
    db_session.add(user)
    await db_session.commit()

    mock_refresh_token.side_effect = Exception("Auth failure")

    # We mock Celery's retry mechanism to trigger MaxRetriesExceeded immediately
    # We patch self.retry to raise Celery's MaxRetriesExceeded exception directly
    from celery.exceptions import MaxRetriesExceededError
    
    # We will invoke the inner async function directly with a mocked task self wrapper
    task_self = MagicMock()
    task_self.request.retries = 3
    task_self.default_retry_delay = 60
    task_self.MaxRetriesExceededError = MaxRetriesExceededError
    task_self.retry.side_effect = MaxRetriesExceededError("Max retries exceeded")

    from src.tasks.email_tasks import renew_single_user_watch_async

    with pytest.raises(MaxRetriesExceededError):
        await renew_single_user_watch_async(task_self, user.id)

    # Check that database model states are correct
    await db_session.refresh(user)
    assert user.watch_active is False

    # Check warning telegram dispatch occurred
    mock_send_tg.assert_called_once_with(
        user.telegram_id,
        "<b>⚠️ Gmail Connection Expired</b>\n\nYour secure Gmail connection has expired and we could not automatically renew it. Please re-authenticate via the bot to continue receiving placement notifications."
    )

    # Check audit log failure entries
    result = await db_session.execute(
        select(AuditLog).filter_by(user_id=user.id).order_by(AuditLog.id.desc())
    )
    logs = result.scalars().all()
    # At least two logs should be recorded (the retries/failures and the final max retries failure)
    assert len(logs) >= 2
    assert logs[0].event_type == "watch_renew"
    assert logs[0].status == "failed"
    assert logs[0].error_code == "MAX_RETRIES_EXCEEDED"


@pytest.mark.asyncio
async def test_cleanup_old_logs(db_session):
    """Verify that cleanup_old_logs removes records older than 90 days."""
    now = datetime.datetime.now(timezone.utc)
    old_time = now - datetime.timedelta(days=95)
    new_time = now - datetime.timedelta(days=85)

    # Insert mock audit logs with varying timestamps
    old_audit = AuditLog(
        event_type="test_old",
        status="success",
        created_at=old_time
    )
    new_audit = AuditLog(
        event_type="test_new",
        status="success",
        created_at=new_time
    )

    old_dlq = DeadLetterQueue(
        message_id="msg_old",
        payload={"data": "old"},
        failed_at=old_time
    )
    new_dlq = DeadLetterQueue(
        message_id="msg_new",
        payload={"data": "new"},
        failed_at=new_time
    )

    db_session.add_all([old_audit, new_audit, old_dlq, new_dlq])
    await db_session.commit()

    # Trigger cleanup
    cleanup_old_logs()

    # Verify only newer logs exist
    audits = (await db_session.execute(select(AuditLog))).scalars().all()
    assert len(audits) == 1
    assert audits[0].event_type == "test_new"

    dlqs = (await db_session.execute(select(DeadLetterQueue))).scalars().all()
    assert len(dlqs) == 1
    assert dlqs[0].message_id == "msg_new"
