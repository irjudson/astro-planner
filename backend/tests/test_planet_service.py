"""Tests for planet service."""

import pytest
from datetime import datetime
from app.services.planet_service import PlanetService, PLANET_DATA
from app.models import Location, PlanetTarget, PlanetEphemeris, PlanetVisibility


@pytest.fixture
def planet_service():
    """Create planet service."""
    return PlanetService()


@pytest.fixture
def sample_location():
    """Create sample observer location."""
    return Location(
        name="Test Observatory",
        latitude=45.0,
        longitude=-111.0,
        elevation=1500.0,
        timezone="America/Denver"
    )


class TestPlanetData:
    """Test PLANET_DATA static information."""

    def test_all_major_planets_present(self):
        """Test that all major planets are in data."""
        expected = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
        for planet in expected:
            assert planet in PLANET_DATA, f"Missing planet: {planet}"

    def test_moon_and_sun_present(self):
        """Test that Moon and Sun are in data."""
        assert "Moon" in PLANET_DATA
        assert "Sun" in PLANET_DATA

    def test_planet_data_has_required_fields(self):
        """Test that each planet has required fields."""
        required_fields = [
            "planet_type", "diameter_km", "orbital_period_days",
            "rotation_period_hours", "has_rings", "num_moons", "notes"
        ]
        for name, data in PLANET_DATA.items():
            for field in required_fields:
                assert field in data, f"{name} missing field: {field}"


class TestGetAllPlanets:
    """Test get_all_planets method."""

    def test_returns_list(self, planet_service):
        """Test returns a list."""
        result = planet_service.get_all_planets()
        assert isinstance(result, list)

    def test_returns_correct_count(self, planet_service):
        """Test returns correct number of planets."""
        result = planet_service.get_all_planets()
        assert len(result) == len(PLANET_DATA)

    def test_returns_planet_target_objects(self, planet_service):
        """Test returns PlanetTarget objects."""
        result = planet_service.get_all_planets()
        for planet in result:
            assert isinstance(planet, PlanetTarget)

    def test_jupiter_has_correct_data(self, planet_service):
        """Test Jupiter has correct static data."""
        planets = planet_service.get_all_planets()
        jupiter = next((p for p in planets if p.name == "Jupiter"), None)
        assert jupiter is not None
        assert jupiter.planet_type == "gas_giant"
        assert jupiter.has_rings is True
        assert jupiter.num_moons == 95

    def test_saturn_has_rings(self, planet_service):
        """Test Saturn has prominent rings."""
        planets = planet_service.get_all_planets()
        saturn = next((p for p in planets if p.name == "Saturn"), None)
        assert saturn is not None
        assert saturn.has_rings is True


class TestGetPlanetByName:
    """Test get_planet_by_name method."""

    def test_get_mars(self, planet_service):
        """Test getting Mars."""
        result = planet_service.get_planet_by_name("Mars")
        assert result is not None
        assert result.name == "Mars"
        assert result.planet_type == "terrestrial"

    def test_get_jupiter_lowercase(self, planet_service):
        """Test getting planet with lowercase name."""
        result = planet_service.get_planet_by_name("jupiter")
        assert result is not None
        assert result.name == "Jupiter"

    def test_get_planet_case_insensitive(self, planet_service):
        """Test case insensitivity."""
        result1 = planet_service.get_planet_by_name("SATURN")
        result2 = planet_service.get_planet_by_name("saturn")
        result3 = planet_service.get_planet_by_name("Saturn")
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.name == result2.name == result3.name

    def test_get_nonexistent_planet(self, planet_service):
        """Test getting non-existent planet returns None."""
        result = planet_service.get_planet_by_name("Pluto")
        assert result is None

    def test_get_with_whitespace(self, planet_service):
        """Test getting planet with extra whitespace."""
        result = planet_service.get_planet_by_name("  Venus  ")
        assert result is not None
        assert result.name == "Venus"


