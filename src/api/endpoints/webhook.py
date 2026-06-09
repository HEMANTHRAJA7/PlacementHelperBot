import base64
import json
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
import redis.asyncio as aioredis

from src.core.config import settings
from src.core.security import verify_pubsub_jwt
from src.tasks.email_tasks import process_email_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

async def get_redis():
    """Dependency injection helper returning an async Redis client instance."""
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()

class PubSubMessage(BaseModel):
    data: str
    messageId: str
    publishTime: str

class PubSubPushRequest(BaseModel):
    message: PubSubMessage
    subscription: str

@router.post("/webhook")
async def webhook(
    payload: PubSubPushRequest,
    authorization: str = Header(..., alias="Authorization"),
    redis = Depends(get_redis)
):
    """Processes push webhooks from GCP Pub/Sub.
    
    Validates sender JWT, checks duplicate history/message IDs in Redis,
    and forwards unique tasks to background workers.
    """
    # 1. Verify Google OIDC JWT Signature
    verify_pubsub_jwt(authorization)
    
    message_id = payload.message.messageId
    
    # 2. Check message_id idempotency
    msg_key = f"placement_sentinel:msg:{message_id}"
    is_msg_seen = await redis.get(msg_key)
    if is_msg_seen:
        logger.info(f"Duplicate messageId received: {message_id}. Ignoring event.")
        return {"status": "ignored", "detail": "duplicate messageId"}
        
    # Decode base64 data to extract emailAddress and historyId
    try:
        decoded_bytes = base64.b64decode(payload.message.data)
        data_json = json.loads(decoded_bytes.decode("utf-8"))
        email = data_json.get("emailAddress")
        history_id = data_json.get("historyId")
    except Exception as e:
        logger.error(f"Failed to decode message data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode message data: {str(e)}"
        )
        
    if not email or not history_id:
        logger.error("Webhook payload missing emailAddress or historyId parameters.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message data must contain emailAddress and historyId"
        )
        
    # Check historyId idempotency per email to block retry storms
    history_key = f"placement_sentinel:history:{email}:{history_id}"
    is_history_seen = await redis.get(history_key)
    if is_history_seen:
        logger.info(f"Duplicate historyId {history_id} for email {email}. Ignoring event.")
        # Cache message_id so we drop subsequent retries of this push event immediately
        await redis.set(msg_key, "1", ex=86400) # 24-hour TTL
        return {"status": "ignored", "detail": "duplicate historyId"}
        
    # Store both in Redis with 24-hour expiration to block duplicates (D-06)
    await redis.set(msg_key, "1", ex=86400)
    await redis.set(history_key, "1", ex=86400)
    
    # 3. Dispatch background task to Celery out-of-band (T-01-04)
    process_email_event.delay(email, history_id, message_id)
    logger.info(f"Successfully enqueued process_email_event for {email} (historyId={history_id})")
    
    return {"status": "queued"}
