"""Processing service with direct FITS processing."""

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
    """Orchestrates processing pipeline execution using direct processing."""

    def __init__(self):
        self.processor = DirectProcessor()
        self.data_dir = Path("/app/data/processing")

        # Ensure processing directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def execute_pipeline(
        self,
        session_id: int,
        pipeline_id: int,
        job_id: int
    ) -> Dict[str, Any]:
        """Execute a processing pipeline in an isolated Docker container."""

        db = SessionLocal()
        try:
            # Load session and pipeline
            session = db.query(ProcessingSession).filter(ProcessingSession.id == session_id).first()
            pipeline = db.query(ProcessingPipeline).filter(ProcessingPipeline.id == pipeline_id).first()
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

            if not session or not pipeline or not job:
                raise ValueError("Session, pipeline, or job not found")

            # Update job status
            job.status = "starting"
            job.started_at = datetime.utcnow()
            db.commit()

            # Get processing base directory from session metadata
            processing_base = Path(session.session_metadata.get("processing_base", str(self.data_dir)) if session.session_metadata else str(self.data_dir))

            # Create job directory inside the session folder
            session_dir = processing_base / f"session_{session_id}"
            session_dir.mkdir(parents=True, exist_ok=True)

            job_dir = session_dir / f"job_{job_id}"
            job_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (job_dir / "outputs").mkdir(exist_ok=True)

            # Find stacked file from session
            stacked_file = None
            for file in session.files:
                if file.file_type == "stacked":
                    stacked_file = Path(file.file_path)
                    break

            if not stacked_file:
                raise ValueError("No stacked FITS file found in session")

            # Update job status
            job.gpu_used = False  # No GPU support in direct mode
            job.status = "running"
            job.progress_percent = 10.0
            job.current_step = "Processing FITS file"
            db.commit()

            # Run processing directly
            logger.info(f"Processing job {job_id} with direct processor")
            log_messages = []

            output_dir = job_dir / "outputs"
            try:
                log_messages.append(f"Loading FITS file: {stacked_file}")
                output_files_paths = self.processor.process_fits(
                    input_file=stacked_file,
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

            # Get object name from the first file in session
            object_name = "processed"
            if session.files:
                first_file = Path(session.files[0].file_path)
                # Extract object name from filename or use parent directory name
                object_name = first_file.parent.name

            # Get pipeline name for the filename
            pipeline_name = pipeline.name.lower().replace(" ", "_")

            output_files = []
            for output_file_path in output_files_paths:
                output_file = Path(output_file_path)
                if output_file.is_file():
                    # Create descriptive filename
                    ext = output_file.suffix
                    final_name = f"{object_name}_{pipeline_name}_{timestamp}{ext}"
                    final_path = processing_base / final_name

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

    def _build_container_config(self, job_dir: Path, use_gpu: bool) -> Dict[str, Any]:
        """Build Docker container configuration."""

        config = {
            "image": self.processing_image,
            "command": ["--config", "/job/job_config.json"],
            "volumes": {
                str(job_dir): {"bind": "/job", "mode": "rw"}
            },
            "environment": {
                "JOB_DIR": "/job"
            },
            # Resource limits
            "mem_limit": "4g",
            "memswap_limit": "4g",
            "cpu_quota": 200000,  # 2 CPU cores
            # Security
            "network_disabled": True,  # No network access needed
            "security_opt": ["no-new-privileges"],
            # Cleanup
            "auto_remove": True,
            "detach": False,  # Wait for completion
            # Logging
            "stdout": True,
            "stderr": True
        }

        # Add GPU support if available
        if use_gpu:
            config["device_requests"] = [
                docker.types.DeviceRequest(
                    count=-1,  # Use all GPUs
                    capabilities=[['gpu', 'compute', 'utility']]
                )
            ]
            config["environment"]["CUDA_VISIBLE_DEVICES"] = "0"
            config["environment"]["NVIDIA_VISIBLE_DEVICES"] = "all"

        return config

    async def cancel_job(self, job_id: int) -> bool:
        """Cancel a running job."""
        db = SessionLocal()
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job:
                return False

            # If container is running, stop it
            if job.container_id and self.docker_available:
                try:
                    container = self.docker_client.containers.get(job.container_id)
                    container.stop(timeout=10)
                    container.remove()
                except Exception as e:
                    logger.warning(f"Could not stop container {job.container_id}: {e}")

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
