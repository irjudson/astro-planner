"""Tests for asteroid service."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import AsteroidEphemeris, AsteroidOrbitalElements, AsteroidTarget, AsteroidVisibility, Location
from app.models.catalog_models import AsteroidCatalog
from app.services.asteroid_service import AsteroidService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def asteroid_service(mock_db):
    """Create asteroid service with mock database."""
    return AsteroidService(mock_db)


@pytest.fixture
def sample_orbital_elements():
    """Create sample orbital elements for Ceres."""
    return AsteroidOrbitalElements(
        epoch_jd=2460000.5,
        semi_major_axis_au=2.7691,
        eccentricity=0.0760,
        inclination_deg=10.59,
        arg_perihelion_deg=73.6,
        ascending_node_deg=80.3,
        mean_anomaly_deg=77.37,
    )


@pytest.fixture
def sample_asteroid(sample_orbital_elements):
    """Create sample asteroid target."""
    return AsteroidTarget(
        designation="(1) Ceres",
        name="Ceres",
        number=1,
        orbital_elements=sample_orbital_elements,
        absolute_magnitude=3.34,
        slope_parameter=0.12,
        current_magnitude=7.0,
        diameter_km=939.4,
        albedo=0.09,
        spectral_type="C",
        rotation_period_hours=9.074,
        asteroid_type="Main Belt",
        discovery_date="1801-01-01",  # String, not datetime
        data_source="MPC",
        notes="Dwarf planet",
    )


@pytest.fixture
def sample_location():
    """Create sample observer location."""
    return Location(
        name="Test Observatory", latitude=45.0, longitude=-111.0, elevation=1500.0, timezone="America/Denver"
    )


class TestAsteroidService:
    """Test asteroid service core functionality."""

    def test_init(self, asteroid_service, mock_db):
        """Test service initialization."""
        assert asteroid_service.db == mock_db

    def test_compute_perihelion_distance(self, asteroid_service, sample_orbital_elements):
        """Test perihelion distance calculation."""
        perihelion = asteroid_service._compute_perihelion_distance(sample_orbital_elements)
        # q = a * (1 - e) = 2.7691 * (1 - 0.0760) = ~2.559
        assert 2.5 < perihelion < 2.6

    def test_add_asteroid(self, asteroid_service, mock_db, sample_asteroid):
        """Test adding asteroid to catalog."""
        # Mock the database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda x: setattr(x, "id", 1))

        result = asteroid_service.add_asteroid(sample_asteroid)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result == 1

    def test_get_asteroid_by_designation_found(self, asteroid_service, mock_db, sample_orbital_elements):
        """Test getting asteroid by designation when found."""
        mock_db_asteroid = MagicMock(spec=AsteroidCatalog)
        mock_db_asteroid.designation = "(1) Ceres"
        mock_db_asteroid.name = "Ceres"
        mock_db_asteroid.number = 1
        mock_db_asteroid.epoch_jd = 2460000.5
        mock_db_asteroid.semi_major_axis_au = 2.7691
        mock_db_asteroid.eccentricity = 0.0760
        mock_db_asteroid.inclination_deg = 10.59
        mock_db_asteroid.arg_perihelion_deg = 73.6
        mock_db_asteroid.ascending_node_deg = 80.3
        mock_db_asteroid.mean_anomaly_deg = 77.37
        mock_db_asteroid.absolute_magnitude = 3.34
        mock_db_asteroid.slope_parameter = 0.12
        mock_db_asteroid.current_magnitude = 7.0
        mock_db_asteroid.diameter_km = 939.4
        mock_db_asteroid.albedo = 0.09
        mock_db_asteroid.spectral_type = "C"
        mock_db_asteroid.rotation_period_hours = 9.074
        mock_db_asteroid.asteroid_type = "Main Belt"
        mock_db_asteroid.discovery_date = "1801-01-01"
        mock_db_asteroid.data_source = "MPC"
        mock_db_asteroid.notes = "Dwarf planet"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_db_asteroid
        mock_db.query.return_value = mock_query

        result = asteroid_service.get_asteroid_by_designation("(1) Ceres")

        assert result is not None
        assert result.designation == "(1) Ceres"
        assert result.name == "Ceres"

    def test_get_asteroid_by_designation_not_found(self, asteroid_service, mock_db):
        """Test getting asteroid by designation when not found."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = asteroid_service.get_asteroid_by_designation("nonexistent")

        assert result is None

    def test_get_all_asteroids_empty(self, asteroid_service, mock_db):
        """Test getting all asteroids when empty."""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = asteroid_service.get_all_asteroids()

        assert result == []

    def test_get_all_asteroids_with_limit(self, asteroid_service, mock_db):
        """Test getting asteroids with limit."""
        mock_query = Mock()
        mock_query.order_by.return_value.limit.return_value.offset.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = asteroid_service.get_all_asteroids(limit=10, offset=5)

        mock_query.order_by.return_value.limit.assert_called_once_with(10)

    def test_db_to_asteroid(self, asteroid_service):
        """Test conversion from database model to AsteroidTarget."""
        mock_db_asteroid = MagicMock(spec=AsteroidCatalog)
        mock_db_asteroid.designation = "(433) Eros"
        mock_db_asteroid.name = "Eros"
        mock_db_asteroid.number = 433
        mock_db_asteroid.epoch_jd = 2460000.5
        mock_db_asteroid.semi_major_axis_au = 1.458
        mock_db_asteroid.eccentricity = 0.223
        mock_db_asteroid.inclination_deg = 10.83
        mock_db_asteroid.arg_perihelion_deg = 178.9
        mock_db_asteroid.ascending_node_deg = 304.3
        mock_db_asteroid.mean_anomaly_deg = 320.5
        mock_db_asteroid.absolute_magnitude = 11.16
        mock_db_asteroid.slope_parameter = 0.46
        mock_db_asteroid.current_magnitude = 10.5
        mock_db_asteroid.diameter_km = 16.84
        mock_db_asteroid.albedo = 0.25
        mock_db_asteroid.spectral_type = "S"
        mock_db_asteroid.rotation_period_hours = 5.27
        mock_db_asteroid.asteroid_type = "NEA"
        mock_db_asteroid.discovery_date = "1898-08-13"
        mock_db_asteroid.data_source = "MPC"
        mock_db_asteroid.notes = "Near-Earth Asteroid"

        result = asteroid_service._db_to_asteroid(mock_db_asteroid)

        assert result.designation == "(433) Eros"
        assert result.name == "Eros"
        assert result.number == 433
        assert result.orbital_elements.semi_major_axis_au == 1.458
        assert result.orbital_elements.eccentricity == 0.223


