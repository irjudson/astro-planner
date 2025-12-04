"""Tests for planet service."""

import pytest
from datetime import datetime, timedelta
import pytz

from app.services.planet_service import PlanetService, PLANET_DATA
from app.models import Location, PlanetTarget, PlanetEphemeris, PlanetVisibility


@pytest.fixture
def sample_location():
    """Sample location for testing."""
    return Location(
        name="Three Forks, MT",
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234.0,
        timezone="America/Denver"
    )


@pytest.mark.slow
class TestPlanetService:
    """Test planet service."""

    def test_get_all_planets(self):
        """Test retrieving all planets."""
        service = PlanetService()
        planets = service.get_all_planets()

        # Should have all planets in PLANET_DATA
        assert len(planets) == len(PLANET_DATA)
        assert all(isinstance(p, PlanetTarget) for p in planets)

        # Check that all expected planets are present
        planet_names = [p.name for p in planets]
        assert "Mercury" in planet_names
        assert "Venus" in planet_names
        assert "Mars" in planet_names
        assert "Jupiter" in planet_names
        assert "Saturn" in planet_names
        assert "Uranus" in planet_names
        assert "Neptune" in planet_names
        assert "Moon" in planet_names
        assert "Sun" in planet_names

    def test_get_planet_by_name_valid(self):
        """Test getting a specific planet by name."""
        service = PlanetService()

        # Test with exact case
        jupiter = service.get_planet_by_name("Jupiter")
        assert jupiter is not None
        assert jupiter.name == "Jupiter"
        assert jupiter.planet_type == "gas_giant"
        assert jupiter.num_moons == 95

        # Test with lowercase
        mars = service.get_planet_by_name("mars")
        assert mars is not None
        assert mars.name == "Mars"
        assert mars.planet_type == "terrestrial"

        # Test with uppercase
        venus = service.get_planet_by_name("VENUS")
        assert venus is not None
        assert venus.name == "Venus"

    def test_get_planet_by_name_invalid(self):
        """Test getting planet with invalid name."""
        service = PlanetService()

        result = service.get_planet_by_name("InvalidPlanet")
        assert result is None

        result = service.get_planet_by_name("")
        assert result is None

    def test_get_planet_by_name_with_whitespace(self):
        """Test getting planet with whitespace in name."""
        service = PlanetService()

        result = service.get_planet_by_name("  Saturn  ")
        assert result is not None
        assert result.name == "Saturn"

    def test_compute_ephemeris_jupiter(self):
        """Test ephemeris computation for Jupiter."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)

        ephemeris = service.compute_ephemeris("Jupiter", time_utc)

        assert isinstance(ephemeris, PlanetEphemeris)
        assert ephemeris.name == "Jupiter"
        assert ephemeris.date_utc == time_utc
        assert 0 <= ephemeris.ra_hours < 24
        assert -90 <= ephemeris.dec_degrees <= 90
        assert ephemeris.distance_au > 0
        assert ephemeris.magnitude < 0  # Jupiter is bright
        assert ephemeris.angular_diameter_arcsec > 0
        assert 0 <= ephemeris.phase_percent <= 100
        assert 0 <= ephemeris.elongation_deg <= 180

    def test_compute_ephemeris_sun(self):
        """Test ephemeris computation for Sun."""
        service = PlanetService()
        time_utc = datetime(2025, 6, 21, 12, 0, 0, tzinfo=pytz.UTC)  # Summer solstice

        ephemeris = service.compute_ephemeris("Sun", time_utc)

        assert isinstance(ephemeris, PlanetEphemeris)
        assert ephemeris.name == "Sun"
        assert ephemeris.elongation_deg == 0.0  # Sun's elongation from itself is 0
        assert ephemeris.phase_percent == 100.0  # Sun is always "full"
        assert ephemeris.magnitude == -26.7  # Sun's apparent magnitude
        assert ephemeris.distance_au > 0
        assert ephemeris.angular_diameter_arcsec > 1800  # Sun's angular diameter ~1920"

    def test_compute_ephemeris_moon(self):
        """Test ephemeris computation for Moon."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)

        ephemeris = service.compute_ephemeris("Moon", time_utc)

        assert isinstance(ephemeris, PlanetEphemeris)
        assert ephemeris.name == "Moon"
        assert 0 <= ephemeris.ra_hours < 24
        assert -90 <= ephemeris.dec_degrees <= 90
        assert 0 < ephemeris.distance_au < 0.01  # Moon is close
        assert 0 <= ephemeris.phase_percent <= 100
        assert -15 < ephemeris.magnitude < -8  # Moon magnitude range
        assert ephemeris.angular_diameter_arcsec > 1700  # Moon's angular diameter ~1800-2000"

    def test_compute_ephemeris_mars(self):
        """Test ephemeris computation for Mars."""
        service = PlanetService()
        time_utc = datetime(2025, 3, 15, 0, 0, 0, tzinfo=pytz.UTC)

        ephemeris = service.compute_ephemeris("Mars", time_utc)

        assert isinstance(ephemeris, PlanetEphemeris)
        assert ephemeris.name == "Mars"
        assert 0 <= ephemeris.ra_hours < 24
        assert -90 <= ephemeris.dec_degrees <= 90
        assert ephemeris.distance_au > 0
        assert -3 < ephemeris.magnitude < 2  # Mars magnitude range
        assert 0 <= ephemeris.phase_percent <= 100
        assert 0 <= ephemeris.elongation_deg <= 180

    def test_compute_ephemeris_invalid_planet(self):
        """Test ephemeris computation with invalid planet."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)

        with pytest.raises(ValueError, match="Unknown planet"):
            service.compute_ephemeris("InvalidPlanet", time_utc)

    def test_estimate_magnitude_mercury(self):
        """Test magnitude estimation for Mercury."""
        service = PlanetService()

        # Mercury at various distances and phase angles
        mag = service._estimate_magnitude("Mercury", 0.8, 0.4, 45.0)
        assert -4 < mag < 2  # Mercury magnitude range (can be very bright when close)

        # At opposition (brighter)
        mag_opposition = service._estimate_magnitude("Mercury", 0.6, 0.4, 10.0)
        assert -4 < mag_opposition < 1  # Can reach magnitude -3.3 when very close

    def test_estimate_magnitude_venus(self):
        """Test magnitude estimation for Venus."""
        service = PlanetService()

        # Venus is the brightest planet
        mag = service._estimate_magnitude("Venus", 0.7, 0.72, 30.0)
        assert -5 < mag < -3  # Venus magnitude range

    def test_estimate_magnitude_outer_planets(self):
        """Test magnitude estimation for outer planets."""
        service = PlanetService()

        # Jupiter
        mag_jupiter = service._estimate_magnitude("Jupiter", 5.2, 5.2, 11.0)
        assert -3 < mag_jupiter < 0  # Jupiter is bright

        # Saturn
        mag_saturn = service._estimate_magnitude("Saturn", 9.5, 9.5, 6.0)
        assert -1 < mag_saturn < 2  # Saturn varies with rings

        # Uranus
        mag_uranus = service._estimate_magnitude("Uranus", 19.2, 19.2, 3.0)
        assert 5 < mag_uranus < 7  # Uranus is faint

        # Neptune
        mag_neptune = service._estimate_magnitude("Neptune", 29.1, 29.1, 2.0)
        assert 7 < mag_neptune < 9  # Neptune is very faint

    def test_get_heliocentric_distance(self):
        """Test heliocentric distance calculation."""
        service = PlanetService()
        from astropy.time import Time

        time = Time(datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC))

        # Mercury should be close to Sun
        dist_mercury = service._get_heliocentric_distance("Mercury", time)
        assert 0.3 < dist_mercury < 0.5

        # Mars
        dist_mars = service._get_heliocentric_distance("Mars", time)
        assert 1.3 < dist_mars < 1.7

        # Jupiter
        dist_jupiter = service._get_heliocentric_distance("Jupiter", time)
        assert 4.5 < dist_jupiter < 5.5

        # Neptune (farthest)
        dist_neptune = service._get_heliocentric_distance("Neptune", time)
        assert 28 < dist_neptune < 32

    def test_compute_visibility_above_horizon(self, sample_location):
        """Test visibility computation when planet is above horizon."""
        service = PlanetService()

        # Use a time when Jupiter is typically visible
        # Evening time
        time_utc = datetime(2025, 1, 15, 2, 0, 0, tzinfo=pytz.UTC)  # 7pm local

        visibility = service.compute_visibility("Jupiter", sample_location, time_utc)

        assert isinstance(visibility, PlanetVisibility)
        assert visibility.planet.name == "Jupiter"
        assert isinstance(visibility.ephemeris, PlanetEphemeris)
        assert -90 <= visibility.altitude_deg <= 90
        assert 0 <= visibility.azimuth_deg <= 360
        assert isinstance(visibility.is_visible, bool)
        assert isinstance(visibility.is_daytime, bool)
        assert isinstance(visibility.elongation_ok, bool)
        assert isinstance(visibility.recommended, bool)

    def test_compute_visibility_sun(self, sample_location):
        """Test visibility computation for Sun."""
        service = PlanetService()

        # Midday
        time_utc = datetime(2025, 6, 21, 19, 0, 0, tzinfo=pytz.UTC)  # Noon local

        visibility = service.compute_visibility("Sun", sample_location, time_utc)

        assert visibility.planet.name == "Sun"
        # Sun should be visible during day
        assert visibility.is_daytime
        # Sun elongation from itself is 0, so elongation_ok will be False
        assert not visibility.elongation_ok

    def test_compute_visibility_invalid_planet(self, sample_location):
        """Test visibility with invalid planet name."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)

        with pytest.raises(ValueError, match="Unknown planet"):
            service.compute_visibility("InvalidPlanet", sample_location, time_utc)

    def test_get_visible_planets_basic(self, sample_location):
        """Test getting list of visible planets."""
        service = PlanetService()

        # Evening time
        time_utc = datetime(2025, 1, 15, 2, 0, 0, tzinfo=pytz.UTC)

        visible = service.get_visible_planets(sample_location, time_utc)

        # Should return a list
        assert isinstance(visible, list)
        assert all(isinstance(v, PlanetVisibility) for v in visible)

        # All returned planets should meet visibility criteria
        for v in visible:
            assert v.altitude_deg >= 0  # Above horizon

        # Should be sorted by altitude (highest first)
        if len(visible) > 1:
            for i in range(len(visible) - 1):
                assert visible[i].altitude_deg >= visible[i + 1].altitude_deg

    def test_get_visible_planets_with_min_altitude(self, sample_location):
        """Test getting visible planets with minimum altitude filter."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 15, 2, 0, 0, tzinfo=pytz.UTC)

        # Get planets above 30 degrees
        visible = service.get_visible_planets(
            sample_location,
            time_utc,
            min_altitude=30.0
        )

        # All should be above 30 degrees
        for v in visible:
            assert v.altitude_deg >= 30.0

    def test_get_visible_planets_daytime_filter(self, sample_location):
        """Test daytime filtering."""
        service = PlanetService()

        # Midday time
        time_utc = datetime(2025, 6, 21, 19, 0, 0, tzinfo=pytz.UTC)

        # Without daytime planets
        visible_no_daytime = service.get_visible_planets(
            sample_location,
            time_utc,
            include_daytime=False
        )

        # With daytime planets (Venus might be visible)
        visible_with_daytime = service.get_visible_planets(
            sample_location,
            time_utc,
            include_daytime=True
        )

        # With daytime should have >= without daytime
        assert len(visible_with_daytime) >= len(visible_no_daytime)

    def test_calculate_rise_set_times(self, sample_location):
        """Test rise and set time calculation."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)

        rise_time, set_time = service._calculate_rise_set_times(
            "Jupiter",
            sample_location,
            time_utc
        )

        # Should return datetime objects or None
        if rise_time is not None:
            assert isinstance(rise_time, datetime)
            # Rise time should be within 24 hours
            assert time_utc <= rise_time <= time_utc + timedelta(hours=24)

        if set_time is not None:
            assert isinstance(set_time, datetime)
            # Set time should be within 24 hours
            assert time_utc <= set_time <= time_utc + timedelta(hours=24)

    def test_planet_data_completeness(self):
        """Test that all planets have required data fields."""
        required_fields = [
            "planet_type",
            "diameter_km",
            "orbital_period_days",
            "rotation_period_hours",
            "has_rings",
            "num_moons",
            "notes"
        ]

        for planet_name, planet_data in PLANET_DATA.items():
            for field in required_fields:
                assert field in planet_data, f"{planet_name} missing {field}"

    def test_planet_types(self):
        """Test that planet types are correct."""
        service = PlanetService()
        planets = service.get_all_planets()

        # Check specific planet types
        type_map = {
            "Mercury": "terrestrial",
            "Venus": "terrestrial",
            "Mars": "terrestrial",
            "Jupiter": "gas_giant",
            "Saturn": "gas_giant",
            "Uranus": "ice_giant",
            "Neptune": "ice_giant",
            "Moon": "satellite",
            "Sun": "star"
        }

        for planet in planets:
            assert planet.planet_type == type_map[planet.name]

    def test_gas_giants_have_rings(self):
        """Test that gas giants have ring systems."""
        service = PlanetService()

        jupiter = service.get_planet_by_name("Jupiter")
        assert jupiter.has_rings  # Jupiter has faint rings

        saturn = service.get_planet_by_name("Saturn")
        assert saturn.has_rings  # Saturn has prominent rings

    def test_terrestrial_planets_no_rings(self):
        """Test that terrestrial planets don't have rings."""
        service = PlanetService()

        mercury = service.get_planet_by_name("Mercury")
        assert not mercury.has_rings

        venus = service.get_planet_by_name("Venus")
        assert not venus.has_rings

        mars = service.get_planet_by_name("Mars")
        assert not mars.has_rings

    def test_planet_moon_counts(self):
        """Test that moon counts are reasonable."""
        service = PlanetService()

        # Planets with no moons
        mercury = service.get_planet_by_name("Mercury")
        assert mercury.num_moons == 0

        venus = service.get_planet_by_name("Venus")
        assert venus.num_moons == 0

        # Planets with many moons
        jupiter = service.get_planet_by_name("Jupiter")
        assert jupiter.num_moons >= 50  # Jupiter has many moons

        saturn = service.get_planet_by_name("Saturn")
        assert saturn.num_moons >= 50  # Saturn has many moons

    def test_magnitude_clamping(self):
        """Test that magnitude estimation is clamped to reasonable range."""
        service = PlanetService()

        # Test with extreme values
        mag = service._estimate_magnitude("Jupiter", 100.0, 100.0, 180.0)
        assert -10.0 <= mag <= 20.0  # Should be clamped

        mag = service._estimate_magnitude("Venus", 0.01, 0.01, 0.0)
        assert -10.0 <= mag <= 20.0  # Should be clamped

    def test_phase_percent_range(self):
        """Test that phase percent is always in valid range."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)

        # Test multiple planets
        for planet_name in ["Mercury", "Venus", "Mars", "Jupiter"]:
            ephemeris = service.compute_ephemeris(planet_name, time_utc)
            assert 0 <= ephemeris.phase_percent <= 100

    def test_elongation_range(self):
        """Test that elongation is in valid range."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 1, 0, 0, 0, tzinfo=pytz.UTC)

        # Test multiple planets
        for planet_name in ["Mercury", "Venus", "Mars", "Jupiter"]:
            ephemeris = service.compute_ephemeris(planet_name, time_utc)
            assert 0 <= ephemeris.elongation_deg <= 180

    def test_venus_daytime_observability(self, sample_location):
        """Test that Venus can be observed during daytime."""
        service = PlanetService()

        # Venus should be bright enough for daytime observation
        venus = service.get_planet_by_name("Venus")
        assert venus.planet_type == "terrestrial"

        # Test visibility calculation considers Venus for daytime
        time_utc = datetime(2025, 3, 15, 18, 0, 0, tzinfo=pytz.UTC)
        visibility = service.compute_visibility("Venus", sample_location, time_utc)

        # Venus magnitude should be very bright
        assert visibility.ephemeris.magnitude < -3.0

    def test_compute_visibility_rise_set_times(self, sample_location):
        """Test that visibility includes rise and set times."""
        service = PlanetService()
        time_utc = datetime(2025, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)

        visibility = service.compute_visibility("Mars", sample_location, time_utc)

        # Rise and set times might be None or datetime
        if visibility.rise_time is not None:
            assert isinstance(visibility.rise_time, datetime)

        if visibility.set_time is not None:
            assert isinstance(visibility.set_time, datetime)
