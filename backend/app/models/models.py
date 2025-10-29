"""Data models for the Astro Planner application."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Observatory location information."""
    name: str = Field(default="Three Forks, MT", description="Location name")
    latitude: float = Field(description="Latitude in degrees (-90 to 90)")
    longitude: float = Field(description="Longitude in degrees (-180 to 180)")
    elevation: float = Field(default=1234.0, description="Elevation in meters")
    timezone: str = Field(default="America/Denver", description="IANA timezone")


class ObservingConstraints(BaseModel):
    """Constraints for observing session."""
    min_altitude: float = Field(default=30.0, ge=0, le=90, description="Minimum altitude in degrees")
    max_altitude: float = Field(default=80.0, ge=0, le=90, description="Maximum altitude in degrees")
    setup_time_minutes: int = Field(default=15, ge=0, description="Setup time in minutes")
    object_types: List[str] = Field(default=["galaxy", "nebula", "cluster", "planetary_nebula"],
                                    description="Object types to include")


class PlanRequest(BaseModel):
    """Request to generate an observing plan."""
    location: Location
    observing_date: str = Field(description="ISO date for observing session (YYYY-MM-DD)")
    constraints: ObservingConstraints = Field(default_factory=ObservingConstraints)


class DSOTarget(BaseModel):
    """Deep sky object target information."""
    name: str = Field(description="Object name")
    catalog_id: str = Field(description="Catalog identifier (M, NGC, IC)")
    object_type: str = Field(description="Object type (galaxy, nebula, etc.)")
    ra_hours: float = Field(description="Right ascension in hours")
    dec_degrees: float = Field(description="Declination in degrees")
    magnitude: float = Field(description="Visual magnitude")
    size_arcmin: float = Field(description="Approximate size in arcminutes")
    description: Optional[str] = Field(default=None, description="Object description")


class TargetScore(BaseModel):
    """Scoring components for a target."""
    visibility_score: float = Field(ge=0, le=1, description="Visibility score (0-1)")
    weather_score: float = Field(ge=0, le=1, description="Weather score (0-1)")
    object_score: float = Field(ge=0, le=1, description="Object suitability score (0-1)")
    total_score: float = Field(ge=0, le=1, description="Combined total score (0-1)")


class ScheduledTarget(BaseModel):
    """A target scheduled in the observing plan."""
    target: DSOTarget
    start_time: datetime = Field(description="Start time (local timezone)")
    end_time: datetime = Field(description="End time (local timezone)")
    duration_minutes: int = Field(description="Duration in minutes")
    start_altitude: float = Field(description="Altitude at start in degrees")
    end_altitude: float = Field(description="Altitude at end in degrees")
    start_azimuth: float = Field(description="Azimuth at start in degrees")
    end_azimuth: float = Field(description="Azimuth at end in degrees")
    field_rotation_rate: float = Field(description="Field rotation rate in deg/min")
    recommended_exposure: int = Field(description="Recommended exposure time in seconds")
    recommended_frames: int = Field(description="Recommended number of frames")
    score: TargetScore


class WeatherForecast(BaseModel):
    """Weather forecast information."""
    timestamp: datetime
    cloud_cover: float = Field(ge=0, le=100, description="Cloud cover percentage")
    humidity: float = Field(ge=0, le=100, description="Humidity percentage")
    temperature: float = Field(description="Temperature in Celsius")
    wind_speed: float = Field(ge=0, description="Wind speed in m/s")
    conditions: str = Field(description="Weather conditions description")


class SessionInfo(BaseModel):
    """Information about the observing session."""
    observing_date: str = Field(description="Date of observing session")
    sunset: datetime = Field(description="Sunset time")
    civil_twilight_end: datetime = Field(description="Civil twilight end")
    nautical_twilight_end: datetime = Field(description="Nautical twilight end")
    astronomical_twilight_end: datetime = Field(description="Astronomical twilight end")
    astronomical_twilight_start: datetime = Field(description="Astronomical twilight start")
    nautical_twilight_start: datetime = Field(description="Nautical twilight start")
    civil_twilight_start: datetime = Field(description="Civil twilight start")
    sunrise: datetime = Field(description="Sunrise time")
    imaging_start: datetime = Field(description="Imaging start time (after setup)")
    imaging_end: datetime = Field(description="Imaging end time")
    total_imaging_minutes: int = Field(description="Total imaging time in minutes")


class ObservingPlan(BaseModel):
    """Complete observing plan for a session."""
    session: SessionInfo
    location: Location
    scheduled_targets: List[ScheduledTarget]
    weather_forecast: List[WeatherForecast]
    total_targets: int = Field(description="Total number of targets")
    coverage_percent: float = Field(description="Percentage of night covered")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExportFormat(BaseModel):
    """Export format configuration."""
    format_type: str = Field(description="Export format: json, seestar_alp, text, csv")
    data: str = Field(description="Exported data as string")
