"""Celery tasks for processing jobs."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.processing_models import ProcessingJob
from app.services.auto_stretch_service import AutoStretchService
from app.services.processing_service import ProcessingService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_file")
def process_file_task(self, file_id: int, pipeline_id: int, job_id: int) -> Dict[str, Any]:
    """
    Celery task that processes a single FITS file.

    Args:
        file_id: ID of the ProcessingFile to process
        pipeline_id: ID of the ProcessingPipeline to use
        job_id: ID of the ProcessingJob tracking this work
    """
    service = ProcessingService()

    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(service.execute_pipeline(file_id, pipeline_id, job_id))
        return result
    finally:
        loop.close()


@celery_app.task(bind=True, name="auto_process")
def auto_process_task(self, file_path: str, formats: List[str], job_id: int) -> Dict[str, Any]:
    """
    Celery task for auto-processing a FITS file with Seestar-matching stretch.

    Args:
        file_path: Path to the FITS file
        formats: Output formats (jpg, png, tiff)
        job_id: ID of the ProcessingJob tracking this work

    Returns:
        Dictionary with processing results
    """
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.current_step = "Loading FITS file"
        job.progress_percent = 10.0
        db.commit()

        # Run auto-stretch processing
        service = AutoStretchService()
        fits_path = Path(file_path)

        logger.info(f"Auto-processing job {job_id}: {fits_path}")

        # Update progress
        job.current_step = "Detecting stretch parameters"
        job.progress_percent = 30.0
        db.commit()

        # Process the file
        result = service.auto_process(fits_path, formats=formats)

        # Update progress
        job.current_step = "Saving outputs"
        job.progress_percent = 80.0
        db.commit()

        # Update job with results
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        job.progress_percent = 100.0
        job.current_step = "Complete"
        job.output_files = [str(p) for p in result.output_files]
        job.processing_log = (
            f"Processed {fits_path.name}\n"
            f"Input shape: {result.input_shape}\n"
            f"Stretch factor: {result.params.stretch_factor}\n"
            f"Black point: {result.params.black_point:.2f}\n"
            f"White point: {result.params.white_point:.2f}\n"
            f"Output files: {len(result.output_files)}"
        )
        db.commit()

        logger.info(f"Auto-processing job {job_id} complete: {len(result.output_files)} files created")

        return {
            "status": "complete",
            "output_files": [str(p) for p in result.output_files],
            "params": {
                "stretch_factor": result.params.stretch_factor,
                "black_point": result.params.black_point,
                "white_point": result.params.white_point,
            },
        }

    except Exception as e:
        logger.error(f"Auto-processing job {job_id} failed: {e}")

        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()

        raise

    finally:
        db.close()


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
