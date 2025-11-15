"""Processing service with direct FITS file processing."""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.database import SessionLocal
from app.models.processing_models import ProcessingFile, ProcessingJob, ProcessingPipeline
from app.services.direct_processor import DirectProcessor

logger = logging.getLogger(__name__)


class ProcessingService:
    """Orchestrates processing pipeline execution using direct file processing."""

    def __init__(self):
        self.processor = DirectProcessor()
        self.data_dir = Path("/app/data/processing")

        # Ensure processing directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def execute_pipeline(
        self,
        file_id: int,
        pipeline_id: int,
        job_id: int
    ) -> Dict[str, Any]:
        """Execute a processing pipeline on a single file."""

        db = SessionLocal()
        try:
            # Load file, pipeline, and job
            processing_file = db.query(ProcessingFile).filter(ProcessingFile.id == file_id).first()
            pipeline = db.query(ProcessingPipeline).filter(ProcessingPipeline.id == pipeline_id).first()
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

            if not processing_file or not pipeline or not job:
                raise ValueError("File, pipeline, or job not found")

            # Update job status
            job.status = "starting"
            job.started_at = datetime.utcnow()
            db.commit()

            # Get the input file path
            input_file = Path(processing_file.file_path)
            if not input_file.exists():
                raise ValueError(f"Input file not found: {input_file}")

            # Create job directory
            job_dir = self.data_dir / f"job_{job_id}"
            job_dir.mkdir(parents=True, exist_ok=True)

            # Create output directory
            output_dir = job_dir / "outputs"
            output_dir.mkdir(exist_ok=True)

            # Update job status
            job.gpu_used = False  # No GPU support in direct mode
            job.status = "running"
            job.progress_percent = 10.0
            job.current_step = "Processing FITS file"
            db.commit()

            # Run processing directly
            logger.info(f"Processing job {job_id} with direct processor")
            log_messages = []

            try:
                log_messages.append(f"Loading FITS file: {input_file}")
                output_files_paths = self.processor.process_fits(
                    input_file=input_file,
                    output_dir=output_dir,
                    pipeline_steps=pipeline.pipeline_steps
                )
                log_messages.append(f"Processing complete, {len(output_files_paths)} files generated")

            except Exception as proc_error:
                raise Exception(f"Processing error: {proc_error}")

            # Update progress
            job.progress_percent = 80.0
            job.current_step = "Copying final outputs"
            db.commit()

            # Copy final outputs to processing_base with descriptive names
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Get object name from the input file
            object_name = input_file.parent.name if input_file.parent.name else "processed"

            # Get pipeline name for the filename
            pipeline_name = pipeline.name.lower().replace(" ", "_")

            output_files = []
            for output_file_path in output_files_paths:
                output_file = Path(output_file_path)
                if output_file.is_file():
                    # Create descriptive filename
                    ext = output_file.suffix
                    final_name = f"{object_name}_{pipeline_name}_{timestamp}{ext}"
                    final_path = self.data_dir / final_name

                    # Copy to processing base directory
                    shutil.copy2(output_file, final_path)
                    output_files.append(str(final_path))

                    log_messages.append(f"Copied final output: {final_path}")
                    logger.info(f"Copied final output: {final_path}")

            # Update job
            job.status = "complete"
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100.0
            job.current_step = "Complete"
            job.processing_log = "\n".join(log_messages)
            job.output_files = output_files

            db.commit()

            return {
                "status": "complete",
                "output_files": output_files,
                "processing_log": job.processing_log,
                "gpu_used": False
            }

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()

            raise

        finally:
            db.close()

    async def cancel_job(self, job_id: int) -> bool:
        """Cancel a running job."""
        db = SessionLocal()
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job:
                return False

            # Update job status
            job.status = "cancelled"
            job.completed_at = datetime.utcnow()
            db.commit()

            return True

        finally:
            db.close()

    def cleanup_old_jobs(self, days: int = 7):
        """Clean up old job directories."""
        cutoff = datetime.utcnow().timestamp() - (days * 24 * 3600)

        for job_dir in self.data_dir.glob("job_*"):
            if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
                logger.info(f"Cleaning up old job directory: {job_dir}")
                import shutil
                shutil.rmtree(job_dir, ignore_errors=True)
