import asyncio
import logging
from celery.utils.log import get_task_logger
from src.tasks.worker import celery_app
from src.models.user import DeadLetterQueue
from src.core import database

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
        # Task payload execution logic
        # For testing retries and DLQ routing, we raise an exception for fail@vit.edu
        if email == "fail@vit.edu":
            raise ValueError("Simulated processing failure for email event")
            
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
            # Run the async DB write inside the synchronous Celery worker context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(
                write_to_dlq_async(message_id, email, history_id, f"MaxRetriesExceeded: {str(exc)}")
            )
            # Re-raise max retries exceeded error for Celery tracking
            raise retry_exc
