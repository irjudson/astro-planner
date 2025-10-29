"""API routes for the Astro Planner."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from app.models import (
    PlanRequest, ObservingPlan, DSOTarget, Location, ExportFormat
)
from app.services.planner_service import PlannerService
from app.services.catalog_service import CatalogService

router = APIRouter()

# Initialize services
planner = PlannerService()
catalog = CatalogService()


@router.post("/plan", response_model=ObservingPlan)
async def generate_plan(request: PlanRequest):
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
        plan = planner.generate_plan(request)
        return plan
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")


@router.get("/targets", response_model=List[DSOTarget])
async def list_targets(
    object_type: Optional[str] = Query(None, description="Filter by object type")
):
    """
    List all available DSO targets.

    Args:
        object_type: Optional filter by object type (galaxy, nebula, cluster, planetary_nebula)

    Returns:
        List of DSO targets
    """
    try:
        if object_type:
            targets = catalog.filter_targets([object_type])
        else:
            targets = catalog.get_all_targets()
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching targets: {str(e)}")


@router.get("/targets/{catalog_id}", response_model=DSOTarget)
async def get_target(catalog_id: str):
    """
    Get details for a specific target.

    Args:
        catalog_id: Catalog identifier (e.g., M31, NGC7000)

    Returns:
        Target details
    """
    target = catalog.get_target_by_id(catalog_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target not found: {catalog_id}")
    return target


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
        "version": "1.0.0"
    }
