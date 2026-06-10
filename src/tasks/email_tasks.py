import asyncio
import logging
from celery.utils.log import get_task_logger
from sqlalchemy.future import select

from src.tasks.worker import celery_app
from src.models.user import DeadLetterQueue, User
from src.core import database
from src.core.security import CredentialEncryptor
from src.core.gmail import fetch_gmail_message, parse_gmail_message, refresh_access_token, fetch_gmail_attachment
from src.core.pre_check import check_student_identifiers
from src.core.ai_gateway import AIGateway, PlacementCategory
from src.core.telegram_dispatcher import format_telegram_message, send_telegram_alert
from src.core.attachment_parser import parse_pdf_in_memory, parse_excel_in_memory, parse_image_in_memory
from src.core.audit import log_audit_event
from src.core.metrics import (
    NOTIFICATIONS_SENT,
    DLQ_FAILURES,
    ATTACHMENT_PARSE_FAILURES,
    ATTACHMENT_MATCHES,
    GMAIL_WATCH_RENEW_FAILURES,
)

logger = get_task_logger(__name__)

async def write_to_dlq_async(message_id: str, email: str, history_id: int, error_reason: str):
    """Asynchronously logs failed message payload details into PostgreSQL DLQ table."""
    async with database.SessionLocal() as session:
        result = await session.execute(select(User).filter_by(gmail_address=email))
        user = result.scalars().first()
        user_id = user.id if user else None

        dlq_entry = DeadLetterQueue(
            message_id=message_id,
            payload={"emailAddress": email, "historyId": history_id},
            error_reason=error_reason
        )
        session.add(dlq_entry)
        await session.commit()
        logger.info(f"Successfully wrote failed message {message_id} to Dead-Letter Queue database.")

        DLQ_FAILURES.inc()

        await log_audit_event(
            event_type="dlq_routing",
            status="success",
            user_id=user_id,
            message_id=message_id,
            resource_type="database",
            error_code="MAX_RETRIES_EXCEEDED"
        )


def _extract_attachments(part: dict) -> list[dict]:
    """Recursively traverses MIME parts to find attachment details."""
    attachments = []
    body = part.get("body", {})
    attachment_id = body.get("attachmentId")
    if attachment_id:
        attachments.append({
            "filename": part.get("filename", ""),
            "mime_type": part.get("mimeType", ""),
            "attachment_id": attachment_id
        })
        
    parts = part.get("parts", [])
    for subpart in parts:
        attachments.extend(_extract_attachments(subpart))
    return attachments

