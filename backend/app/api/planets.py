"""API endpoints for planet information and ephemeris."""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime

from app.models import (
    Location,
    PlanetTarget,
    PlanetEphemeris,
    PlanetVisibility
)
from app.services.planet_service import PlanetService

router = APIRouter(prefix="/planets", tags=["planets"])

# Initialize planet service
planet_service = PlanetService()


@router.get("/", response_model=List[PlanetTarget])
async def list_planets():
    """
    List all major planets plus Moon and Sun.

    Returns static information about the 8 major planets, Moon, and Sun including:
    - Physical properties (diameter, rotation period)
    - Orbital properties (orbital period)
    - Special features (rings, number of moons)
    - Observing notes

    Returns:
        List of all 8 major planets
    """
    try:
        planets = planet_service.get_all_planets()
        return planets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing planets: {str(e)}")


@router.get("/{planet_name}", response_model=PlanetTarget)
async def get_planet(planet_name: str):
    """
    Get information about a specific planet.

    Args:
        planet_name: Planet name (case-insensitive)
                    Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune

    Returns:
        Planet information

    Raises:
        404: Planet not found
    """
    try:
        planet = planet_service.get_planet_by_name(planet_name)
        if not planet:
            raise HTTPException(status_code=404, detail=f"Planet not found: {planet_name}")
        return planet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving planet: {str(e)}")


@router.post("/{planet_name}/ephemeris", response_model=PlanetEphemeris)
async def compute_ephemeris(
    planet_name: str,
    time_utc: datetime = Query(..., description="UTC time for ephemeris (ISO format)")
):
    """
    Compute ephemeris (position and properties) for a planet at a specific time.

    Uses Astropy's built-in planetary ephemeris (based on JPL data) to compute:
    - Right ascension and declination (J2000)
    - Distance from Earth
    - Visual magnitude
    - Angular diameter
    - Phase percentage (illuminated fraction)
    - Solar elongation
    - Phase angle

    Args:
        planet_name: Planet name (case-insensitive)
        time_utc: UTC time for computation

    Returns:
        Planet ephemeris with computed position and properties

    Raises:
        400: Invalid planet name
        500: Computation error
    """
    try:
        ephemeris = planet_service.compute_ephemeris(planet_name, time_utc)
        return ephemeris
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing ephemeris: {str(e)}")


@router.post("/{planet_name}/visibility", response_model=PlanetVisibility)
async def compute_visibility(
    planet_name: str,
    location: Location,
    time_utc: datetime = Query(..., description="UTC time for visibility check")
):
    """
    Compute visibility of a planet from a specific location at a specific time.

    Calculates:
    - Altitude and azimuth in local sky
    - Whether planet is above horizon
    - Whether it's daytime (Sun above horizon)
    - Solar elongation check
    - Recommended observing flag
    - Rise and set times

    Special handling for Venus and Mercury:
    - Can be observed during twilight/daytime if bright enough
    - Venus can be visible during daytime when magnitude < -3

    Args:
        planet_name: Planet name
        location: Observer location (lat, lon, elevation)
        time_utc: UTC time for visibility

    Returns:
        Planet visibility information including altitude, rise/set times

    Raises:
        400: Invalid planet name
        500: Computation error
    """
    try:
        visibility = planet_service.compute_visibility(planet_name, location, time_utc)
        return visibility
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing visibility: {str(e)}")


@router.post("/visible", response_model=List[PlanetVisibility])
async def get_visible_planets(
    location: Location,
    time_utc: datetime = Query(..., description="UTC time for visibility check"),
    min_altitude: float = Query(0.0, description="Minimum altitude in degrees (default: 0 = horizon)"),
    include_daytime: bool = Query(False, description="Include planets visible during daytime (e.g., Venus)")
):
    """
    Get all planets currently visible from a location.

    Useful for:
    - "What planets can I see right now?"
    - Planning planetary observations
    - Finding bright planets during twilight

    Filters planets by:
    - Above horizon (altitude > min_altitude)
    - Optionally exclude daytime observations
    - Solar elongation sufficient for observation

    Results sorted by altitude (highest first).

    Args:
        location: Observer location
        time_utc: UTC time for visibility
        min_altitude: Minimum altitude in degrees (default: 0)
        include_daytime: Whether to include daytime-visible planets like Venus

    Returns:
        List of visible planets sorted by altitude

    Example:
        POST /api/planets/visible?time_utc=2025-03-15T02:00:00&min_altitude=20
        {
            "latitude": 45.9183,
            "longitude": -111.5433,
            "elevation": 1234,
            "timezone": "America/Denver"
        }
    """
    try:
        visible_planets = planet_service.get_visible_planets(
            location=location,
            time_utc=time_utc,
            min_altitude=min_altitude,
            include_daytime=include_daytime
        )
        return visible_planets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding visible planets: {str(e)}")
