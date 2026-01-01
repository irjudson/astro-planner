"""Data models for the Astro Planner application."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class VisibilityStatus(str, Enum):
    """Visibility status enumeration."""

    VISIBLE = "visible"
    RISING = "rising"
    SETTING = "setting"
    BELOW_HORIZON = "below_horizon"


class Location(BaseModel):
    """Observatory location information."""

    name: str = Field(default="Three Forks, MT", description="Location name")
    latitude: float = Field(ge=-90, le=90, description="Latitude in degrees (-90 to 90)")
    longitude: float = Field(ge=-180, le=180, description="Longitude in degrees (-180 to 180)")
    elevation: float = Field(default=1234.0, description="Elevation in meters")
    timezone: str = Field(default="America/Denver", description="IANA timezone")


class ObservingConstraints(BaseModel):
    """Constraints for observing session."""

    min_altitude: float = Field(default=30.0, ge=0, le=90, description="Minimum altitude in degrees")
    max_altitude: float = Field(default=90.0, ge=0, le=90, description="Maximum altitude in degrees")
    setup_time_minutes: int = Field(default=30, ge=0, description="Setup time in minutes")
    object_types: List[str] = Field(
        default=["galaxy", "nebula", "cluster", "planetary_nebula"], description="Object types to include"
    )
    planning_mode: str = Field(default="balanced", description="Planning mode: balanced, quality, or quantity")
    daytime_planning: bool = Field(
        default=False, description="Enable daytime planning mode (for Sun, Moon, Venus observations)"
    )


class PlanRequest(BaseModel):
    """Request to generate an observing plan."""

    location: Location
    observing_date: str = Field(description="ISO date for observing session (YYYY-MM-DD)")
    constraints: ObservingConstraints = Field(default_factory=ObservingConstraints)
    custom_targets: Optional[List[str]] = Field(None, description="Custom list of catalog IDs to schedule")

    @field_validator("observing_date")
    @classmethod
    def validate_observing_date(cls, v: str) -> str:
        """Validate that observing_date is a valid ISO date (YYYY-MM-DD)."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"observing_date must be in ISO format (YYYY-MM-DD), got: {v}")
        return v


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
    image_url: Optional[str] = Field(default=None, description="Preview image URL (relative path)")
    visibility: Optional["TargetVisibility"] = Field(None, description="Real-time visibility info (if calculated)")
    capture_history: Optional[Dict[str, Any]] = Field(None, description="Capture history for this target (if available)")


class TargetVisibility(BaseModel):
    """Real-time visibility information for a catalog object.

    Note: Uses current_altitude/current_azimuth naming for consistency with
    planning documents, though other visibility models use altitude_deg/azimuth_deg.
    """

    current_altitude: float = Field(..., ge=-90, le=90, description="Current altitude in degrees")
    current_azimuth: float = Field(..., ge=0, lt=360, description="Current azimuth in degrees")
    status: VisibilityStatus = Field(..., description="Visibility status")
    best_time_tonight: Optional[datetime] = Field(
        None, description="Best viewing time during tonight's observing window"
    )
    best_altitude_tonight: Optional[float] = Field(None, ge=-90, le=90, description="Altitude at best time")
    is_optimal_now: bool = Field(False, description="True if currently at optimal altitude (45-65°)")


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


class AsteroidOrbitalElements(BaseModel):
    """Keplerian orbital elements for an asteroid."""

    epoch_jd: float = Field(description="Epoch of elements (Julian Date)")
    semi_major_axis_au: float = Field(description="Semi-major axis in AU")
    eccentricity: float = Field(description="Orbital eccentricity")
    inclination_deg: float = Field(description="Inclination in degrees")
    arg_perihelion_deg: float = Field(description="Argument of perihelion (ω) in degrees")
    ascending_node_deg: float = Field(description="Longitude of ascending node (Ω) in degrees")
    mean_anomaly_deg: float = Field(description="Mean anomaly at epoch in degrees")


