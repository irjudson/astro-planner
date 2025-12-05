"""Service for managing planets and computing ephemeris."""

from datetime import datetime
from typing import List, Optional

import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, get_body, get_sun, solar_system_ephemeris
from astropy.time import Time

from app.models import Location, PlanetEphemeris, PlanetTarget, PlanetVisibility

# Static planet data
PLANET_DATA = {
    "Mercury": {
        "planet_type": "terrestrial",
        "diameter_km": 4879.4,
        "orbital_period_days": 87.969,
        "rotation_period_hours": 1407.6,  # Very slow rotation
        "has_rings": False,
        "num_moons": 0,
        "notes": "Closest planet to the Sun, best viewed during twilight near greatest elongation",
    },
    "Venus": {
        "planet_type": "terrestrial",
        "diameter_km": 12103.6,
        "orbital_period_days": 224.701,
        "rotation_period_hours": 5832.5,  # Retrograde rotation
        "has_rings": False,
        "num_moons": 0,
        "notes": "Brightest planet, often visible during daytime, shows phases like the Moon",
    },
    "Mars": {
        "planet_type": "terrestrial",
        "diameter_km": 6792.4,
        "orbital_period_days": 686.980,
        "rotation_period_hours": 24.623,
        "has_rings": False,
        "num_moons": 2,
        "notes": "The Red Planet, shows polar caps and surface features in telescopes",
    },
    "Jupiter": {
        "planet_type": "gas_giant",
        "diameter_km": 142984.0,
        "orbital_period_days": 4332.589,
        "rotation_period_hours": 9.925,
        "has_rings": True,  # Faint ring system
        "num_moons": 95,  # As of 2023
        "notes": "Largest planet, shows cloud bands, Great Red Spot, and four Galilean moons",
    },
    "Saturn": {
        "planet_type": "gas_giant",
        "diameter_km": 120536.0,
        "orbital_period_days": 10759.22,
        "rotation_period_hours": 10.656,
        "has_rings": True,  # Prominent ring system
        "num_moons": 146,  # As of 2023
        "notes": "Famous for spectacular ring system, Cassini Division visible in small telescopes",
    },
    "Uranus": {
        "planet_type": "ice_giant",
        "diameter_km": 51118.0,
        "orbital_period_days": 30688.5,
        "rotation_period_hours": 17.24,  # Retrograde rotation, tilted on side
        "has_rings": True,  # Faint ring system
        "num_moons": 27,
        "notes": "Blue-green disk in telescopes, rotates on its side",
    },
    "Neptune": {
        "planet_type": "ice_giant",
        "diameter_km": 49528.0,
        "orbital_period_days": 60182.0,
        "rotation_period_hours": 16.11,
        "has_rings": True,  # Faint ring system
        "num_moons": 14,
        "notes": "Deep blue color, farthest major planet, requires telescope to observe",
    },
    "Moon": {
        "planet_type": "satellite",
        "diameter_km": 3474.8,
        "orbital_period_days": 27.322,  # Sidereal month
        "rotation_period_hours": 655.7,  # Tidally locked (same as orbital period)
        "has_rings": False,
        "num_moons": 0,
        "notes": "Earth's only natural satellite, excellent for surface detail imaging, shows phases and libration",
    },
    "Sun": {
        "planet_type": "star",
        "diameter_km": 1392700.0,
        "orbital_period_days": 0.0,  # Not applicable
        "rotation_period_hours": 609.12,  # At equator (~25.4 days)
        "has_rings": False,
        "num_moons": 0,
        "notes": "⚠️ REQUIRES PROPER SOLAR FILTER! Never observe without certified solar filter. Good for sunspots, prominences, solar disk imaging",
    },
}


