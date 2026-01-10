"""API routes for the Astro Planner."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.asteroids import router as asteroid_router
from app.api.astronomy import router as astronomy_router
from app.api.captures import router as captures_router

# Import comet, asteroid, planet, processing, plans, astronomy, and settings routers
from app.api.comets import router as comet_router
from app.api.planets import router as planet_router
from app.api.plans import router as plans_router
from app.api.processing import router as processing_router
from app.api.settings import router as settings_router
from app.api.telescope_features import router as telescope_features_router
from app.api.user_preferences import router as user_preferences_router
from app.clients.seestar_client import SeestarClient
from app.database import get_db
from app.models import DSOTarget, ExportFormat, Location, ObservingPlan, PlanRequest, ScheduledTarget
from app.models.settings_models import SeestarDevice
from app.services.catalog_service import CatalogService
from app.services.light_pollution_service import LightPollutionService
from app.services.planner_service import PlannerService

router = APIRouter()

router.include_router(comet_router)
router.include_router(asteroid_router)
router.include_router(planet_router)
router.include_router(processing_router)
router.include_router(plans_router)
router.include_router(astronomy_router)
router.include_router(settings_router)
router.include_router(captures_router)
router.include_router(telescope_features_router, prefix="/telescope/features", tags=["telescope-features"])
router.include_router(user_preferences_router, prefix="/user", tags=["user"])

# Telescope control (singleton seestar client instance)
seestar_client: Optional[SeestarClient] = None

# In-memory storage for shared plans (in production, use Redis or database)
shared_plans: Dict[str, ObservingPlan] = {}

# Simple TTL cache for catalog queries (cache_key -> (result, expiry_time))
catalog_cache: Dict[str, tuple[Any, float]] = {}
CATALOG_CACHE_TTL = 60  # seconds


# Request/Response models for telescope endpoints
class TelescopeConnectRequest(BaseModel):
    host: Optional[str] = None  # Optional: can specify host directly
    port: Optional[int] = None  # Optional: can specify port directly
    device_id: Optional[int] = None  # Optional: or specify device_id to load from database


class ExecutePlanRequest(BaseModel):
    scheduled_targets: List[ScheduledTarget]
    park_when_done: bool = True  # Default to True (park telescope when complete)
    saved_plan_id: Optional[int] = None  # Optional: link execution to saved plan


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
    offset: int = Query(0, description="Offset for pagination (default: 0)", ge=0),
    include_visibility: bool = Query(True, description="Include real-time visibility calculations"),
    sort_by: str = Query("magnitude", description="Sort order: magnitude|size|name|visibility"),
):
    """
    List available DSO targets with advanced filtering, sorting, and optional visibility.

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
    - /targets?sort_by=visibility&include_visibility=true - Get objects sorted by visibility

    Args:
        object_types: Filter by one or more object types
        min_magnitude: Filter by minimum magnitude (brighter)
        max_magnitude: Filter by maximum magnitude (fainter)
        constellation: Filter by constellation
        limit: Maximum number of results to return
        offset: Number of results to skip (for pagination)
        include_visibility: Calculate real-time visibility (requires location in settings)
        sort_by: Sort order (magnitude, size, name, visibility)

    Returns:
        List of DSO targets matching filters with optional visibility info
    """
    try:
        from datetime import datetime

        import pytz

        from app.services.ephemeris_service import EphemerisService
        from app.services.settings_service import SettingsService

        catalog_service = CatalogService(db)

        # Get filtered targets (without pagination to allow sorting)
        targets = catalog_service.filter_targets(
            object_types=object_types,
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            constellation=constellation,
            limit=None,  # Get all for sorting, then paginate
            offset=0,
        )

        # Performance optimization: Only calculate visibility for ALL targets if sorting by visibility
        # Otherwise, sort first, paginate, then calculate visibility only for paginated results
        if sort_by == "visibility" and include_visibility:
            # Performance: When sorting by visibility, limit to brightest 500 targets first
            # This avoids expensive ephemeris calculations on 1000+ faint objects
            # Sort by magnitude first to get the brightest candidates
            targets.sort(key=lambda t: t.magnitude)

            # Take only brightest 500 targets for visibility calculations
            # This is a reasonable tradeoff: most visible objects are bright anyway
            max_visibility_calc = 500
            targets_for_visibility = targets[:max_visibility_calc]

            try:
                settings_service = SettingsService(db)
                location = settings_service.get_location()

                if location:
                    ephemeris = EphemerisService()
                    current_time = datetime.now(pytz.timezone(location.timezone))

                    # Add visibility to each target (only brightest 500)
                    targets_for_visibility = [
                        catalog_service.add_visibility_info(target, location, ephemeris, current_time)
                        for target in targets_for_visibility
                    ]
            except Exception as e:
                # If visibility fails, continue without it
                print(f"Warning: Could not calculate visibility: {e}")

            # Sort by: optimal now > visible > rising > setting > below horizon
            # Within each group, sort by altitude
            def visibility_sort_key(t):
                if not t.visibility:
                    return (999, -999)  # No visibility - sort last

                status_order = {"visible": 0, "rising": 1, "setting": 2, "below_horizon": 3}
                status_rank = status_order.get(t.visibility.status, 999)

                # Within status, prefer higher altitude
                alt = t.visibility.current_altitude

                return (status_rank, -alt)

            targets_for_visibility.sort(key=visibility_sort_key)

            # Apply pagination after sorting by visibility
            paginated = targets_for_visibility[offset : offset + limit] if limit else targets_for_visibility[offset:]

        else:
            # Sort by non-visibility fields first (no visibility calculation needed)
            if sort_by == "magnitude":
                targets.sort(key=lambda t: t.magnitude)
            elif sort_by == "size":
                targets.sort(key=lambda t: t.size_arcmin, reverse=True)
            elif sort_by == "name":
                targets.sort(key=lambda t: t.catalog_id)

            # Apply pagination BEFORE calculating visibility (performance optimization)
            paginated = targets[offset : offset + limit] if limit else targets[offset:]

            # Now add visibility only to the paginated results
            if include_visibility:
                try:
                    settings_service = SettingsService(db)
                    location = settings_service.get_location()

                    if location:
                        ephemeris = EphemerisService()
                        current_time = datetime.now(pytz.timezone(location.timezone))

                        # Add visibility to each paginated target
                        paginated = [
                            catalog_service.add_visibility_info(target, location, ephemeris, current_time)
                            for target in paginated
                        ]
                except Exception as e:
                    # If visibility fails, continue without it
                    print(f"Warning: Could not calculate visibility: {e}")

        # Add capture history for all paginated targets (single efficient query)
        try:
            from app.models.capture_models import CaptureHistory

            # Extract catalog IDs from paginated targets
            catalog_ids = [target.catalog_id for target in paginated]

            # Fetch all capture history in ONE query (not N+1)
            if catalog_ids:
                try:
                    capture_histories = (
                        db.query(CaptureHistory).filter(CaptureHistory.catalog_id.in_(catalog_ids)).all()
                    )

                    # Create a dictionary mapping catalog_id -> capture history data
                    capture_dict = {
                        ch.catalog_id: {
                            "total_exposure_seconds": ch.total_exposure_seconds,
                            "total_frames": ch.total_frames,
                            "total_sessions": ch.total_sessions,
                            "first_captured_at": ch.first_captured_at.isoformat() if ch.first_captured_at else None,
                            "last_captured_at": ch.last_captured_at.isoformat() if ch.last_captured_at else None,
                            "status": ch.status,
                            "suggested_status": ch.suggested_status,
                            "best_fwhm": ch.best_fwhm,
                            "best_star_count": ch.best_star_count,
                        }
                        for ch in capture_histories
                    }

                    # Merge capture history into each target using model_copy for immutability
                    paginated = [
                        (
                            target.model_copy(update={"capture_history": capture_dict[target.catalog_id]})
                            if target.catalog_id in capture_dict
                            else target
                        )
                        for target in paginated
                    ]
                except Exception as query_error:
                    # If session is in failed transaction, just continue without capture history
                    # This can happen if visibility calculation fails first
                    print(f"Warning: Could not fetch capture history: {query_error}")
        except Exception as e:
            # Outer exception handler
            print(f"Warning: Capture history processing failed: {e}")

        return paginated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching targets: {str(e)}")


@router.get("/targets/scored", response_model=List[DSOTarget])
async def list_scored_targets(
    db: Session = Depends(get_db),
    context: str = Query("tonight", description="Context for scoring: 'tonight' or 'plan'"),
    plan_id: Optional[int] = Query(None, description="Plan ID (required if context='plan')"),
    object_types: Optional[List[str]] = Query(None, description="Filter by object types"),
    limit: int = Query(100, description="Maximum number of results", le=1000),
    offset: int = Query(0, description="Offset for pagination", ge=0),
):
    """
    Get catalog targets scored and sorted by scheduler algorithm.

    This endpoint uses the same scoring logic as the planner to rank targets
    by their suitability for observation. Supports two context modes:

    - 'tonight': Score targets for tonight's observing window at saved location
    - 'plan': Score targets using parameters from a saved plan

    Args:
        context: Scoring context ('tonight' or 'plan')
        plan_id: Saved plan ID (required if context='plan')
        object_types: Filter by object types
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of targets sorted by scheduler score (best first)
    """
    try:
        from datetime import datetime, timedelta

        import pytz

        from app.models.plan_models import SavedPlan
        from app.services.ephemeris_service import EphemerisService
        from app.services.scheduler_service import SchedulerService
        from app.services.settings_service import SettingsService
        from app.services.weather_service import WeatherService

        # Validate context
        if context not in ["tonight", "plan"]:
            raise HTTPException(status_code=400, detail="context must be 'tonight' or 'plan'")

        if context == "plan" and not plan_id:
            raise HTTPException(status_code=400, detail="plan_id required when context='plan'")

        catalog_service = CatalogService(db)
        settings_service = SettingsService(db)
        scheduler = SchedulerService()

        # Build scoring context based on mode
        if context == "tonight":
            # Use saved location + tonight's window
            location = settings_service.get_location()
            if not location:
                raise HTTPException(status_code=400, detail="No location configured in settings")

            tz = pytz.timezone(location.timezone)
            now = datetime.now(tz)

            # Calculate tonight's twilight times
            ephemeris = EphemerisService()
            twilight_times = ephemeris.calculate_twilight_times(location, now)

            scoring_start = twilight_times["astronomical_twilight_end"]
            scoring_end = twilight_times["astronomical_twilight_start"]

            # Use default constraints
            from app.models import ObservingConstraints

            constraints = ObservingConstraints()

        else:  # context == "plan"
            # Load plan and extract context
            plan_record = db.query(SavedPlan).filter(SavedPlan.id == plan_id).first()
            if not plan_record:
                raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

            # Reconstruct plan from saved data
            from app.models import ObservingPlan

            plan = ObservingPlan(**plan_record.plan_data)

            location = plan.location
            scoring_start = plan.session.imaging_start
            scoring_end = plan.session.imaging_end

            # Use constraints from request (or defaults if plan doesn't have them)
            from app.models import ObservingConstraints

            constraints = ObservingConstraints()  # TODO: Extract from plan if stored

        # Get candidate targets with filters
        targets = catalog_service.filter_targets(
            object_types=object_types,
            max_magnitude=12.0,  # Same limit as planner
            limit=500,  # Reasonable pool for scoring
            offset=0,
        )

        # Score each target using scheduler algorithm
        weather_service = WeatherService()
        weather_forecasts = weather_service.get_forecast(location, scoring_start, scoring_end)

        scored_targets = []
        for target in targets:
            # Check if visible during scoring window
            mid_time = scoring_start + (scoring_end - scoring_start) / 2
            if not scheduler.ephemeris.is_target_visible(
                target, location, mid_time, constraints.min_altitude, constraints.max_altitude
            ):
                continue

            # Calculate visibility duration
            duration = scheduler._calculate_visibility_duration(
                target, location, scoring_start, scoring_end, constraints
            )

            if duration < timedelta(minutes=scheduler.settings.min_target_duration_minutes):
                continue

            # Get weather score
            weather_score = scheduler._get_weather_score_for_time(mid_time, weather_forecasts)

            # Score the target
            score_data = scheduler._score_target(target, location, mid_time, duration, constraints, weather_score)

            # Store score in target (for sorting)
            target_with_score = target.model_copy()
            # We can't add a score field to DSOTarget, so we'll just sort by the score
            scored_targets.append((target_with_score, score_data.total_score))

        # Sort by score descending
        scored_targets.sort(key=lambda x: x[1], reverse=True)

        # Apply pagination
        paginated = [t for t, _ in scored_targets[offset : offset + limit]]

        return paginated

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error scoring targets: {str(e)}")


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
    limit: Optional[int] = Query(
        109, description="Maximum number of results (default: all 109 Caldwell objects)", le=109
    ),
    offset: int = Query(0, description="Offset for pagination (default: 0)", ge=0),
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


@router.get("/catalog/search")
async def search_catalog(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by object name or catalog ID"),
    type: Optional[str] = Query(None, description="Filter by object type"),
    constellation: Optional[str] = Query(None, description="Filter by constellation"),
    max_magnitude: Optional[float] = Query(None, description="Maximum magnitude (fainter limit)"),
    sort_by: str = Query("name", description="Sort by: name, magnitude, or type"),
    page: int = Query(1, description="Page number (1-indexed)", ge=1),
    page_size: int = Query(20, description="Items per page", ge=1, le=100),
):
    """
    Search and filter catalog objects for discovery workflow.

    This endpoint is specifically designed for the catalog search interface,
    providing paginated results with search and filter capabilities.

    Args:
        search: Free text search (matches object name or catalog ID)
        type: Object type filter (galaxy, nebula, cluster, etc.)
        constellation: Constellation filter (3-letter abbreviation)
        max_magnitude: Maximum magnitude filter
        sort_by: Sort field (name, magnitude, type)
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated catalog search results
    """
    try:
        import time

        from sqlalchemy import func, or_

        from app.models.catalog_models import DSOCatalog

        # Create cache key from query parameters
        cache_key = f"catalog:{search}:{type}:{constellation}:{max_magnitude}:{sort_by}:{page}:{page_size}"

        # Check cache
        if cache_key in catalog_cache:
            cached_result, expiry = catalog_cache[cache_key]
            if time.time() < expiry:
                return cached_result
            else:
                # Remove expired entry
                del catalog_cache[cache_key]

        # Build query with filters (do NOT call .all() yet!)
        query = db.query(DSOCatalog)

        # Apply type filter
        if type:
            query = query.filter(DSOCatalog.object_type == type)

        # Apply constellation filter
        if constellation:
            query = query.filter(DSOCatalog.constellation == constellation)

        # Apply magnitude filter
        if max_magnitude:
            query = query.filter(DSOCatalog.magnitude <= max_magnitude)

        # Apply search filter using SQL ILIKE for case-insensitive search
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    DSOCatalog.common_name.ilike(search_pattern),
                    func.concat(DSOCatalog.catalog_name, DSOCatalog.catalog_number).ilike(search_pattern),
                )
            )

        # Get total count BEFORE pagination (efficient - just counts, doesn't fetch rows)
        total = query.count()

        # Apply sorting using SQL ORDER BY
        if sort_by == "magnitude":
            query = query.order_by(DSOCatalog.magnitude.asc().nullslast())
        elif sort_by == "type":
            query = query.order_by(DSOCatalog.object_type.asc())
        else:  # name (default)
            query = query.order_by(DSOCatalog.catalog_name.asc(), DSOCatalog.catalog_number.asc())

        # Apply pagination using SQL LIMIT/OFFSET
        offset = (page - 1) * page_size
        paginated_results = query.limit(page_size).offset(offset).all()

        # Convert ONLY the paginated results to response format
        catalog_service = CatalogService(db)
        items = []
        for dso in paginated_results:
            target = catalog_service._db_row_to_target(dso)
            # Get constellation details
            constellation_details = catalog_service._get_constellation_details(dso.constellation)

            items.append(
                {
                    "id": target.catalog_id,
                    "name": target.name,
                    "common_name": dso.common_name,  # Include common_name from database
                    "type": target.object_type,
                    "constellation": dso.constellation,
                    "constellation_full": (
                        constellation_details["full_name"] if constellation_details else dso.constellation
                    ),
                    "constellation_common": constellation_details["common_name"] if constellation_details else None,
                    "magnitude": target.magnitude,
                    "ra": target.ra_hours * 15,  # Convert hours to degrees
                    "dec": target.dec_degrees,
                    "size": f"{target.size_arcmin:.1f}'" if target.size_arcmin and target.size_arcmin > 1 else None,
                }
            )

        result = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

        # Cache the result
        catalog_cache[cache_key] = (result, time.time() + CATALOG_CACHE_TTL)

        return result

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error searching catalog: {str(e)}")


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
        from sqlalchemy import case, func

        from app.models.catalog_models import DSOCatalog

        # Total objects
        total = db.query(func.count(DSOCatalog.id)).scalar()

        # By object type
        by_type_query = (
            db.query(DSOCatalog.object_type, func.count(DSOCatalog.id))
            .group_by(DSOCatalog.object_type)
            .order_by(func.count(DSOCatalog.id).desc())
            .all()
        )
        by_type = {row[0]: row[1] for row in by_type_query}

        # By catalog
        by_catalog_query = (
            db.query(DSOCatalog.catalog_name, func.count(DSOCatalog.id))
            .group_by(DSOCatalog.catalog_name)
            .order_by(func.count(DSOCatalog.id).desc())
            .all()
        )
        by_catalog = {row[0]: row[1] for row in by_catalog_query}

        # Count Caldwell objects
        caldwell_count = db.query(func.count(DSOCatalog.id)).filter(DSOCatalog.caldwell_number.isnot(None)).scalar()
        by_catalog["Caldwell"] = caldwell_count

        # Count Messier objects (stored with common_name starting with M)
        messier_count = db.query(func.count(DSOCatalog.id)).filter(DSOCatalog.common_name.like("M%")).scalar()
        by_catalog["Messier"] = messier_count

        # Magnitude ranges
        mag_query = (
            db.query(
                func.count(case((DSOCatalog.magnitude <= 5, 1))).label("very_bright"),
                func.count(case(((DSOCatalog.magnitude > 5) & (DSOCatalog.magnitude <= 10), 1))).label("bright"),
                func.count(case(((DSOCatalog.magnitude > 10) & (DSOCatalog.magnitude <= 15), 1))).label("moderate"),
                func.count(case((DSOCatalog.magnitude > 15, 1))).label("faint"),
            )
            .filter(DSOCatalog.magnitude.isnot(None), DSOCatalog.magnitude < 99)
            .one()
        )

        magnitude_ranges = {
            "<=5.0 (Very Bright)": mag_query.very_bright,
            "5.0-10.0 (Bright)": mag_query.bright,
            "10.0-15.0 (Moderate)": mag_query.moderate,
            ">15.0 (Faint)": mag_query.faint,
        }

        return {"total_objects": total, "by_type": by_type, "by_catalog": by_catalog, "by_magnitude": magnitude_ranges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching catalog stats: {str(e)}")


@router.post("/twilight")
async def calculate_twilight(
    location: Location, date: str = Query(..., description="ISO date (YYYY-MM-DD)"), db: Session = Depends(get_db)
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
    db: Session = Depends(get_db),
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
            "message": "Plan saved successfully",
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
async def connect_telescope(request: TelescopeConnectRequest, db: Session = Depends(get_db)):
    """
    Connect to Seestar telescope.

    Can connect either by:
    1. Specifying device_id (loads configuration from database)
    2. Specifying host and port directly

    Args:
        request: Connection details (device_id OR host/port)
        db: Database session

    Returns:
        Connection status and telescope info
    """
    global seestar_client

    try:
        # Determine which device to connect to
        if request.device_id is not None:
            # Load device from database
            device = db.query(SeestarDevice).filter(SeestarDevice.id == request.device_id).first()
            if not device:
                raise HTTPException(status_code=404, detail=f"Device {request.device_id} not found")

            if not device.is_control_enabled:
                raise HTTPException(
                    status_code=400, detail=f"Device '{device.name}' control is not enabled. Enable in settings first."
                )

            host = device.control_host
            port = device.control_port

        elif request.host is not None:
            host = request.host
            port = request.port or 4700

        else:
            raise HTTPException(status_code=400, detail="Must provide either device_id or host parameter")

        # Create client and connect
        seestar_client = SeestarClient()
        success = await seestar_client.connect(host, port)

        if not success:
            seestar_client = None  # Reset on failure
            raise HTTPException(status_code=500, detail="Connection failed")

        return {
            "connected": True,
            "host": host,
            "port": port,
            "state": seestar_client.status.state.value,
            "firmware_version": seestar_client.status.firmware_version,
            "message": f"Connected to Seestar at {host}:{port}",
        }
    except HTTPException:
        seestar_client = None  # Reset on any error
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        seestar_client = None  # Reset on any error
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.post("/telescope/disconnect")
async def disconnect_telescope():
    """
    Disconnect from telescope.

    Returns:
        Disconnection status
    """
    global seestar_client

    try:
        if seestar_client is None:
            return {"connected": False, "message": "No telescope connected"}

        await seestar_client.disconnect()
        seestar_client = None

        return {"connected": False, "message": "Disconnected from telescope"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect failed: {str(e)}")


@router.get("/telescope/status")
async def get_telescope_status():
    """
    Get current telescope status.

    Returns:
        Telescope connection and state information
    """
    if seestar_client is None:
        return {
            "connected": False,
            "state": "disconnected",
            "message": "No telescope connected",
        }

    try:
        # Actively poll telescope to keep connection alive
        # This sends get_device_state command which acts as a keepalive
        await seestar_client.get_device_state()

        status = seestar_client.status

        return {
            "connected": status.connected,
            "state": status.state.value if status.state else "unknown",
            "firmware_version": status.firmware_version,
            "is_tracking": status.is_tracking,
            "current_target": status.current_target,
            "current_ra_hours": status.current_ra_hours,
            "current_dec_degrees": status.current_dec_degrees,
            "last_error": status.last_error,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


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
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(
                status_code=400, detail="Telescope not connected. Connect first using /telescope/connect"
            )

        # Check if there's already an active execution
        from app.database import SessionLocal
        from app.models.telescope_models import TelescopeExecution

        db = SessionLocal()
        try:
            active_execution = (
                db.query(TelescopeExecution).filter(TelescopeExecution.state.in_(["starting", "running"])).first()
            )

            if active_execution:
                raise HTTPException(
                    status_code=400, detail=f"Execution already in progress: {active_execution.execution_id}"
                )
        finally:
            db.close()

        # Generate execution ID
        execution_id = str(uuid.uuid4())[:8]

        # Get telescope connection info
        telescope_host = request.dict().get("telescope_host") or seestar_client.host or "192.168.2.47"
        telescope_port = request.dict().get("telescope_port") or seestar_client.port or 4700

        # Convert targets to dict for Celery serialization
        targets_data = [t.dict() for t in request.scheduled_targets]

        # Start execution via Celery task
        from app.tasks.telescope_tasks import execute_observation_plan_task

        task = execute_observation_plan_task.delay(
            execution_id=execution_id,
            targets_data=targets_data,
            telescope_host=telescope_host,
            telescope_port=telescope_port,
            park_when_done=request.park_when_done,
            saved_plan_id=request.saved_plan_id,
        )

        return {
            "execution_id": execution_id,
            "celery_task_id": task.id,
            "status": "started",
            "total_targets": len(request.scheduled_targets),
            "message": "Execution started. Use /telescope/progress to monitor.",
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
    from datetime import timedelta

    from app.database import SessionLocal
    from app.models.telescope_models import TelescopeExecution

    db = SessionLocal()
    try:
        # Get most recent active or recent execution
        execution = db.query(TelescopeExecution).order_by(TelescopeExecution.started_at.desc()).first()

        if not execution:
            return {"state": "idle", "message": "No execution in progress"}

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
            "errors": errors,
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
        from app.database import SessionLocal
        from app.models.telescope_models import TelescopeExecution
        from app.tasks.telescope_tasks import abort_observation_plan_task

        db = SessionLocal()
        try:
            # Find running execution
            execution = (
                db.query(TelescopeExecution).filter(TelescopeExecution.state.in_(["starting", "running"])).first()
            )

            if not execution:
                raise HTTPException(status_code=400, detail="No execution in progress to abort")

            execution_id = execution.execution_id

        finally:
            db.close()

        # Abort via Celery task
        result = abort_observation_plan_task.delay(execution_id).get(timeout=5)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error aborting execution"))

        return {"status": "aborted", "execution_id": execution_id, "message": "Execution aborted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Abort failed: {str(e)}")


@router.post("/telescope/unpark")
async def unpark_telescope():
    """
    Unpark/open telescope and make ready for observing.

    Returns:
        Unpark status
    """
    try:
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        # Call unpark if available, otherwise try to wake up the telescope
        if hasattr(seestar_client, "unpark"):
            success = await seestar_client.unpark()
        else:
            # Fallback: Some telescopes might not have explicit unpark
            # For Seestar, we can issue a status check which wakes it up
            status = seestar_client.status
            success = status.connected

        if success:
            return {"status": "active", "message": "Telescope unparked and ready"}
        else:
            return {"status": "error", "message": "Failed to unpark telescope"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unpark failed: {str(e)}")


@router.post("/telescope/park")
async def park_telescope():
    """
    Park telescope at home position.

    Returns:
        Park status
    """
    try:
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        success = await seestar_client.park()

        if success:
            return {"status": "parking", "message": "Telescope parking"}
        else:
            return {"status": "error", "message": "Failed to park telescope"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Park failed: {str(e)}")


@router.post("/telescope/goto")
async def goto_coordinates(request: dict):
    """
    Slew telescope to RA/Dec coordinates.

    Args:
        request: {"ra": float (hours), "dec": float (degrees), "target_name": str (optional)}

    Returns:
        Goto status
    """
    try:
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        ra = request.get("ra")
        dec = request.get("dec")
        target_name = request.get("target_name", "Manual Target")

        if ra is None or dec is None:
            raise HTTPException(status_code=400, detail="Must provide ra and dec coordinates")

        success = await seestar_client.goto_target(ra, dec, target_name)

        if success:
            return {"status": "slewing", "message": f"Slewing to RA={ra}, Dec={dec}"}
        else:
            return {"status": "error", "message": "Failed to start goto"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Goto failed: {str(e)}")


@router.post("/telescope/stop-slew")
async def stop_slew():
    """
    Stop current slew/goto operation.

    Returns:
        Stop status
    """
    try:
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        success = await seestar_client.stop_slew()

        if success:
            return {"status": "stopped", "message": "Slew stopped"}
        else:
            return {"status": "error", "message": "Failed to stop slew"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop slew failed: {str(e)}")


@router.post("/telescope/start-imaging")
async def start_imaging(request: dict = None):
    """
    Start imaging/stacking.

    Args:
        request: {"restart": bool (optional, default True)}

    Returns:
        Imaging status
    """
    try:
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        restart = True if request is None else request.get("restart", True)

        success = await seestar_client.start_imaging(restart=restart)

        if success:
            return {"status": "imaging", "message": "Imaging started"}
        else:
            return {"status": "error", "message": "Failed to start imaging"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Start imaging failed: {str(e)}")


@router.post("/telescope/stop-imaging")
async def stop_imaging():
    """
    Stop current imaging/stacking.

    Returns:
        Stop status
    """
    try:
        if seestar_client is None or not seestar_client.connected:
            raise HTTPException(status_code=400, detail="Telescope not connected")

        success = await seestar_client.stop_imaging()

        if success:
            return {"status": "stopped", "message": "Imaging stopped"}
        else:
            return {"status": "error", "message": "Failed to stop imaging"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stop imaging failed: {str(e)}")


@router.get("/telescope/preview")
async def get_telescope_preview():
    """
    Get the latest preview image from telescope.

    This endpoint looks for the most recent stacked JPEG image in the
    telescope's FITS directory. Returns image metadata and access path.

    Returns:
        Preview image information with path for download
    """
    import os
    from pathlib import Path

    try:
        # Look for recent JPEG files in /fits directory
        fits_root = Path(os.getenv("FITS_DIR", "/fits"))

        if not fits_root.exists():
            return {
                "available": False,
                "message": "Telescope image directory not mounted. Configure FITS_DIR environment variable.",
            }

        # Find all JPEG files (Seestar creates preview JPEGs during stacking)
        jpeg_files = []
        for ext in ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG"]:
            jpeg_files.extend(fits_root.rglob(ext))

        if not jpeg_files:
            return {"available": False, "message": "No preview images found. Start imaging on the telescope first."}

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
            "message": f"Latest image from {modified_time.strftime('%H:%M:%S')}",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preview: {str(e)}")


@router.get("/telescope/preview/latest")
async def get_latest_preview():
    """
    Get the latest preview image from telescope as raw image bytes.

    This endpoint returns the most recent JPEG image directly for display
    in the live preview panel. Polls this endpoint to get updated images.

    Returns:
        Latest preview image (JPEG bytes)
    """
    import os
    from pathlib import Path

    from fastapi.responses import Response

    try:
        # Look for recent JPEG files in /fits directory
        fits_root = Path(os.getenv("FITS_DIR", "/fits"))

        if not fits_root.exists():
            raise HTTPException(status_code=503, detail="Telescope image directory not mounted")

        # Find all JPEG files (Seestar creates preview JPEGs during stacking)
        jpeg_files = []
        for ext in ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG"]:
            jpeg_files.extend(fits_root.rglob(ext))

        if not jpeg_files:
            raise HTTPException(status_code=404, detail="No preview images available. Start imaging first.")

        # Sort by modification time, get most recent
        latest_image = max(jpeg_files, key=lambda p: p.stat().st_mtime)

        # Read and return image bytes
        image_bytes = latest_image.read_bytes()

        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest preview: {str(e)}")


@router.get("/telescope/preview/download")
async def download_telescope_preview(path: str = Query(..., description="Relative path to image")):
    """
    Download a specific preview image from telescope storage.

    Args:
        path: Relative path to the image file

    Returns:
        Image file for display
    """
    import os
    from pathlib import Path

    from fastapi.responses import FileResponse

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
        return FileResponse(path=str(requested_path), media_type="image/jpeg", filename=requested_path.name)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download preview: {str(e)}")


# NOTE: This endpoint is disabled while transitioning to adapter pattern
# It provided direct access to SeestarClient methods which doesn't fit the adapter abstraction
# Telescope-specific commands should be implemented as proper adapter methods
#
# @router.post("/telescope/command/{command}")
# async def execute_telescope_command(command: str, params: Optional[Dict[str, Any]] = None):
#     """Generic telescope command proxy (DISABLED)."""
#     raise HTTPException(status_code=501, detail="Generic command endpoint not implemented with adapter pattern")


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
            timezone="UTC",  # Not needed for light pollution
        )

        # Get sky quality data
        service = LightPollutionService()
        sky_quality = service.get_sky_quality(location)

        # Get observing recommendations
        recommendations = service.get_observing_recommendations(sky_quality)

        # Return combined data
        return {
            "location": {"name": location_name, "latitude": lat, "longitude": lon},
            "bortle_class": sky_quality.bortle_class,
            "bortle_name": sky_quality.bortle_name,
            "sqm_estimate": sky_quality.sqm_estimate,
            "light_pollution_level": sky_quality.light_pollution_level,
            "visibility_description": sky_quality.visibility_description,
            "suitable_for": sky_quality.suitable_for,
            "limiting_magnitude": sky_quality.limiting_magnitude,
            "milky_way_visibility": sky_quality.milky_way_visibility,
            "data_source": sky_quality.light_pollution_source,
            "recommendations": recommendations,
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
        "service": "astronomus-api",
        "version": "1.0.0",
        "telescope_connected": seestar_client is not None and seestar_client.connected,
    }


@router.get("/images/previews/{filename}")
async def get_preview_image(filename: str):
    """
    Serve cached preview image.

    Args:
        filename: Image filename

    Returns:
        Image file
    """
    try:
        cache_dir = Path(os.getenv("IMAGE_CACHE_DIR", "/app/data/previews"))
        image_path = cache_dir / filename

        # Sanitize path to prevent directory traversal
        image_path = image_path.resolve()
        if not str(image_path).startswith(str(cache_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        return FileResponse(
            path=str(image_path),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=2592000"},  # Cache for 30 days
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving image: {str(e)}")


@router.get("/images/targets/{sanitized_catalog_id}")
async def get_target_preview(sanitized_catalog_id: str, db: Session = Depends(get_db)):
    """
    Fetch or serve preview image for a target by catalog ID.
    This endpoint fetches images on-demand to avoid blocking plan generation.

    Args:
        sanitized_catalog_id: Sanitized catalog ID (spaces/slashes replaced with underscores)
        db: Database session

    Returns:
        Image file (JPEG)
    """
    try:
        from app.services.catalog_service import CatalogService
        from app.services.image_preview_service import ImagePreviewService

        # Parse catalog ID to find target in database
        # Catalog IDs are like: M31, NGC224, IC434, C80
        catalog_service = CatalogService(db)

        target = None

        # Try to parse catalog ID format
        import logging
        import re

        logger = logging.getLogger(__name__)

        # Match patterns like M31, NGC224, IC434, C80
        match = re.match(r"([A-Z]+)(\d+)", sanitized_catalog_id)
        if match:
            catalog_name = match.group(1)
            catalog_number = int(match.group(2))

            logger.info(f"Looking up target: {catalog_name}{catalog_number}")

            # Query database for this specific catalog entry
            from app.models.catalog_models import DSOCatalog

            # Handle special cases
            if catalog_name == "M":
                # Messier objects - find by common_name starting with M
                dso = db.query(DSOCatalog).filter(DSOCatalog.common_name.like(f"M%{catalog_number:03d}")).first()
            elif catalog_name == "C":
                # Caldwell objects - find by caldwell_number
                dso = db.query(DSOCatalog).filter(DSOCatalog.caldwell_number == catalog_number).first()
            else:
                # NGC, IC, etc. - find by catalog_name and catalog_number
                dso = (
                    db.query(DSOCatalog)
                    .filter(DSOCatalog.catalog_name == catalog_name, DSOCatalog.catalog_number == catalog_number)
                    .first()
                )
                logger.info(f"DSO query result for {catalog_name}{catalog_number}: {dso is not None}")

            if dso:
                target = catalog_service._db_row_to_target(dso)
                logger.info(f"Successfully created target for {sanitized_catalog_id}")
        else:
            logger.warning(f"Failed to parse catalog ID: {sanitized_catalog_id}")

        if not target:
            logger.warning(f"Target not found: {sanitized_catalog_id}")
            raise HTTPException(status_code=404, detail=f"Target not found: {sanitized_catalog_id}")

        # Use image preview service to get or fetch image
        image_service = ImagePreviewService(db=db)
        cache_filename = f"{sanitized_catalog_id}.jpg"
        cache_dir = Path(os.getenv("IMAGE_CACHE_DIR", "/app/data/previews"))

        # Ensure cache directory exists
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_path = cache_dir / cache_filename

        # Check cache first
        if cache_path.exists():
            return FileResponse(
                path=str(cache_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=2592000"},
            )

        # Fetch from multi-source service (this will cache it)
        image_data = image_service._fetch_from_skyview(target)
        if image_data:
            cache_path.write_bytes(image_data)
            return FileResponse(
                path=str(cache_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=2592000"},
            )

        # If fetch failed, return 404
        raise HTTPException(status_code=404, detail="Image not available")

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching target image: {str(e)}")
