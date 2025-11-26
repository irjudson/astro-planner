"""API routes for the Astro Planner."""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from app.models import (
    PlanRequest, ObservingPlan, DSOTarget, Location, ExportFormat, ScheduledTarget
)
from app.services.planner_service import PlannerService
from app.services.catalog_service import CatalogService
from app.clients.seestar_client import SeestarClient, SeestarState
from app.services.telescope_service import TelescopeService, ExecutionState
from app.services.light_pollution_service import LightPollutionService
from app.database import get_db
from pydantic import BaseModel

# Import comet, asteroid, planet, processing, plans, and astronomy routers
from app.api.comets import router as comet_router
from app.api.asteroids import router as asteroid_router
from app.api.planets import router as planet_router
from app.api.processing import router as processing_router
from app.api.plans import router as plans_router
from app.api.astronomy import router as astronomy_router

router = APIRouter()

# Include comet, asteroid, planet, processing, plans, and astronomy endpoints
router.include_router(comet_router)
router.include_router(asteroid_router)
router.include_router(planet_router)
router.include_router(processing_router)
router.include_router(plans_router)
router.include_router(astronomy_router)

# Telescope control (singleton instances)
seestar_client = SeestarClient()
telescope_service = TelescopeService(seestar_client)

# In-memory storage for shared plans (in production, use Redis or database)
shared_plans: Dict[str, ObservingPlan] = {}

# Request/Response models for telescope endpoints
class TelescopeConnectRequest(BaseModel):
    host: str = "seestar.local"
    port: int = 4700  # Port 4700 for firmware v5.x

class ExecutePlanRequest(BaseModel):
    scheduled_targets: List[ScheduledTarget]
    park_when_done: bool = True  # Default to True (park telescope when complete)


@router.post("/plan", response_model=ObservingPlan)
async def generate_plan(request: PlanRequest, db: Session = Depends(get_db)):
    """
    Generate a complete observing plan.

    This endpoint orchestrates the entire planning process:
    - Calculates twilight times
    - Filters targets by type
    - Fetches weather forecast
    - Schedules targets using greedy algorithm
    - Returns complete plan

    Args:
        request: Plan request with location, date, and constraints

    Returns:
        Complete observing plan with scheduled targets
    """
    try:
        planner = PlannerService(db)
        plan = planner.generate_plan(request)
        return plan
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")


@router.get("/targets", response_model=List[DSOTarget])
async def list_targets(
    db: Session = Depends(get_db),
    object_types: Optional[List[str]] = Query(None, description="Filter by object types (can specify multiple)"),
    min_magnitude: Optional[float] = Query(None, description="Minimum magnitude (brighter objects have lower values)"),
    max_magnitude: Optional[float] = Query(None, description="Maximum magnitude (fainter limit)"),
    constellation: Optional[str] = Query(None, description="Filter by constellation (3-letter abbreviation)"),
    limit: Optional[int] = Query(100, description="Maximum number of results (default: 100, max: 1000)", le=1000),
    offset: int = Query(0, description="Offset for pagination (default: 0)", ge=0)
):
    """
    List available DSO targets with advanced filtering.

    Supports filtering by:
    - Object type (galaxy, nebula, cluster, planetary_nebula)
    - Magnitude range (brightness)
    - Constellation
    - Pagination (limit/offset)

    Examples:
    - /targets?limit=20 - Get 20 brightest objects
    - /targets?object_types=galaxy&object_types=nebula - Get galaxies and nebulae
    - /targets?max_magnitude=10&limit=50 - Get 50 objects brighter than magnitude 10
    - /targets?constellation=Ori - Get all objects in Orion

    Args:
        object_types: Filter by one or more object types
        min_magnitude: Filter by minimum magnitude (brighter)
        max_magnitude: Filter by maximum magnitude (fainter)
        constellation: Filter by constellation
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)

    Returns:
        List of DSO targets matching filters, sorted by brightness
    """
    try:
        catalog = CatalogService(db)
        targets = catalog.filter_targets(
            object_types=object_types,
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            constellation=constellation,
            limit=limit,
            offset=offset
        )
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching targets: {str(e)}")


