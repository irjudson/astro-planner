"""Celery application configuration."""

import os

from celery import Celery

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery("astro_planner", broker=REDIS_URL, backend=REDIS_URL, include=["app.tasks.processing_tasks"])

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    worker_prefetch_multiplier=1,  # Disable prefetching for long tasks
)

if __name__ == "__main__":
    celery_app.start()
