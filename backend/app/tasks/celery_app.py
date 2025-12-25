"""Celery application configuration."""

import os

from celery import Celery
from celery.schedules import crontab

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

# Get timezone for beat scheduler (defaults to America/Denver)
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", os.getenv("DEFAULT_TIMEZONE", "America/Denver"))

# Create Celery app
celery_app = Celery(
    "astro_planner",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.processing_tasks", "app.tasks.planning_tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=CELERY_TIMEZONE,
    enable_utc=False,  # Use local timezone for scheduling
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    worker_prefetch_multiplier=1,  # Disable prefetching for long tasks
)

# Configure Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "generate-daily-plan": {
        "task": "generate_daily_plan",
        "schedule": crontab(hour=12, minute=0),  # Daily at noon in configured timezone
        "args": (),
    },
}

if __name__ == "__main__":
    celery_app.start()
