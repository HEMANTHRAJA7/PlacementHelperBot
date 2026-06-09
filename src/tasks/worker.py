from celery import Celery
from src.core.config import settings

# Format PostgreSQL URL for Celery backend (uses synchronous drivers)
backend_url = "db+" + settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

celery_app = Celery(
    "placement_sentinel_tasks",
    broker=settings.REDIS_URL,
    backend=backend_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
