"""Comet catalog and ephemeris service."""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
import numpy as np

from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_body, solar_system_ephemeris
from astropy import units as u
from astropy.coordinates import get_sun

from app.models import (
    CometTarget,
    CometEphemeris,
    CometVisibility,
    OrbitalElements,
    Location,
)


class CometService:
    """Service for managing comet catalog and computing ephemerides."""

    def __init__(self, db_path: str = None):
        """Initialize comet service with SQLite database."""
        # Auto-detect database path
        if db_path is None:
            # Try Docker path first, then local dev path
            docker_path = Path("/app/data/catalogs.db")
            local_path = Path("backend/data/catalogs.db")
            if docker_path.exists():
                db_path = str(docker_path)
            else:
                db_path = str(local_path)

        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Ensure database file exists."""
        db_file = Path(self.db_path)
        if not db_file.exists():
            db_file.parent.mkdir(parents=True, exist_ok=True)
            # Database will be created automatically when first accessed

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        return conn

    def add_comet(self, comet: CometTarget) -> int:
        """
        Add a new comet to the catalog.

        Args:
            comet: CometTarget object to add

        Returns:
            Database ID of inserted comet
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        oe = comet.orbital_elements
        cursor.execute("""
            INSERT INTO comet_catalog (
                designation, name, discovery_date,
                epoch_jd, perihelion_distance_au, eccentricity,
                inclination_deg, arg_perihelion_deg, ascending_node_deg,
                perihelion_time_jd, absolute_magnitude, magnitude_slope,
                current_magnitude, activity_status,
                comet_type, data_source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comet.designation, comet.name, comet.discovery_date,
            oe.epoch_jd, oe.perihelion_distance_au, oe.eccentricity,
            oe.inclination_deg, oe.arg_perihelion_deg, oe.ascending_node_deg,
            oe.perihelion_time_jd, comet.absolute_magnitude, comet.magnitude_slope,
            comet.current_magnitude, comet.activity_status,
            comet.comet_type, comet.data_source, comet.notes
        ))

        comet_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return comet_id

    def get_comet_by_designation(self, designation: str) -> Optional[CometTarget]:
        """
        Get a comet by its designation.

        Args:
            designation: Official comet designation

        Returns:
            CometTarget or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT designation, name, discovery_date,
                   epoch_jd, perihelion_distance_au, eccentricity,
                   inclination_deg, arg_perihelion_deg, ascending_node_deg,
                   perihelion_time_jd, absolute_magnitude, magnitude_slope,
                   current_magnitude, activity_status,
                   comet_type, data_source, notes
            FROM comet_catalog
            WHERE designation = ?
        """, (designation,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_comet(row)

    def get_all_comets(self, limit: Optional[int] = None, offset: int = 0) -> List[CometTarget]:
        """
        Get all comets in catalog.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of CometTarget objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT designation, name, discovery_date,
                   epoch_jd, perihelion_distance_au, eccentricity,
                   inclination_deg, arg_perihelion_deg, ascending_node_deg,
                   perihelion_time_jd, absolute_magnitude, magnitude_slope,
                   current_magnitude, activity_status,
                   comet_type, data_source, notes
            FROM comet_catalog ORDER BY current_magnitude ASC
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_comet(row) for row in rows]

    def _row_to_comet(self, row: tuple) -> CometTarget:
        """Convert database row to CometTarget."""
        (designation, name, discovery_date,
         epoch_jd, perihelion_distance_au, eccentricity,
         inclination_deg, arg_perihelion_deg, ascending_node_deg,
         perihelion_time_jd, absolute_magnitude, magnitude_slope,
         current_magnitude, activity_status,
         comet_type, data_source, notes) = row

        orbital_elements = OrbitalElements(
            epoch_jd=epoch_jd,
            perihelion_distance_au=perihelion_distance_au,
            eccentricity=eccentricity,
            inclination_deg=inclination_deg,
            arg_perihelion_deg=arg_perihelion_deg,
            ascending_node_deg=ascending_node_deg,
            perihelion_time_jd=perihelion_time_jd
        )

        return CometTarget(
            designation=designation,
            name=name,
            orbital_elements=orbital_elements,
            absolute_magnitude=absolute_magnitude,
            magnitude_slope=magnitude_slope,
            current_magnitude=current_magnitude,
            comet_type=comet_type,
            activity_status=activity_status,
            discovery_date=discovery_date,
            data_source=data_source,
            notes=notes
        )

    def compute_ephemeris(
        self,
        comet: CometTarget,
        time_utc: datetime
    ) -> CometEphemeris:
        """
        Compute ephemeris for a comet at a specific time.

        This uses a simplified approach - for production, you'd want to use
        more sophisticated orbital propagation (e.g., via JPL Horizons).

        Args:
            comet: Comet to compute ephemeris for
            time_utc: Time to compute ephemeris at (UTC)

        Returns:
            CometEphemeris object
        """
        # Convert to astropy Time
        t = Time(time_utc)
        jd = t.jd

        oe = comet.orbital_elements

        # Compute mean anomaly (simplified)
        # M = n * (t - T) where n is mean motion
        # For comets, we use Kepler's 3rd law: n = sqrt(GM_sun / a^3)
        # a = q / (1 - e) for elliptical orbits

        # Semi-major axis in AU
        if oe.eccentricity < 1.0:
            semi_major_axis = oe.perihelion_distance_au / (1.0 - oe.eccentricity)
        else:
            # Hyperbolic orbit - use approximation
            semi_major_axis = oe.perihelion_distance_au / (oe.eccentricity - 1.0)

        # Mean motion in radians per day
        # Using GM_sun = 1.32712440018e20 m³/s²
        # Simplified: n ≈ 0.01720209895 / sqrt(a^3) rad/day (Gaussian constant)
        k = 0.01720209895  # Gaussian gravitational constant
        if semi_major_axis > 0:
            mean_motion = k / np.sqrt(abs(semi_major_axis) ** 3)
        else:
            mean_motion = k  # Fallback

        # Time since perihelion in days
        dt = jd - oe.perihelion_time_jd

        # Mean anomaly
        mean_anomaly = mean_motion * dt

        # Solve Kepler's equation for eccentric anomaly (simplified Newton-Raphson)
        E = mean_anomaly  # Initial guess
        for _ in range(10):  # Iterate
            E = E - (E - oe.eccentricity * np.sin(E) - mean_anomaly) / (1 - oe.eccentricity * np.cos(E))

        # True anomaly
        true_anomaly = 2 * np.arctan2(
            np.sqrt(1 + oe.eccentricity) * np.sin(E / 2),
            np.sqrt(1 - oe.eccentricity) * np.cos(E / 2)
        )

        # Heliocentric distance
        r = oe.perihelion_distance_au * (1 + oe.eccentricity) / (1 + oe.eccentricity * np.cos(true_anomaly))

        # Convert orbital elements to ecliptic coordinates
        # This is a simplified approach - production should use JPL Horizons or more sophisticated orbital propagation

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

        # Estimate magnitude using H-G model for comets
        # m = H + 5*log10(delta) + 2.5*n*log10(r)
        # where delta is Earth distance, r is Sun distance, n is slope parameter
        if comet.absolute_magnitude is not None:
            magnitude = (comet.absolute_magnitude +
                        5 * np.log10(geo_distance_au) +
                        2.5 * comet.magnitude_slope * np.log10(r))
        else:
            magnitude = None

        # Solar elongation (angle from Sun) - simplified
        elongation_deg = 90.0  # Placeholder

        return CometEphemeris(
            designation=comet.designation,
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
        comet: CometTarget,
        location: Location,
        time_utc: datetime
    ) -> CometVisibility:
        """
        Compute visibility of comet from a specific location and time.

        Args:
            comet: Comet to check visibility for
            location: Observer location
            time_utc: Time to check (UTC)

        Returns:
            CometVisibility object
        """
        # Compute ephemeris
        ephemeris = self.compute_ephemeris(comet, time_utc)

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

        # Check elongation (should be > 30 degrees from Sun for comets)
        elongation_ok = ephemeris.elongation_deg and ephemeris.elongation_deg > 30

        # Overall recommendation
        recommended = is_visible and is_dark_enough and elongation_ok

        return CometVisibility(
            comet=comet,
            ephemeris=ephemeris,
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            is_visible=is_visible,
            is_dark_enough=is_dark_enough,
            elongation_ok=elongation_ok,
            recommended=recommended
        )

    def get_visible_comets(
        self,
        location: Location,
        time_utc: datetime,
        min_altitude: float = 30.0,
        max_magnitude: float = 12.0
    ) -> List[CometVisibility]:
        """
        Get all visible comets for a location and time.

        Args:
            location: Observer location
            time_utc: Time to check
            min_altitude: Minimum altitude in degrees
            max_magnitude: Maximum (faintest) magnitude

        Returns:
            List of visible comets with visibility info
        """
        all_comets = self.get_all_comets()
        visible = []

        for comet in all_comets:
            # Skip if too faint
            if comet.current_magnitude and comet.current_magnitude > max_magnitude:
                continue

            try:
                visibility = self.compute_visibility(comet, location, time_utc)

                if (visibility.is_visible and
                    visibility.altitude_deg >= min_altitude and
                    visibility.is_dark_enough):
                    visible.append(visibility)
            except Exception as e:
                # Skip comets that fail computation
                print(f"Warning: Failed to compute visibility for {comet.designation}: {e}")
                continue

        # Sort by magnitude (brightest first)
        visible.sort(key=lambda v: v.ephemeris.magnitude if v.ephemeris.magnitude else 99.0)

        return visible
