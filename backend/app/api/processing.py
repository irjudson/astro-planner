"""API endpoints for processing system (direct file processing)."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.processing_models import ProcessingFile, ProcessingJob, ProcessingPipeline
from app.tasks.processing_tasks import auto_process_task, process_file_task

router = APIRouter(prefix="/process", tags=["processing"])


# Pydantic models for requests/responses
class JobResponse(BaseModel):
    id: int
    status: str
    progress_percent: float
    current_step: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    gpu_used: bool
    output_files: Optional[List[str]]

    class Config:
        from_attributes = True


class DirectProcessRequest(BaseModel):
    file_path: str
    processing_type: str  # "quick_preview" or "export_editing"


# Processing data directory
PROCESSING_DIR = Path(os.getenv("PROCESSING_DIR", "./data/processing"))
PROCESSING_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/browse")
async def browse_files(path: str = ""):
    """Browse FITS files in the mounted directory."""
    fits_root = Path("/fits")

    if not fits_root.exists():
        raise HTTPException(status_code=404, detail="FITS directory not mounted")

    # Sanitize path to prevent directory traversal
    browse_path = fits_root / path.lstrip("/")
    browse_path = browse_path.resolve()

    # Ensure we're still within /fits
    if not str(browse_path).startswith(str(fits_root)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not browse_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    items = []
    if browse_path.is_dir():
        for item in sorted(browse_path.iterdir()):
            relative_path = str(item.relative_to(fits_root))
            items.append(
                {
                    "name": item.name,
                    "path": relative_path,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                    "is_fits": item.suffix.lower() in [".fit", ".fits", ".fit.gz"] if item.is_file() else False,
                }
            )

    return {"current_path": str(browse_path.relative_to(fits_root)) if browse_path != fits_root else "", "items": items}


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(limit: int = 10, db: Session = Depends(get_db)):
    """List recent processing jobs, ordered by most recent first."""
    jobs = db.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(limit).all()

    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job status."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel a running job."""
    from app.tasks.processing_tasks import cancel_job_task

    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Queue cancel task
    cancel_job_task.delay(job_id)

    return {"message": "Job cancellation requested", "job_id": job_id}


