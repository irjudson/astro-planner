"""Celery tasks package."""

# Import tasks to register them with Celery
from app.tasks import planning_tasks, processing_tasks  # noqa: F401
