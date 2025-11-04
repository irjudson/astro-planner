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
    max_altitude: float = Field(default=90.0, ge=0, le=90, description="Maximum altitude in degrees")
    setup_time_minutes: int = Field(default=30, ge=0, description="Setup time in minutes")
    object_types: List[str] = Field(default=["galaxy", "nebula", "cluster", "planetary_nebula"],
                                    description="Object types to include")
    planning_mode: str = Field(default="balanced", description="Planning mode: balanced, quality, or quantity")


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


class OrbitalElements(BaseModel):
    """Keplerian orbital elements for a comet."""
    epoch_jd: float = Field(description="Epoch of elements (Julian Date)")
    perihelion_distance_au: float = Field(description="Perihelion distance in AU")
    eccentricity: float = Field(description="Orbital eccentricity")
    inclination_deg: float = Field(description="Inclination in degrees")
    arg_perihelion_deg: float = Field(description="Argument of perihelion (ω) in degrees")
    ascending_node_deg: float = Field(description="Longitude of ascending node (Ω) in degrees")
    perihelion_time_jd: float = Field(description="Time of perihelion passage (Julian Date)")


class CometTarget(BaseModel):
    """Comet target information."""
    designation: str = Field(description="Official designation (e.g., C/2020 F3)")
    name: Optional[str] = Field(default=None, description="Common name (e.g., NEOWISE)")
    orbital_elements: OrbitalElements = Field(description="Orbital elements")
    absolute_magnitude: Optional[float] = Field(default=None, description="Absolute magnitude H")
    magnitude_slope: float = Field(default=4.0, description="Magnitude slope parameter")
    current_magnitude: Optional[float] = Field(default=None, description="Current estimated magnitude")
    comet_type: Optional[str] = Field(default=None, description="Type: short-period, long-period, hyperbolic")
    activity_status: Optional[str] = Field(default=None, description="Activity status: active, inactive, unknown")
    discovery_date: Optional[str] = Field(default=None, description="Discovery date (ISO)")
    data_source: Optional[str] = Field(default="manual", description="Data source: MPC, JPL, manual")
    notes: Optional[str] = Field(default=None, description="Observing notes")


class CometEphemeris(BaseModel):
    """Ephemeris (computed position) for a comet at a specific time."""
    designation: str = Field(description="Comet designation")
    date_utc: datetime = Field(description="UTC date/time of ephemeris")
    date_jd: float = Field(description="Julian Date")
    ra_hours: float = Field(description="Right ascension in hours")
    dec_degrees: float = Field(description="Declination in degrees")
    geo_distance_au: float = Field(description="Distance from Earth in AU")
    helio_distance_au: float = Field(description="Distance from Sun in AU")
    magnitude: Optional[float] = Field(default=None, description="Estimated magnitude")
    elongation_deg: Optional[float] = Field(default=None, description="Solar elongation in degrees")
    phase_angle_deg: Optional[float] = Field(default=None, description="Phase angle in degrees")


class CometVisibility(BaseModel):
    """Visibility information for a comet at a specific location and time."""
    comet: CometTarget
    ephemeris: CometEphemeris
    altitude_deg: float = Field(description="Altitude in degrees")
    azimuth_deg: float = Field(description="Azimuth in degrees")
    is_visible: bool = Field(description="Whether comet is above horizon")
    is_dark_enough: bool = Field(description="Whether sky is dark enough (astronomical twilight)")
    elongation_ok: bool = Field(description="Whether solar elongation is sufficient")
    recommended: bool = Field(description="Whether comet is recommended for observing")


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
