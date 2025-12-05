"""API routes for asteroid catalog and visibility."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AsteroidEphemeris, AsteroidTarget, AsteroidVisibility, Location
from app.services.asteroid_service import AsteroidService

router = APIRouter(prefix="/asteroids", tags=["asteroids"])


@router.get("/", response_model=List[AsteroidTarget])
async def list_asteroids(
    limit: Optional[int] = Query(50, description="Maximum number of results", le=500),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    max_magnitude: Optional[float] = Query(None, description="Maximum (faintest) magnitude to include"),
    db: Session = Depends(get_db),
):
    """
    List all asteroids in the catalog.

    Returns a list of asteroids sorted by brightness (brightest first).
    Use limit and offset for pagination.

    Args:
        limit: Maximum number of asteroids to return (default: 50, max: 500)
        offset: Number of asteroids to skip for pagination
        max_magnitude: Only include asteroids brighter than this magnitude

    Returns:
        List of AsteroidTarget objects
    """
    try:
        asteroid_service = AsteroidService(db)
        asteroids = asteroid_service.get_all_asteroids(limit=limit, offset=offset)

        # Filter by magnitude if specified
        if max_magnitude is not None:
            asteroids = [a for a in asteroids if a.current_magnitude and a.current_magnitude <= max_magnitude]

        return asteroids
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing asteroids: {str(e)}")


@router.get("/{designation}", response_model=AsteroidTarget)
async def get_asteroid(designation: str, db: Session = Depends(get_db)):
    """
    Get a specific asteroid by its designation.

    Args:
        designation: Official asteroid designation (e.g., "2000 SG344", "433")

    Returns:
        AsteroidTarget object

    Raises:
        404: Asteroid not found
    """
    try:
        asteroid_service = AsteroidService(db)
        asteroid = asteroid_service.get_asteroid_by_designation(designation)
        if not asteroid:
            raise HTTPException(status_code=404, detail=f"Asteroid {designation} not found")
        return asteroid
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asteroid: {str(e)}")


@router.post("/", response_model=dict, status_code=201)
async def add_asteroid(asteroid: AsteroidTarget = Body(...), db: Session = Depends(get_db)):
    """
    Add a new asteroid to the catalog.

    Requires complete asteroid information including orbital elements.

    Args:
        asteroid: AsteroidTarget object with all required fields

    Returns:
        Dictionary with asteroid_id and designation

    Raises:
        400: Invalid asteroid data
        500: Database error
    """
    try:
        asteroid_service = AsteroidService(db)
        asteroid_id = asteroid_service.add_asteroid(asteroid)
        return {
            "asteroid_id": asteroid_id,
            "designation": asteroid.designation,
            "message": "Asteroid added successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding asteroid: {str(e)}")


@router.post("/{designation}/ephemeris", response_model=AsteroidEphemeris)
async def compute_ephemeris(
    designation: str,
    time_utc: Optional[datetime] = Query(None, description="UTC time for ephemeris (ISO format). Defaults to now."),
    db: Session = Depends(get_db),
):
    """
    Compute ephemeris (position) for an asteroid at a specific time.

    Calculates the asteroid's position, distance, and estimated magnitude.

    Args:
        designation: Asteroid designation
        time_utc: UTC time for computation (defaults to current time)

    Returns:
        AsteroidEphemeris with position, distance, and magnitude

    Raises:
        404: Asteroid not found
    """
    try:
        asteroid_service = AsteroidService(db)
        asteroid = asteroid_service.get_asteroid_by_designation(designation)
        if not asteroid:
            raise HTTPException(status_code=404, detail=f"Asteroid {designation} not found")

        # Use current time if not specified
        if time_utc is None:
            time_utc = datetime.utcnow()

        ephemeris = asteroid_service.compute_ephemeris(asteroid, time_utc)
        return ephemeris
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing ephemeris: {str(e)}")


@router.post("/{designation}/visibility", response_model=AsteroidVisibility)
async def check_visibility(
    designation: str,
    location: Location = Body(...),
    time_utc: Optional[datetime] = Query(None, description="UTC time (ISO format). Defaults to now."),
    db: Session = Depends(get_db),
):
    """
    Check visibility of an asteroid from a specific location and time.

    Computes altitude, azimuth, and provides observability recommendations.

    Args:
        designation: Asteroid designation
        location: Observer location with lat/lon/elevation
        time_utc: UTC time for visibility check (defaults to current time)

    Returns:
        AsteroidVisibility with altitude, azimuth, and recommendations

    Raises:
        404: Asteroid not found
    """
    try:
        asteroid_service = AsteroidService(db)
        asteroid = asteroid_service.get_asteroid_by_designation(designation)
        if not asteroid:
            raise HTTPException(status_code=404, detail=f"Asteroid {designation} not found")

        # Use current time if not specified
        if time_utc is None:
            time_utc = datetime.utcnow()

        visibility = asteroid_service.compute_visibility(asteroid, location, time_utc)
        return visibility
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking visibility: {str(e)}")


@router.post("/visible", response_model=List[AsteroidVisibility])
async def list_visible_asteroids(
    location: Location = Body(...),
    time_utc: Optional[datetime] = Query(None, description="UTC time (ISO format). Defaults to now."),
    min_altitude: float = Query(30.0, description="Minimum altitude in degrees", ge=0, le=90),
    max_magnitude: float = Query(12.0, description="Maximum (faintest) magnitude", ge=0, le=20),
    db: Session = Depends(get_db),
):
    """
    Get all visible asteroids for a location and time.

    Filters asteroids by altitude and magnitude, returns those that are
    above the horizon and meet observability criteria.

    Args:
        location: Observer location
        time_utc: UTC time for visibility check (defaults to current time)
        min_altitude: Minimum altitude in degrees (default: 30°)
        max_magnitude: Maximum magnitude to include (default: 12.0)

    Returns:
        List of AsteroidVisibility objects for observable asteroids,
        sorted by brightness (brightest first)
    """
    try:
        # Use current time if not specified
        if time_utc is None:
            time_utc = datetime.utcnow()

        asteroid_service = AsteroidService(db)
        visible_asteroids = asteroid_service.get_visible_asteroids(
            location=location, time_utc=time_utc, min_altitude=min_altitude, max_magnitude=max_magnitude
        )

        return visible_asteroids
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting visible asteroids: {str(e)}")