async def process_email_pipeline_async(email: str, history_id: int, message_id: str):
    """Asynchronous pipeline orchestrating token decrypt, Gmail fetch, pre-checks, AI classification, and TG alerts."""
    user = None
    try:
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

        # 5. Local pre-checks on email body
        pre_check_matched = check_student_identifiers(
            body,
            register_number=register_number,
            email=email,
            neopat_id=neopat_id
        )

        # 5.5 In-Memory Attachment Processing (D-21)
        attachments = _extract_attachments(message_data.get("payload", {}))
        attachment_matched = False
        matched_attachments = []
        
        student_info = {
            "full_name": email.split("@")[0],
            "register_number": register_number,
            "neopat_id": neopat_id,
            "email": email
        }
        
        ai_gateway = AIGateway()
        
        for att in attachments:
            filename = att["filename"]
            mime_type = att["mime_type"].lower()
            attachment_id = att["attachment_id"]
            
            try:
                attachment_bytes = await fetch_gmail_attachment(access_token, message_id, attachment_id)
            except Exception as e:
                logger.error(f"Failed to download attachment {filename}: {e}")
                ATTACHMENT_PARSE_FAILURES.inc()
                continue

            matched_this_att = False
            escalate = False
            extracted_text = ""
            confidence = 100.0
            
            # Check PDF (D-22, D-23)
            if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
                try:
                    extracted_text = parse_pdf_in_memory(attachment_bytes)
                    if not extracted_text.strip():
                        escalate = True
                except Exception as e:
                    logger.warning(f"Error parsing PDF locally: {e}")
                    ATTACHMENT_PARSE_FAILURES.inc()
                    escalate = True
                    
            # Check Excel (D-22)
            elif mime_type in [
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ] or filename.lower().endswith((".xls", ".xlsx")):
                try:
                    extracted_text = parse_excel_in_memory(attachment_bytes)
                    if not extracted_text.strip():
                        escalate = True
                except Exception as e:
                    logger.warning(f"Error parsing Excel locally: {e}")
                    ATTACHMENT_PARSE_FAILURES.inc()
                    escalate = True
                    
            # Check Image (D-20)
            elif mime_type.startswith("image/") or filename.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    extracted_text, confidence = parse_image_in_memory(attachment_bytes)
                    if confidence < 80.0:
                        escalate = True
                except Exception as e:
                    logger.warning(f"Error running local OCR: {e}")
                    ATTACHMENT_PARSE_FAILURES.inc()
                    escalate = True
            
            # Match locally if no escalation is required
            if extracted_text and not escalate:
                matched_this_att = check_student_identifiers(
                    extracted_text,
                    register_number=register_number,
                    email=email,
                    neopat_id=neopat_id
                )
                
            # Escalation Trigger (D-24, D-25)
            if escalate:
                try:
                    vision_res = await ai_gateway.classify_attachment_vision(
                        attachment_bytes=attachment_bytes,
                        mime_type=mime_type or "image/png",
                        student_info=student_info,
                        message_id=message_id
                    )
                    if vision_res.is_matched:
                        matched_this_att = True
                except Exception as e:
                    logger.error(f"Gemini Vision fallback failed for attachment {filename}: {e}")
                    
            if matched_this_att:
                attachment_matched = True
                matched_attachments.append(filename)
                ATTACHMENT_MATCHES.inc()

        is_student_matched = pre_check_matched or attachment_matched

        # 6. Route to AI Gateway (Email Classification)
        try:
            classification = await ai_gateway.classify_email(subject, body, message_id)
            
            should_notify = is_student_matched or (
                classification.is_placement and
                classification.category == PlacementCategory.OPPORTUNITY
            )
            
            if should_notify:
                category = "Shortlist"
                if classification.is_placement and classification.category:
                    category = classification.category.value
                elif is_student_matched:
                    category = "Shortlist"
                    
                text = format_telegram_message(
                    company=classification.company if classification.is_placement else "Unknown Company",
                    category=category,
                    role=classification.role if classification.is_placement else None,
                    package=classification.package if classification.is_placement else None,
                    deadline=classification.deadline if classification.is_placement else None,
                    application_links=classification.application_links if classification.is_placement else []
                )
                
                if attachment_matched:
                    text += f"\n\n<i>📎 Matched in attachment: {', '.join(matched_attachments)}</i>"
                    
                tg_ok = await send_telegram_alert(user.telegram_id, text)
                if tg_ok:
                    NOTIFICATIONS_SENT.labels(category=category).inc()
                    await log_audit_event(
                        event_type="notification",
                        status="success",
                        user_id=user.id,
                        message_id=message_id,
                        resource_type="telegram_api"
                    )
                else:
                    await log_audit_event(
                        event_type="notification",
                        status="failed",
                        user_id=user.id,
                        message_id=message_id,
                        resource_type="telegram_api",
                        error_code="DELIVERY_FAILED"
                    )
                
        except Exception as exc:
            logger.error(f"AI Gateway failed for message {message_id}: {exc}")
            # Fallback to local rule-based parsing and send corresponding alert
            if is_student_matched:
                fallback_text = (
                    "<b>🔴 High Priority Match (Fallback)</b>\n\n"
                    f"A placement update for <b>{email}</b> has been received and verified locally.\n"
                    "AI classification is currently unavailable. Please check your VIT mail immediately."
                )
                if attachment_matched:
                    fallback_text += f"\n\n<i>📎 Matched in attachment: {', '.join(matched_attachments)}</i>"
                tg_ok = await send_telegram_alert(user.telegram_id, fallback_text)
                if tg_ok:
                    NOTIFICATIONS_SENT.labels(category="Shortlist").inc()
                    await log_audit_event(
                        event_type="notification",
                        status="success",
                        user_id=user.id,
                        message_id=message_id,
                        resource_type="telegram_api"
                    )
                else:
                    await log_audit_event(
                        event_type="notification",
                        status="failed",
                        user_id=user.id,
                        message_id=message_id,
                        resource_type="telegram_api",
                        error_code="DELIVERY_FAILED"
                    )
            else:
                fallback_text = (
                    "<b>⚠️ Placement Update</b>\n\n"
                    "Placement-related email detected. Please check your VIT mail."
                )
                tg_ok = await send_telegram_alert(user.telegram_id, fallback_text)
                if tg_ok:
                    NOTIFICATIONS_SENT.labels(category="Opportunity").inc()
                    await log_audit_event(
                        event_type="notification",
                        status="success",
                        user_id=user.id,
                        message_id=message_id,
                        resource_type="telegram_api"
                    )
                else:
                    await log_audit_event(
                        event_type="notification",
                        status="failed",
                        user_id=user.id,
                        message_id=message_id,
                        resource_type="telegram_api",
                        error_code="DELIVERY_FAILED"
                    )

        await log_audit_event(
            event_type="email_processed",
            status="success",
            user_id=user.id,
            message_id=message_id
        )

    except Exception as e:
        uid = user.id if user else None
        await log_audit_event(
            event_type="email_processed",
            status="failed",
            user_id=uid,
            message_id=message_id,
            error_code=type(e).__name__
        )
        raise e

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

