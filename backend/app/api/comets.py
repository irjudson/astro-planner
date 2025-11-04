"""API routes for comet catalog and visibility."""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from datetime import datetime

from app.models import (
    CometTarget,
    CometEphemeris,
    CometVisibility,
    Location,
)
from app.services.comet_service import CometService
from app.services.horizons_service import HorizonsService

router = APIRouter(prefix="/comets", tags=["comets"])

# Initialize services
comet_service = CometService()
horizons_service = HorizonsService()


@router.get("/", response_model=List[CometTarget])
async def list_comets(
    limit: Optional[int] = Query(50, description="Maximum number of results", le=500),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    max_magnitude: Optional[float] = Query(None, description="Maximum (faintest) magnitude to include")
):
    """
    List all comets in the catalog.

    Returns a list of comets sorted by brightness (brightest first).
    Use limit and offset for pagination.

    Args:
        limit: Maximum number of comets to return (default: 50, max: 500)
        offset: Number of comets to skip for pagination
        max_magnitude: Only include comets brighter than this magnitude

    Returns:
        List of CometTarget objects
    """
    try:
        comets = comet_service.get_all_comets(limit=limit, offset=offset)

        # Filter by magnitude if specified
        if max_magnitude is not None:
            comets = [c for c in comets if c.current_magnitude and c.current_magnitude <= max_magnitude]

        return comets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing comets: {str(e)}")


@router.get("/{designation}", response_model=CometTarget)
async def get_comet(designation: str):
    """
    Get a specific comet by its designation.

    Args:
        designation: Official comet designation (e.g., "C/2020 F3", "1P")

    Returns:
        CometTarget object

    Raises:
        404: Comet not found
    """
    try:
        comet = comet_service.get_comet_by_designation(designation)
        if not comet:
            raise HTTPException(status_code=404, detail=f"Comet {designation} not found")
        return comet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving comet: {str(e)}")


@router.post("/", response_model=dict, status_code=201)
async def add_comet(comet: CometTarget = Body(...)):
    """
    Add a new comet to the catalog.

    Requires complete comet information including orbital elements.

    Args:
        comet: CometTarget object with all required fields

    Returns:
        Dictionary with comet_id and designation

    Raises:
        400: Invalid comet data
        500: Database error
    """
    try:
        comet_id = comet_service.add_comet(comet)
        return {
            "comet_id": comet_id,
            "designation": comet.designation,
            "message": "Comet added successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding comet: {str(e)}")


@router.post("/{designation}/ephemeris", response_model=CometEphemeris)
async def compute_ephemeris(
    designation: str,
    time_utc: Optional[datetime] = Query(None, description="UTC time for ephemeris (ISO format). Defaults to now.")
):
    """
    Compute ephemeris (position) for a comet at a specific time.

    Calculates the comet's position, distance, and estimated magnitude.

    Args:
        designation: Comet designation
        time_utc: UTC time for computation (defaults to current time)

    Returns:
        CometEphemeris with position, distance, and magnitude

    Raises:
        404: Comet not found
    """
    try:
        comet = comet_service.get_comet_by_designation(designation)
        if not comet:
            raise HTTPException(status_code=404, detail=f"Comet {designation} not found")

        # Use current time if not specified
        if time_utc is None:
            time_utc = datetime.utcnow()

        ephemeris = comet_service.compute_ephemeris(comet, time_utc)
        return ephemeris
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing ephemeris: {str(e)}")


@router.post("/{designation}/visibility", response_model=CometVisibility)
async def check_visibility(
    designation: str,
    location: Location = Body(...),
    time_utc: Optional[datetime] = Query(None, description="UTC time (ISO format). Defaults to now.")
):
    """
    Check visibility of a comet from a specific location and time.

    Computes altitude, azimuth, and provides observability recommendations.

    Args:
        designation: Comet designation
        location: Observer location with lat/lon/elevation
        time_utc: UTC time for visibility check (defaults to current time)

    Returns:
        CometVisibility with altitude, azimuth, and recommendations

    Raises:
        404: Comet not found
    """
    try:
        comet = comet_service.get_comet_by_designation(designation)
        if not comet:
            raise HTTPException(status_code=404, detail=f"Comet {designation} not found")

        # Use current time if not specified
        if time_utc is None:
            time_utc = datetime.utcnow()

        visibility = comet_service.compute_visibility(comet, location, time_utc)
        return visibility
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking visibility: {str(e)}")


