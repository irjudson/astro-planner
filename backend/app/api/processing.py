"""API endpoints for processing system."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import shutil
import uuid
from datetime import datetime

from app.database import get_db
from app.models.processing_models import (
    ProcessingSession, ProcessingFile, ProcessingPipeline, ProcessingJob
)
from app.tasks.processing_tasks import process_session_task
from pydantic import BaseModel

router = APIRouter(prefix="/process", tags=["processing"])


# Pydantic models for requests/responses
class SessionCreate(BaseModel):
    session_name: str
    observation_plan_id: Optional[int] = None


class SessionResponse(BaseModel):
    id: int
    session_name: str
    status: str
    total_files: int
    total_size_bytes: int
    upload_timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size_bytes: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    pipeline_name: str  # "quick_dso", "export_pixinsight", etc.


class JobResponse(BaseModel):
    id: int
    status: str
    progress_percent: float
    current_step: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    gpu_used: bool

    class Config:
        from_attributes = True


# Processing data directory
import os
PROCESSING_DIR = Path(os.getenv("PROCESSING_DIR", "./data/processing"))
PROCESSING_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new processing session."""
    session = ProcessingSession(
        session_name=session_data.session_name,
        observation_plan_id=session_data.observation_plan_id,
        status="uploading"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create session directory
    session_dir = PROCESSING_DIR / f"session_{session.id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    return session


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all processing sessions."""
    sessions = db.query(ProcessingSession).order_by(
        ProcessingSession.created_at.desc()
    ).offset(skip).limit(limit).all()

    return sessions


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get session details."""
    session = db.query(ProcessingSession).filter(
        ProcessingSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Delete a processing session and all its files."""
    session = db.query(ProcessingSession).filter(
        ProcessingSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get processing base from session metadata
    if session.session_metadata and "processing_base" in session.session_metadata:
        processing_base = Path(session.session_metadata["processing_base"])
    else:
        processing_base = PROCESSING_DIR

    # Delete session directory (which contains all jobs)
    session_dir = processing_base / f"session_{session_id}"
    if session_dir.exists():
        shutil.rmtree(session_dir)

    # Note: Final outputs remain in processing_base directory
    # They are named descriptively and don't collide

    # Delete database records (cascade will handle files and jobs)
    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully"}


@router.post("/sessions/{session_id}/upload")
async def upload_file(
    session_id: int,
    file: UploadFile = File(...),
    file_type: str = Form("stacked"),  # light, dark, flat, bias, stacked
    db: Session = Depends(get_db)
):
    """Upload a file to a processing session."""
    session = db.query(ProcessingSession).filter(
        ProcessingSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Create session directory
    session_dir = PROCESSING_DIR / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = session_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = file_path.stat().st_size

    # Create database record
    processing_file = ProcessingFile(
        session_id=session_id,
        filename=file.filename,
        file_type=file_type,
        file_path=str(file_path),
        file_size_bytes=file_size
    )
    db.add(processing_file)

    # Update session
    session.total_files += 1
    session.total_size_bytes += file_size

    db.commit()

    return {
        "id": processing_file.id,
        "filename": file.filename,
        "file_type": file_type,
        "size_bytes": file_size,
        "message": "File uploaded successfully"
    }


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
            items.append({
                "name": item.name,
                "path": relative_path,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
                "is_fits": item.suffix.lower() in ['.fit', '.fits', '.fit.gz'] if item.is_file() else False
            })

    return {
        "current_path": str(browse_path.relative_to(fits_root)) if browse_path != fits_root else "",
        "items": items
    }


@router.post("/sessions/{session_id}/import")
async def import_file(
    session_id: int,
    file_path: str = Form(...),
    file_type: str = Form("stacked"),
    db: Session = Depends(get_db)
):
    """Import a file from the FITS directory into a session."""
    session = db.query(ProcessingSession).filter(
        ProcessingSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Sanitize and resolve path
    fits_root = Path("/fits")
    source_file = (fits_root / file_path.lstrip("/")).resolve()

    # Security check
    if not str(source_file).startswith(str(fits_root)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not source_file.exists() or not source_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Detect object directory (parent of the FITS file)
    object_dir = source_file.parent

    # Create processing directory inside object directory
    processing_base = object_dir / "astro-planner-processed"
    processing_base.mkdir(parents=True, exist_ok=True)

    # Create session directory under the object's processing directory
    session_dir = processing_base / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Create symlink to original file instead of copying (saves space)
    dest_file = session_dir / source_file.name
    if dest_file.exists():
        dest_file.unlink()
    dest_file.symlink_to(source_file)

    # Store the processing base path for this session
    if not session.session_metadata:
        session.session_metadata = {}
    session.session_metadata["processing_base"] = str(processing_base)

    file_size = dest_file.stat().st_size

    # Create database record
    processing_file = ProcessingFile(
        session_id=session_id,
        filename=source_file.name,
        file_type=file_type,
        file_path=str(dest_file),
        file_size_bytes=file_size
    )
    db.add(processing_file)

    # Update session
    session.total_files += 1
    session.total_size_bytes += file_size

    db.commit()

    return {
        "id": processing_file.id,
        "filename": source_file.name,
        "size_bytes": file_size,
        "message": "File imported successfully"
    }


@router.post("/sessions/{session_id}/finalize")
async def finalize_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Finalize session after all uploads are complete."""
    session = db.query(ProcessingSession).filter(
        ProcessingSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "ready"
    db.commit()

    return {"message": "Session finalized", "session_id": session_id}


@router.post("/sessions/{session_id}/process", response_model=JobResponse)
async def process_session(
    session_id: int,
    job_data: JobCreate,
    db: Session = Depends(get_db)
):
    """Start processing a session with a pipeline."""
    session = db.query(ProcessingSession).filter(
        ProcessingSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get or create pipeline
    pipeline = get_or_create_pipeline(job_data.pipeline_name, db)

    # Create job
    job = ProcessingJob(
        session_id=session_id,
        pipeline_id=pipeline.id,
        status="queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue Celery task
    process_session_task.delay(session_id, pipeline.id, job.id)

    return job


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get job status."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Cancel a running job."""
    from app.tasks.processing_tasks import cancel_job_task

    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Queue cancel task
    cancel_job_task.delay(job_id)

    return {"message": "Job cancellation requested", "job_id": job_id}


@router.get("/jobs/{job_id}/download", response_class=FileResponse)
async def download_job_output(
    job_id: int,
    db: Session = Depends(get_db)
):
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

    return FileResponse(
        path=str(output_file),
        filename=output_file.name,
        media_type="application/octet-stream"
    )


def get_or_create_pipeline(pipeline_name: str, db: Session) -> ProcessingPipeline:
    """Get or create a processing pipeline."""
    # Check if pipeline exists
    pipeline = db.query(ProcessingPipeline).filter(
        ProcessingPipeline.name == pipeline_name,
        ProcessingPipeline.is_preset == True
    ).first()

    if pipeline:
        return pipeline

    # Create built-in pipelines
    if pipeline_name == "quick_dso":
        steps = [
            {
                "step": "histogram_stretch",
                "params": {
                    "algorithm": "auto",
                    "midtones": 0.5
                }
            },
            {
                "step": "export",
                "params": {
                    "format": "jpeg",
                    "quality": 95,
                    "bit_depth": 8
                }
            }
        ]

        pipeline = ProcessingPipeline(
            name="quick_dso",
            description="Quick DSO processing: auto-stretch and JPEG export",
            pipeline_steps=steps,
            is_preset=True
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        return pipeline

    elif pipeline_name == "export_pixinsight":
        steps = [
            {
                "step": "export",
                "params": {
                    "format": "tiff",
                    "bit_depth": 16,
                    "compression": "none"
                }
            }
        ]

        pipeline = ProcessingPipeline(
            name="export_pixinsight",
            description="Export for PixInsight: 16-bit TIFF",
            pipeline_steps=steps,
            is_preset=True
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        return pipeline

    else:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")


# ============================================================================
# SIMPLIFIED DIRECT PROCESSING API (No sessions required)
# ============================================================================

class DirectProcessRequest(BaseModel):
    file_path: str
    processing_type: str  # "quick_preview" or "export_editing"


@router.post("/file", response_model=JobResponse)
async def process_file_direct(
    request: DirectProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process a FITS file directly without creating a session.

    This is the simplified API - just point to a file and process it.

    Processing types:
    - quick_preview: Auto-stretch to JPEG for quick viewing/sharing
    - export_editing: 16-bit TIFF for PixInsight/Photoshop
    """
    # Validate file exists
    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.suffix.lower() in ['.fit', '.fits']:
        raise HTTPException(status_code=400, detail="File must be a FITS file")

    # Map processing type to pipeline
    pipeline_map = {
        "quick_preview": "quick_dso",
        "export_editing": "export_pixinsight"
    }

    pipeline_name = pipeline_map.get(request.processing_type)
    if not pipeline_name:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid processing_type. Use: {list(pipeline_map.keys())}"
        )

    # Get or create pipeline
    pipeline = get_or_create_pipeline(pipeline_name, db)

    # Create a minimal session (for backward compatibility)
    session = ProcessingSession(
        session_name=f"direct_{file_path.stem}_{int(datetime.now().timestamp())}",
        status="ready",
        total_files=1,
        total_size_bytes=file_path.stat().st_size
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Create file record
    processing_file = ProcessingFile(
        session_id=session.id,
        filename=file_path.name,
        file_type="stacked",
        file_path=str(file_path),
        file_size_bytes=file_path.stat().st_size
    )
    db.add(processing_file)
    db.commit()

    # Create job
    job = ProcessingJob(
        session_id=session.id,
        pipeline_id=pipeline.id,
        status="queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue task
    process_session_task.delay(session.id, pipeline.id, job.id)

    return job
