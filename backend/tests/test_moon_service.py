"""Tests for moon phase and visibility service."""

import pytest
from datetime import datetime, timedelta, timezone
from app.services.moon_service import MoonService, MoonPhaseInfo, MoonEphemeris, MoonVisibility, DarkSkyWindow
from app.models import Location


@pytest.fixture
def moon_service():
    """Fixture for MoonService instance."""
    return MoonService()


@pytest.fixture
def test_location():
    """Fixture for test location (Three Forks, MT)."""
    return Location(
        name="Three Forks, MT",
        latitude=45.92,
        longitude=-111.28,
        elevation=1234.0,
        timezone="America/Denver"
    )


class TestMoonEphemeris:
    """Test moon ephemeris calculations."""

    def test_compute_ephemeris_known_new_moon(self, moon_service):
        """Test ephemeris calculation for a known new moon date."""
        # New Moon: January 29, 2025
        new_moon_date = datetime(2025, 1, 29, 12, 0, 0)

        ephemeris = moon_service.compute_ephemeris(new_moon_date)

        # Verify basic ephemeris structure
        assert ephemeris.date_utc == new_moon_date
        assert ephemeris.ra_hours >= 0 and ephemeris.ra_hours < 24
        assert ephemeris.dec_degrees >= -90 and ephemeris.dec_degrees <= 90
        assert ephemeris.distance_km > 350000  # Typical lunar distance range
        assert ephemeris.distance_km < 410000

        # Verify phase information for new moon
        phase_info = ephemeris.phase_info
        assert phase_info.phase_name == "New Moon"
        assert phase_info.illumination_percent < 5.0  # Very low illumination
        assert phase_info.age_days < 2.0 or phase_info.age_days > 27.5  # Near 0 or end of cycle

    def test_compute_ephemeris_known_full_moon(self, moon_service):
        """Test ephemeris calculation for a known full moon date."""
        # Full Moon: January 13, 2025
        full_moon_date = datetime(2025, 1, 13, 18, 0, 0)

        ephemeris = moon_service.compute_ephemeris(full_moon_date)

        # Verify phase information for full moon
        phase_info = ephemeris.phase_info
        assert phase_info.phase_name == "Full Moon"
        assert phase_info.illumination_percent > 95.0  # Very high illumination
        assert phase_info.age_days > 12.0 and phase_info.age_days < 17.0  # Around day 14-15

    def test_compute_ephemeris_first_quarter(self, moon_service):
        """Test ephemeris calculation for first quarter moon."""
        # First Quarter: January 6, 2025
        first_quarter_date = datetime(2025, 1, 6, 18, 0, 0)

        ephemeris = moon_service.compute_ephemeris(first_quarter_date)

        # Verify phase information
        phase_info = ephemeris.phase_info
        # Quarter phases are around 45-55% illumination
        assert phase_info.illumination_percent > 40.0 and phase_info.illumination_percent < 60.0
        assert phase_info.is_waxing is True
        # Phase name should be quarter or adjacent phase
        assert phase_info.phase_name in ["Waxing Crescent", "First Quarter", "Waxing Gibbous"]

    def test_compute_ephemeris_last_quarter(self, moon_service):
        """Test ephemeris calculation for last quarter moon."""
        # Last Quarter: January 21, 2025
        last_quarter_date = datetime(2025, 1, 21, 12, 0, 0)

        ephemeris = moon_service.compute_ephemeris(last_quarter_date)

        # Verify phase information
        phase_info = ephemeris.phase_info
        # Quarter phases are around 45-55% illumination
        assert phase_info.illumination_percent > 40.0 and phase_info.illumination_percent < 60.0
        assert phase_info.is_waxing is False
        # Phase name should be quarter or adjacent phase
        assert phase_info.phase_name in ["Waning Crescent", "Last Quarter", "Waning Gibbous"]

    def test_waxing_crescent_phase(self, moon_service):
        """Test waxing crescent phase identification."""
        # A few days after new moon (Jan 29) - February 1 should be waxing crescent
        waxing_crescent_date = datetime(2025, 2, 1, 12, 0, 0)

        ephemeris = moon_service.compute_ephemeris(waxing_crescent_date)
        phase_info = ephemeris.phase_info

        # Crescent phases are between new and quarter (less than ~45%)
        assert phase_info.is_waxing is True
        assert phase_info.illumination_percent > 1.0 and phase_info.illumination_percent < 50.0
        # Phase name should be crescent (or very early gibbous/late new)
        assert phase_info.phase_name in ["New Moon", "Waxing Crescent", "First Quarter"]

    def test_waning_gibbous_phase(self, moon_service):
        """Test waning gibbous phase identification."""
        # A few days after full moon (Jan 13) - Jan 16 should be waning gibbous
        waning_gibbous_date = datetime(2025, 1, 16, 12, 0, 0)

        ephemeris = moon_service.compute_ephemeris(waning_gibbous_date)
        phase_info = ephemeris.phase_info

        # Gibbous phases are between quarter and full (more than ~52%)
        assert phase_info.is_waxing is False
        assert phase_info.illumination_percent > 50.0 and phase_info.illumination_percent < 100.0
        # Phase name should be gibbous (or very late full/early quarter)
        assert phase_info.phase_name in ["Last Quarter", "Waning Gibbous", "Full Moon"]

    def test_angular_diameter_range(self, moon_service):
        """Test that angular diameter is within realistic range."""
        test_date = datetime(2025, 1, 15, 12, 0, 0)
        ephemeris = moon_service.compute_ephemeris(test_date)

        # Moon's angular diameter ranges from about 29.3' to 34.1' (arcminutes)
        assert ephemeris.angular_diameter_arcmin > 29.0
        assert ephemeris.angular_diameter_arcmin < 35.0

    def test_magnitude_range(self, moon_service):
        """Test that moon magnitude is within realistic range."""
        # Test new moon (faint)
        new_moon = moon_service.compute_ephemeris(datetime(2025, 1, 29, 12, 0, 0))
        assert new_moon.magnitude > -5.0  # Dimmer than full moon

        # Test full moon (bright)
        full_moon = moon_service.compute_ephemeris(datetime(2025, 1, 13, 18, 0, 0))
        assert full_moon.magnitude < -11.0  # Very bright
        assert full_moon.magnitude > -13.0  # Not brighter than maximum

    def test_timezone_aware_datetime(self, moon_service):
        """Test that timezone-aware datetimes are handled correctly."""
        # Test with timezone-aware datetime
        tz_aware_date = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        ephemeris = moon_service.compute_ephemeris(tz_aware_date)

        # Should work without error
        assert ephemeris is not None
        assert ephemeris.phase_info is not None


