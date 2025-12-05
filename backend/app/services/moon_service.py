"""Lunar phase and visibility service for observing planning.

This service provides comprehensive moon data including:
- Lunar phase calculations (name, illumination %, age)
- Rise/set times for moon avoidance planning
- Lunar position and visibility
- Dark sky window calculations (time between moonset and astronomical twilight)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, GeocentricMeanEcliptic, get_body, get_sun
from astropy.time import Time

from app.models import Location


class MoonPhaseInfo:
    """Moon phase information for a specific time."""

    def __init__(
        self,
        phase_name: str,
        illumination_percent: float,
        phase_angle: float,
        age_days: float,
        is_waxing: bool,
    ):
        self.phase_name = phase_name
        self.illumination_percent = illumination_percent
        self.phase_angle = phase_angle
        self.age_days = age_days
        self.is_waxing = is_waxing


class MoonEphemeris:
    """Computed lunar position and properties."""

    def __init__(
        self,
        date_utc: datetime,
        ra_hours: float,
        dec_degrees: float,
        distance_km: float,
        angular_diameter_arcmin: float,
        magnitude: float,
        phase_info: MoonPhaseInfo,
    ):
        self.date_utc = date_utc
        self.ra_hours = ra_hours
        self.dec_degrees = dec_degrees
        self.distance_km = distance_km
        self.angular_diameter_arcmin = angular_diameter_arcmin
        self.magnitude = magnitude
        self.phase_info = phase_info


class MoonVisibility:
    """Moon visibility at a specific location and time."""

    def __init__(
        self,
        ephemeris: MoonEphemeris,
        altitude_deg: float,
        azimuth_deg: float,
        is_visible: bool,
        rise_time: Optional[datetime] = None,
        set_time: Optional[datetime] = None,
    ):
        self.ephemeris = ephemeris
        self.altitude_deg = altitude_deg
        self.azimuth_deg = azimuth_deg
        self.is_visible = is_visible
        self.rise_time = rise_time
        self.set_time = set_time


class DarkSkyWindow:
    """Dark sky window information (time without moon interference)."""

    def __init__(
        self,
        moonset_time: Optional[datetime],
        astronomical_twilight_end: datetime,
        astronomical_twilight_start: datetime,
        moonrise_time: Optional[datetime],
        has_evening_window: bool,
        evening_window_hours: float,
        has_morning_window: bool,
        morning_window_hours: float,
        moon_free_hours: float,
    ):
        self.moonset_time = moonset_time
        self.astronomical_twilight_end = astronomical_twilight_end
        self.astronomical_twilight_start = astronomical_twilight_start
        self.moonrise_time = moonrise_time
        self.has_evening_window = has_evening_window
        self.evening_window_hours = evening_window_hours
        self.has_morning_window = has_morning_window
        self.morning_window_hours = morning_window_hours
        self.moon_free_hours = moon_free_hours


class MoonService:
    """Service for lunar ephemeris and observing conditions.

    Provides detailed moon phase information, visibility calculations,
    and dark sky window analysis for deep-sky observing planning.
    """

    # Moon physical constants
    MOON_RADIUS_KM = 1737.4  # Mean radius
    SYNODIC_MONTH_DAYS = 29.530588  # Average lunation period

    def __init__(self):
        """Initialize moon service."""
        self.logger = logging.getLogger(__name__)

    def compute_ephemeris(self, time_utc: datetime) -> MoonEphemeris:
        """Compute lunar ephemeris for a specific time.

        Args:
            time_utc: Time in UTC (timezone-naive or timezone-aware)

        Returns:
            MoonEphemeris with position, phase, and physical data
        """
        # Convert to Astropy Time
        if time_utc.tzinfo is not None:
            time_utc = time_utc.replace(tzinfo=None)
        t = Time(time_utc)

        # Get lunar and solar positions
        moon = get_body("moon", t)
        sun = get_sun(t)

        # Extract coordinates
        ra_hours = moon.ra.hour
        dec_degrees = moon.dec.degree
        distance_km = moon.distance.to(u.km).value

        # Calculate phase from ecliptic longitude difference
        # Transform to ecliptic coordinates for accurate phase calculation
        moon_ecl = moon.transform_to(GeocentricMeanEcliptic(equinox=t))
        sun_ecl = sun.transform_to(GeocentricMeanEcliptic(equinox=t))

        # Phase angle is the difference in ecliptic longitude
        # 0° = New Moon, 90° = First Quarter, 180° = Full Moon, 270° = Last Quarter
        phase_angle = (moon_ecl.lon.degree - sun_ecl.lon.degree) % 360

        # Illumination percentage (0% = new moon, 100% = full moon)
        # Using the formula: illumination = 50 * (1 - cos(phase_angle))
        illumination_percent = 50.0 * (1.0 - np.cos(np.radians(phase_angle)))

        # Determine if waxing or waning
        # Waxing: phase angle 0° to 180° (new to full)
        # Waning: phase angle 180° to 360° (full to new)
        is_waxing = bool(phase_angle < 180.0)

        # Calculate lunar age (days since new moon)
        # Age is proportional to phase angle from 0° (new moon)
        age_days = (phase_angle / 360.0) * self.SYNODIC_MONTH_DAYS

        # Phase name
        phase_name = self._get_phase_name(illumination_percent, is_waxing)

        # Calculate angular diameter
        # Angular diameter = 2 * arctan(radius / distance)
        angular_diameter_rad = 2 * np.arctan(self.MOON_RADIUS_KM / distance_km)
        angular_diameter_arcmin = np.degrees(angular_diameter_rad) * 60

        # Estimate magnitude (moon magnitude varies with phase)
        # At full moon: -12.7, at quarter: ~-10, at new: invisible
        # Simplified model: magnitude increases as illumination decreases
        magnitude = -12.7 + (1.0 - illumination_percent / 100.0) * 10.0

        phase_info = MoonPhaseInfo(
            phase_name=phase_name,
            illumination_percent=illumination_percent,
            phase_angle=phase_angle,
            age_days=age_days,
            is_waxing=is_waxing,
        )

        return MoonEphemeris(
            date_utc=time_utc,
            ra_hours=ra_hours,
            dec_degrees=dec_degrees,
            distance_km=distance_km,
            angular_diameter_arcmin=angular_diameter_arcmin,
            magnitude=magnitude,
            phase_info=phase_info,
        )

    def compute_visibility(self, location: Location, time_utc: datetime) -> MoonVisibility:
        """Compute moon visibility at a specific location and time.

        Args:
            location: Observer location
            time_utc: Time in UTC

        Returns:
            MoonVisibility with altitude, azimuth, and rise/set times
        """
        # Get ephemeris
        ephemeris = self.compute_ephemeris(time_utc)

        # Convert to Astropy Time and Location
        if time_utc.tzinfo is not None:
            time_utc = time_utc.replace(tzinfo=None)
        t = Time(time_utc)

        earth_location = EarthLocation(
            lat=location.latitude * u.deg,
            lon=location.longitude * u.deg,
            height=location.elevation * u.m,
        )

        # Get moon position
        moon = get_body("moon", t)

        # Convert to horizontal coordinates
        altaz_frame = AltAz(obstime=t, location=earth_location)
        moon_altaz = moon.transform_to(altaz_frame)

        altitude_deg = float(moon_altaz.alt.degree)
        azimuth_deg = float(moon_altaz.az.degree)
        is_visible = bool(altitude_deg > 0)

        # Calculate rise/set times (next 24 hours)
        rise_time, set_time = self._calculate_rise_set_times(location, time_utc, earth_location)

        return MoonVisibility(
            ephemeris=ephemeris,
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            is_visible=is_visible,
            rise_time=rise_time,
            set_time=set_time,
        )

    def calculate_dark_sky_window(
        self,
        location: Location,
        observing_date: datetime,
        astronomical_twilight_end: datetime,
        astronomical_twilight_start: datetime,
    ) -> DarkSkyWindow:
        """Calculate dark sky window (time without moon).

        For deep-sky observing, the moon-free dark time is critical.
        This calculates when the sky is both astronomically dark AND
        the moon is below the horizon.

        Args:
            location: Observer location
            observing_date: Date of observation
            astronomical_twilight_end: When sky becomes dark (evening)
            astronomical_twilight_start: When sky becomes light (morning)

        Returns:
            DarkSkyWindow with moon-free observing windows
        """
        # Normalize timezone awareness - convert all to timezone-naive UTC
        if observing_date.tzinfo is not None:
            observing_date = observing_date.replace(tzinfo=None)
        if astronomical_twilight_end.tzinfo is not None:
            astronomical_twilight_end = astronomical_twilight_end.replace(tzinfo=None)
        if astronomical_twilight_start.tzinfo is not None:
            astronomical_twilight_start = astronomical_twilight_start.replace(tzinfo=None)

        # Calculate moon rise/set times for the observing night
        earth_location = EarthLocation(
            lat=location.latitude * u.deg,
            lon=location.longitude * u.deg,
            height=location.elevation * u.m,
        )

        moonset_time, moonrise_time = self._calculate_rise_set_times(location, observing_date, earth_location)

        # Calculate evening dark sky window (twilight end to moonrise, or all night if no moonrise)
        has_evening_window = False
        evening_window_hours = 0.0

        if moonset_time and moonset_time < astronomical_twilight_end:
            # Moon sets before darkness - excellent!
            has_evening_window = True
            if moonrise_time and moonrise_time < astronomical_twilight_start:
                # Moon rises before morning twilight
                evening_window_hours = (moonrise_time - astronomical_twilight_end).total_seconds() / 3600
            else:
                # Moon doesn't rise before morning twilight - full dark window
                evening_window_hours = (astronomical_twilight_start - astronomical_twilight_end).total_seconds() / 3600
        elif not moonrise_time or moonrise_time > astronomical_twilight_start:
            # Moon never rises during dark time
            has_evening_window = True
            evening_window_hours = (astronomical_twilight_start - astronomical_twilight_end).total_seconds() / 3600

        # Calculate morning dark sky window (moonset to twilight start)
        has_morning_window = False
        morning_window_hours = 0.0

        if moonset_time and astronomical_twilight_end < moonset_time < astronomical_twilight_start:
            has_morning_window = True
            morning_window_hours = (astronomical_twilight_start - moonset_time).total_seconds() / 3600

        # Total moon-free dark time
        moon_free_hours = evening_window_hours + morning_window_hours

        return DarkSkyWindow(
            moonset_time=moonset_time,
            astronomical_twilight_end=astronomical_twilight_end,
            astronomical_twilight_start=astronomical_twilight_start,
            moonrise_time=moonrise_time,
            has_evening_window=has_evening_window,
            evening_window_hours=evening_window_hours,
            has_morning_window=has_morning_window,
            morning_window_hours=morning_window_hours,
            moon_free_hours=moon_free_hours,
        )

    def _calculate_rise_set_times(
        self, location: Location, time_utc: datetime, earth_location: EarthLocation
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Calculate moon rise and set times for next 24 hours.

        Args:
            location: Observer location
            time_utc: Start time
            earth_location: Astropy EarthLocation

        Returns:
            Tuple of (set_time, rise_time), either can be None
        """
        # Sample altitude every 15 minutes for 24 hours
        times = []
        altitudes = []

        for minutes in range(0, 24 * 60, 15):
            t = time_utc + timedelta(minutes=minutes)
            if t.tzinfo is not None:
                t = t.replace(tzinfo=None)

            astro_time = Time(t)
            moon = get_body("moon", astro_time)

            altaz_frame = AltAz(obstime=astro_time, location=earth_location)
            moon_altaz = moon.transform_to(altaz_frame)

            times.append(t)
            altitudes.append(moon_altaz.alt.degree)

        # Find rise and set times (altitude crosses 0°)
        rise_time = None
        set_time = None

        for i in range(len(altitudes) - 1):
            if altitudes[i] < 0 and altitudes[i + 1] >= 0:
                # Rising
                rise_time = times[i]
            elif altitudes[i] >= 0 and altitudes[i + 1] < 0:
                # Setting
                set_time = times[i]

        return set_time, rise_time

    def _get_phase_name(self, illumination: float, is_waxing: bool) -> str:
        """Map illumination percentage to phase name.

        Args:
            illumination: Percentage illuminated (0-100)
            is_waxing: True if moon is waxing

        Returns:
            Phase name (e.g., "First Quarter", "Waning Gibbous")
        """
        if illumination < 1:
            return "New Moon"
        elif illumination < 48:
            return "Waxing Crescent" if is_waxing else "Waning Crescent"
        elif 48 <= illumination < 52:
            return "First Quarter" if is_waxing else "Last Quarter"
        elif illumination < 99:
            return "Waxing Gibbous" if is_waxing else "Waning Gibbous"
        else:
            return "Full Moon"
