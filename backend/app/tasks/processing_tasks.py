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
from app.services.stacking_service import StackingService
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


@celery_app.task(bind=True, name="stack_and_stretch")
def stack_and_stretch_task(
    self, folder_path: str, pattern: str, sigma: float, formats: List[str], job_id: int
) -> Dict[str, Any]:
    """
    Celery task for stacking sub-frames and auto-stretching.

    This is the complete Seestar-matching pipeline:
    1. Stack Light_*.fit files with sigma clipping
    2. Debayer to RGB
    3. Auto-stretch
    4. Save outputs

    Args:
        folder_path: Path to folder containing sub-frames
        pattern: Glob pattern for sub-frames (e.g., "Light_*.fit")
        sigma: Sigma threshold for outlier rejection
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
        job.current_step = "Loading sub-frames"
        job.progress_percent = 10.0
        db.commit()

        folder = Path(folder_path)
        logger.info(f"Stack-and-stretch job {job_id}: {folder}")

        # Step 1: Stack sub-frames
        job.current_step = "Stacking sub-frames"
        job.progress_percent = 20.0
        db.commit()

        stacking_service = StackingService(use_gpu=True)
        stacking_result = stacking_service.stack_folder(folder, pattern=pattern, sigma=sigma)

        logger.info(
            f"Stacked {stacking_result.num_frames} frames -> {stacking_result.stacked_file}, "
            f"rejected ~{stacking_result.rejected_frames} frames"
        )

        # Step 2: Auto-stretch the stacked file
        job.current_step = "Auto-stretching"
        job.progress_percent = 60.0
        db.commit()

        stretch_service = AutoStretchService()
        stretch_result = stretch_service.auto_process(stacking_result.stacked_file, formats=formats)

        logger.info(f"Auto-stretch complete: {len(stretch_result.output_files)} files created")

        # Update job with results
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        job.progress_percent = 100.0
        job.current_step = "Complete"
        job.output_files = [str(p) for p in stretch_result.output_files]
        job.processing_log = (
            f"Stacked {stacking_result.num_frames} sub-frames from {folder.name}\n"
            f"Input shape: {stacking_result.input_shape}\n"
            f"Stacked shape: {stacking_result.output_shape}\n"
            f"Rejected frames: ~{stacking_result.rejected_frames}\n"
            f"Sigma threshold: {sigma}\n"
            f"\n"
            f"Auto-stretch parameters:\n"
            f"  Stretch factor: {stretch_result.params.stretch_factor}\n"
            f"  Black point: {stretch_result.params.black_point:.2f}\n"
            f"  White point: {stretch_result.params.white_point:.2f}\n"
            f"\n"
            f"Output files: {len(stretch_result.output_files)}\n"
            f"  Stacked FITS: {stacking_result.stacked_file}\n"
            + "\n".join(f"  {p.name}" for p in stretch_result.output_files)
        )
        db.commit()

        logger.info(f"Stack-and-stretch job {job_id} complete")

        return {
            "status": "complete",
            "stacked_file": str(stacking_result.stacked_file),
            "output_files": [str(p) for p in stretch_result.output_files],
            "num_frames": stacking_result.num_frames,
            "params": {
                "stretch_factor": stretch_result.params.stretch_factor,
                "black_point": stretch_result.params.black_point,
                "white_point": stretch_result.params.white_point,
            },
        }

    except Exception as e:
        logger.error(f"Stack-and-stretch job {job_id} failed: {e}")

        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()

        raise

    finally:
        db.close()
