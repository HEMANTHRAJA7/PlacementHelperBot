from celery import Celery
from src.core.config import settings

# Format PostgreSQL URL for Celery backend (uses synchronous drivers)
backend_url = "db+" + settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

celery_app = Celery(
    "placement_sentinel_tasks",
    broker=settings.REDIS_URL,
    backend=backend_url
)

from celery.schedules import crontab

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "renew-gmail-watches-daily": {
        "task": "src.tasks.email_tasks.renew_all_watches_task",
        "schedule": crontab(hour=0, minute=0),
    },
    "cleanup-old-logs-daily": {
        "task": "src.tasks.email_tasks.cleanup_old_logs",
        "schedule": crontab(hour=1, minute=0),
    },
}

