import logging
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.core.config import settings
from src.core.database import get_db
from src.models.user import User, AuditLog
from src.core.metrics import ACTIVE_WATCHES, CELERY_PENDING_TASKS
from src.tasks.worker import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])

def check_celery_workers():
    try:
        inspector = celery_app.control.inspect()
        active = inspector.active()
        return active is not None and len(active) > 0
    except Exception as e:
        logger.error(f"Celery inspect failed: {e}")
        return False

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Exposes Prometheus-compatible telemetry metrics, updating dynamic values on scrape."""
    try:
        # 1. Update Active Watches Gauge
        active_stmt = select(func.count(User.id)).where(User.watch_active == True)
        inactive_stmt = select(func.count(User.id)).where(User.watch_active == False)
        
        active_res = await db.execute(active_stmt)
        inactive_res = await db.execute(inactive_stmt)
        
        active_count = active_res.scalar() or 0
        inactive_count = inactive_res.scalar() or 0
        
        ACTIVE_WATCHES.labels(status="active").set(active_count)
        ACTIVE_WATCHES.labels(status="inactive").set(inactive_count)
    except Exception as e:
        logger.error(f"Failed to query user watch counts for metrics: {e}")

    try:
        # 2. Update Celery Queue Gauge from Redis
        r = aioredis.from_url(settings.REDIS_URL)
        queue_len = await r.llen("celery")
        CELERY_PENDING_TASKS.set(queue_len)
        await r.aclose()
    except Exception as e:
        logger.error(f"Failed to query Redis queue length for metrics: {e}")

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/health")
@router.get("/api/v1/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Actively checks PostgreSQL, Redis, Celery heartbeat, and watch renewal freshness."""
    postgres_status = "healthy"
    redis_status = "healthy"
    celery_status = "healthy"
    watch_status = "healthy"
    
    # 1. Check PostgreSQL
    try:
        await db.execute(select(1))
    except Exception as e:
        logger.error(f"Health check: PostgreSQL is down: {e}")
        postgres_status = "unhealthy"

    # 2. Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception as e:
        logger.error(f"Health check: Redis is down: {e}")
        redis_status = "unhealthy"

    # 3. Check Celery Heartbeat
    try:
        celery_ok = await asyncio.to_thread(check_celery_workers)
        if not celery_ok:
            celery_status = "unhealthy"
    except Exception as e:
        logger.error(f"Health check: Celery heartbeat check failed: {e}")
        celery_status = "unhealthy"

    # 4. Check Gmail Watch Renewal freshness (last 24 hours, or healthy if 0 users)
    try:
        user_count_stmt = select(func.count(User.id))
        user_count_res = await db.execute(user_count_stmt)
        user_count = user_count_res.scalar() or 0
        
        if user_count > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            stmt = select(AuditLog).where(
                AuditLog.event_type == "watch_renew",
                AuditLog.status == "success",
                AuditLog.created_at >= cutoff
            ).limit(1)
            res = await db.execute(stmt)
            if res.scalar() is None:
                watch_status = "unhealthy"
    except Exception as e:
        logger.error(f"Health check: watch renewal verification failed: {e}")
        watch_status = "unhealthy"

    healthy = (
        postgres_status == "healthy"
        and redis_status == "healthy"
        and celery_status == "healthy"
        and watch_status == "healthy"
    )

    content = {
        "status": "healthy" if healthy else "unhealthy",
        "postgresql": postgres_status,
        "redis": redis_status,
        "celery": celery_status,
        "watch_renewal": watch_status
    }

    if healthy:
        return JSONResponse(status_code=status.HTTP_200_OK, content=content)
    else:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=content)
