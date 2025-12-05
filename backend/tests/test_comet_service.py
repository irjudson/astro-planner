"""Tests for comet service."""

import pytest
from datetime import datetime
from app.services.comet_service import CometService
from app.models import CometTarget, OrbitalElements, Location
from app.models.catalog_models import CometCatalog


@pytest.fixture
def comet_service(override_get_db):
    """Create comet service instance with isolated test database."""
    return CometService(override_get_db)


@pytest.fixture
def test_comet():
    """Create a test comet (NEOWISE)."""
    return CometTarget(
        designation="C/2020 F3",
        name="NEOWISE",
        orbital_elements=OrbitalElements(
            epoch_jd=2459000.5,
            perihelion_distance_au=0.29,
            eccentricity=0.999,
            inclination_deg=128.9,
            arg_perihelion_deg=37.3,
            ascending_node_deg=61.0,
            perihelion_time_jd=2459034.0
        ),
        absolute_magnitude=3.0,
        magnitude_slope=4.0,
        current_magnitude=7.0,
        comet_type="long-period",
        activity_status="active",
        discovery_date=None,
        data_source="Test",
        notes="Test comet"
    )


@pytest.fixture
def test_location():
    """Create a test location."""
    return Location(
        latitude=45.9183,
        longitude=-111.5433,
        elevation_meters=1234,
        timezone="America/Denver",
        name="Three Forks, MT"
    )


def test_add_comet(comet_service, test_comet, override_get_db):
    """Test adding a comet to the catalog."""
    comet_id = comet_service.add_comet(test_comet)
    assert comet_id is not None
    assert comet_id > 0


def test_get_comet_by_designation(comet_service, test_comet, override_get_db):
    """Test retrieving a comet by designation."""
    # Add comet first
    comet_service.add_comet(test_comet)

    # Retrieve it
    retrieved = comet_service.get_comet_by_designation("C/2020 F3")
    assert retrieved is not None
    assert retrieved.designation == "C/2020 F3"
    assert retrieved.name == "NEOWISE"
    assert retrieved.comet_type == "long-period"


def test_get_all_comets(comet_service, test_comet, override_get_db):
    """Test retrieving all comets."""
    # Add comet
    comet_service.add_comet(test_comet)

    # Retrieve all
    comets = comet_service.get_all_comets(limit=10)
    assert len(comets) > 0
    assert any(c.designation == "C/2020 F3" for c in comets)


def test_compute_ephemeris(comet_service, test_comet):
    """Test computing ephemeris for a comet."""
    time_utc = datetime(2020, 7, 15, 0, 0, 0)
    ephemeris = comet_service.compute_ephemeris(test_comet, time_utc)

    assert ephemeris is not None
    assert ephemeris.designation == "C/2020 F3"
    assert ephemeris.ra_hours is not None
    assert ephemeris.dec_degrees is not None
    assert ephemeris.helio_distance_au > 0
    assert ephemeris.geo_distance_au > 0
    assert ephemeris.magnitude is not None


def test_compute_visibility(comet_service, test_comet, test_location):
    """Test computing visibility for a comet."""
    time_utc = datetime(2020, 7, 15, 3, 0, 0)  # 9 PM local time
    visibility = comet_service.compute_visibility(test_comet, test_location, time_utc)

    assert visibility is not None
    assert visibility.comet.designation == "C/2020 F3"
    assert visibility.altitude_deg is not None
    assert visibility.azimuth_deg is not None
    assert isinstance(visibility.is_visible, bool)
    assert isinstance(visibility.is_dark_enough, bool)


def test_get_visible_comets(comet_service, test_comet, test_location, override_get_db):
    """Test getting all visible comets."""
    # Add comet
    comet_service.add_comet(test_comet)

    time_utc = datetime(2020, 7, 15, 3, 0, 0)
    visible = comet_service.get_visible_comets(
        location=test_location,
        time_utc=time_utc,
        min_altitude=0.0,
        max_magnitude=15.0
    )

    assert isinstance(visible, list)
    # Visibility depends on position and time, so just check structure
    for vis in visible:
        assert vis.comet is not None
        assert vis.ephemeris is not None
        assert vis.altitude_deg is not None


def test_orbital_elements_validation():
    """Test that orbital elements are properly validated."""
    # Test with valid eccentricity
    oe = OrbitalElements(
        epoch_jd=2459000.5,
        perihelion_distance_au=1.0,
        eccentricity=0.5,  # Elliptical
        inclination_deg=10.0,
        arg_perihelion_deg=45.0,
        ascending_node_deg=90.0,
        perihelion_time_jd=2459000.0
    )
    assert oe.eccentricity < 1.0

    # Test with hyperbolic orbit
    oe_hyp = OrbitalElements(
        epoch_jd=2459000.5,
        perihelion_distance_au=1.0,
        eccentricity=1.1,  # Hyperbolic
        inclination_deg=10.0,
        arg_perihelion_deg=45.0,
        ascending_node_deg=90.0,
        perihelion_time_jd=2459000.0
    )
    assert oe_hyp.eccentricity > 1.0


def test_comet_magnitude_calculation(comet_service):
    """Test that magnitude calculation works correctly."""
    # Create a comet with known magnitude parameters
    comet = CometTarget(
        designation="TEST",
        name="Test Comet",
        orbital_elements=OrbitalElements(
            epoch_jd=2459000.5,
            perihelion_distance_au=1.0,
            eccentricity=0.5,
            inclination_deg=10.0,
            arg_perihelion_deg=45.0,
            ascending_node_deg=90.0,
            perihelion_time_jd=2459000.0
        ),
        absolute_magnitude=5.0,
        magnitude_slope=4.0,
        current_magnitude=None,
        comet_type="short-period",
        activity_status="active",
        data_source="Test"
    )

    # Compute ephemeris
    time_utc = datetime(2020, 1, 1, 0, 0, 0)
    ephemeris = comet_service.compute_ephemeris(comet, time_utc)

    # Check that magnitude was calculated
    assert ephemeris.magnitude is not None
    # Magnitude should be reasonable (not NaN or extreme values)
    assert -5.0 < ephemeris.magnitude < 30.0