class TestComputeEphemeris:
    """Test compute_ephemeris method."""

    def test_compute_mars_ephemeris(self, planet_service):
        """Test computing Mars ephemeris."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Mars", time_utc)

        assert isinstance(result, PlanetEphemeris)
        assert result.name == "Mars"
        assert result.date_utc == time_utc
        assert 0 <= result.ra_hours < 24
        assert -90 <= result.dec_degrees <= 90
        assert result.distance_au > 0
        assert result.angular_diameter_arcsec > 0

    def test_compute_jupiter_ephemeris(self, planet_service):
        """Test computing Jupiter ephemeris."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Jupiter", time_utc)

        assert result.name == "Jupiter"
        # Jupiter is brighter (more negative magnitude) than Mars
        assert result.magnitude < 0  # Jupiter should be bright

    def test_compute_venus_ephemeris(self, planet_service):
        """Test computing Venus ephemeris."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Venus", time_utc)

        assert result.name == "Venus"
        # Venus is very bright
        assert result.magnitude < 0

    def test_ephemeris_has_julian_date(self, planet_service):
        """Test ephemeris includes Julian date."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Mars", time_utc)

        assert result.date_jd > 2450000  # Reasonable JD range

    def test_ephemeris_phase_percent(self, planet_service):
        """Test ephemeris includes phase percentage."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Mars", time_utc)

        # Phase should be between 0 and 100
        assert 0 <= result.phase_percent <= 100

    def test_compute_invalid_planet_raises(self, planet_service):
        """Test that invalid planet raises ValueError."""
        with pytest.raises(ValueError, match="Unknown planet"):
            planet_service.compute_ephemeris("Pluto", datetime.now())

    def test_ephemeris_case_insensitive(self, planet_service):
        """Test ephemeris with different case names."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("MARS", time_utc)
        assert result.name == "Mars"


class TestSunEphemeris:
    """Test Sun ephemeris computation."""

    def test_compute_sun_ephemeris(self, planet_service):
        """Test computing Sun ephemeris."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Sun", time_utc)

        assert result.name == "Sun"
        assert result.elongation_deg == 0.0  # Sun has no elongation from itself
        assert result.phase_percent == 100.0  # Sun is always "full"
        assert result.magnitude == -26.7  # Sun's magnitude

    def test_sun_angular_diameter(self, planet_service):
        """Test Sun angular diameter is large."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Sun", time_utc)

        # Sun should have large angular diameter (~32 arcmin = 1920 arcsec)
        assert result.angular_diameter_arcsec > 1800


class TestMoonEphemeris:
    """Test Moon ephemeris computation."""

    def test_compute_moon_ephemeris(self, planet_service):
        """Test computing Moon ephemeris."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Moon", time_utc)

        assert result.name == "Moon"
        assert 0 <= result.phase_percent <= 100

    def test_moon_distance_reasonable(self, planet_service):
        """Test Moon distance is in reasonable range."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_ephemeris("Moon", time_utc)

        # Moon distance is about 0.0026 AU (384,400 km / 149,597,870.7 km/AU)
        assert 0.002 < result.distance_au < 0.003


class TestHeliocentricDistance:
    """Test heliocentric distance calculation."""

    def test_mercury_heliocentric_distance(self, planet_service):
        """Test Mercury heliocentric distance."""
        from astropy.time import Time
        t = Time(datetime(2024, 6, 15, 12, 0, 0))
        dist = planet_service._get_heliocentric_distance("Mercury", t)

        # Mercury semi-major axis is ~0.387 AU
        assert 0.3 < dist < 0.5

    def test_mars_heliocentric_distance(self, planet_service):
        """Test Mars heliocentric distance."""
        from astropy.time import Time
        t = Time(datetime(2024, 6, 15, 12, 0, 0))
        dist = planet_service._get_heliocentric_distance("Mars", t)

        # Mars semi-major axis is ~1.52 AU
        assert 1.3 < dist < 1.7


class TestEstimateMagnitude:
    """Test magnitude estimation."""

    def test_jupiter_brighter_than_mars(self, planet_service):
        """Test Jupiter is brighter than Mars."""
        jupiter_mag = planet_service._estimate_magnitude(
            "Jupiter", 5.0, 5.2, 10.0
        )
        mars_mag = planet_service._estimate_magnitude(
            "Mars", 1.5, 1.52, 20.0
        )
        # Jupiter should be brighter (more negative magnitude)
        assert jupiter_mag < mars_mag

    def test_venus_is_very_bright(self, planet_service):
        """Test Venus magnitude calculation."""
        venus_mag = planet_service._estimate_magnitude(
            "Venus", 0.7, 0.72, 30.0
        )
        # Venus is very bright
        assert venus_mag < -3.0

    def test_magnitude_clamped(self, planet_service):
        """Test magnitude is clamped to reasonable range."""
        # Extreme values should still be clamped
        mag = planet_service._estimate_magnitude(
            "Neptune", 50.0, 30.0, 180.0  # Very extreme values
        )
        assert -10.0 <= mag <= 20.0


