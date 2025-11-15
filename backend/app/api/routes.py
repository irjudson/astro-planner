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
from app.database import get_db
from pydantic import BaseModel

# Import comet, asteroid, planet, and processing routers
from app.api.comets import router as comet_router
from app.api.asteroids import router as asteroid_router
from app.api.planets import router as planet_router
from app.api.processing import router as processing_router

router = APIRouter()

# Include comet, asteroid, planet, and processing endpoints
router.include_router(comet_router)
router.include_router(asteroid_router)
router.include_router(planet_router)
router.include_router(processing_router)

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
        catalog_id: Catalog identifier (e.g., M31, NGC7000)

    Returns:
        Target details
    """
    catalog = CatalogService(db)
    target = catalog.get_target_by_id(catalog_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target not found: {catalog_id}")
    return target


@router.get("/catalog/stats")
async def get_catalog_stats(db: Session = Depends(get_db)):
    """
    Get statistics about the DSO catalog.

    Returns summary information about the catalog including:
    - Total number of objects
    - Count by object type
    - Count by catalog (Messier, NGC, IC)
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
async def calculate_twilight(location: Location, date: str = Query(..., description="ISO date (YYYY-MM-DD)")):
    """
    Calculate twilight times for a specific location and date.

    Args:
        location: Observer location
        date: ISO date string

    Returns:
        Dictionary of twilight times
    """
    try:
        twilight_times = planner.calculate_twilight(location, date)
        return twilight_times
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating twilight: {str(e)}")


@router.post("/export")
async def export_plan(plan: ObservingPlan, format: str = Query(..., description="Export format: json, seestar_plan, seestar_alp, text, csv")):
    """
    Export an observing plan in various formats.

    Args:
        plan: Observing plan to export
        format: Export format type

    Returns:
        Exported plan data
    """
    try:
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
            "message": "Plan saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sharing plan: {str(e)}")


@router.get("/plans/{plan_id}")
async def get_shared_plan(plan_id: str):
    """
    Retrieve a shared plan by ID.

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

    This starts background execution of the provided scheduled targets.
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

        if telescope_service.execution_state not in [
            ExecutionState.IDLE,
            ExecutionState.COMPLETED,
            ExecutionState.ABORTED,
            ExecutionState.ERROR
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Execution already in progress: {telescope_service.execution_state.value}"
            )

        # Generate execution ID
        execution_id = str(uuid.uuid4())[:8]

        # Start execution in background
        import asyncio
        asyncio.create_task(
            telescope_service.execute_plan(
                execution_id=execution_id,
                targets=request.scheduled_targets,
                park_when_done=request.park_when_done
            )
        )

        return {
            "execution_id": execution_id,
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
    progress = telescope_service.progress

    if not progress:
        return {
            "state": telescope_service.execution_state.value,
            "message": "No execution in progress"
        }

    return {
        "execution_id": progress.execution_id,
        "state": progress.state.value,
        "total_targets": progress.total_targets,
        "current_target_index": progress.current_target_index,
        "targets_completed": progress.targets_completed,
        "targets_failed": progress.targets_failed,
        "current_target_name": progress.current_target_name,
        "current_phase": progress.current_phase,
        "progress_percent": round(progress.progress_percent, 1),
        "elapsed_time": str(progress.elapsed_time) if progress.elapsed_time else None,
        "estimated_remaining": str(progress.estimated_remaining) if progress.estimated_remaining else None,
        "estimated_end_time": progress.estimated_end_time.isoformat() if progress.estimated_end_time else None,
        "errors": [
            {
                "timestamp": err.timestamp.isoformat(),
                "target": err.target_name,
                "phase": err.phase,
                "message": err.error_message,
                "retries": err.retry_count
            }
            for err in progress.errors
        ]
    }


@router.post("/telescope/abort")
async def abort_execution():
    """
    Abort the current execution.

    Stops the current imaging operation and cancels remaining targets.

    Returns:
        Abort status
    """
    try:
        await telescope_service.abort_execution()
        return {
            "status": "aborted",
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
