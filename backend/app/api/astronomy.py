"""Astronomy-specific API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.cleardarksky_service import ClearDarkSkyService
from app.services.satellite_service import SatelliteService
from app.services.viewing_months_service import ViewingMonthsService

router = APIRouter(tags=["astronomy"])


# Request/Response Models
class AstronomyWeatherResponse(BaseModel):
    """Response model for astronomy weather forecast."""

    forecast: List[dict]
    location: dict


class SatellitePassResponse(BaseModel):
    """Response model for satellite passes."""

    passes: List[dict]
    satellite_name: str
    location: dict
    days: int


class ViewingMonthsResponse(BaseModel):
    """Response model for viewing months."""

    months: List[dict]
    object_name: Optional[str] = None
    coordinates: dict


# ========================================================================
# ClearDarkSky Weather Endpoint
# ========================================================================


@router.get("/weather/astronomy")
async def get_astronomy_weather(
    lat: float = Query(..., description="Latitude in decimal degrees", ge=-90, le=90),
    lon: float = Query(..., description="Longitude in decimal degrees", ge=-180, le=180),
    hours: int = Query(48, description="Forecast period in hours", ge=1, le=120),
):
    """
    Get astronomy-specific weather forecast for a location.

    This endpoint provides astronomy-focused weather information including:
    - Cloud cover (clear, mostly clear, partly cloudy, etc.)
    - Atmospheric transparency (excellent to poor)
    - Astronomical seeing conditions (excellent to poor)
    - Temperature and wind speed
    - Overall astronomy quality score (0-1)

    Data is sourced from ClearDarkSky when available, with fallback
    to general weather services.

    Args:
        lat: Latitude in decimal degrees (-90 to +90)
        lon: Longitude in decimal degrees (-180 to +180)
        hours: Forecast period in hours (default: 48, max: 120)

    Returns:
        Astronomy weather forecast with conditions and quality scores
    """
    try:
        # Validate coordinates
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail=f"Invalid latitude: {lat}. Must be between -90 and +90.")
        if not (-180 <= lon <= 180):
            raise HTTPException(status_code=400, detail=f"Invalid longitude: {lon}. Must be between -180 and +180.")

        service = ClearDarkSkyService()
        forecast = service.get_forecast(latitude=lat, longitude=lon, hours=hours)

        # Convert forecast objects to dicts
        forecast_data = []
        for entry in forecast:
            forecast_data.append(
                {
                    "time": entry.time.isoformat(),
                    "cloud_cover": {
                        "range": entry.cloud_cover.value,
                        "description": entry.cloud_cover.name.replace("_", " ").title(),
                    },
                    "transparency": entry.transparency.value,
                    "seeing": entry.seeing.value,
                    "temperature_c": entry.temperature_c,
                    "wind_speed_kmh": entry.wind_speed_kmh,
                    "astronomy_score": entry.astronomy_score(),
                }
            )

        return {
            "forecast": forecast_data,
            "location": {"latitude": lat, "longitude": lon},
            "hours": hours,
            "count": len(forecast_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching astronomy weather: {str(e)}")


# ========================================================================
# Satellite Pass Prediction Endpoints
# ========================================================================


@router.get("/satellites/iss")
async def get_iss_passes(
    lat: float = Query(..., description="Latitude in decimal degrees", ge=-90, le=90),
    lon: float = Query(..., description="Longitude in decimal degrees", ge=-180, le=180),
    days: int = Query(10, description="Number of days to predict", ge=1, le=30),
    min_altitude: float = Query(0.0, description="Minimum altitude in degrees", ge=0, le=90),
):
    """
    Get ISS (International Space Station) pass predictions.

    This endpoint provides upcoming visible passes of the ISS for a specific
    location. Each pass includes:
    - Start and end times
    - Maximum altitude and time
    - Start and end azimuth directions
    - Visibility classification (excellent, good, fair, poor)
    - Apparent magnitude (brightness)
    - Quality score (0-1)

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        days: Number of days to predict (default: 10, max: 30)
        min_altitude: Minimum altitude threshold (default: 0)

    Returns:
        List of ISS pass predictions sorted by start time
    """
    try:
        # Validate coordinates
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail=f"Invalid latitude: {lat}. Must be between -90 and +90.")
        if not (-180 <= lon <= 180):
            raise HTTPException(status_code=400, detail=f"Invalid longitude: {lon}. Must be between -180 and +180.")

        service = SatelliteService()
        passes = service.get_iss_passes(latitude=lat, longitude=lon, days=days, min_altitude=min_altitude)

        # Convert pass objects to dicts
        passes_data = []
        for pass_obj in passes:
            passes_data.append(
                {
                    "satellite_name": pass_obj.satellite_name,
                    "start_time": pass_obj.start_time.isoformat(),
                    "end_time": pass_obj.end_time.isoformat(),
                    "max_altitude_deg": pass_obj.max_altitude_deg,
                    "max_altitude_time": pass_obj.max_altitude_time.isoformat(),
                    "start_azimuth_deg": pass_obj.start_azimuth_deg,
                    "end_azimuth_deg": pass_obj.end_azimuth_deg,
                    "visibility": pass_obj.visibility.name.lower(),
                    "magnitude": pass_obj.magnitude,
                    "duration_minutes": pass_obj.duration_minutes(),
                    "quality_score": pass_obj.quality_score(),
                }
            )

        return {
            "passes": passes_data,
            "satellite_name": "ISS (ZARYA)",
            "location": {"latitude": lat, "longitude": lon},
            "days": days,
            "count": len(passes_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ISS passes: {str(e)}")


@router.get("/satellites/passes")
async def get_satellite_passes(
    norad_id: int = Query(..., description="NORAD catalog ID"),
    lat: float = Query(..., description="Latitude in decimal degrees", ge=-90, le=90),
    lon: float = Query(..., description="Longitude in decimal degrees", ge=-180, le=180),
    days: int = Query(10, description="Number of days to predict", ge=1, le=30),
    satellite_name: str = Query("Satellite", description="Display name for satellite"),
    min_altitude: float = Query(0.0, description="Minimum altitude in degrees", ge=0, le=90),
):
    """
    Get pass predictions for any satellite by NORAD ID.

    Args:
        norad_id: NORAD catalog ID (e.g., 25544 for ISS, 20580 for Hubble)
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        days: Number of days to predict
        satellite_name: Display name for the satellite
        min_altitude: Minimum altitude threshold

    Returns:
        List of satellite pass predictions
    """
    try:
        # Validate coordinates
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail=f"Invalid latitude: {lat}. Must be between -90 and +90.")
        if not (-180 <= lon <= 180):
            raise HTTPException(status_code=400, detail=f"Invalid longitude: {lon}. Must be between -180 and +180.")

        service = SatelliteService()
        passes = service.get_satellite_passes(
            norad_id=norad_id,
            satellite_name=satellite_name,
            latitude=lat,
            longitude=lon,
            days=days,
            min_altitude=min_altitude,
        )

        # Convert pass objects to dicts
        passes_data = []
        for pass_obj in passes:
            passes_data.append(
                {
                    "satellite_name": pass_obj.satellite_name,
                    "start_time": pass_obj.start_time.isoformat(),
                    "end_time": pass_obj.end_time.isoformat(),
                    "max_altitude_deg": pass_obj.max_altitude_deg,
                    "max_altitude_time": pass_obj.max_altitude_time.isoformat(),
                    "start_azimuth_deg": pass_obj.start_azimuth_deg,
                    "end_azimuth_deg": pass_obj.end_azimuth_deg,
                    "visibility": pass_obj.visibility.name.lower(),
                    "magnitude": pass_obj.magnitude,
                    "duration_minutes": pass_obj.duration_minutes(),
                    "quality_score": pass_obj.quality_score(),
                }
            )

        return {
            "passes": passes_data,
            "satellite_name": satellite_name,
            "norad_id": norad_id,
            "location": {"latitude": lat, "longitude": lon},
            "days": days,
            "count": len(passes_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching satellite passes: {str(e)}")


# ========================================================================
# Best Viewing Months Endpoints
# ========================================================================


@router.get("/viewing-months")
async def get_viewing_months(
    ra_hours: float = Query(..., description="Right ascension in hours (0-24)", ge=0, lt=24),
    dec_degrees: float = Query(..., description="Declination in degrees (-90 to +90)", ge=-90, le=90),
    latitude: float = Query(..., description="Observer latitude", ge=-90, le=90),
    object_name: Optional[str] = Query(None, description="Optional object name for reference"),
):
    """
    Calculate best viewing months for a celestial object.

    This endpoint calculates month-by-month viewing conditions based on:
    - Object coordinates (RA and Dec)
    - Observer latitude
    - Seasonal night length variations
    - Object altitude at transit
    - Evening visibility

    Each month receives:
    - Rating (excellent, good, fair, poor, not visible)
    - Visibility hours (time above minimum altitude)
    - Best observation time
    - Notes about conditions

    Args:
        ra_hours: Right ascension in hours (0-24)
        dec_degrees: Declination in degrees (-90 to +90)
        latitude: Observer latitude in degrees
        object_name: Optional name for display

    Returns:
        12 months of viewing data with ratings and recommendations
    """
    try:
        # Validate astronomical coordinates
        if not (0 <= ra_hours < 24):
            raise HTTPException(status_code=400, detail=f"Invalid right ascension: {ra_hours}. Must be 0-24 hours.")
        if not (-90 <= dec_degrees <= 90):
            raise HTTPException(
                status_code=400, detail=f"Invalid declination: {dec_degrees}. Must be -90 to +90 degrees."
            )
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail=f"Invalid latitude: {latitude}. Must be -90 to +90 degrees.")

        service = ViewingMonthsService()
        months = service.calculate_viewing_months(
            ra_hours=ra_hours, dec_degrees=dec_degrees, latitude=latitude, object_name=object_name
        )

        # Convert month objects to dicts
        months_data = []
        for month in months:
            months_data.append(
                {
                    "month": month.month,
                    "month_name": month.month_name,
                    "rating": month.rating.name.lower(),
                    "rating_value": month.rating.value,
                    "visibility_hours": month.visibility_hours,
                    "best_time": month.best_time,
                    "notes": month.notes,
                    "is_good_month": month.is_good_month(),
                }
            )

        return {
            "months": months_data,
            "object_name": object_name,
            "coordinates": {"ra_hours": ra_hours, "dec_degrees": dec_degrees},
            "observer_latitude": latitude,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating viewing months: {str(e)}")


@router.get("/viewing-months/summary")
async def get_viewing_months_summary(
    ra_hours: float = Query(..., description="Right ascension in hours (0-24)", ge=0, lt=24),
    dec_degrees: float = Query(..., description="Declination in degrees (-90 to +90)", ge=-90, le=90),
    latitude: float = Query(..., description="Observer latitude", ge=-90, le=90),
    object_name: Optional[str] = Query(None, description="Optional object name"),
):
    """
    Get summary of best viewing months for an object.

    Returns a concise summary including:
    - Best 3 months for observation
    - Peak viewing month
    - Total number of good viewing months
    - Visibility date ranges

    Args:
        ra_hours: Right ascension in hours (0-24)
        dec_degrees: Declination in degrees (-90 to +90)
        latitude: Observer latitude
        object_name: Optional object name

    Returns:
        Summary of viewing conditions across the year
    """
    try:
        # Validate astronomical coordinates
        if not (0 <= ra_hours < 24):
            raise HTTPException(status_code=400, detail=f"Invalid right ascension: {ra_hours}. Must be 0-24 hours.")
        if not (-90 <= dec_degrees <= 90):
            raise HTTPException(
                status_code=400, detail=f"Invalid declination: {dec_degrees}. Must be -90 to +90 degrees."
            )

        service = ViewingMonthsService()
        months = service.calculate_viewing_months(
            ra_hours=ra_hours, dec_degrees=dec_degrees, latitude=latitude, object_name=object_name
        )

        summary = service.get_viewing_summary(months)

        return {
            **summary,
            "object_name": object_name,
            "coordinates": {"ra_hours": ra_hours, "dec_degrees": dec_degrees},
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating viewing summary: {str(e)}")