@router.get("/jobs/{job_id}/download", response_class=FileResponse)
async def download_job_output(job_id: int, db: Session = Depends(get_db)):
    """Download processed output file."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "complete":
        raise HTTPException(status_code=400, detail="Job not complete")

    if not job.output_files or len(job.output_files) == 0:
        raise HTTPException(status_code=404, detail="No output files")

    # Return first output file
    output_file = Path(job.output_files[0])

    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(path=str(output_file), filename=output_file.name, media_type="application/octet-stream")


def get_or_create_pipeline(pipeline_name: str, db: Session) -> ProcessingPipeline:
    """Get or create a processing pipeline."""
    # Check if pipeline exists
    pipeline = (
        db.query(ProcessingPipeline)
        .filter(ProcessingPipeline.name == pipeline_name, ProcessingPipeline.is_preset == True)
        .first()
    )

    if pipeline:
        return pipeline

    # Create built-in pipelines
    if pipeline_name == "quick_dso":
        steps = [
            {"step": "histogram_stretch", "params": {"algorithm": "auto", "midtones": 0.5}},
            {"step": "export", "params": {"format": "jpeg", "quality": 95, "bit_depth": 8}},
        ]

        pipeline = ProcessingPipeline(
            name="quick_dso",
            description="Quick DSO processing: auto-stretch and JPEG export",
            pipeline_steps=steps,
            is_preset=True,
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        return pipeline

    elif pipeline_name == "export_pixinsight":
        steps = [{"step": "export", "params": {"format": "tiff", "bit_depth": 16, "compression": "none"}}]

        pipeline = ProcessingPipeline(
            name="export_pixinsight",
            description="Export for PixInsight: 16-bit TIFF",
            pipeline_steps=steps,
            is_preset=True,
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        return pipeline

    else:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")


# ============================================================================
# DIRECT FILE PROCESSING API (No sessions required)
# ============================================================================


@router.post("/file", response_model=JobResponse)
async def process_file_direct(request: DirectProcessRequest, db: Session = Depends(get_db)):
    """
    Process a FITS file directly.

    This is the simplified API - just point to a file and process it.

    Processing types:
    - quick_preview: Auto-stretch to JPEG for quick viewing/sharing
    - export_editing: 16-bit TIFF for PixInsight/Photoshop
    """
    # Validate file exists
    # Support both absolute paths (starting with /fits/) and relative paths from browse API
    if request.file_path.startswith("/fits/"):
        file_path = Path(request.file_path)
    else:
        file_path = Path("/fits") / request.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if file_path.suffix.lower() not in [".fit", ".fits"]:
        raise HTTPException(status_code=400, detail="File must be a FITS file")

    # Map processing type to pipeline
    pipeline_map = {"quick_preview": "quick_dso", "export_editing": "export_pixinsight"}

    pipeline_name = pipeline_map.get(request.processing_type)
    if not pipeline_name:
        raise HTTPException(status_code=400, detail=f"Invalid processing_type. Use: {list(pipeline_map.keys())}")

    # Get or create pipeline
    pipeline = get_or_create_pipeline(pipeline_name, db)

    # Create file record (no session needed)
    processing_file = ProcessingFile(
        filename=file_path.name, file_type="stacked", file_path=str(file_path), file_size_bytes=file_path.stat().st_size
    )
    db.add(processing_file)
    db.commit()
    db.refresh(processing_file)

    # Create job
    job = ProcessingJob(file_id=processing_file.id, pipeline_id=pipeline.id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue task (uses file_id in job model)
    process_file_task.delay(processing_file.id, pipeline.id, job.id)

    return job


# ============================================================================
# AUTO-PROCESSING API (Seestar-matching stretch algorithm)
# ============================================================================


class AutoProcessRequest(BaseModel):
    """Request model for auto-processing a single FITS file."""

    file_path: str
    formats: Optional[List[str]] = ["jpg", "png", "tiff"]


class AutoProcessResponse(BaseModel):
    """Response model for auto-processing."""

    job_id: int
    status: str
    file_path: str


class BatchProcessRequest(BaseModel):
    """Request model for batch processing."""

    folder_path: str
    recursive: bool = True
    pattern: str = "Stacked_*.fit"
    formats: Optional[List[str]] = ["jpg", "png", "tiff"]


class BatchProcessResponse(BaseModel):
    """Response model for batch processing."""

    job_ids: List[int]
    files_found: int


class StackAndStretchRequest(BaseModel):
    """Request model for stack-and-stretch processing."""

    folder_path: str
    pattern: str = "Light_*.fit"
    sigma: float = 2.5
    formats: Optional[List[str]] = ["jpg"]


class StackAndStretchResponse(BaseModel):
    """Response model for stack-and-stretch."""

    job_id: int
    status: str
    folder_path: str
    files_found: int


@router.post("/auto", response_model=AutoProcessResponse)
async def auto_process_single(request: AutoProcessRequest, db: Session = Depends(get_db)):
    """
    Auto-process a single FITS file using Seestar-matching arcsinh stretch.

    This uses the reverse-engineered Seestar algorithm with auto-detected parameters
    to produce output that visually matches Seestar's own processing.

    Output files are saved alongside the input file with '_processed' suffix.
    """
    # Validate file exists
    file_path = Path(request.file_path)

    # Handle paths relative to /fits mount
    if not file_path.is_absolute():
        file_path = Path("/fits") / request.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if file_path.suffix.lower() not in [".fit", ".fits"]:
        raise HTTPException(status_code=400, detail="File must be a FITS file")

    # Validate formats
    valid_formats = ["jpg", "png", "tiff"]
    for fmt in request.formats:
        if fmt.lower() not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}. Valid: {valid_formats}")

    # Create file record
    processing_file = ProcessingFile(
        filename=file_path.name, file_type="stacked", file_path=str(file_path), file_size_bytes=file_path.stat().st_size
    )
    db.add(processing_file)
    db.commit()
    db.refresh(processing_file)

    # Create job with auto_stretch pipeline
    job = ProcessingJob(file_id=processing_file.id, pipeline_id=None, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue the auto-process task
    auto_process_task.delay(str(file_path), request.formats, job.id)

    return AutoProcessResponse(job_id=job.id, status="queued", file_path=str(file_path))


@router.post("/batch", response_model=BatchProcessResponse)
async def batch_process(request: BatchProcessRequest, db: Session = Depends(get_db)):
    """
    Batch process all matching FITS files in a folder.

    Finds all files matching the pattern and queues them for auto-processing.
    Default pattern matches Seestar stacked files: 'Stacked_*.fit'
    """
    # Validate folder exists
    folder_path = Path(request.folder_path)

    # Handle paths relative to /fits mount
    if not folder_path.is_absolute():
        folder_path = Path("/fits") / request.folder_path

    if not folder_path.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path must be a directory")

    # Find matching files
    if request.recursive:
        fits_files = list(folder_path.rglob(request.pattern))
    else:
        fits_files = list(folder_path.glob(request.pattern))

    if not fits_files:
        raise HTTPException(status_code=404, detail=f"No files matching '{request.pattern}' found in {folder_path}")

    job_ids = []

    for fits_file in fits_files:
        # Create file record
        processing_file = ProcessingFile(
            filename=fits_file.name,
            file_type="stacked",
            file_path=str(fits_file),
            file_size_bytes=fits_file.stat().st_size,
        )
        db.add(processing_file)
        db.commit()
        db.refresh(processing_file)

        # Create job
        job = ProcessingJob(file_id=processing_file.id, pipeline_id=None, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)

        # Queue the auto-process task
        auto_process_task.delay(str(fits_file), request.formats, job.id)

        job_ids.append(job.id)

    return BatchProcessResponse(job_ids=job_ids, files_found=len(fits_files))


@router.post("/stack-and-stretch", response_model=StackAndStretchResponse)
async def stack_and_stretch(request: StackAndStretchRequest, db: Session = Depends(get_db)):
    """
    One-button processing: Stack sub-frames and auto-stretch to match Seestar output.

    This is the complete pipeline that:
    1. Loads all Light_*.fit sub-frames from the folder
    2. Stacks them with sigma-clipping (rejects outliers)
    3. Debayers the result (Bayer pattern -> RGB)
    4. Auto-stretches using the Seestar-matching algorithm
    5. Saves output as JPG/PNG/TIFF

    This recreates the exact processing that Seestar does internally.

    Example:
        folder_path: "/fits/M81_sub" or "M 31_mosaic_sub"
    """
    # Validate folder exists
    folder_path = Path(request.folder_path)

    # Handle paths relative to /fits mount
    if not folder_path.is_absolute():
        folder_path = Path("/fits") / request.folder_path

    if not folder_path.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")

    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path must be a directory")

    # Count matching files
    sub_frames = list(folder_path.glob(request.pattern))
    if not sub_frames:
        raise HTTPException(status_code=404, detail=f"No files matching '{request.pattern}' found in {folder_path}")

    # Create job
    job = ProcessingJob(
        file_id=None,  # No single file, processing a folder
        pipeline_id=None,  # Custom pipeline
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue the stack-and-stretch task
    from app.tasks.processing_tasks import stack_and_stretch_task

    stack_and_stretch_task.delay(str(folder_path), request.pattern, request.sigma, request.formats, job.id)

    return StackAndStretchResponse(
        job_id=job.id, status="queued", folder_path=str(folder_path), files_found=len(sub_frames)
    )
