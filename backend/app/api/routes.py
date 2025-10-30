"""API routes for the Astro Planner."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import datetime
import uuid

from app.models import (
    PlanRequest, ObservingPlan, DSOTarget, Location, ExportFormat
)
from app.services.planner_service import PlannerService
from app.services.catalog_service import CatalogService

router = APIRouter()

# Initialize services
planner = PlannerService()
catalog = CatalogService()

# In-memory storage for shared plans (in production, use Redis or database)
shared_plans: Dict[str, ObservingPlan] = {}


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


@router.get("/catalog/stats")
async def get_catalog_stats():
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
        import sqlite3
        from pathlib import Path

        # Get database path
        db_path = catalog.db_path
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Total objects
        cursor.execute("SELECT COUNT(*) FROM dso_catalog")
        total = cursor.fetchone()[0]

        # By object type
        cursor.execute("""
            SELECT object_type, COUNT(*)
            FROM dso_catalog
            GROUP BY object_type
            ORDER BY COUNT(*) DESC
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # By catalog
        cursor.execute("""
            SELECT catalog_name, COUNT(*)
            FROM dso_catalog
            GROUP BY catalog_name
            ORDER BY COUNT(*) DESC
        """)
        by_catalog = {row[0]: row[1] for row in cursor.fetchall()}

        # Magnitude ranges
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN magnitude <= 5 THEN 1 END) as very_bright,
                COUNT(CASE WHEN magnitude > 5 AND magnitude <= 10 THEN 1 END) as bright,
                COUNT(CASE WHEN magnitude > 10 AND magnitude <= 15 THEN 1 END) as moderate,
                COUNT(CASE WHEN magnitude > 15 THEN 1 END) as faint
            FROM dso_catalog
            WHERE magnitude IS NOT NULL AND magnitude < 99
        """)
        mag_row = cursor.fetchone()
        magnitude_ranges = {
            "<=5.0 (Very Bright)": mag_row[0],
            "5.0-10.0 (Bright)": mag_row[1],
            "10.0-15.0 (Moderate)": mag_row[2],
            ">15.0 (Faint)": mag_row[3]
        }

        conn.close()

        return {
            "total_objects": total,
            "by_type": by_type,
            "by_catalog": by_catalog,
            "by_magnitude": magnitude_ranges,
            "database_path": str(db_path)
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