@router.post("/visible", response_model=List[CometVisibility])
async def list_visible_comets(
    location: Location = Body(...),
    time_utc: Optional[datetime] = Query(None, description="UTC time (ISO format). Defaults to now."),
    min_altitude: float = Query(30.0, description="Minimum altitude in degrees", ge=0, le=90),
    max_magnitude: float = Query(12.0, description="Maximum (faintest) magnitude", ge=0, le=20)
):
    """
    Get all visible comets for a location and time.

    Filters comets by altitude and magnitude, returns those that are
    above the horizon and meet observability criteria.

    Args:
        location: Observer location
        time_utc: UTC time for visibility check (defaults to current time)
        min_altitude: Minimum altitude in degrees (default: 30°)
        max_magnitude: Maximum magnitude to include (default: 12.0)

    Returns:
        List of CometVisibility objects for observable comets,
        sorted by brightness (brightest first)
    """
    try:
        # Use current time if not specified
        if time_utc is None:
            time_utc = datetime.utcnow()

        visible_comets = comet_service.get_visible_comets(
            location=location,
            time_utc=time_utc,
            min_altitude=min_altitude,
            max_magnitude=max_magnitude
        )

        return visible_comets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting visible comets: {str(e)}")


@router.post("/import", response_model=dict, status_code=201)
async def import_comet_from_horizons(
    designation: str = Query(..., description="Comet designation (e.g., 'C/2020 F3', '1P/Halley')"),
    epoch: Optional[datetime] = Query(None, description="Epoch for orbital elements (defaults to current time)")
):
    """
    Import a comet from JPL Horizons and add it to the catalog.

    Fetches orbital elements from JPL Horizons system and stores the comet
    in the local catalog for faster access.

    Args:
        designation: Comet designation (e.g., "C/2020 F3", "1P/Halley")
        epoch: Optional epoch for orbital elements (defaults to current time)

    Returns:
        Dictionary with comet_id, designation, and success message

    Raises:
        404: Comet not found in JPL Horizons
        409: Comet already exists in catalog
        500: Import error
    """
    try:
        # Check if comet already exists
        existing = comet_service.get_comet_by_designation(designation)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Comet {designation} already exists in catalog. Use PUT to update."
            )

        # Fetch from Horizons
        comet = horizons_service.fetch_comet_by_designation(designation, epoch)

        if not comet:
            raise HTTPException(
                status_code=404,
                detail=f"Comet {designation} not found in JPL Horizons database"
            )

        # Add to local catalog
        comet_id = comet_service.add_comet(comet)

        return {
            "comet_id": comet_id,
            "designation": comet.designation,
            "name": comet.name,
            "comet_type": comet.comet_type,
            "current_magnitude": comet.current_magnitude,
            "message": f"Successfully imported {designation} from JPL Horizons"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing comet: {str(e)}")


@router.get("/search/bright", response_model=List[CometTarget])
async def search_bright_comets(
    max_magnitude: float = Query(12.0, description="Maximum magnitude to include", ge=0, le=20),
    epoch: Optional[datetime] = Query(None, description="Epoch for orbital elements")
):
    """
    Search for currently bright comets using JPL Horizons.

    Queries JPL Horizons for a curated list of known comets and returns
    those that are currently bright enough to observe.

    Note: This queries a predefined list of well-known comets. For a complete
    list of all visible comets, use a dedicated comet discovery service.

    Args:
        max_magnitude: Maximum (faintest) magnitude to include (default: 12.0)
        epoch: Epoch for orbital elements (defaults to current time)

    Returns:
        List of bright comets sorted by magnitude (brightest first)
    """
    try:
        comets = horizons_service.fetch_bright_comets(
            max_magnitude=max_magnitude,
            epoch=epoch
        )

        # Sort by brightness
        comets.sort(key=lambda c: c.current_magnitude if c.current_magnitude else 99.0)

        return comets

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for bright comets: {str(e)}")