class TestComputeVisibility:
    """Test compute_visibility method."""

    def test_compute_mars_visibility(self, planet_service, sample_location):
        """Test computing Mars visibility."""
        time_utc = datetime(2024, 6, 15, 2, 0, 0)  # Night time
        result = planet_service.compute_visibility("Mars", sample_location, time_utc)

        assert isinstance(result, PlanetVisibility)
        assert isinstance(result.planet, PlanetTarget)
        assert isinstance(result.ephemeris, PlanetEphemeris)
        assert -90 <= result.altitude_deg <= 90
        assert 0 <= result.azimuth_deg <= 360
        assert isinstance(result.is_visible, bool)
        assert isinstance(result.is_daytime, bool)

    def test_visibility_invalid_planet_raises(self, planet_service, sample_location):
        """Test visibility with invalid planet raises ValueError."""
        with pytest.raises(ValueError, match="Unknown planet"):
            planet_service.compute_visibility("Pluto", sample_location, datetime.now())

    def test_visibility_at_night(self, planet_service, sample_location):
        """Test visibility calculation at night."""
        time_utc = datetime(2024, 6, 15, 6, 0, 0)  # 6 AM UTC = midnight MDT
        result = planet_service.compute_visibility("Jupiter", sample_location, time_utc)

        # Should correctly determine if it's night
        assert isinstance(result.is_daytime, bool)

    def test_elongation_check(self, planet_service, sample_location):
        """Test elongation check for visibility."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.compute_visibility("Jupiter", sample_location, time_utc)

        # elongation_ok should be a boolean
        assert isinstance(result.elongation_ok, bool)


class TestRiseSetTimes:
    """Test rise/set time calculation."""

    def test_calculate_rise_set_returns_tuple(self, planet_service, sample_location):
        """Test rise/set calculation returns tuple."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        rise, set_time = planet_service._calculate_rise_set_times(
            "Jupiter", sample_location, time_utc
        )

        # Should return tuple of (datetime or None, datetime or None)
        assert rise is None or isinstance(rise, datetime)
        assert set_time is None or isinstance(set_time, datetime)


class TestGetVisiblePlanets:
    """Test get_visible_planets method."""

    def test_returns_list(self, planet_service, sample_location):
        """Test returns a list."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.get_visible_planets(sample_location, time_utc)

        assert isinstance(result, list)

    def test_returns_visibility_objects(self, planet_service, sample_location):
        """Test returns PlanetVisibility objects."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.get_visible_planets(sample_location, time_utc)

        for item in result:
            assert isinstance(item, PlanetVisibility)

    def test_sorted_by_altitude(self, planet_service, sample_location):
        """Test results are sorted by altitude (highest first)."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.get_visible_planets(
            sample_location, time_utc, include_daytime=True
        )

        if len(result) > 1:
            altitudes = [v.altitude_deg for v in result]
            assert altitudes == sorted(altitudes, reverse=True)

    def test_min_altitude_filter(self, planet_service, sample_location):
        """Test minimum altitude filter."""
        time_utc = datetime(2024, 6, 15, 12, 0, 0)
        result = planet_service.get_visible_planets(
            sample_location, time_utc, min_altitude=30.0, include_daytime=True
        )

        for visibility in result:
            assert visibility.altitude_deg >= 30.0

    def test_include_daytime_option(self, planet_service, sample_location):
        """Test include_daytime option works."""
        # Daytime UTC
        time_utc = datetime(2024, 6, 15, 18, 0, 0)  # 18:00 UTC = noon MDT

        with_daytime = planet_service.get_visible_planets(
            sample_location, time_utc, include_daytime=True
        )
        without_daytime = planet_service.get_visible_planets(
            sample_location, time_utc, include_daytime=False
        )

        # With daytime should have >= planets than without
        assert len(with_daytime) >= len(without_daytime)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_extreme_latitude(self, planet_service):
        """Test with extreme latitude location."""
        arctic_location = Location(
            name="Arctic",
            latitude=89.0,
            longitude=0.0,
            elevation=0.0,
            timezone="UTC"
        )
        time_utc = datetime(2024, 6, 15, 12, 0, 0)

        # Should not crash
        result = planet_service.compute_visibility(
            "Jupiter", arctic_location, time_utc
        )
        assert isinstance(result, PlanetVisibility)

    def test_southern_hemisphere(self, planet_service):
        """Test with southern hemisphere location."""
        sydney = Location(
            name="Sydney",
            latitude=-33.87,
            longitude=151.21,
            elevation=58.0,
            timezone="Australia/Sydney"
        )
        time_utc = datetime(2024, 6, 15, 12, 0, 0)

        result = planet_service.get_visible_planets(sydney, time_utc)
        assert isinstance(result, list)

    def test_different_times_give_different_results(self, planet_service, sample_location):
        """Test that different times give different ephemeris results."""
        time1 = datetime(2024, 6, 15, 12, 0, 0)
        time2 = datetime(2024, 7, 15, 12, 0, 0)  # One month later

        result1 = planet_service.compute_ephemeris("Mars", time1)
        result2 = planet_service.compute_ephemeris("Mars", time2)

        # Position should change over a month
        assert result1.ra_hours != result2.ra_hours or result1.dec_degrees != result2.dec_degrees
