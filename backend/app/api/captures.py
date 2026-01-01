"""API routes for capture history and output files."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.capture_models import CaptureHistory, OutputFile
from app.services.file_transfer_service import FileTransferService

router = APIRouter(prefix="/captures", tags=["captures"])


class CaptureHistoryResponse(BaseModel):
    """Response model for capture history."""

    id: int
    catalog_id: str
    total_exposure_seconds: int
    total_frames: int
    total_sessions: int
    first_captured_at: Optional[datetime] = None
    last_captured_at: Optional[datetime] = None
    status: Optional[str] = None
    suggested_status: Optional[str] = None
    best_fwhm: Optional[float] = None
    best_star_count: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class OutputFileResponse(BaseModel):
    """Response model for output file."""

    id: int
    file_path: str
    file_type: str
    file_size_bytes: int
    catalog_id: str
    catalog_id_confidence: float
    execution_id: Optional[int] = None
    execution_target_id: Optional[int] = None
    exposure_seconds: Optional[int] = None
    filter_name: Optional[str] = None
    temperature_celsius: Optional[float] = None
    gain: Optional[int] = None
    fwhm: Optional[float] = None
    star_count: Optional[int] = None
    observation_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransferResultResponse(BaseModel):
    """Response model for file transfer results."""

    transferred: int
    scanned: int
    errors: int
    skipped: int
    message: str


@router.get("", response_model=List[CaptureHistoryResponse])
async def list_captures(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status (needs_more_data, complete, etc.)"),
    min_exposure_seconds: Optional[int] = Query(None, description="Minimum total exposure seconds"),
    max_exposure_seconds: Optional[int] = Query(None, description="Maximum total exposure seconds"),
):
    """
    List all capture history records.

    Supports filtering by:
    - status: User-controlled status (needs_more_data, complete, etc.)
    - min_exposure_seconds: Minimum total exposure time
    - max_exposure_seconds: Maximum total exposure time

    Returns:
        List of capture history records
    """
    try:
        query = db.query(CaptureHistory)

        # Apply filters
        if status:
            query = query.filter(CaptureHistory.status == status)

        if min_exposure_seconds is not None:
            query = query.filter(CaptureHistory.total_exposure_seconds >= min_exposure_seconds)

        if max_exposure_seconds is not None:
            query = query.filter(CaptureHistory.total_exposure_seconds <= max_exposure_seconds)

        captures = query.order_by(CaptureHistory.last_captured_at.desc()).all()

        return [CaptureHistoryResponse.from_orm(c) for c in captures]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing captures: {str(e)}")


@router.get("/{catalog_id}", response_model=CaptureHistoryResponse)
async def get_capture_by_catalog_id(catalog_id: str, db: Session = Depends(get_db)):
    """
    Get capture history for a specific catalog target.

    Args:
        catalog_id: Target catalog ID (e.g., M31, NGC7000)

    Returns:
        Capture history for the target
    """
    try:
        capture = db.query(CaptureHistory).filter(CaptureHistory.catalog_id == catalog_id).first()

        if not capture:
            raise HTTPException(status_code=404, detail=f"Capture not found for target: {catalog_id}")

        return CaptureHistoryResponse.from_orm(capture)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching capture: {str(e)}")


@router.get("/{catalog_id}/files", response_model=List[OutputFileResponse])
async def get_capture_files(
    catalog_id: str,
    db: Session = Depends(get_db),
    file_type: Optional[str] = Query(None, description="Filter by file type (raw_fits, stacked_fits, jpg, png, tiff)"),
    min_confidence: Optional[float] = Query(None, description="Minimum catalog ID confidence (0.0-1.0)"),
):
    """
    Get all output files for a specific capture target.

    Supports filtering by:
    - file_type: File type (raw_fits, stacked_fits, jpg, png, tiff)
    - min_confidence: Minimum catalog ID fuzzy match confidence

    Args:
        catalog_id: Target catalog ID

    Returns:
        List of output files for the target
    """
    try:
        query = db.query(OutputFile).filter(OutputFile.catalog_id == catalog_id)

        # Apply filters
        if file_type:
            query = query.filter(OutputFile.file_type == file_type)

        if min_confidence is not None:
            query = query.filter(OutputFile.catalog_id_confidence >= min_confidence)

        files = query.order_by(OutputFile.created_at.desc()).all()

        return [OutputFileResponse.from_orm(f) for f in files]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching capture files: {str(e)}")


@router.get("/files/all", response_model=List[OutputFileResponse])
async def list_all_output_files(
    db: Session = Depends(get_db),
    file_type: Optional[str] = Query(None, description="Filter by file type (raw_fits, stacked_fits, jpg, png, tiff)"),
    min_confidence: Optional[float] = Query(None, description="Minimum catalog ID confidence (0.0-1.0)"),
    limit: int = Query(100, description="Maximum number of results (default: 100)", ge=1, le=1000),
    offset: int = Query(0, description="Offset for pagination (default: 0)", ge=0),
):
    """
    List all output files across all targets.

    Supports filtering by:
    - file_type: File type (raw_fits, stacked_fits, jpg, png, tiff)
    - min_confidence: Minimum catalog ID fuzzy match confidence
    - limit: Maximum number of results
    - offset: Pagination offset

    Returns:
        List of output files
    """
    try:
        query = db.query(OutputFile)

        # Apply filters
        if file_type:
            query = query.filter(OutputFile.file_type == file_type)

        if min_confidence is not None:
            query = query.filter(OutputFile.catalog_id_confidence >= min_confidence)

        # Apply pagination
        files = query.order_by(OutputFile.created_at.desc()).offset(offset).limit(limit).all()

        return [OutputFileResponse.from_orm(f) for f in files]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing output files: {str(e)}")


@router.post("/transfer", response_model=TransferResultResponse)
async def trigger_file_transfer(db: Session = Depends(get_db)):
    """
    Trigger file transfer from Seestar.

    This endpoint:
    1. Lists all files from Seestar mount
    2. Transfers them to organized directory structure
    3. Scans transferred files to create OutputFile records
    4. Updates CaptureHistory aggregates

    Returns:
        Results with counts of transferred, scanned, errors, skipped
    """
    try:
        transfer_service = FileTransferService()
        results = transfer_service.transfer_and_scan_all(db)

        message = f"Transferred {results['transferred']} files"
        if results['errors'] > 0:
            message += f" with {results['errors']} errors"
        if results['skipped'] > 0:
            message += f" ({results['skipped']} skipped)"

        return TransferResultResponse(
            transferred=results['transferred'],
            scanned=results['scanned'],
            errors=results['errors'],
            skipped=results['skipped'],
            message=message
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")