class PlanetService:
    """Service for planet ephemeris and visibility calculations."""

    def __init__(self):
        """Initialize planet service."""
        # Use built-in ephemeris for planets
        solar_system_ephemeris.set("builtin")

    def get_all_planets(self) -> List[PlanetTarget]:
        """
        Get all major planets (Mercury through Neptune).

        Returns:
            List of PlanetTarget objects with static planet information
        """
        planets = []
        for name, data in PLANET_DATA.items():
            planet = PlanetTarget(name=name, **data)
            planets.append(planet)
        return planets

    def get_planet_by_name(self, name: str) -> Optional[PlanetTarget]:
        """
        Get a specific planet by name.

        Args:
            name: Planet name (case-insensitive)

        Returns:
            PlanetTarget or None if not found
        """
        # Normalize name
        name_normalized = name.strip().title()

        if name_normalized not in PLANET_DATA:
            return None

        return PlanetTarget(name=name_normalized, **PLANET_DATA[name_normalized])

    def compute_ephemeris(self, planet_name: str, time_utc: datetime) -> PlanetEphemeris:
        """
        Compute ephemeris for a planet at a specific time using Astropy.

        Args:
            planet_name: Planet name
            time_utc: UTC time for ephemeris

        Returns:
            PlanetEphemeris with computed position and properties

        Raises:
            ValueError: If planet name is invalid
        """
        # Normalize planet name
        planet_name = planet_name.strip().title()

        if planet_name not in PLANET_DATA:
            raise ValueError(f"Unknown planet: {planet_name}")

        # Convert to Astropy Time
        t = Time(time_utc)

        # Special handling for Sun and Moon
        if planet_name == "Sun":
            # Sun is special - use get_sun() directly
            planet = get_sun(t)
            sun = planet  # Sun is itself
        elif planet_name == "Moon":
            # Moon uses get_body
            planet = get_body("moon", t)
            sun = get_sun(t)
        else:
            # Get planet position using Astropy's get_body
            # This uses built-in ephemeris (based on JPL data)
            planet = get_body(planet_name.lower(), t)
            # Get Sun position for phase angle and elongation
            sun = get_sun(t)

        # Convert coordinates
        ra_hours = planet.ra.hour
        dec_degrees = planet.dec.degree

        # Geocentric distance
        # get_body returns GCRS coordinates, distance is in the coordinate object
        distance_au = planet.distance.to(u.AU).value

        # Calculate solar elongation and phase - special handling for Sun and Moon
        if planet_name == "Sun":
            # Sun has no elongation from itself and is always "full phase"
            elongation_deg = 0.0
            phase_angle_deg = 0.0
            phase_percent = 100.0
            magnitude = -26.7  # Sun's apparent magnitude
        elif planet_name == "Moon":
            # Moon elongation from Sun determines phase
            elongation_deg = planet.separation(sun).degree
            # For Moon, phase angle is approximately 180 - elongation
            # when elongation = 0 (new moon), phase = 0%
            # when elongation = 180 (full moon), phase = 100%
            phase_angle_deg = 180.0 - elongation_deg
            # Illuminated fraction based on elongation
            phase_percent = 50.0 * (1.0 - np.cos(np.radians(elongation_deg)))
            # Moon magnitude varies with phase, roughly -12.7 at full moon
            # Simple approximation: brighter when fuller
            magnitude = -12.7 + (1.0 - phase_percent / 100.0) * 10.0
        else:
            # Calculate solar elongation (angular separation from Sun)
            elongation_deg = planet.separation(sun).degree

            # Calculate phase angle (angle Sun-planet-Earth)
            # For phase angle calculation, we need heliocentric distance
            # Use rough approximation based on planet and orbital data
            helio_distance_au = self._get_heliocentric_distance(planet_name, t)

            # Phase angle using law of cosines
            # cos(phase) = (r^2 + delta^2 - R^2) / (2 * r * delta)
            # where r = heliocentric distance, delta = geocentric distance, R = Earth-Sun distance (1 AU)
            earth_sun_dist = 1.0  # AU
            cos_phase = (helio_distance_au**2 + distance_au**2 - earth_sun_dist**2) / (
                2 * helio_distance_au * distance_au
            )
            cos_phase = np.clip(cos_phase, -1, 1)  # Ensure valid range
            phase_angle_deg = np.degrees(np.arccos(cos_phase))

            # Illuminated fraction (phase percent)
            # phase_percent = 100 * (1 + cos(phase_angle)) / 2
            phase_percent = 100.0 * (1.0 + np.cos(np.radians(phase_angle_deg))) / 2.0

            # Estimate visual magnitude
            magnitude = self._estimate_magnitude(planet_name, distance_au, helio_distance_au, phase_angle_deg)

        # Calculate angular diameter
        # Angular diameter = 2 * arctan(radius / distance)
        planet_data = PLANET_DATA[planet_name]
        radius_km = planet_data["diameter_km"] / 2.0
        radius_au = radius_km / 149597870.7  # km per AU
        angular_diameter_rad = 2 * np.arctan(radius_au / distance_au)
        angular_diameter_arcsec = np.degrees(angular_diameter_rad) * 3600

        # Get constellation (requires additional calculation)
        # For now, we'll leave it as None (could use astropy.coordinates.get_constellation)
        constellation = None

        return PlanetEphemeris(
            name=planet_name,
            date_utc=time_utc,
            date_jd=t.jd,
            ra_hours=ra_hours,
            dec_degrees=dec_degrees,
            distance_au=distance_au,
            magnitude=magnitude,
            angular_diameter_arcsec=angular_diameter_arcsec,
            phase_percent=phase_percent,
            elongation_deg=elongation_deg,
            constellation=constellation,
        )

    def _get_heliocentric_distance(self, planet_name: str, t: Time) -> float:
        """
        Get heliocentric distance for a planet.

        Args:
            planet_name: Planet name
            t: Astropy Time object

        Returns:
            Heliocentric distance in AU
        """
        # Get planet position relative to Sun
        # Use get_body with location at solar system barycenter
        get_body(planet_name.lower(), t)

        # For heliocentric distance, use rough semi-major axis approximation
        # (More accurate calculation would require barycentric coordinates)
        planet_data = PLANET_DATA[planet_name]
        orbital_period_days = planet_data["orbital_period_days"]

        # Kepler's third law: a^3 = T^2 (with T in years, a in AU)
        orbital_period_years = orbital_period_days / 365.25
        semi_major_axis_au = orbital_period_years ** (2.0 / 3.0)

        # Return semi-major axis as rough approximation
        # (Could improve with actual heliocentric coordinates)
        return semi_major_axis_au

    def _estimate_magnitude(
        self, planet_name: str, geo_dist_au: float, helio_dist_au: float, phase_angle_deg: float
    ) -> float:
        """
        Estimate visual magnitude of a planet.

        Uses simplified magnitude formulas for each planet.

        Args:
            planet_name: Planet name
            geo_dist_au: Geocentric distance in AU
            helio_dist_au: Heliocentric distance in AU
            phase_angle_deg: Phase angle in degrees

        Returns:
            Estimated visual magnitude
        """
        # Simplified magnitude formulas (Astronomical Algorithms, Meeus)
        # V = V0 + 5*log10(r*delta) + corrections

        # Base magnitude parameters (V0) for each planet
        # These are approximate values
        mag_params = {
            "Mercury": -0.60,
            "Venus": -4.40,
            "Mars": -1.52,
            "Jupiter": -9.40,
            "Saturn": -8.88,  # Without rings, rings add ~+0.6
            "Uranus": -7.19,
            "Neptune": -6.87,
        }

        v0 = mag_params.get(planet_name, 0.0)

        # Distance term: 5 * log10(r * delta)
        # where r = heliocentric distance, delta = geocentric distance
        dist_term = 5.0 * np.log10(helio_dist_au * geo_dist_au)

        # Phase angle correction (simplified)
        # Most planets use a quadratic phase function
        np.radians(phase_angle_deg)
        phase_correction = 0.0

        if planet_name in ["Mercury", "Venus"]:
            # Inner planets have significant phase effects
            phase_correction = 0.0384 * phase_angle_deg - 0.000125 * phase_angle_deg**2
        elif planet_name == "Mars":
            phase_correction = 0.016 * phase_angle_deg

        magnitude = v0 + dist_term + phase_correction

        # Clamp to reasonable range
        return np.clip(magnitude, -10.0, 20.0)

    def compute_visibility(self, planet_name: str, location: Location, time_utc: datetime) -> PlanetVisibility:
        """
        Compute visibility of a planet at a specific location and time.

        Args:
            planet_name: Planet name
            location: Observer location
            time_utc: UTC time for visibility calculation

        Returns:
            PlanetVisibility with visibility information
        """
        # Get planet info
        planet = self.get_planet_by_name(planet_name)
        if not planet:
            raise ValueError(f"Unknown planet: {planet_name}")

        # Compute ephemeris
        ephemeris = self.compute_ephemeris(planet_name, time_utc)

        # Set up observer location
        earth_location = EarthLocation(
            lat=location.latitude * u.deg, lon=location.longitude * u.deg, height=location.elevation * u.m
        )

        # Convert to Astropy Time
        t = Time(time_utc)

        # Get planet alt/az
        planet_coord = get_body(planet_name.lower(), t)
        altaz_frame = AltAz(obstime=t, location=earth_location)
        planet_altaz = planet_coord.transform_to(altaz_frame)

        altitude_deg = planet_altaz.alt.degree
        azimuth_deg = planet_altaz.az.degree

        # Check if planet is visible (above horizon)
        is_visible = altitude_deg > 0

        # Get Sun position to check daytime
        sun_coord = get_sun(t)
        sun_altaz = sun_coord.transform_to(altaz_frame)
        sun_altitude_deg = sun_altaz.alt.degree

        # Daytime if Sun is above horizon
        is_daytime = sun_altitude_deg > 0

        # Solar elongation check (should be far enough from Sun)
        # For most planets, require >15 degrees
        # For Venus/Mercury, can be observed closer to Sun
        min_elongation = 15.0 if planet_name in ["Venus", "Mercury"] else 30.0
        elongation_ok = ephemeris.elongation_deg >= min_elongation

        # Recommended for observing:
        # - Above horizon
        # - Good elongation from Sun
        # - Either nighttime OR bright enough for daytime (Venus/Mercury)
        can_observe_daytime = planet_name in ["Venus"] and ephemeris.magnitude < -3.0
        recommended = is_visible and elongation_ok and (not is_daytime or can_observe_daytime)

        # Calculate rise and set times (simplified - next rise/set within 24 hours)
        rise_time, set_time = self._calculate_rise_set_times(planet_name, location, time_utc)

        return PlanetVisibility(
            planet=planet,
            ephemeris=ephemeris,
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            is_visible=is_visible,
            is_daytime=is_daytime,
            elongation_ok=elongation_ok,
            recommended=recommended,
            rise_time=rise_time,
            set_time=set_time,
        )

    def _calculate_rise_set_times(
        self, planet_name: str, location: Location, time_utc: datetime
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Calculate rise and set times for a planet.

        This is a simplified calculation that searches for the next
        rise and set within 24 hours of the given time.

        Args:
            planet_name: Planet name
            location: Observer location
            time_utc: Reference time (UTC)

        Returns:
            Tuple of (rise_time, set_time) or (None, None) if not found
        """
        # Set up observer location
        earth_location = EarthLocation(
            lat=location.latitude * u.deg, lon=location.longitude * u.deg, height=location.elevation * u.m
        )

        # Search for rise/set over next 24 hours
        # Sample every 10 minutes
        from datetime import timedelta

        rise_time = None
        set_time = None

        prev_alt = None
        for i in range(144):  # 24 hours * 6 samples per hour
            t_sample = time_utc + timedelta(minutes=i * 10)
            t = Time(t_sample)

            planet_coord = get_body(planet_name.lower(), t)
            altaz_frame = AltAz(obstime=t, location=earth_location)
            planet_altaz = planet_coord.transform_to(altaz_frame)
            alt = planet_altaz.alt.degree

            if prev_alt is not None:
                # Check for rise (crossing horizon from below)
                if prev_alt <= 0 and alt > 0 and rise_time is None:
                    rise_time = t_sample

                # Check for set (crossing horizon from above)
                if prev_alt > 0 and alt <= 0 and set_time is None:
                    set_time = t_sample

                # Stop if we found both
                if rise_time and set_time:
                    break

            prev_alt = alt

        return rise_time, set_time

    def get_visible_planets(
        self, location: Location, time_utc: datetime, min_altitude: float = 0.0, include_daytime: bool = False
    ) -> List[PlanetVisibility]:
        """
        Get all planets that are currently visible.

        Args:
            location: Observer location
            time_utc: UTC time for visibility
            min_altitude: Minimum altitude in degrees (default: 0 = horizon)
            include_daytime: Include planets visible during daytime (Venus)

        Returns:
            List of PlanetVisibility for visible planets
        """
        all_planets = self.get_all_planets()
        visible = []

        for planet in all_planets:
            try:
                visibility = self.compute_visibility(planet.name, location, time_utc)

                # Filter by criteria
                if visibility.altitude_deg >= min_altitude:
                    if include_daytime or not visibility.is_daytime or visibility.recommended:
                        visible.append(visibility)
            except Exception:
                # Skip planets that can't be computed
                continue

        # Sort by altitude (highest first)
        visible.sort(key=lambda v: v.altitude_deg, reverse=True)

        return visible