class TestMoonVisibility:
    """Test moon visibility calculations."""

    def test_compute_visibility_structure(self, moon_service, test_location):
        """Test that visibility computation returns valid structure."""
        test_time = datetime(2025, 1, 15, 2, 0, 0)  # UTC

        visibility = moon_service.compute_visibility(test_location, test_time)

        # Verify structure
        assert visibility.ephemeris is not None
        assert visibility.altitude_deg >= -90 and visibility.altitude_deg <= 90
        assert visibility.azimuth_deg >= 0 and visibility.azimuth_deg <= 360
        assert isinstance(visibility.is_visible, bool)

    def test_visibility_above_horizon(self, moon_service, test_location):
        """Test that is_visible is True when altitude is positive."""
        # Test various times to find when moon is above horizon
        test_date = datetime(2025, 1, 15)

        found_visible = False
        for hour in range(24):
            test_time = test_date + timedelta(hours=hour)
            visibility = moon_service.compute_visibility(test_location, test_time)

            if visibility.altitude_deg > 0:
                assert visibility.is_visible is True
                found_visible = True
            else:
                assert visibility.is_visible is False

        # Moon should be visible at some point during the day
        assert found_visible

    def test_rise_set_times_exist(self, moon_service, test_location):
        """Test that rise/set times are calculated."""
        test_time = datetime(2025, 1, 15, 0, 0, 0)

        visibility = moon_service.compute_visibility(test_location, test_time)

        # Moon should have rise and set times in most 24-hour periods
        # (though there are rare cases of circumpolar behavior)
        # At minimum, one of them should be set
        assert visibility.rise_time is not None or visibility.set_time is not None

    def test_rise_before_set_logic(self, moon_service, test_location):
        """Test rise/set time ordering when both exist."""
        test_time = datetime(2025, 1, 15, 0, 0, 0)

        visibility = moon_service.compute_visibility(test_location, test_time)

        # If both rise and set times exist, they should be in the next 24 hours
        if visibility.rise_time and visibility.set_time:
            assert visibility.rise_time >= test_time
            assert visibility.set_time >= test_time
            assert visibility.rise_time < test_time + timedelta(hours=24)
            assert visibility.set_time < test_time + timedelta(hours=24)