class TestAsteroidEphemeris:
    """Test ephemeris computation."""

    def test_compute_ephemeris(self, asteroid_service, sample_asteroid):
        """Test computing ephemeris for an asteroid."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)

        result = asteroid_service.compute_ephemeris(sample_asteroid, time_utc)

        assert result is not None
        assert result.designation == "(1) Ceres"
        assert result.date_utc == time_utc
        assert 0 <= result.ra_hours < 24
        assert -90 <= result.dec_degrees <= 90
        assert result.helio_distance_au > 0
        assert result.geo_distance_au > 0

    def test_compute_ephemeris_with_magnitude(self, asteroid_service, sample_asteroid):
        """Test that ephemeris includes magnitude calculation."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)

        result = asteroid_service.compute_ephemeris(sample_asteroid, time_utc)

        # Ceres has absolute magnitude, so computed magnitude should exist
        assert result.magnitude is not None

    def test_compute_ephemeris_without_magnitude(self, asteroid_service, sample_orbital_elements):
        """Test ephemeris for asteroid without absolute magnitude."""
        asteroid = AsteroidTarget(
            designation="(999999) Test",
            name="Test",
            number=999999,
            orbital_elements=sample_orbital_elements,
            absolute_magnitude=None,  # No magnitude
            slope_parameter=0.15,  # Default value, cannot be None
            current_magnitude=None,
        )
        time_utc = datetime(2024, 6, 15, 12, 0, 0)

        result = asteroid_service.compute_ephemeris(asteroid, time_utc)

        assert result.magnitude is None


