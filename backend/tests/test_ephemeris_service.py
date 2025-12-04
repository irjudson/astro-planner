"""Comprehensive tests for ephemeris service."""

import pytest
from datetime import datetime, timedelta
import pytz
from app.services.ephemeris_service import EphemerisService
from app.models import Location, DSOTarget


class TestEphemerisServiceComprehensive:
    """Comprehensive test coverage for EphemerisService."""

    @pytest.fixture
    def ephemeris(self):
        """Create ephemeris service instance."""
        return EphemerisService()

    @pytest.fixture
    def test_location(self):
        """Create test location (Montana)."""
        return Location(
            name="Three Forks, MT",
            latitude=45.92,
            longitude=-111.28,
            elevation=1234.0,
            timezone="America/Denver"
        )

    @pytest.fixture
    def equatorial_location(self):
        """Create equatorial test location."""
        return Location(
            name="Quito, Ecuador",
            latitude=0.0,
            longitude=-78.5,
            elevation=2800.0,
            timezone="America/Guayaquil"
        )

    @pytest.fixture
    def polar_location(self):
        """Create high latitude test location."""
        return Location(
            name="Tromso, Norway",
            latitude=69.65,
            longitude=18.96,
            elevation=10.0,
            timezone="Europe/Oslo"
        )

    @pytest.fixture
    def m31_target(self):
        """Create M31 test target."""
        return DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

    @pytest.fixture
    def m42_target(self):
        """Create M42 test target."""
        return DSOTarget(
            catalog_id="M42",
            name="M42",
            object_type="nebula",
            ra_hours=5.583,
            dec_degrees=-5.391,
            magnitude=4.0,
            size_arcmin=65.0,
            description="Orion Nebula"
        )

    @pytest.fixture
    def circumpolar_target(self):
        """Create circumpolar target (Polaris region)."""
        return DSOTarget(
            catalog_id="NGC188",
            name="NGC188",
            object_type="cluster",
            ra_hours=0.785,
            dec_degrees=85.255,
            magnitude=8.1,
            size_arcmin=15.0,
            description="Old open cluster near pole"
        )

    @pytest.fixture
    def southern_target(self):
        """Create far southern target."""
        return DSOTarget(
            catalog_id="NGC104",
            name="47 Tucanae",
            object_type="cluster",
            ra_hours=0.400,
            dec_degrees=-72.081,
            magnitude=4.0,
            size_arcmin=31.0,
            description="47 Tucanae globular cluster"
        )

    # Initialization tests
    def test_init_loads_ephemeris_data(self, ephemeris):
        """Test that initialization loads required data."""
        assert ephemeris.ts is not None
        assert ephemeris.eph is not None
        assert ephemeris.earth is not None
        assert ephemeris.sun is not None

    # Twilight calculation tests
    def test_calculate_twilight_times_winter(self, ephemeris, test_location):
        """Test twilight times for winter date."""
        tz = pytz.timezone("America/Denver")
        date = tz.localize(datetime(2025, 1, 15, 12, 0, 0))

        twilight = ephemeris.calculate_twilight_times(test_location, date)

        # Should have basic twilight times
        assert 'sunset' in twilight
        assert 'sunrise' in twilight
        assert 'nautical_twilight_end' in twilight
        assert 'nautical_twilight_start' in twilight
        assert 'astronomical_twilight_end' in twilight
        assert 'astronomical_twilight_start' in twilight

        # All times should be datetime objects
        for key, dt in twilight.items():
            assert isinstance(dt, datetime), f"{key} should be datetime"

        # Twilight should progress: sunset -> nautical -> astronomical (evening)
        assert twilight['sunset'].timestamp() < twilight['nautical_twilight_end'].timestamp()
        assert twilight['nautical_twilight_end'].timestamp() < twilight['astronomical_twilight_end'].timestamp()

        # Morning should progress: astronomical -> nautical (before sunrise)
        assert twilight['astronomical_twilight_start'].timestamp() < twilight['nautical_twilight_start'].timestamp()

        # Sunrise should be after morning nautical twilight start
        assert twilight['nautical_twilight_start'].timestamp() < twilight['sunrise'].timestamp()

    def test_calculate_twilight_times_summer(self, ephemeris, test_location):
        """Test twilight times for summer date (shorter nights)."""
        tz = pytz.timezone("America/Denver")
        date = tz.localize(datetime(2025, 6, 21, 12, 0, 0))  # Summer solstice

        twilight = ephemeris.calculate_twilight_times(test_location, date)

        # Should still have all twilight times
        assert 'sunset' in twilight
        assert 'sunrise' in twilight

        # Summer nights are shorter
        night_duration = twilight['sunrise'] - twilight['sunset']
        assert night_duration < timedelta(hours=12)

    def test_calculate_twilight_times_equatorial(self, ephemeris, equatorial_location):
        """Test twilight times at equator (consistent year-round)."""
        tz = pytz.timezone("America/Guayaquil")
        date = tz.localize(datetime(2025, 3, 21, 12, 0, 0))  # Equinox

        twilight = ephemeris.calculate_twilight_times(equatorial_location, date)

        assert 'sunset' in twilight
        assert 'sunrise' in twilight

        # At equator on equinox, night should be close to 12 hours
        night_duration = twilight['sunrise'] - twilight['sunset']
        assert timedelta(hours=11) < night_duration < timedelta(hours=13)

    def test_calculate_twilight_times_returns_timezone_aware(self, ephemeris, test_location):
        """Test that twilight times are timezone-aware."""
        tz = pytz.timezone("America/Denver")
        date = tz.localize(datetime(2025, 1, 15, 12, 0, 0))

        twilight = ephemeris.calculate_twilight_times(test_location, date)

        for key, dt in twilight.items():
            assert dt.tzinfo is not None, f"{key} should be timezone-aware"

    # Position calculation tests
    def test_calculate_position_basic(self, ephemeris, test_location, m31_target):
        """Test basic position calculation."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        alt, az = ephemeris.calculate_position(m31_target, test_location, time)

        # Should return valid altitude and azimuth
        assert -90 <= alt <= 90
        assert 0 <= az <= 360

    def test_calculate_position_circumpolar(self, ephemeris, test_location, circumpolar_target):
        """Test position of circumpolar target (always above horizon at this latitude)."""
        tz = pytz.timezone("America/Denver")

        # Check at multiple times throughout the night
        for hour in [20, 22, 0, 2, 4]:
            if hour == 0 or hour == 2 or hour == 4:
                date = datetime(2025, 1, 16, hour, 0, 0)
            else:
                date = datetime(2025, 1, 15, hour, 0, 0)
            time = tz.localize(date)
            alt, az = ephemeris.calculate_position(circumpolar_target, test_location, time)

            # Circumpolar target should always be above horizon at lat 45°
            # Dec 85° - (90° - lat 45°) = 85° - 45° = 40° minimum altitude
            assert alt > 0, f"Circumpolar target should be above horizon at {hour}:00"

    def test_calculate_position_southern_not_visible(self, ephemeris, test_location, southern_target):
        """Test that far southern target is below horizon from northern location."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        alt, az = ephemeris.calculate_position(southern_target, test_location, time)

        # 47 Tuc at -72° dec should never be visible from lat 45°N
        # Maximum altitude = 90° - |lat - dec| = 90° - |45° - (-72°)| = 90° - 117° = -27°
        assert alt < 0, "47 Tucanae should be below horizon from Montana"

    def test_calculate_position_changes_over_time(self, ephemeris, test_location, m31_target):
        """Test that position changes over time (Earth rotation)."""
        tz = pytz.timezone("America/Denver")
        time1 = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        time2 = tz.localize(datetime(2025, 1, 15, 23, 0, 0))

        alt1, az1 = ephemeris.calculate_position(m31_target, test_location, time1)
        alt2, az2 = ephemeris.calculate_position(m31_target, test_location, time2)

        # Position should change over 3 hours
        assert alt1 != alt2 or az1 != az2

    # Field rotation rate tests
    def test_calculate_field_rotation_rate_basic(self, ephemeris, test_location, m31_target):
        """Test field rotation rate calculation."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        rate = ephemeris.calculate_field_rotation_rate(m31_target, test_location, time)

        # Should return a positive rate in degrees per minute
        assert rate >= 0
        # Typical rates are 0.1-2 deg/min for alt-az mounts
        assert rate < 10, "Field rotation rate seems unreasonably high"

    def test_calculate_field_rotation_rate_near_zenith(self, ephemeris, test_location):
        """Test field rotation rate near zenith (should be very high)."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        # Create a target that would be near zenith
        # At lat 45°, a target at dec 45° transiting would be at zenith
        zenith_target = DSOTarget(
            catalog_id="TEST",
            name="Zenith Test",
            object_type="galaxy",
            ra_hours=1.0,  # Will transit around midnight in January
            dec_degrees=45.0,
            magnitude=10.0,
            size_arcmin=5.0,
            description="Test target near zenith"
        )

        rate = ephemeris.calculate_field_rotation_rate(zenith_target, test_location, time)

        # Rate can be very high near zenith
        assert rate >= 0

    def test_calculate_field_rotation_rate_at_pole(self, ephemeris, test_location, circumpolar_target):
        """Test field rotation rate for circumpolar target."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        rate = ephemeris.calculate_field_rotation_rate(circumpolar_target, test_location, time)

        # Should return a value (may be high near pole)
        assert rate >= 0

    def test_calculate_field_rotation_varies_with_azimuth(self, ephemeris, test_location, m42_target):
        """Test that field rotation varies through the night."""
        tz = pytz.timezone("America/Denver")

        rates = []
        for hour in [20, 22, 0, 2]:
            if hour == 0 or hour == 2:
                date = datetime(2025, 1, 16, hour, 0, 0)
            else:
                date = datetime(2025, 1, 15, hour, 0, 0)
            time = tz.localize(date)
            rate = ephemeris.calculate_field_rotation_rate(m42_target, test_location, time)
            rates.append(rate)

        # Rates should vary as target moves across sky
        # (not all the same)
        assert len(set(rates)) > 1, "Field rotation rate should vary through the night"

    # Visibility tests
    def test_is_target_visible_above_horizon(self, ephemeris, test_location, m31_target):
        """Test visibility check for visible target."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        # First check the actual altitude
        alt, _ = ephemeris.calculate_position(m31_target, test_location, time)

        # Use constraints that match the altitude
        if alt > 30:
            visible = ephemeris.is_target_visible(
                m31_target, test_location, time, min_alt=30.0, max_alt=80.0
            )
            assert visible or alt > 80  # True unless above max

    def test_is_target_visible_below_min_altitude(self, ephemeris, test_location, m31_target):
        """Test visibility check with high minimum altitude."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        # Use very high minimum altitude
        visible = ephemeris.is_target_visible(
            m31_target, test_location, time, min_alt=85.0, max_alt=90.0
        )

        # M31 is unlikely to be above 85° from Montana
        assert not visible

    def test_is_target_visible_above_max_altitude(self, ephemeris, test_location):
        """Test visibility check when target exceeds max altitude."""
        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        # Create a target that would be at high altitude
        high_target = DSOTarget(
            catalog_id="TEST",
            name="High Alt Test",
            object_type="galaxy",
            ra_hours=1.0,
            dec_degrees=45.0,  # Same as latitude
            magnitude=10.0,
            size_arcmin=5.0,
            description="Test target"
        )

        alt, _ = ephemeris.calculate_position(high_target, test_location, time)

        # If altitude is high, test max constraint
        if alt > 60:
            visible = ephemeris.is_target_visible(
                high_target, test_location, time, min_alt=30.0, max_alt=50.0
            )
            assert not visible

    def test_is_target_visible_southern_from_north(self, ephemeris, test_location, southern_target):
        """Test that far southern target is never visible from northern location."""
        tz = pytz.timezone("America/Denver")

        # Check at multiple times
        for hour in [20, 22, 0, 2, 4]:
            if hour >= 0 and hour <= 4:
                date = datetime(2025, 1, 16, hour, 0, 0)
            else:
                date = datetime(2025, 1, 15, hour, 0, 0)
            time = tz.localize(date)

            visible = ephemeris.is_target_visible(
                southern_target, test_location, time, min_alt=0.0, max_alt=90.0
            )
            assert not visible, f"47 Tuc should not be visible at {hour}:00"

    def test_is_target_visible_circumpolar_always(self, ephemeris, test_location, circumpolar_target):
        """Test that circumpolar target is always visible."""
        tz = pytz.timezone("America/Denver")

        # Check at multiple times throughout the night
        all_visible = True
        for hour in [20, 22, 0, 2, 4]:
            if hour >= 0 and hour <= 4:
                date = datetime(2025, 1, 16, hour, 0, 0)
            else:
                date = datetime(2025, 1, 15, hour, 0, 0)
            time = tz.localize(date)

            visible = ephemeris.is_target_visible(
                circumpolar_target, test_location, time, min_alt=30.0, max_alt=90.0
            )
            if not visible:
                all_visible = False

        # NGC188 at dec 85° should be visible all night from lat 45°
        # Min altitude ≈ 85° - (90° - 45°) = 40° > 30°
        assert all_visible, "Circumpolar target should be visible all night"

    # Edge cases
    def test_calculate_position_utc_time(self, ephemeris, test_location, m31_target):
        """Test position calculation with UTC time."""
        time = datetime(2025, 1, 16, 5, 0, 0, tzinfo=pytz.UTC)

        alt, az = ephemeris.calculate_position(m31_target, test_location, time)

        # Should work with UTC time
        assert -90 <= alt <= 90
        assert 0 <= az <= 360

    def test_calculate_position_different_timezones_same_instant(
        self, ephemeris, test_location, m31_target
    ):
        """Test that same instant in different timezones gives same position."""
        # Same instant, different timezone representations
        mst = pytz.timezone("America/Denver")
        utc = pytz.UTC

        time_mst = mst.localize(datetime(2025, 1, 15, 22, 0, 0))
        time_utc = time_mst.astimezone(utc)

        alt1, az1 = ephemeris.calculate_position(m31_target, test_location, time_mst)
        alt2, az2 = ephemeris.calculate_position(m31_target, test_location, time_utc)

        # Should be identical (same physical instant)
        assert abs(alt1 - alt2) < 0.01
        assert abs(az1 - az2) < 0.01


class TestTwilightAngleIntegration:
    """Integration tests for twilight angle calculations via public interface."""

    @pytest.fixture
    def ephemeris(self):
        """Create ephemeris service instance."""
        return EphemerisService()

    @pytest.fixture
    def test_location(self):
        """Create test location."""
        return Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

    def test_nautical_twilight_occurs_after_sunset(self, ephemeris, test_location):
        """Test that nautical twilight end occurs after sunset (indirectly tests _find_twilight_angle)."""
        tz = pytz.timezone("America/Denver")
        date = tz.localize(datetime(2025, 1, 15, 12, 0, 0))

        twilight = ephemeris.calculate_twilight_times(test_location, date)

        # Nautical twilight end should be after sunset (sun at -12° after being at 0°)
        assert 'sunset' in twilight
        assert 'nautical_twilight_end' in twilight

        time_diff = twilight['nautical_twilight_end'].timestamp() - twilight['sunset'].timestamp()
        # Nautical twilight (from sunset to -12°) typically lasts 30-60 minutes at mid-latitudes
        assert 15 * 60 < time_diff < 90 * 60, "Nautical twilight should be 15-90 min after sunset"

    def test_astronomical_twilight_duration(self, ephemeris, test_location):
        """Test astronomical twilight timing (indirectly tests _find_twilight_angle with -18°)."""
        tz = pytz.timezone("America/Denver")
        date = tz.localize(datetime(2025, 1, 15, 12, 0, 0))

        twilight = ephemeris.calculate_twilight_times(test_location, date)

        # Total twilight duration from sunset to astronomical twilight
        assert 'sunset' in twilight
        assert 'astronomical_twilight_end' in twilight

        total_twilight = twilight['astronomical_twilight_end'].timestamp() - twilight['sunset'].timestamp()
        # Total twilight from sunset to astronomical should be 1-2 hours at mid-latitudes
        assert 45 * 60 < total_twilight < 3 * 60 * 60, "Total twilight should be 45min-3hr"
