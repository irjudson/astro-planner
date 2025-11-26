"""Asteroid catalog and ephemeris service."""

from typing import List, Optional
from datetime import datetime
import numpy as np

from sqlalchemy.orm import Session
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
from astropy import units as u

from app.models import (
    AsteroidTarget,
    AsteroidEphemeris,
    AsteroidVisibility,
    AsteroidOrbitalElements,
    Location,
)
from app.models.catalog_models import AsteroidCatalog


class AsteroidService:
    """Service for managing asteroid catalog and computing ephemerides."""

    def __init__(self, db: Session):
        """Initialize asteroid service with database session."""
        self.db = db

    def add_asteroid(self, asteroid: AsteroidTarget) -> int:
        """
        Add a new asteroid to the catalog.

        Args:
            asteroid: AsteroidTarget object to add

        Returns:
            Database ID of inserted asteroid
        """
        oe = asteroid.orbital_elements

        db_asteroid = AsteroidCatalog(
            designation=asteroid.designation,
            name=asteroid.name,
            number=asteroid.number,
            discovery_date=asteroid.discovery_date,
            epoch_jd=oe.epoch_jd,
            perihelion_distance_au=self._compute_perihelion_distance(oe),
            eccentricity=oe.eccentricity,
            inclination_deg=oe.inclination_deg,
            arg_perihelion_deg=oe.arg_perihelion_deg,
            ascending_node_deg=oe.ascending_node_deg,
            mean_anomaly_deg=oe.mean_anomaly_deg,
            semi_major_axis_au=oe.semi_major_axis_au,
            absolute_magnitude=asteroid.absolute_magnitude,
            slope_parameter=asteroid.slope_parameter,
            current_magnitude=asteroid.current_magnitude,
            diameter_km=asteroid.diameter_km,
            albedo=asteroid.albedo,
            spectral_type=asteroid.spectral_type,
            rotation_period_hours=asteroid.rotation_period_hours,
            asteroid_type=asteroid.asteroid_type,
            data_source=asteroid.data_source,
            notes=asteroid.notes
        )

        self.db.add(db_asteroid)
        self.db.commit()
        self.db.refresh(db_asteroid)

        return db_asteroid.id

    def _compute_perihelion_distance(self, oe: AsteroidOrbitalElements) -> float:
        """Compute perihelion distance from semi-major axis and eccentricity."""
        return oe.semi_major_axis_au * (1.0 - oe.eccentricity)

    def get_asteroid_by_designation(self, designation: str) -> Optional[AsteroidTarget]:
        """
        Get an asteroid by its designation.

        Args:
            designation: Official asteroid designation

        Returns:
            AsteroidTarget or None if not found
        """
        db_asteroid = self.db.query(AsteroidCatalog).filter(
            AsteroidCatalog.designation == designation
        ).first()

        if not db_asteroid:
            return None

        return self._db_to_asteroid(db_asteroid)

    def get_all_asteroids(self, limit: Optional[int] = None, offset: int = 0) -> List[AsteroidTarget]:
        """
        Get all asteroids in catalog.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of AsteroidTarget objects
        """
        query = self.db.query(AsteroidCatalog).order_by(
            AsteroidCatalog.current_magnitude.asc().nullslast()
        )

        if limit:
            query = query.limit(limit).offset(offset)

        db_asteroids = query.all()
        return [self._db_to_asteroid(db_asteroid) for db_asteroid in db_asteroids]

    def _db_to_asteroid(self, db_asteroid: AsteroidCatalog) -> AsteroidTarget:
        """Convert database model to AsteroidTarget."""
        orbital_elements = AsteroidOrbitalElements(
            epoch_jd=db_asteroid.epoch_jd,
            semi_major_axis_au=db_asteroid.semi_major_axis_au,
            eccentricity=db_asteroid.eccentricity,
            inclination_deg=db_asteroid.inclination_deg,
            arg_perihelion_deg=db_asteroid.arg_perihelion_deg,
            ascending_node_deg=db_asteroid.ascending_node_deg,
            mean_anomaly_deg=db_asteroid.mean_anomaly_deg
        )

        return AsteroidTarget(
            designation=db_asteroid.designation,
            name=db_asteroid.name,
            number=db_asteroid.number,
            orbital_elements=orbital_elements,
            absolute_magnitude=db_asteroid.absolute_magnitude,
            slope_parameter=db_asteroid.slope_parameter,
            current_magnitude=db_asteroid.current_magnitude,
            diameter_km=db_asteroid.diameter_km,
            albedo=db_asteroid.albedo,
            spectral_type=db_asteroid.spectral_type,
            rotation_period_hours=db_asteroid.rotation_period_hours,
            asteroid_type=db_asteroid.asteroid_type,
            discovery_date=db_asteroid.discovery_date,
            data_source=db_asteroid.data_source,
            notes=db_asteroid.notes
        )

    def compute_ephemeris(
        self,
        asteroid: AsteroidTarget,
        time_utc: datetime
    ) -> AsteroidEphemeris:
        """
        Compute ephemeris for an asteroid at a specific time.

        Uses Keplerian orbital mechanics to compute position.

        Args:
            asteroid: Asteroid to compute ephemeris for
            time_utc: Time to compute ephemeris at (UTC)

        Returns:
            AsteroidEphemeris object
        """
        # Convert to astropy Time
        t = Time(time_utc)
        jd = t.jd

        oe = asteroid.orbital_elements

        # Compute mean motion in radians per day
        # n = sqrt(GM_sun / a^3) where k = Gaussian gravitational constant
        k = 0.01720209895  # Gaussian gravitational constant
        mean_motion = k / np.sqrt(oe.semi_major_axis_au ** 3)

        # Time since epoch in days
        dt = jd - oe.epoch_jd

        # Mean anomaly at observation time
        mean_anomaly = np.radians(oe.mean_anomaly_deg) + mean_motion * dt

        # Solve Kepler's equation for eccentric anomaly (Newton-Raphson)
        E = mean_anomaly  # Initial guess
        for _ in range(10):  # Iterate
            E = E - (E - oe.eccentricity * np.sin(E) - mean_anomaly) / (1 - oe.eccentricity * np.cos(E))

        # True anomaly
        true_anomaly = 2 * np.arctan2(
            np.sqrt(1 + oe.eccentricity) * np.sin(E / 2),
            np.sqrt(1 - oe.eccentricity) * np.cos(E / 2)
        )

        # Heliocentric distance
        r = oe.semi_major_axis_au * (1 - oe.eccentricity * np.cos(E))

        # Convert orbital elements to ecliptic coordinates
        # Argument of latitude (ω + ν)
        arg_latitude = np.radians(oe.arg_perihelion_deg) + true_anomaly

        # Position in orbital plane
        x_orb = r * np.cos(arg_latitude)
        y_orb = r * np.sin(arg_latitude)

        # Transform to ecliptic frame
        incl = np.radians(oe.inclination_deg)
        omega = np.radians(oe.ascending_node_deg)

        # Ecliptic coordinates
        x_ecl = (np.cos(omega) * x_orb - np.sin(omega) * y_orb * np.cos(incl))
        y_ecl = (np.sin(omega) * x_orb + np.cos(omega) * y_orb * np.cos(incl))
        z_ecl = y_orb * np.sin(incl)

        # Convert ecliptic to equatorial (J2000)
        # Obliquity of ecliptic (23.4393 degrees)
        epsilon = np.radians(23.4393)

        x_eq = x_ecl
        y_eq = y_ecl * np.cos(epsilon) - z_ecl * np.sin(epsilon)
        z_eq = y_ecl * np.sin(epsilon) + z_ecl * np.cos(epsilon)

        # Calculate RA and Dec
        ra_rad = np.arctan2(y_eq, x_eq)
        if ra_rad < 0:
            ra_rad += 2 * np.pi
        ra_hours = np.degrees(ra_rad) / 15.0

        # Declination (clamped to valid range)
        r_eq = np.sqrt(x_eq**2 + y_eq**2 + z_eq**2)
        dec_degrees = np.degrees(np.arcsin(np.clip(z_eq / r_eq, -1.0, 1.0)))

        # Get Sun position for elongation calculation
        sun = get_sun(t)

        # Estimate geocentric distance (simplified - doesn't account for Earth's position properly)
        # For better accuracy, should compute Earth's position and vector difference
        geo_distance_au = r  # Approximation

        # Estimate magnitude using H-G model for asteroids
        # m = H + 5*log10(r*delta) - 2.5*log10((1-G)*phi_1 + G*phi_2)
        # Simplified: m ≈ H + 5*log10(r*delta)
        if asteroid.absolute_magnitude is not None:
            magnitude = (asteroid.absolute_magnitude +
                        5 * np.log10(r * geo_distance_au))
        else:
            magnitude = None

        # Solar elongation (angle from Sun) - simplified
        elongation_deg = 90.0  # Placeholder

        return AsteroidEphemeris(
            designation=asteroid.designation,
            date_utc=time_utc,
            date_jd=jd,
            ra_hours=ra_hours,
            dec_degrees=dec_degrees,
            geo_distance_au=geo_distance_au,
            helio_distance_au=r,
            magnitude=magnitude,
            elongation_deg=elongation_deg,
            phase_angle_deg=None  # Would compute from geometry
        )

    def compute_visibility(
        self,
        asteroid: AsteroidTarget,
        location: Location,
        time_utc: datetime
    ) -> AsteroidVisibility:
        """
        Compute visibility of asteroid from a specific location and time.

        Args:
            asteroid: Asteroid to check visibility for
            location: Observer location
            time_utc: Time to check (UTC)

        Returns:
            AsteroidVisibility object
        """
        # Compute ephemeris
        ephemeris = self.compute_ephemeris(asteroid, time_utc)

        # Create observer location
        obs_location = EarthLocation(
            lat=location.latitude * u.deg,
            lon=location.longitude * u.deg,
            height=location.elevation * u.m
        )

        # Create astropy time
        t = Time(time_utc)

        # Create coordinate from RA/Dec
        coord = SkyCoord(
            ra=ephemeris.ra_hours * u.hourangle,
            dec=ephemeris.dec_degrees * u.deg,
            frame='icrs'
        )

        # Transform to AltAz frame
        altaz_frame = AltAz(obstime=t, location=obs_location)
        altaz = coord.transform_to(altaz_frame)

        altitude_deg = altaz.alt.degree
        azimuth_deg = altaz.az.degree

        # Check visibility conditions
        is_visible = altitude_deg > 0

        # Check if it's dark enough (Sun below -18 degrees)
        sun = get_sun(t)
        sun_altaz = sun.transform_to(altaz_frame)
        is_dark_enough = sun_altaz.alt.degree < -18

        # Check elongation (should be > 30 degrees from Sun for asteroids)
        elongation_ok = ephemeris.elongation_deg and ephemeris.elongation_deg > 30

        # Overall recommendation
        recommended = is_visible and is_dark_enough and elongation_ok

        return AsteroidVisibility(
            asteroid=asteroid,
            ephemeris=ephemeris,
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            is_visible=is_visible,
            is_dark_enough=is_dark_enough,
            elongation_ok=elongation_ok,
            recommended=recommended
        )

    def get_visible_asteroids(
        self,
        location: Location,
        time_utc: datetime,
        min_altitude: float = 30.0,
        max_magnitude: float = 12.0
    ) -> List[AsteroidVisibility]:
        """
        Get all visible asteroids for a location and time.

        Args:
            location: Observer location
            time_utc: Time to check
            min_altitude: Minimum altitude in degrees
            max_magnitude: Maximum (faintest) magnitude

        Returns:
            List of visible asteroids with visibility info
        """
        all_asteroids = self.get_all_asteroids()
        visible = []

        for asteroid in all_asteroids:
            # Skip if too faint
            if asteroid.current_magnitude and asteroid.current_magnitude > max_magnitude:
                continue

            try:
                visibility = self.compute_visibility(asteroid, location, time_utc)

                if (visibility.is_visible and
                    visibility.altitude_deg >= min_altitude and
                    visibility.is_dark_enough):
                    visible.append(visibility)
            except Exception as e:
                # Skip asteroids that fail computation
                print(f"Warning: Failed to compute visibility for {asteroid.designation}: {e}")
                continue

        # Sort by magnitude (brightest first)
        visible.sort(key=lambda v: v.ephemeris.magnitude if v.ephemeris.magnitude else 99.0)

        return visible
