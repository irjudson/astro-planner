"""Celery tasks for processing jobs."""

import asyncio
from typing import Dict, Any

from app.tasks.celery_app import celery_app
from app.services.processing_service import ProcessingService


@celery_app.task(bind=True, name="process_session")
def process_session_task(self, session_id: int, pipeline_id: int, job_id: int) -> Dict[str, Any]:
    """
    Celery task that orchestrates Docker container for processing.

    This task runs in the celery worker and launches
    a separate processing container for actual work.
    """
    service = ProcessingService()

    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            service.execute_pipeline(session_id, pipeline_id, job_id)
        )
        return result
    finally:
        loop.close()


@celery_app.task(bind=True, name="cancel_job")
def cancel_job_task(self, job_id: int) -> bool:
    """Cancel a running processing job."""
    service = ProcessingService()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(service.cancel_job(job_id))
        return result
    finally:
        loop.close()


@celery_app.task(name="cleanup_old_jobs")
def cleanup_old_jobs_task(days: int = 7):
    """Clean up old job directories."""
    service = ProcessingService()
    service.cleanup_old_jobs(days=days)
