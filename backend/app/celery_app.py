"""Celery configuration for background tasks."""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "russian_science_hub",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.crawler_tasks",
        "app.tasks.embedding_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "update-embeddings-daily": {
        "task": "app.tasks.embedding_tasks.update_missing_embeddings",
        "schedule": 86400.0,  # Daily
    },
}