class TestAsteroidVisibility:
    """Test visibility computation."""

    def test_compute_visibility(self, asteroid_service, sample_asteroid, sample_location):
        """Test computing visibility for an asteroid."""
        time_utc = datetime(2024, 6, 15, 2, 0, 0)  # Night time

        result = asteroid_service.compute_visibility(sample_asteroid, sample_location, time_utc)

        assert result is not None
        assert result.asteroid == sample_asteroid
        assert result.ephemeris is not None
        assert -90 <= result.altitude_deg <= 90
        assert 0 <= result.azimuth_deg <= 360
        assert isinstance(result.is_visible, bool)
        assert isinstance(result.is_dark_enough, bool)

    def test_compute_visibility_checks_altitude(self, asteroid_service, sample_asteroid, sample_location):
        """Test that visibility correctly checks altitude."""
        # At noon, Ceres might be below horizon
        time_utc = datetime(2024, 6, 15, 12, 0, 0)

        result = asteroid_service.compute_visibility(sample_asteroid, sample_location, time_utc)

        # is_visible should match altitude > 0
        assert result.is_visible == (result.altitude_deg > 0)


class TestGetVisibleAsteroids:
    """Test getting visible asteroids."""

    def test_get_visible_asteroids_empty_catalog(self, asteroid_service, mock_db, sample_location):
        """Test getting visible asteroids from empty catalog."""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        time_utc = datetime(2024, 6, 15, 2, 0, 0)
        result = asteroid_service.get_visible_asteroids(sample_location, time_utc)

        assert result == []

    def test_get_visible_asteroids_filters_by_magnitude(self, asteroid_service, mock_db, sample_location):
        """Test that visible asteroids filters by maximum magnitude."""
        # Create mock asteroid that is too faint
        mock_db_asteroid = MagicMock(spec=AsteroidCatalog)
        mock_db_asteroid.designation = "(99999) Faint"
        mock_db_asteroid.name = "Faint"
        mock_db_asteroid.number = 99999
        mock_db_asteroid.epoch_jd = 2460000.5
        mock_db_asteroid.semi_major_axis_au = 2.5
        mock_db_asteroid.eccentricity = 0.1
        mock_db_asteroid.inclination_deg = 5.0
        mock_db_asteroid.arg_perihelion_deg = 45.0
        mock_db_asteroid.ascending_node_deg = 90.0
        mock_db_asteroid.mean_anomaly_deg = 180.0
        mock_db_asteroid.absolute_magnitude = 20.0
        mock_db_asteroid.slope_parameter = 0.15
        mock_db_asteroid.current_magnitude = 15.0  # Too faint for default max_magnitude of 12
        mock_db_asteroid.diameter_km = None
        mock_db_asteroid.albedo = None
        mock_db_asteroid.spectral_type = None
        mock_db_asteroid.rotation_period_hours = None
        mock_db_asteroid.asteroid_type = None
        mock_db_asteroid.discovery_date = None
        mock_db_asteroid.data_source = None
        mock_db_asteroid.notes = None

        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_db_asteroid]
        mock_db.query.return_value = mock_query

        time_utc = datetime(2024, 6, 15, 2, 0, 0)
        result = asteroid_service.get_visible_asteroids(sample_location, time_utc, max_magnitude=12.0)

        # Should be empty because asteroid is too faint
        assert result == []


class TestAsteroidOrbitalElements:
    """Test orbital elements model."""

    def test_orbital_elements_creation(self, sample_orbital_elements):
        """Test creating orbital elements."""
        assert sample_orbital_elements.epoch_jd == 2460000.5
        assert sample_orbital_elements.semi_major_axis_au == 2.7691
        assert sample_orbital_elements.eccentricity == 0.0760
        assert sample_orbital_elements.inclination_deg == 10.59

    def test_orbital_elements_perihelion_calculation(self, sample_orbital_elements):
        """Test perihelion can be calculated from elements."""
        perihelion = sample_orbital_elements.semi_major_axis_au * (1 - sample_orbital_elements.eccentricity)
        aphelion = sample_orbital_elements.semi_major_axis_au * (1 + sample_orbital_elements.eccentricity)

        assert perihelion < sample_orbital_elements.semi_major_axis_au
        assert aphelion > sample_orbital_elements.semi_major_axis_au