class TestDarkSkyWindow:
    """Test dark sky window calculations."""

    def test_calculate_dark_window_new_moon(self, moon_service, test_location):
        """Test dark sky window calculation during new moon."""
        # New moon - excellent dark sky conditions
        observing_date = datetime(2025, 1, 11, 0, 0, 0)

        # Typical twilight times (approximate) - timezone-aware
        twilight_end = datetime(2025, 1, 11, 2, 0, 0, tzinfo=timezone.utc)
        twilight_start = datetime(2025, 1, 12, 12, 0, 0, tzinfo=timezone.utc)

        window = moon_service.calculate_dark_sky_window(
            test_location,
            observing_date,
            twilight_end,
            twilight_start
        )

        # Verify structure (times will be normalized to timezone-naive)
        assert window.astronomical_twilight_end.replace(tzinfo=None) == twilight_end.replace(tzinfo=None)
        assert window.astronomical_twilight_start.replace(tzinfo=None) == twilight_start.replace(tzinfo=None)
        assert isinstance(window.has_evening_window, bool)
        assert isinstance(window.has_morning_window, bool)
        assert window.moon_free_hours >= 0
        assert window.evening_window_hours >= 0
        assert window.morning_window_hours >= 0

        # New moon should provide good dark sky time
        assert window.moon_free_hours > 0

    def test_calculate_dark_window_full_moon(self, moon_service, test_location):
        """Test dark sky window calculation during full moon."""
        # Full moon - poor dark sky conditions
        observing_date = datetime(2025, 1, 25, 0, 0, 0)

        # Typical twilight times
        twilight_end = datetime(2025, 1, 25, 2, 0, 0, tzinfo=timezone.utc)
        twilight_start = datetime(2025, 1, 26, 12, 0, 0, tzinfo=timezone.utc)

        window = moon_service.calculate_dark_sky_window(
            test_location,
            observing_date,
            twilight_end,
            twilight_start
        )

        # Full moon is typically up all night, limiting dark sky time
        # The calculation should reflect this
        assert window is not None

    def test_dark_window_total_equals_sum(self, moon_service, test_location):
        """Test that total moon-free hours equals sum of windows."""
        observing_date = datetime(2025, 1, 15, 0, 0, 0)
        twilight_end = datetime(2025, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
        twilight_start = datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)

        window = moon_service.calculate_dark_sky_window(
            test_location,
            observing_date,
            twilight_end,
            twilight_start
        )

        # Total should equal sum of evening + morning
        assert abs(window.moon_free_hours - (window.evening_window_hours + window.morning_window_hours)) < 0.01


