"""Comprehensive tests for planner service."""

import pytest
from datetime import datetime, timedelta
import pytz
from app.services.planner_service import PlannerService
from app.models import PlanRequest, Location, ObservingConstraints


class TestPlannerServiceComprehensive:
    """Comprehensive test coverage for PlannerService."""

    def test_init_creates_all_services(self, override_get_db):
        """Test that initialization creates all required services."""
        planner = PlannerService(override_get_db)

        assert planner.ephemeris is not None
        assert planner.catalog is not None
        assert planner.comet_service is not None
        assert planner.weather is not None
        assert planner.scheduler is not None
        assert planner.exporter is not None
        assert planner.light_pollution is not None

    def test_generate_plan_basic(self, override_get_db):
        """Test generating a basic observing plan."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy", "nebula"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        assert plan is not None
        assert plan.session is not None
        assert plan.location is not None
        assert plan.scheduled_targets is not None
        assert isinstance(plan.total_targets, int)
        assert isinstance(plan.coverage_percent, float)

    def test_generate_plan_creates_session_info(self, override_get_db):
        """Test that plan includes complete session info."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Check all session fields are populated
        assert plan.session.observing_date is not None
        assert plan.session.sunset is not None
        assert plan.session.sunrise is not None
        assert plan.session.astronomical_twilight_end is not None
        assert plan.session.astronomical_twilight_start is not None
        assert plan.session.imaging_start is not None
        assert plan.session.imaging_end is not None
        assert plan.session.total_imaging_minutes > 0

    def test_generate_plan_with_setup_time(self, override_get_db):
        """Test that setup time is added to imaging start."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"],
                setup_time_minutes=30
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Imaging should start after astronomical twilight + setup time
        time_diff = (plan.session.imaging_start - plan.session.astronomical_twilight_end).total_seconds()
        assert time_diff == 30 * 60  # 30 minutes in seconds

    def test_generate_plan_daytime_planning(self, override_get_db):
        """Test daytime planning mode uses different imaging window."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["planet"],
                daytime_planning=True,
                setup_time_minutes=15
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # In daytime mode, imaging should be between sunrise and sunset
        # imaging_start should be after sunrise (from previous day's twilight calculation)
        # imaging_end should be at sunset
        assert plan.session.imaging_start < plan.session.imaging_end
        assert plan.session.imaging_end == plan.session.sunset

    def test_generate_plan_filters_by_object_type(self, override_get_db):
        """Test that plan only includes requested object types."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]  # Only galaxies
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # All scheduled targets should be galaxies
        if plan.scheduled_targets:
            for scheduled in plan.scheduled_targets:
                assert scheduled.target.object_type == "galaxy"

    def test_generate_plan_respects_magnitude_limit(self, override_get_db):
        """Test that plan only includes bright enough objects."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy", "nebula", "cluster"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # All targets should be magnitude 12 or brighter (excluding defaults)
        if plan.scheduled_targets:
            for scheduled in plan.scheduled_targets:
                if scheduled.target.magnitude < 90:  # Exclude default values
                    assert scheduled.target.magnitude <= 12.0

    def test_generate_plan_includes_weather(self, override_get_db):
        """Test that plan includes weather forecast."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Weather forecast should be present
        assert plan.weather_forecast is not None

    def test_generate_plan_includes_sky_quality(self, override_get_db):
        """Test that plan includes sky quality information."""
        request = PlanRequest(
            location=Location(
                name="Three Forks, MT",
                latitude=45.92,
                longitude=-111.28,
                elevation=1234.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Sky quality should be present for valid location
        assert plan.sky_quality is not None
        if plan.sky_quality:
            assert "bortle_class" in plan.sky_quality
            assert "suitable_for" in plan.sky_quality

    def test_generate_plan_calculates_coverage(self, override_get_db):
        """Test that coverage percentage is calculated."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy", "nebula"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Coverage should be between 0 and 100
        assert 0 <= plan.coverage_percent <= 100

        # If there are scheduled targets, coverage should be > 0
        if plan.total_targets > 0:
            assert plan.coverage_percent > 0

    def test_generate_plan_empty_object_types(self, override_get_db):
        """Test plan generation with no object types specified."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=[]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Should still generate a valid plan
        assert plan is not None
        assert plan.session is not None

    def test_generate_plan_with_comets(self, override_get_db):
        """Test plan generation includes comets when requested."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["comet", "galaxy"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Plan should be generated successfully
        # (may or may not have visible comets, but shouldn't fail)
        assert plan is not None
        assert plan.session is not None

    def test_generate_plan_different_timezones(self, override_get_db):
        """Test plan generation with different timezones."""
        # Test with coordinates that match the timezone for realistic results
        test_cases = [
            ("America/Denver", 39.7392, -104.9903),  # Denver, CO
            ("America/New_York", 40.7128, -74.0060),  # New York, NY
            ("UTC", 51.5074, -0.1278),  # London (UTC in winter)
        ]

        for tz, lat, lon in test_cases:
            request = PlanRequest(
                location=Location(
                    name="Test Location",
                    latitude=lat,
                    longitude=lon,
                    elevation=1000.0,
                    timezone=tz
                ),
                observing_date="2025-01-15",
                constraints=ObservingConstraints(
                    min_altitude=30.0,
                    object_types=["galaxy"]
                )
            )

            planner = PlannerService(override_get_db)
            plan = planner.generate_plan(request)

            # Should generate valid plan for each timezone
            assert plan is not None
            assert plan.session is not None
            # Imaging minutes may be 0 if it's polar night or no dark time
            assert plan.session.total_imaging_minutes >= 0

    def test_generate_plan_summer_vs_winter(self, override_get_db):
        """Test that summer and winter dates produce different imaging durations."""
        location = Location(
            name="Test Location",
            latitude=45.0,  # Northern hemisphere
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        # Winter date (longer nights)
        winter_request = PlanRequest(
            location=location,
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]
            )
        )

        # Summer date (shorter nights)
        summer_request = PlanRequest(
            location=location,
            observing_date="2025-07-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]
            )
        )

        planner = PlannerService(override_get_db)
        winter_plan = planner.generate_plan(winter_request)
        summer_plan = planner.generate_plan(summer_request)

        # Winter should have more imaging time than summer at this latitude
        assert winter_plan.session.total_imaging_minutes > summer_plan.session.total_imaging_minutes

    def test_calculate_twilight_basic(self, override_get_db):
        """Test basic twilight calculation."""
        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        planner = PlannerService(override_get_db)
        twilight = planner.calculate_twilight(location, "2025-01-15")

        # Should return all twilight times as ISO strings
        assert "sunset" in twilight
        assert "sunrise" in twilight
        assert "astronomical_twilight_end" in twilight
        assert "astronomical_twilight_start" in twilight
        assert "civil_twilight_end" in twilight
        assert "civil_twilight_start" in twilight

    def test_calculate_twilight_returns_iso_strings(self, override_get_db):
        """Test that twilight times are returned as ISO format strings."""
        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        planner = PlannerService(override_get_db)
        twilight = planner.calculate_twilight(location, "2025-01-15")

        # Each value should be parseable as ISO datetime
        for key, value in twilight.items():
            assert isinstance(value, str)
            # Should be able to parse as ISO format
            parsed = datetime.fromisoformat(value)
            assert parsed is not None

    def test_calculate_twilight_times_exist(self, override_get_db):
        """Test that all twilight times are returned and parseable."""
        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        planner = PlannerService(override_get_db)
        twilight = planner.calculate_twilight(location, "2025-01-15")

        # Verify all required keys are present and parseable
        required_keys = [
            "sunset", "sunrise",
            "civil_twilight_end", "civil_twilight_start",
            "nautical_twilight_end", "nautical_twilight_start",
            "astronomical_twilight_end", "astronomical_twilight_start"
        ]

        for key in required_keys:
            assert key in twilight
            # Should be parseable as datetime
            dt = datetime.fromisoformat(twilight[key])
            assert dt is not None

    def test_generate_plan_preserves_location(self, override_get_db):
        """Test that generated plan preserves the request location."""
        location = Location(
            name="Three Forks, MT",
            latitude=45.92,
            longitude=-111.28,
            elevation=1234.0,
            timezone="America/Denver"
        )

        request = PlanRequest(
            location=location,
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Plan should preserve location details
        assert plan.location.name == location.name
        assert plan.location.latitude == location.latitude
        assert plan.location.longitude == location.longitude
        assert plan.location.elevation == location.elevation
        assert plan.location.timezone == location.timezone

    def test_generate_plan_scheduled_targets_have_times(self, override_get_db):
        """Test that scheduled targets have start time and duration."""
        request = PlanRequest(
            location=Location(
                name="Test Location",
                latitude=45.0,
                longitude=-110.0,
                elevation=1000.0,
                timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0,
                object_types=["galaxy", "nebula", "cluster"]
            )
        )

        planner = PlannerService(override_get_db)
        plan = planner.generate_plan(request)

        # Check that each scheduled target has timing info
        if plan.scheduled_targets:
            for scheduled in plan.scheduled_targets:
                assert scheduled.start_time is not None
                assert scheduled.duration_minutes > 0
                assert scheduled.target is not None