async def renew_single_user_watch_async(self, user_id: int):
    from src.core.gmail import setup_gmail_watch
    from src.core.config import settings

    async with database.SessionLocal() as session:
        result = await session.execute(select(User).filter_by(id=user_id))
        user = result.scalars().first()
        if not user:
            logger.error(f"User {user_id} not found for watch renewal.")
            return

        encryptor = CredentialEncryptor()
        try:
            refresh_token = encryptor.decrypt(user.encrypted_refresh_token)
            access_token = await refresh_access_token(refresh_token)

            topic_name = settings.GMAIL_PUBSUB_TOPIC or "projects/placement-sentinel/topics/gmail-push"
            watch_res = await setup_gmail_watch(access_token, topic_name)

            user.watch_active = True
            user.watch_resource_id = watch_res.get("historyId")
            user.watch_expiration = int(watch_res.get("expiration", 0))

            await session.commit()

            await log_audit_event(
                event_type="watch_renew",
                status="success",
                user_id=user.id,
                resource_type="gmail_api",
                retry_count=self.request.retries
            )
            logger.info(f"Successfully renewed watch for user {user.gmail_address}")

        except Exception as exc:
            logger.warning(
                f"Error renewing watch for user {user.gmail_address} (Attempt {self.request.retries + 1}/4): {exc}"
            )
            GMAIL_WATCH_RENEW_FAILURES.inc()

            await log_audit_event(
                event_type="watch_renew",
                status="failed",
                user_id=user.id,
                resource_type="gmail_api",
                error_code=type(exc).__name__,
                retry_count=self.request.retries
            )

            countdown = (2 ** self.request.retries) * self.default_retry_delay
            try:
                raise self.retry(exc=exc, countdown=countdown)
            except self.MaxRetriesExceededError as retry_exc:
                logger.error(f"Max retries exceeded for watch renewal for user {user.gmail_address}.")
                user.watch_active = False
                await session.commit()

                warning_text = (
                    "<b>⚠️ Gmail Connection Expired</b>\n\n"
                    "Your secure Gmail connection has expired and we could not automatically renew it. "
                    "Please re-authenticate via the bot to continue receiving placement notifications."
                )
                await send_telegram_alert(user.telegram_id, warning_text)

                await log_audit_event(
                    event_type="watch_renew",
                    status="failed",
                    user_id=user.id,
                    resource_type="gmail_api",
                    error_code="MAX_RETRIES_EXCEEDED",
                    retry_count=self.request.retries
                )
                raise retry_exc

async def renew_all_watches_async():
    async with database.SessionLocal() as session:
        result = await session.execute(select(User.id))
        user_ids = result.scalars().all()

    for user_id in user_ids:
        renew_single_user_watch_task.delay(user_id)
    logger.info(f"Enqueued watch renewals for {len(user_ids)} users.")

@celery_app.task(name="src.tasks.email_tasks.renew_all_watches_task")
def renew_all_watches_task():
    """Daily periodic task to enqueue watch renewals for all users."""
    run_coroutine_sync(renew_all_watches_async())

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="src.tasks.email_tasks.renew_single_user_watch_task"
)
def renew_single_user_watch_task(self, user_id: int):
    """Renews the Gmail watch subscription for a single user."""
    logger.info(f"Executing renew_single_user_watch_task for user_id={user_id}")
    try:
        run_coroutine_sync(renew_single_user_watch_async(self, user_id))
        return {"status": "success", "user_id": user_id}
    except Exception as exc:
        if "MaxRetriesExceeded" in type(exc).__name__ or type(exc).__name__ == "Retry":
            raise exc
        logger.error(f"Task failed during renewal of user_id={user_id}: {exc}")
        raise exc

async def cleanup_old_logs_async():
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import delete
    from src.models.user import AuditLog, DeadLetterQueue

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    async with database.SessionLocal() as session:
        audit_stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
        audit_res = await session.execute(audit_stmt)

        dlq_stmt = delete(DeadLetterQueue).where(DeadLetterQueue.failed_at < cutoff)
        dlq_res = await session.execute(dlq_stmt)

        await session.commit()
        logger.info(
            f"Pruned {audit_res.rowcount} old audit logs and {dlq_res.rowcount} DLQ entries older than 90 days."
        )

@celery_app.task(name="src.tasks.email_tasks.cleanup_old_logs")
def cleanup_old_logs():
    """Daily periodic task to prune audit logs and DLQ entries older than 90 days."""
    run_coroutine_sync(cleanup_old_logs_async())