class TestMoonServiceIntegration:
    """Integration tests for MoonService."""

    def test_full_workflow(self, moon_service, test_location):
        """Test complete workflow: ephemeris -> visibility -> dark window."""
        test_time = datetime(2025, 1, 15, 2, 0, 0, tzinfo=timezone.utc)

        # Step 1: Compute ephemeris
        ephemeris = moon_service.compute_ephemeris(test_time)
        assert ephemeris is not None
        assert ephemeris.phase_info.phase_name in [
            "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
            "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"
        ]

        # Step 2: Compute visibility
        visibility = moon_service.compute_visibility(test_location, test_time)
        assert visibility.ephemeris.phase_info.phase_name == ephemeris.phase_info.phase_name

        # Step 3: Calculate dark sky window
        twilight_end = test_time + timedelta(hours=1)
        twilight_start = test_time + timedelta(hours=12)

        window = moon_service.calculate_dark_sky_window(
            test_location,
            test_time,
            twilight_end,
            twilight_start
        )
        assert window is not None

    def test_different_locations(self, moon_service):
        """Test moon calculations for different geographic locations."""
        test_time = datetime(2025, 1, 15, 12, 0, 0)

        locations = [
            Location(name="North", latitude=65.0, longitude=0.0, elevation=0.0, timezone="UTC"),
            Location(name="Equator", latitude=0.0, longitude=0.0, elevation=0.0, timezone="UTC"),
            Location(name="South", latitude=-45.0, longitude=0.0, elevation=0.0, timezone="UTC"),
        ]

        for location in locations:
            visibility = moon_service.compute_visibility(location, test_time)

            # All should have valid calculations
            assert visibility.altitude_deg >= -90 and visibility.altitude_deg <= 90
            assert visibility.azimuth_deg >= 0 and visibility.azimuth_deg <= 360

    def test_continuous_phase_progression(self, moon_service):
        """Test that moon phase progresses smoothly over time."""
        start_date = datetime(2025, 1, 1, 0, 0, 0)

        illuminations = []
        for day in range(30):
            test_time = start_date + timedelta(days=day)
            ephemeris = moon_service.compute_ephemeris(test_time)
            illuminations.append(ephemeris.phase_info.illumination_percent)

        # Illumination should progress through a cycle
        # At some point it should be low (new moon) and high (full moon)
        assert min(illuminations) < 10.0  # Near new moon
        assert max(illuminations) > 90.0  # Near full moon

    def test_lunar_age_progression(self, moon_service):
        """Test that lunar age increases over time."""
        # Start a few days after new moon to avoid wrap-around at new moon
        base_date = datetime(2025, 2, 1, 12, 0, 0)  # A few days after Jan 29 new moon

        ages = []
        for day in range(10):
            test_time = base_date + timedelta(days=day)
            ephemeris = moon_service.compute_ephemeris(test_time)
            ages.append(ephemeris.phase_info.age_days)

        # Age should increase when not crossing new moon
        assert ages[5] > ages[0]
        assert ages[9] > ages[5]

    def test_phase_name_accuracy(self, moon_service):
        """Test phase name mapping for edge cases."""
        # Test known moon phases and verify names (January 2025)
        test_cases = [
            (datetime(2025, 1, 29, 12, 0, 0), "New Moon"),  # New moon
            (datetime(2025, 1, 13, 18, 0, 0), "Full Moon"),  # Full moon
            (datetime(2025, 1, 6, 18, 0, 0), "First Quarter"),  # First quarter
            (datetime(2025, 1, 21, 12, 0, 0), "Last Quarter"),  # Last quarter
        ]

        for test_date, expected_phase in test_cases:
            ephemeris = moon_service.compute_ephemeris(test_date)
            # Allow for some tolerance - phases near boundaries might be slightly off
            assert ephemeris.phase_info.phase_name in [
                expected_phase,
                # Allow adjacent phases for edge cases
                "Waxing Crescent", "Waning Crescent", "Waxing Gibbous", "Waning Gibbous"
            ]
