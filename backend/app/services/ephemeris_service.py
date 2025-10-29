"""Ephemeris calculations using Skyfield."""

from datetime import datetime, timedelta
from typing import Tuple, Dict
import pytz
import math
from skyfield.api import load, wgs84, Star
from skyfield import almanac
from astropy.coordinates import SkyCoord
from astropy import units as u

from app.models import Location, DSOTarget


class EphemerisService:
    """Service for astronomical calculations."""

    def __init__(self):
        """Initialize with ephemeris data."""
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        self.sun = self.eph['sun']

    def calculate_twilight_times(
        self, location: Location, date: datetime
    ) -> Dict[str, datetime]:
        """
        Calculate twilight times for a given location and date.

        Args:
            location: Observer location
            date: Date for calculations (will find night containing this date)

        Returns:
            Dictionary with sunset, twilight times, and sunrise
        """
        # Create observer location
        observer = self.earth + wgs84.latlon(
            location.latitude, location.longitude, elevation_m=location.elevation
        )

        # Get timezone
        tz = pytz.timezone(location.timezone)

        # Start search from noon of the given date to find evening
        noon_local = tz.localize(datetime.combine(date.date(), datetime.min.time().replace(hour=12)))
        noon_utc = noon_local.astimezone(pytz.UTC)

        # Search for twilight times over 36 hours to ensure we get the right night
        t0 = self.ts.from_datetime(noon_utc)
        t1 = self.ts.from_datetime(noon_utc + timedelta(hours=36))

        # Find sunset and sunrise
        f = almanac.sunrise_sunset(self.eph, observer)
        times, events = almanac.find_discrete(t0, t1, f)

        # Find twilight times (civil, nautical, astronomical)
        twilight_times = {}

        # Sunset/Sunrise (0° below horizon)
        sunset_idx = None
        sunrise_idx = None
        for i, (t, event) in enumerate(zip(times, events)):
            if event == 0:  # Sunset
                sunset_idx = i
                twilight_times['sunset'] = t.utc_datetime().replace(tzinfo=pytz.UTC).astimezone(tz)
            elif event == 1 and sunset_idx is not None:  # Sunrise after sunset
                sunrise_idx = i
                twilight_times['sunrise'] = t.utc_datetime().replace(tzinfo=pytz.UTC).astimezone(tz)
                break

        # Civil twilight (6° below)
        f_civil = almanac.dark_twilight_day(self.eph, observer)
        times_civil, events_civil = almanac.find_discrete(t0, t1, f_civil)

        for i, (t, event) in enumerate(zip(times_civil, events_civil)):
            dt = t.utc_datetime().replace(tzinfo=pytz.UTC).astimezone(tz)
            if event == 0:  # Evening civil twilight ends
                if 'sunset' in twilight_times and dt > twilight_times['sunset']:
                    twilight_times['civil_twilight_end'] = dt
            elif event == 4:  # Morning civil twilight begins
                if 'sunrise' in twilight_times and dt < twilight_times['sunrise']:
                    twilight_times['civil_twilight_start'] = dt

        # Nautical and astronomical twilight (using custom angles)
        # Nautical: 12° below, Astronomical: 18° below
        nautical_angle = -12.0
        astronomical_angle = -18.0

        # Calculate nautical twilight
        nautical_times = self._find_twilight_angle(observer, t0, t1, nautical_angle)
        twilight_times['nautical_twilight_end'] = nautical_times[0].astimezone(tz)
        twilight_times['nautical_twilight_start'] = nautical_times[1].astimezone(tz)

        # Calculate astronomical twilight
        astro_times = self._find_twilight_angle(observer, t0, t1, astronomical_angle)
        twilight_times['astronomical_twilight_end'] = astro_times[0].astimezone(tz)
        twilight_times['astronomical_twilight_start'] = astro_times[1].astimezone(tz)

        return twilight_times

    def _find_twilight_angle(self, observer, t0, t1, angle: float) -> Tuple[datetime, datetime]:
        """Find times when sun reaches a specific angle below horizon."""
        def sun_altitude_below(t):
            """Return True when sun is below the specified angle."""
            sun_apparent = observer.at(t).observe(self.sun).apparent()
            alt, _, _ = sun_apparent.altaz()
            return alt.degrees < angle

        times, events = almanac.find_discrete(t0, t1, sun_altitude_below)

        # First True event is evening (sun going below angle)
        # First False event after that is morning (sun coming back above angle)
        evening_time = None
        morning_time = None

        for t, event in zip(times, events):
            dt = t.utc_datetime().replace(tzinfo=pytz.UTC)
            if event and evening_time is None:
                evening_time = dt
            elif not event and evening_time is not None:
                morning_time = dt
                break

        return evening_time, morning_time

    def calculate_position(
        self, target: DSOTarget, location: Location, time: datetime
    ) -> Tuple[float, float]:
        """
        Calculate altitude and azimuth for a target at a specific time.

        Args:
            target: DSO target
            location: Observer location
            time: Time for calculation (timezone-aware)

        Returns:
            Tuple of (altitude, azimuth) in degrees
        """
        # Create observer location
        observer = self.earth + wgs84.latlon(
            location.latitude, location.longitude, elevation_m=location.elevation
        )

        # Convert time to UTC
        time_utc = time.astimezone(pytz.UTC)
        t = self.ts.from_datetime(time_utc)

        # Create star at target coordinates
        star = Star(
            ra_hours=target.ra_hours,
            dec_degrees=target.dec_degrees
        )

        # Calculate position
        astrometric = observer.at(t).observe(star)
        apparent = astrometric.apparent()
        alt, az, _ = apparent.altaz()

        return alt.degrees, az.degrees

    def calculate_field_rotation_rate(
        self, target: DSOTarget, location: Location, time: datetime
    ) -> float:
        """
        Calculate field rotation rate for alt-az mount.

        Formula: rate = 15 * cos(lat) / cos(alt) * |sin(az)|

        Args:
            target: DSO target
            location: Observer location
            time: Time for calculation

        Returns:
            Field rotation rate in degrees per minute
        """
        alt, az = self.calculate_position(target, location, time)

        # Avoid division by zero near zenith
        if alt > 85:
            return 999.9  # Very high rotation rate

        # Convert to radians
        lat_rad = math.radians(location.latitude)
        alt_rad = math.radians(alt)
        az_rad = math.radians(az)

        # Calculate rate in degrees per hour
        rate_per_hour = 15.0 * math.cos(lat_rad) / math.cos(alt_rad) * abs(math.sin(az_rad))

        # Convert to degrees per minute
        rate_per_minute = rate_per_hour / 60.0

        return rate_per_minute

    def is_target_visible(
        self, target: DSOTarget, location: Location, time: datetime, min_alt: float, max_alt: float
    ) -> bool:
        """
        Check if a target is visible (within altitude constraints).

        Args:
            target: DSO target
            location: Observer location
            time: Time for check
            min_alt: Minimum altitude in degrees
            max_alt: Maximum altitude in degrees

        Returns:
            True if target is visible
        """
        alt, _ = self.calculate_position(target, location, time)
        return min_alt <= alt <= max_alt
