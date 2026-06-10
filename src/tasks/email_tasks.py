import asyncio
import logging
from celery.utils.log import get_task_logger
from sqlalchemy.future import select

from src.tasks.worker import celery_app
from src.models.user import DeadLetterQueue, User
from src.core import database
from src.core.security import CredentialEncryptor
from src.core.gmail import fetch_gmail_message, parse_gmail_message, refresh_access_token
from src.core.pre_check import check_student_identifiers
from src.core.ai_gateway import AIGateway
from src.core.telegram_dispatcher import format_telegram_message, send_telegram_alert

logger = get_task_logger(__name__)

async def write_to_dlq_async(message_id: str, email: str, history_id: int, error_reason: str):
    """Asynchronously logs failed message payload details into PostgreSQL DLQ table."""
    async with database.SessionLocal() as session:
        dlq_entry = DeadLetterQueue(
            message_id=message_id,
            payload={"emailAddress": email, "historyId": history_id},
            error_reason=error_reason
        )
        session.add(dlq_entry)
        await session.commit()
        logger.info(f"Successfully wrote failed message {message_id} to Dead-Letter Queue database.")

async def process_email_pipeline_async(email: str, history_id: int, message_id: str):
    """Asynchronous pipeline orchestrating token decrypt, Gmail fetch, pre-checks, AI classification, and TG alerts."""
    if email == "fail@vit.edu":
        raise ValueError("Simulated processing failure for email event")

    # 1. Retrieve user details
    async with database.SessionLocal() as session:
        result = await session.execute(select(User).filter_by(gmail_address=email))
        user = result.scalars().first()
        
    if not user:
        raise ValueError(f"User with email {email} not found in database.")

    # 2. Decrypt credentials
    encryptor = CredentialEncryptor()
    refresh_token = encryptor.decrypt(user.encrypted_refresh_token)
    register_number = encryptor.decrypt(user.encrypted_register_number) if user.encrypted_register_number else None
    neopat_id = encryptor.decrypt(user.encrypted_neopat_id) if user.encrypted_neopat_id else None

    # 3. Refresh Access Token
    access_token = await refresh_access_token(refresh_token)

    # 4. Fetch Gmail message details
    message_data = await fetch_gmail_message(access_token, message_id)
    subject, sender, body = parse_gmail_message(message_data)

    # 5. Local pre-checks
    pre_check_matched = check_student_identifiers(
        body,
        register_number=register_number,
        email=email,
        neopat_id=neopat_id
    )

    # 6. Route to AI Gateway
    ai_gateway = AIGateway()
    try:
        classification = await ai_gateway.classify_email(subject, body, message_id)
        if classification.is_placement:
            text = format_telegram_message(
                company=classification.company,
                category=classification.category.value if classification.category else None,
                role=classification.role,
                package=classification.package,
                deadline=classification.deadline,
                application_links=classification.application_links
            )
            await send_telegram_alert(user.telegram_id, text)
    except Exception as exc:
        logger.error(f"AI Gateway failed for message {message_id}: {exc}")
        # Fallback to local rule-based parsing and send corresponding alert
        if pre_check_matched:
            # Student matched explicitly in the body, but AI failed
            fallback_text = (
                "<b>🔴 High Priority Match (Fallback)</b>\n\n"
                f"A placement email for <b>{email}</b> has been received and verified locally. "
                "AI processing is currently unavailable. Please check your VIT mail immediately."
            )
        else:
            # General placement email warning since specific student match confidence is insufficient
            fallback_text = (
                "<b>⚠️ Placement Update</b>\n\n"
                "Placement-related email detected. Please check your VIT mail."
            )
        await send_telegram_alert(user.telegram_id, fallback_text)

def run_coroutine_sync(coro):
    """Runs a coroutine synchronously, handling cases where an event loop is already running."""
    import threading
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        result = []
        error = []
        
        def target():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                res = new_loop.run_until_complete(coro)
                result.append(res)
            except Exception as e:
                error.append(e)
            finally:
                new_loop.close()
                
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        
        if error:
            raise error[0]
        return result[0] if result else None
    else:
        try:
            current_loop = asyncio.get_event_loop()
        except RuntimeError:
            current_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(current_loop)
        return current_loop.run_until_complete(coro)

@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    name="src.tasks.email_tasks.process_email_event"
)
def process_email_event(self, email: str, history_id: int, message_id: str):
    """Background task to process incoming Gmail webhook push events."""
    logger.info(f"Executing process_email_event task for {email} (history_id={history_id}, message_id={message_id})")
    try:
        run_coroutine_sync(
            process_email_pipeline_async(email, history_id, message_id)
        )
        return {"status": "success", "email": email, "history_id": history_id}
    except Exception as exc:
        logger.warning(
            f"Error processing email event for {email} (Attempt {self.request.retries + 1}/6): {exc}"
        )
        
        # Calculate exponential backoff countdown: 60s, 120s, 240s, 480s, 960s
        countdown = (2 ** self.request.retries) * self.default_retry_delay
        
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError as retry_exc:
            logger.error(
                f"Max retries exhausted for email event {email} (message_id={message_id}). routing to DLQ."
            )
            run_coroutine_sync(
                write_to_dlq_async(message_id, email, history_id, f"MaxRetriesExceeded: {str(exc)}")
            )
            raise retry_exc


