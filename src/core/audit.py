import logging
from typing import Optional
from src.core import database
from src.models.user import AuditLog

logger = logging.getLogger(__name__)

async def log_audit_event(
    event_type: str,
    status: str,
    user_id: Optional[int] = None,
    message_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    error_code: Optional[str] = None,
    retry_count: int = 0
) -> None:
    """Logs a security/system event for auditing, strictly storing metadata only."""
    try:
        async with database.SessionLocal() as session:
            audit_entry = AuditLog(
                user_id=user_id,
                event_type=event_type,
                status=status,
                message_id=message_id,
                resource_type=resource_type,
                error_code=error_code,
                retry_count=retry_count
            )
            session.add(audit_entry)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