@router.get("/targets/{catalog_id}", response_model=DSOTarget)
async def get_target(catalog_id: str, db: Session = Depends(get_db)):
    """
    Get details for a specific target.

    Args:
        catalog_id: Catalog identifier (e.g., M31, NGC7000, C80)

    Returns:
        Target details
    """
    catalog = CatalogService(db)
    target = catalog.get_target_by_id(catalog_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target not found: {catalog_id}")
    return target


@router.get("/caldwell", response_model=List[DSOTarget])
async def list_caldwell_targets(
    db: Session = Depends(get_db),
    limit: Optional[int] = Query(109, description="Maximum number of results (default: all 109 Caldwell objects)", le=109),
    offset: int = Query(0, description="Offset for pagination (default: 0)", ge=0)
):
    """
    List all Caldwell catalog targets.

    The Caldwell Catalog is a collection of 109 deep sky objects compiled by
    Sir Patrick Caldwell-Moore for amateur astronomers. These are bright, large
    objects not included in the Messier catalog.

    Args:
        limit: Maximum number of results to return (default: all 109)
        offset: Number of results to skip (for pagination)

    Returns:
        List of Caldwell targets ordered by Caldwell number (C1-C109)
    """
    try:
        catalog = CatalogService(db)
        targets = catalog.get_caldwell_targets(limit=limit, offset=offset)
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Caldwell targets: {str(e)}")


@router.get("/catalog/stats")
async def get_catalog_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the DSO catalog.

    Returns summary information about the catalog including:
    - Total number of objects
    - Count by object type
    - Count by catalog (Messier, NGC, IC, Caldwell)
    - Magnitude distribution

    Returns:
        Catalog statistics dictionary
    """
    try:
        from sqlalchemy import func, case
        from app.models.catalog_models import DSOCatalog

        # Total objects
        total = db.query(func.count(DSOCatalog.id)).scalar()

        # By object type
        by_type_query = db.query(
            DSOCatalog.object_type,
            func.count(DSOCatalog.id)
        ).group_by(DSOCatalog.object_type).order_by(func.count(DSOCatalog.id).desc()).all()
        by_type = {row[0]: row[1] for row in by_type_query}

        # By catalog
        by_catalog_query = db.query(
            DSOCatalog.catalog_name,
            func.count(DSOCatalog.id)
        ).group_by(DSOCatalog.catalog_name).order_by(func.count(DSOCatalog.id).desc()).all()
        by_catalog = {row[0]: row[1] for row in by_catalog_query}

        # Count Caldwell objects
        caldwell_count = db.query(func.count(DSOCatalog.id)).filter(
            DSOCatalog.caldwell_number.isnot(None)
        ).scalar()
        by_catalog["Caldwell"] = caldwell_count

        # Count Messier objects (stored with common_name starting with M)
        messier_count = db.query(func.count(DSOCatalog.id)).filter(
            DSOCatalog.common_name.like('M%')
        ).scalar()
        by_catalog["Messier"] = messier_count

        # Magnitude ranges
        mag_query = db.query(
            func.count(case((DSOCatalog.magnitude <= 5, 1))).label('very_bright'),
            func.count(case(((DSOCatalog.magnitude > 5) & (DSOCatalog.magnitude <= 10), 1))).label('bright'),
            func.count(case(((DSOCatalog.magnitude > 10) & (DSOCatalog.magnitude <= 15), 1))).label('moderate'),
            func.count(case((DSOCatalog.magnitude > 15, 1))).label('faint')
        ).filter(
            DSOCatalog.magnitude.isnot(None),
            DSOCatalog.magnitude < 99
        ).one()

        magnitude_ranges = {
            "<=5.0 (Very Bright)": mag_query.very_bright,
            "5.0-10.0 (Bright)": mag_query.bright,
            "10.0-15.0 (Moderate)": mag_query.moderate,
            ">15.0 (Faint)": mag_query.faint
        }

        return {
            "total_objects": total,
            "by_type": by_type,
            "by_catalog": by_catalog,
            "by_magnitude": magnitude_ranges
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching catalog stats: {str(e)}")


@router.post("/twilight")
async def calculate_twilight(
    location: Location,
    date: str = Query(..., description="ISO date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Calculate twilight times for a specific location and date.

    Args:
        location: Observer location
        date: ISO date string
        db: Database session

    Returns:
        Dictionary of twilight times
    """
    try:
        planner = PlannerService(db)
        twilight_times = planner.calculate_twilight(location, date)
        return twilight_times
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating twilight: {str(e)}")


@router.post("/export")
async def export_plan(
    plan: ObservingPlan,
    format: str = Query(..., description="Export format: json, seestar_plan, seestar_alp, text, csv"),
    db: Session = Depends(get_db)
):
    """
    Export an observing plan in various formats.

    Args:
        plan: Observing plan to export
        format: Export format type
        db: Database session

    Returns:
        Exported plan data
    """
    try:
        planner = PlannerService(db)
        exported_data = planner.exporter.export(plan, format)
        return ExportFormat(format_type=format, data=exported_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting plan: {str(e)}")


@router.post("/share")
async def share_plan(plan: ObservingPlan):
    """
    Save a plan and return a shareable ID.

    Args:
        plan: Observing plan to share

    Returns:
        Shareable plan ID and URL
    """
    try:
        # Generate a short, unique ID
        plan_id = str(uuid.uuid4())[:8]

        # Ensure uniqueness
        while plan_id in shared_plans:
            plan_id = str(uuid.uuid4())[:8]

        # Store the plan
        shared_plans[plan_id] = plan

        return {
            "plan_id": plan_id,
            "share_url": f"/plan/{plan_id}",
            "api_url": f"/api/shared-plans/{plan_id}",
            "message": "Plan saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sharing plan: {str(e)}")


@router.get("/shared-plans/{plan_id}")
async def get_shared_plan(plan_id: str):
    """
    Retrieve a shared plan by ID (temporary in-memory storage).

    This is for sharing plans via short-lived links, not for persistent storage.
    Use /plans endpoints for persistent plan storage.

    Args:
        plan_id: Shareable plan ID

    Returns:
        Observing plan
    """
    if plan_id not in shared_plans:
        raise HTTPException(status_code=404, detail="Plan not found")

    return shared_plans[plan_id]


# ========================================================================
# Telescope Control Endpoints
# ========================================================================

@router.post("/telescope/connect")
async def connect_telescope(request: TelescopeConnectRequest):
    """
    Connect to Seestar S50 telescope.

    Args:
        request: Connection details (host and port)

    Returns:
        Connection status and telescope info
    """
    try:
        await seestar_client.connect(request.host, request.port)
        status = seestar_client.status

        return {
            "connected": True,
            "host": request.host,
            "port": request.port,
            "state": status.state.value,
            "firmware_version": status.firmware_version,
            "message": "Connected to Seestar S50"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.post("/telescope/disconnect")
async def disconnect_telescope():
    """
    Disconnect from telescope.

    Returns:
        Disconnection status
    """
    try:
        await seestar_client.disconnect()
        return {
            "connected": False,
            "message": "Disconnected from telescope"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect failed: {str(e)}")


@router.get("/telescope/status")
async def get_telescope_status():
    """
    Get current telescope status.

    Returns:
        Telescope connection and state information
    """
    status = seestar_client.status

    return {
        "connected": status.connected,
        "state": status.state.value if status.state else "unknown",
        "current_target": status.current_target,
        "firmware_version": status.firmware_version,
        "is_tracking": status.is_tracking,
        "last_update": status.last_update.isoformat() if status.last_update else None,
        "last_error": status.last_error
    }


@router.post("/telescope/execute")
async def execute_plan(request: ExecutePlanRequest):
    """
    Execute an observation plan on the telescope.

    This starts background execution of the provided scheduled targets via Celery.
    Use /telescope/progress to monitor execution.

    Args:
        request: List of scheduled targets to execute

    Returns:
        Execution ID and initial status
    """
    try:
        if not seestar_client.connected:
            raise HTTPException(
                status_code=400,
                detail="Telescope not connected. Connect first using /telescope/connect"
            )

        # Check if there's already an active execution
        from app.models.telescope_models import TelescopeExecution
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            active_execution = db.query(TelescopeExecution).filter(
                TelescopeExecution.state.in_(['starting', 'running'])
            ).first()

            if active_execution:
                raise HTTPException(
                    status_code=400,
                    detail=f"Execution already in progress: {active_execution.execution_id}"
                )
        finally:
            db.close()

        # Generate execution ID
        execution_id = str(uuid.uuid4())[:8]

        # Get telescope connection info
        telescope_host = request.dict().get('telescope_host') or seestar_client.host or '192.168.2.47'
        telescope_port = request.dict().get('telescope_port') or seestar_client.port or 4700

        # Convert targets to dict for Celery serialization
        targets_data = [t.dict() for t in request.scheduled_targets]

        # Start execution via Celery task
        from app.tasks.telescope_tasks import execute_observation_plan_task

        task = execute_observation_plan_task.delay(
            execution_id=execution_id,
            targets_data=targets_data,
            telescope_host=telescope_host,
            telescope_port=telescope_port,
            park_when_done=request.park_when_done
        )

        return {
            "execution_id": execution_id,
            "celery_task_id": task.id,
            "status": "started",
            "total_targets": len(request.scheduled_targets),
            "message": "Execution started. Use /telescope/progress to monitor."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/telescope/progress")
async def get_execution_progress():
    """
    Get current execution progress.

    Returns detailed progress information including:
    - Current execution state
    - Current target being executed
    - Progress percentage
    - Elapsed and estimated remaining time
    - Errors encountered

    Returns:
        Execution progress details
    """
    from app.models.telescope_models import TelescopeExecution
    from app.database import SessionLocal
    from datetime import timedelta

    db = SessionLocal()
    try:
        # Get most recent active or recent execution
        execution = db.query(TelescopeExecution).order_by(
            TelescopeExecution.started_at.desc()
        ).first()

        if not execution:
            return {
                "state": "idle",
                "message": "No execution in progress"
            }

        # Format elapsed time
        elapsed_time = None
        if execution.elapsed_seconds:
            elapsed_time = str(timedelta(seconds=execution.elapsed_seconds))

        # Format estimated remaining time
        estimated_remaining = None
        if execution.estimated_remaining_seconds:
            estimated_remaining = str(timedelta(seconds=execution.estimated_remaining_seconds))

        # Parse error log
        errors = []
        if execution.error_log:
            errors = execution.error_log if isinstance(execution.error_log, list) else []

        return {
            "execution_id": execution.execution_id,
            "state": execution.state,
            "total_targets": execution.total_targets,
            "current_target_index": execution.current_target_index,
            "targets_completed": execution.targets_completed,
            "targets_failed": execution.targets_failed,
            "current_target_name": execution.current_target_name,
            "current_phase": execution.current_phase,
            "progress_percent": round(execution.progress_percent, 1),
            "elapsed_time": elapsed_time,
            "estimated_remaining": estimated_remaining,
            "errors": errors
        }

    finally:
        db.close()


@router.post("/telescope/abort")
async def abort_execution():
    """
    Abort the current execution.

    Stops the current imaging operation and cancels remaining targets.

    Returns:
        Abort status
    """
    try:
        from app.tasks.telescope_tasks import abort_observation_plan_task
        from app.models.telescope_models import TelescopeExecution
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            # Find running execution
            execution = db.query(TelescopeExecution).filter(
                TelescopeExecution.state.in_(['starting', 'running'])
            ).first()

            if not execution:
                raise HTTPException(
                    status_code=400,
                    detail="No execution in progress to abort"
                )

            execution_id = execution.execution_id

        finally:
            db.close()

        # Abort via Celery task
        result = abort_observation_plan_task.delay(execution_id).get(timeout=5)

        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Unknown error aborting execution')
            )

        return {
            "status": "aborted",
            "execution_id": execution_id,
            "message": "Execution aborted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Abort failed: {str(e)}")


@router.post("/telescope/park")
async def park_telescope():
    """
    Park telescope at home position.

    Returns:
        Park status
    """
    try:
        if not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        success = await telescope_service.park_telescope()

        if success:
            return {
                "status": "parking",
                "message": "Telescope parking"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to park telescope"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Park failed: {str(e)}")


@router.get("/telescope/preview")
async def get_telescope_preview():
    """
    Get the latest preview image from telescope.

    This endpoint looks for the most recent stacked JPEG image in the
    telescope's FITS directory. Returns image metadata and access path.

    Returns:
        Preview image information with path for download
    """
    from pathlib import Path
    import os
    from datetime import datetime

    try:
        # Look for recent JPEG files in /fits directory
        fits_root = Path(os.getenv("FITS_DIR", "/fits"))

        if not fits_root.exists():
            return {
                "available": False,
                "message": "Telescope image directory not mounted. Configure FITS_DIR environment variable."
            }

        # Find all JPEG files (Seestar creates preview JPEGs during stacking)
        jpeg_files = []
        for ext in ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']:
            jpeg_files.extend(fits_root.rglob(ext))

        if not jpeg_files:
            return {
                "available": False,
                "message": "No preview images found. Start imaging on the telescope first."
            }

        # Sort by modification time, get most recent
        latest_image = max(jpeg_files, key=lambda p: p.stat().st_mtime)

        # Get file info
        file_stats = latest_image.stat()
        modified_time = datetime.fromtimestamp(file_stats.st_mtime)

        # Return relative path from FITS_DIR for frontend to request
        relative_path = latest_image.relative_to(fits_root)

        return {
            "available": True,
            "filename": latest_image.name,
            "path": str(relative_path),
            "size_bytes": file_stats.st_size,
            "modified_at": modified_time.isoformat(),
            "download_url": f"/api/telescope/preview/download?path={relative_path}",
            "message": f"Latest image from {modified_time.strftime('%H:%M:%S')}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preview: {str(e)}")


@router.get("/telescope/preview/download")
async def download_telescope_preview(path: str = Query(..., description="Relative path to image")):
    """
    Download a specific preview image from telescope storage.

    Args:
        path: Relative path to the image file

    Returns:
        Image file for display
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    import os

    try:
        fits_root = Path(os.getenv("FITS_DIR", "/fits"))

        # Sanitize path to prevent directory traversal
        requested_path = fits_root / path.lstrip("/")
        requested_path = requested_path.resolve()

        # Ensure we're still within FITS_DIR
        if not str(requested_path).startswith(str(fits_root)):
            raise HTTPException(status_code=403, detail="Access denied")

        if not requested_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        if not requested_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Return image with appropriate MIME type
        return FileResponse(
            path=str(requested_path),
            media_type="image/jpeg",
            filename=requested_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download preview: {str(e)}")


@router.get("/sky-quality/{lat}/{lon}")
async def get_sky_quality(lat: float, lon: float, location_name: str = Query("Unknown Location")):
    """
    Get sky quality and light pollution data for a location.

    This endpoint provides comprehensive information about sky quality including:
    - Bortle scale classification (1-9)
    - Sky Quality Meter (SQM) estimate
    - Light pollution level
    - Observing recommendations
    - Suitable target types
    - Naked eye limiting magnitude

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        location_name: Optional location name

    Returns:
        Complete sky quality information
    """
    try:
        # Create location object
        location = Location(
            name=location_name,
            latitude=lat,
            longitude=lon,
            elevation=0.0,  # Not needed for light pollution
            timezone="UTC"  # Not needed for light pollution
        )

        # Get sky quality data
        service = LightPollutionService()
        sky_quality = service.get_sky_quality(location)

        # Get observing recommendations
        recommendations = service.get_observing_recommendations(sky_quality)

        # Return combined data
        return {
            "location": {
                "name": location_name,
                "latitude": lat,
                "longitude": lon
            },
            "bortle_class": sky_quality.bortle_class,
            "bortle_name": sky_quality.bortle_name,
            "sqm_estimate": sky_quality.sqm_estimate,
            "light_pollution_level": sky_quality.light_pollution_level,
            "visibility_description": sky_quality.visibility_description,
            "suitable_for": sky_quality.suitable_for,
            "limiting_magnitude": sky_quality.limiting_magnitude,
            "milky_way_visibility": sky_quality.milky_way_visibility,
            "data_source": sky_quality.light_pollution_source,
            "recommendations": recommendations
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching sky quality: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "astro-planner-api",
        "version": "1.0.0",
        "telescope_connected": seestar_client.connected
    }
