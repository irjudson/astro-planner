"""SQLAlchemy models for catalog tables (DSO and comets)."""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text

from app.database import Base


class DSOCatalog(Base):
    """Deep Sky Object catalog table."""

    __tablename__ = "dso_catalog"

    id = Column(Integer, primary_key=True, index=True)
    catalog_name = Column(String(10), nullable=False)  # NGC, IC
    catalog_number = Column(Integer, nullable=False)
    common_name = Column(String(100), nullable=True)  # M31, Andromeda Galaxy, etc.
    caldwell_number = Column(Integer, nullable=True)  # Caldwell catalog number (1-109)
    ra_hours = Column(Float, nullable=False)  # Right ascension in hours
    dec_degrees = Column(Float, nullable=False)  # Declination in degrees
    object_type = Column(String(50), nullable=False)  # galaxy, nebula, cluster, etc.
    magnitude = Column(Float, nullable=True)
    surface_brightness = Column(Float, nullable=True)
    size_major_arcmin = Column(Float, nullable=True)  # Major axis in arcminutes
    size_minor_arcmin = Column(Float, nullable=True)  # Minor axis in arcminutes
    constellation = Column(String(3), nullable=True)  # Constellation abbreviation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CometCatalog(Base):
    """Comet catalog table."""

    __tablename__ = "comet_catalog"

    id = Column(Integer, primary_key=True, index=True)
    designation = Column(String(50), nullable=False, unique=True)  # Official designation (e.g., C/2020 F3)
    name = Column(String(100), nullable=True)  # Common name (e.g., NEOWISE)
    discovery_date = Column(Date, nullable=True)

    # Orbital elements
    epoch_jd = Column(Float, nullable=False)  # Julian date of epoch
    perihelion_distance_au = Column(Float, nullable=False)  # Distance at perihelion in AU
    eccentricity = Column(Float, nullable=False)  # Orbital eccentricity
    inclination_deg = Column(Float, nullable=False)  # Inclination in degrees
    arg_perihelion_deg = Column(Float, nullable=False)  # Argument of perihelion in degrees
    ascending_node_deg = Column(Float, nullable=False)  # Longitude of ascending node in degrees
    perihelion_time_jd = Column(Float, nullable=False)  # Time of perihelion passage (JD)

    # Magnitude parameters
    absolute_magnitude = Column(Float, nullable=False)  # H0 or M1
    magnitude_slope = Column(Float, nullable=False)  # k or K
    current_magnitude = Column(Float, nullable=True)  # Current visual magnitude

    # Comet properties
    activity_status = Column(String(20), nullable=True)  # active, inactive, unknown
    comet_type = Column(String(20), nullable=True)  # long-period, short-period, etc.
    data_source = Column(String(100), nullable=True)  # Source of orbital elements
    notes = Column(Text, nullable=True)


class AsteroidCatalog(Base):
    """Asteroid catalog table."""

    __tablename__ = "asteroid_catalog"

    id = Column(Integer, primary_key=True, index=True)
    designation = Column(String(50), nullable=False, unique=True)  # Official designation
    name = Column(String(100), nullable=True)  # Common name (e.g., Ceres, Vesta)
    number = Column(Integer, nullable=True)  # Numbered asteroids
    discovery_date = Column(Date, nullable=True)

    # Orbital elements
    epoch_jd = Column(Float, nullable=False)  # Julian date of epoch
    perihelion_distance_au = Column(Float, nullable=False)  # Distance at perihelion in AU
    eccentricity = Column(Float, nullable=False)  # Orbital eccentricity
    inclination_deg = Column(Float, nullable=False)  # Inclination in degrees
    arg_perihelion_deg = Column(Float, nullable=False)  # Argument of perihelion in degrees
    ascending_node_deg = Column(Float, nullable=False)  # Longitude of ascending node in degrees
    mean_anomaly_deg = Column(Float, nullable=False)  # Mean anomaly at epoch
    semi_major_axis_au = Column(Float, nullable=False)  # Semi-major axis in AU

    # Magnitude parameters
    absolute_magnitude = Column(Float, nullable=True)  # H - absolute magnitude
    slope_parameter = Column(Float, nullable=True, default=0.15)  # G - slope parameter
    current_magnitude = Column(Float, nullable=True)  # Current visual magnitude

    # Asteroid properties
    diameter_km = Column(Float, nullable=True)  # Diameter in kilometers
    albedo = Column(Float, nullable=True)  # Geometric albedo
    spectral_type = Column(String(10), nullable=True)  # C, S, M, etc.
    rotation_period_hours = Column(Float, nullable=True)  # Rotation period
    asteroid_type = Column(String(20), nullable=True)  # NEA, MBA, Trojan, etc.
    data_source = Column(String(50), nullable=True)  # Source of orbital elements
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConstellationName(Base):
    """Constellation name lookup table."""

    __tablename__ = "constellation_names"

    id = Column(Integer, primary_key=True, index=True)
    abbreviation = Column(String(3), nullable=False, unique=True)  # And, Ori, etc.
    full_name = Column(String(50), nullable=False)  # Andromeda, Orion, etc.
