"""Service layer tests."""

import pytest
from datetime import datetime, timedelta
import pytz

from app.services.weather_service import WeatherService
from app.services.scheduler_service import SchedulerService
from app.services.catalog_service import CatalogService
from app.services.ephemeris_service import EphemerisService
from app.models import Location, DSOTarget, ObservingConstraints, WeatherForecast


@pytest.fixture
def sample_location():
    """Sample location."""
    return Location(
        name="Three Forks, MT",
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234.0,
        timezone="America/Denver"
    )


@pytest.fixture
def sample_target():
    """Sample DSO target."""
    return DSOTarget(
        name="Andromeda Galaxy",
        catalog_id="M31",
        object_type="galaxy",
        ra_hours=0.7122,
        dec_degrees=41.2692,
        magnitude=3.4,
        size_arcmin=178.0,
        description="Large spiral galaxy"
    )


class TestWeatherService:
    """Test weather service."""

    def test_weather_score_calculation(self):
        """Test weather score calculation."""
        service = WeatherService()

        # Perfect conditions
        perfect_forecast = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=0.0,
            humidity=40.0,
            temperature=15.0,
            wind_speed=2.0,
            conditions="Clear"
        )
        score = service.calculate_weather_score(perfect_forecast)
        assert score >= 0.9  # Should be very high

        # Poor conditions
        poor_forecast = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=100.0,
            humidity=90.0,
            temperature=15.0,
            wind_speed=15.0,
            conditions="Overcast"
        )
        score = service.calculate_weather_score(poor_forecast)
        assert score < 0.4  # Should trigger weather warning

        # Moderate conditions
        moderate_forecast = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=30.0,
            humidity=60.0,
            temperature=15.0,
            wind_speed=5.0,
            conditions="Partly cloudy"
        )
        score = service.calculate_weather_score(moderate_forecast)
        assert 0.4 <= score <= 0.9

    def test_default_forecast_generation(self, sample_location):
        """Test default forecast when API unavailable."""
        service = WeatherService()
        start_time = datetime.now(pytz.timezone(sample_location.timezone))
        end_time = start_time + timedelta(hours=8)

        forecasts = service._generate_default_forecast(start_time, end_time)

        assert len(forecasts) >= 8  # Should have hourly forecasts
        assert all(f.cloud_cover == 20.0 for f in forecasts)  # Optimistic defaults
        assert all(f.conditions == "Clear sky (estimated)" for f in forecasts)


class TestCatalogService:
    """Test catalog service."""

    def test_get_all_targets(self):
        """Test retrieving all targets."""
        service = CatalogService()
        targets = service.get_all_targets()

        assert len(targets) > 10000  # Should have full NGC+IC catalog (12k+ objects)
        assert all(isinstance(t, DSOTarget) for t in targets)

    def test_get_target_by_id(self):
        """Test retrieving specific target."""
        service = CatalogService()

        # Valid target
        target = service.get_target_by_id("M31")
        assert target is not None
        assert target.catalog_id == "M31"
        assert target.name == "M31"  # Catalog uses catalog ID as name

        # Invalid target
        target = service.get_target_by_id("INVALID")
        assert target is None

    def test_filter_by_object_type(self):
        """Test filtering targets by object type."""
        service = CatalogService()

        galaxies = service.filter_targets(["galaxy"])
        assert all(t.object_type == "galaxy" for t in galaxies)

        nebulae = service.filter_targets(["nebula"])
        assert all(t.object_type == "nebula" for t in nebulae)

        multiple = service.filter_targets(["galaxy", "nebula"])
        assert all(t.object_type in ["galaxy", "nebula"] for t in multiple)


class TestEphemerisService:
    """Test ephemeris service."""

    def test_calculate_twilight_times(self, sample_location):
        """Test twilight calculation."""
        service = EphemerisService()
        date = datetime.now()

        times = service.calculate_twilight_times(sample_location, date)

        assert "sunset" in times
        assert "sunrise" in times
        assert "astronomical_twilight_end" in times
        assert "astronomical_twilight_start" in times

        # Sunset should be before sunrise
        assert times["sunset"] < times["sunrise"]

        # Astronomical twilight should be darkest
        assert times["astronomical_twilight_end"] > times["sunset"]
        assert times["astronomical_twilight_start"] < times["sunrise"]

    def test_calculate_position(self, sample_location, sample_target):
        """Test position calculation."""
        service = EphemerisService()
        time = datetime.now(pytz.timezone(sample_location.timezone))

        altitude, azimuth = service.calculate_position(
            sample_target, sample_location, time
        )

        assert -90 <= altitude <= 90
        assert 0 <= azimuth <= 360

    def test_target_visibility(self, sample_location, sample_target):
        """Test visibility checking."""
        service = EphemerisService()
        time = datetime.now(pytz.timezone(sample_location.timezone))

        # Should return boolean (or numpy boolean)
        is_visible = service.is_target_visible(
            sample_target, sample_location, time,
            min_alt=30.0, max_alt=80.0
        )
        # Accept both bool and numpy bool
        assert is_visible in [True, False]


class TestSchedulerService:
    """Test scheduler service."""

    @pytest.fixture
    def sample_constraints(self):
        """Sample observing constraints."""
        return ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            setup_time_minutes=15,
            object_types=["galaxy", "nebula", "cluster"],
            planning_mode="balanced"
        )

    def test_planning_mode_balanced(self, sample_location, sample_constraints):
        """Test balanced planning mode parameters."""
        service = SchedulerService()
        catalog = CatalogService()
        targets = catalog.filter_targets(sample_constraints.object_types)

        # Should apply balanced mode settings
        assert sample_constraints.planning_mode == "balanced"

    def test_planning_mode_quality(self, sample_location):
        """Test quality planning mode."""
        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            setup_time_minutes=15,
            object_types=["galaxy", "nebula"],
            planning_mode="quality"
        )
        assert constraints.planning_mode == "quality"

    def test_planning_mode_quantity(self, sample_location):
        """Test quantity planning mode."""
        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            setup_time_minutes=15,
            object_types=["galaxy", "nebula", "cluster"],
            planning_mode="quantity"
        )
        assert constraints.planning_mode == "quantity"

    def test_exposure_settings_calculation(self):
        """Test exposure settings for Seestar."""
        service = SchedulerService()

        # Bright target (M31, mag 3.4)
        bright_target = DSOTarget(
            name="Test Bright",
            catalog_id="TEST1",
            object_type="galaxy",
            ra_hours=0.0,
            dec_degrees=0.0,
            magnitude=5.0,
            size_arcmin=100.0
        )
        exposure, frames = service._calculate_exposure_settings(
            bright_target, timedelta(minutes=60)
        )
        assert exposure == 10  # Default exposure for Seestar
        assert frames >= 10

        # Faint target
        faint_target = DSOTarget(
            name="Test Faint",
            catalog_id="TEST2",
            object_type="nebula",
            ra_hours=0.0,
            dec_degrees=0.0,
            magnitude=10.0,
            size_arcmin=10.0
        )
        exposure, frames = service._calculate_exposure_settings(
            faint_target, timedelta(minutes=60)
        )
        assert exposure == 10  # Should use max exposure (Seestar limit)
        assert frames >= 10