class AsteroidTarget(BaseModel):
    """Asteroid target information."""

    designation: str = Field(description="Official designation (e.g., 2000 SG344)")
    name: Optional[str] = Field(default=None, description="Name (e.g., Ceres, Vesta)")
    number: Optional[int] = Field(default=None, description="Numbered asteroid ID (e.g., 1 for Ceres)")
    orbital_elements: AsteroidOrbitalElements = Field(description="Orbital elements")
    absolute_magnitude: Optional[float] = Field(default=None, description="Absolute magnitude H")
    slope_parameter: float = Field(default=0.15, description="H-G slope parameter (G)")
    current_magnitude: Optional[float] = Field(default=None, description="Current estimated magnitude")
    diameter_km: Optional[float] = Field(default=None, description="Diameter in kilometers")
    albedo: Optional[float] = Field(default=None, description="Geometric albedo (0-1)")
    spectral_type: Optional[str] = Field(default=None, description="Spectral type (C, S, M, etc.)")
    rotation_period_hours: Optional[float] = Field(default=None, description="Rotation period in hours")
    asteroid_type: Optional[str] = Field(default=None, description="Type: MBA, NEA, Trojan, etc.")
    discovery_date: Optional[str] = Field(default=None, description="Discovery date (ISO)")
    data_source: Optional[str] = Field(default="manual", description="Data source: MPC, JPL, manual")
    notes: Optional[str] = Field(default=None, description="Observing notes")


class AsteroidEphemeris(BaseModel):
    """Ephemeris (computed position) for an asteroid at a specific time."""

    designation: str = Field(description="Asteroid designation")
    date_utc: datetime = Field(description="UTC date/time of ephemeris")
    date_jd: float = Field(description="Julian Date")
    ra_hours: float = Field(description="Right ascension in hours")
    dec_degrees: float = Field(description="Declination in degrees")
    geo_distance_au: float = Field(description="Distance from Earth in AU")
    helio_distance_au: float = Field(description="Distance from Sun in AU")
    magnitude: Optional[float] = Field(default=None, description="Estimated magnitude")
    elongation_deg: Optional[float] = Field(default=None, description="Solar elongation in degrees")
    phase_angle_deg: Optional[float] = Field(default=None, description="Phase angle in degrees")


class AsteroidVisibility(BaseModel):
    """Visibility information for an asteroid at a specific location and time."""

    asteroid: AsteroidTarget
    ephemeris: AsteroidEphemeris
    altitude_deg: float = Field(description="Altitude in degrees")
    azimuth_deg: float = Field(description="Azimuth in degrees")
    is_visible: bool = Field(description="Whether asteroid is above horizon")
    is_dark_enough: bool = Field(description="Whether sky is dark enough (astronomical twilight)")
    elongation_ok: bool = Field(description="Whether solar elongation is sufficient")
    recommended: bool = Field(description="Whether asteroid is recommended for observing")


class PlanetTarget(BaseModel):
    """Planet target information."""

    name: str = Field(description="Planet name (e.g., Mars, Jupiter)")
    planet_type: str = Field(description="Type: terrestrial, gas_giant, ice_giant")
    diameter_km: float = Field(description="Diameter in kilometers")
    orbital_period_days: float = Field(description="Orbital period in days")
    rotation_period_hours: Optional[float] = Field(default=None, description="Rotation period in hours")
    has_rings: bool = Field(default=False, description="Whether planet has ring system")
    num_moons: int = Field(default=0, description="Number of known moons")
    notes: Optional[str] = Field(default=None, description="Observing notes")


class PlanetEphemeris(BaseModel):
    """Ephemeris (computed position) for a planet at a specific time."""

    name: str = Field(description="Planet name")
    date_utc: datetime = Field(description="UTC date/time of ephemeris")
    date_jd: float = Field(description="Julian Date")
    ra_hours: float = Field(description="Right ascension in hours")
    dec_degrees: float = Field(description="Declination in degrees")
    distance_au: float = Field(description="Distance from Earth in AU")
    magnitude: float = Field(description="Apparent magnitude")
    angular_diameter_arcsec: float = Field(description="Angular diameter in arcseconds")
    phase_percent: Optional[float] = Field(default=None, description="Illuminated fraction (0-100%)")
    elongation_deg: float = Field(description="Solar elongation in degrees")
    constellation: Optional[str] = Field(default=None, description="Current constellation")


class PlanetVisibility(BaseModel):
    """Visibility information for a planet at a specific location and time."""

    planet: PlanetTarget
    ephemeris: PlanetEphemeris
    altitude_deg: float = Field(description="Altitude in degrees")
    azimuth_deg: float = Field(description="Azimuth in degrees")
    is_visible: bool = Field(description="Whether planet is above horizon")
    is_daytime: bool = Field(description="Whether it's daytime (Sun above horizon)")
    elongation_ok: bool = Field(description="Whether solar elongation is sufficient")
    recommended: bool = Field(description="Whether planet is recommended for observing")
    rise_time: Optional[datetime] = Field(default=None, description="Rise time (local)")
    set_time: Optional[datetime] = Field(default=None, description="Set time (local)")


class TargetScore(BaseModel):
    """Scoring components for a target."""

    visibility_score: float = Field(ge=0, le=1, description="Visibility score (0-1)")
    weather_score: float = Field(ge=0, le=1, description="Weather score (0-1)")
    object_score: float = Field(ge=0, le=1, description="Object suitability score (0-1)")
    total_score: float = Field(ge=0, le=1, description="Combined total score (0-1)")


class GapAlternative(BaseModel):
    """Alternative target suggestion for filling a schedule gap."""

    target: DSOTarget
    score: TargetScore
    duration_minutes: int = Field(description="Duration this target could fill in minutes")


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
    altitude_points: List[Tuple[datetime, float]] = Field(
        default_factory=list, description="Altitude samples at 15-minute intervals (time, altitude)"
    )
    field_rotation_rate: float = Field(description="Field rotation rate in deg/min")
    recommended_exposure: int = Field(description="Recommended exposure time in seconds")
    recommended_frames: int = Field(description="Recommended number of frames")
    score: TargetScore
    is_gap_filler: bool = Field(default=False, description="Whether this target was auto-filled into a gap")
    gap_alternatives: Optional[List["GapAlternative"]] = Field(
        default=None, description="Alternative targets for this gap (if auto-filled)"
    )


class WeatherForecast(BaseModel):
    """Weather forecast information."""

    timestamp: datetime
    cloud_cover: float = Field(ge=0, le=100, description="Cloud cover percentage")
    humidity: float = Field(ge=0, le=100, description="Humidity percentage")
    temperature: float = Field(description="Temperature in Celsius")
    wind_speed: float = Field(ge=0, description="Wind speed in m/s")
    conditions: str = Field(description="Weather conditions description")
    seeing_arcseconds: Optional[float] = Field(
        default=None, description="Atmospheric seeing in arcseconds (lower is better)"
    )
    transparency_magnitude: Optional[float] = Field(
        default=None, description="Sky transparency as limiting magnitude (higher is better)"
    )
    source: str = Field(default="openweathermap", description="Data source: openweathermap, 7timer, or composite")


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


class GapFillStats(BaseModel):
    """Statistics about gap-filling operation."""

    total_gaps_found: int = Field(description="Total number of gaps detected")
    gaps_filled: int = Field(description="Number of gaps successfully filled")
    gaps_unfilled: int = Field(description="Number of gaps that could not be filled")
    total_gap_time_minutes: int = Field(description="Total time across all gaps in minutes")
    filled_gap_time_minutes: int = Field(description="Time filled by gap fillers in minutes")
    unfilled_reasons: List[str] = Field(
        default_factory=list, description="Reasons gaps were not filled (e.g., 'No suitable targets', 'Gap too small')"
    )


class ObservingPlan(BaseModel):
    """Complete observing plan for a session."""

    session: SessionInfo
    location: Location
    scheduled_targets: List[ScheduledTarget]
    weather_forecast: List[WeatherForecast]
    total_targets: int = Field(description="Total number of targets")
    coverage_percent: float = Field(description="Percentage of night covered")
    sky_quality: Optional[Dict[str, Any]] = Field(default=None, description="Sky quality information for location")
    gap_fill_stats: Optional["GapFillStats"] = Field(default=None, description="Gap-filling statistics")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExportFormat(BaseModel):
    """Export format configuration."""

    format_type: str = Field(description="Export format: json, seestar_alp, text, csv")
    data: str = Field(description="Exported data as string")
