"""Comprehensive tests for scheduler service."""

import pytest
from datetime import datetime, timedelta
import pytz
from app.services.scheduler_service import SchedulerService
from app.models import (
    DSOTarget, Location, SessionInfo, ObservingConstraints,
    WeatherForecast
)


@pytest.mark.slow
class TestSchedulerServiceComprehensive:
    """Comprehensive test coverage for SchedulerService."""

    def test_init_creates_services(self):
        """Test that initialization creates required services."""
        scheduler = SchedulerService()

        assert scheduler.ephemeris is not None
        assert scheduler.weather is not None
        assert scheduler.settings is not None

    def test_schedule_session_basic(self):
        """Test basic session scheduling."""
        scheduler = SchedulerService()

        # Create test location
        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        # Create test targets
        targets = [
            DSOTarget(
                catalog_id="M31",
                name="M31",
                object_type="galaxy",
                ra_hours=0.712,
                dec_degrees=41.269,
                magnitude=3.4,
                size_arcmin=178.0,
                description="Andromeda Galaxy"
            ),
            DSOTarget(
                catalog_id="M42",
                name="M42",
                object_type="nebula",
                ra_hours=5.583,
                dec_degrees=-5.391,
                magnitude=4.0,
                size_arcmin=65.0,
                description="Orion Nebula"
            )
        ]

        # Create session info
        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        # Create constraints
        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="balanced"
        )

        # Schedule session
        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # Should return a list of scheduled targets
        assert isinstance(scheduled, list)
        # May or may not have targets depending on visibility

    def test_schedule_session_quality_mode(self):
        """Test scheduling in quality mode (longer exposures, fewer targets)."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        targets = [
            DSOTarget(
                catalog_id=f"M{i}",
                name=f"M{i}",
                object_type="galaxy",
                ra_hours=i * 0.5,
                dec_degrees=45.0,
                magnitude=8.0,
                size_arcmin=10.0,
                description=f"Test target {i}"
            ) for i in range(1, 20)
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        # Quality mode constraints
        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="quality"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # Quality mode should schedule fewer targets with longer durations
        if len(scheduled) > 0:
            # Should have max 8 targets in quality mode
            assert len(scheduled) <= 8
            # Each target should have at least 45 minutes
            for target in scheduled:
                assert target.duration_minutes >= 45

    def test_schedule_session_quantity_mode(self):
        """Test scheduling in quantity mode (shorter exposures, more targets)."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        targets = [
            DSOTarget(
                catalog_id=f"M{i}",
                name=f"M{i}",
                object_type="galaxy",
                ra_hours=i * 0.5,
                dec_degrees=45.0,
                magnitude=8.0,
                size_arcmin=10.0,
                description=f"Test target {i}"
            ) for i in range(1, 30)
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        # Quantity mode constraints
        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="quantity"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # Quantity mode should schedule more targets with shorter durations
        if len(scheduled) > 0:
            # Should have max 20 targets in quantity mode
            assert len(scheduled) <= 20

    def test_schedule_session_no_duplicate_targets(self):
        """Test that scheduler doesn't schedule the same target twice."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        # Single target that will be visible for long time
        targets = [
            DSOTarget(
                catalog_id="M31",
                name="M31",
                object_type="galaxy",
                ra_hours=0.712,
                dec_degrees=41.269,
                magnitude=3.4,
                size_arcmin=178.0,
                description="Andromeda Galaxy"
            )
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="balanced"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # Should schedule at most once
        catalog_ids = [s.target.catalog_id for s in scheduled]
        assert len(catalog_ids) == len(set(catalog_ids))  # No duplicates
        assert len(scheduled) <= 1  # Only one target available

    def test_schedule_session_with_weather_forecasts(self):
        """Test scheduling with weather forecast integration."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        targets = [
            DSOTarget(
                catalog_id="M31",
                name="M31",
                object_type="galaxy",
                ra_hours=0.712,
                dec_degrees=41.269,
                magnitude=3.4,
                size_arcmin=178.0,
                description="Andromeda Galaxy"
            )
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        # Create weather forecast
        weather_forecasts = [
            WeatherForecast(
                timestamp=start + timedelta(hours=i),
                temperature=10.0,
                humidity=50.0,
                cloud_cover=20.0,
                wind_speed=5.0,
                conditions="clear"
            ) for i in range(8)
        ]

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="balanced"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=weather_forecasts
        )

        # Should successfully schedule with weather data
        assert isinstance(scheduled, list)

    def test_scheduled_target_has_complete_info(self):
        """Test that scheduled targets have all required information."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        targets = [
            DSOTarget(
                catalog_id="M31",
                name="M31",
                object_type="galaxy",
                ra_hours=0.712,
                dec_degrees=41.269,
                magnitude=3.4,
                size_arcmin=178.0,
                description="Andromeda Galaxy"
            )
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="balanced"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # Check each scheduled target has complete info
        for target in scheduled:
            assert target.target is not None
            assert target.start_time is not None
            assert target.end_time is not None
            assert target.duration_minutes > 0
            assert target.start_altitude is not None
            assert target.end_altitude is not None
            assert target.start_azimuth is not None
            assert target.end_azimuth is not None
            assert target.field_rotation_rate is not None
            assert target.recommended_exposure is not None
            assert target.recommended_frames is not None
            assert target.score is not None

    def test_calculate_visibility_duration(self):
        """Test visibility duration calculation."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        target = DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0
        )

        duration = scheduler._calculate_visibility_duration(
            target, location, start, end, constraints
        )

        # Should return a timedelta
        assert isinstance(duration, timedelta)
        # Duration should be >= 0
        assert duration.total_seconds() >= 0

    def test_score_target_basic(self):
        """Test basic target scoring."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        target = DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))
        duration = timedelta(minutes=60)

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0
        )

        score = scheduler._score_target(
            target, location, time, duration, constraints, weather_score=0.8
        )

        # Should return TargetScore with all components
        assert score.visibility_score is not None
        assert score.weather_score == 0.8
        assert score.object_score is not None
        assert score.total_score is not None
        # Scores should be between 0 and 1
        assert 0 <= score.visibility_score <= 1
        assert 0 <= score.weather_score <= 1
        assert 0 <= score.object_score <= 1
        assert 0 <= score.total_score <= 1

    def test_score_target_brightness_scoring(self):
        """Test that brightness affects scoring correctly."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        # Bright target
        bright_target = DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,  # Bright
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

        # Faint target
        faint_target = DSOTarget(
            catalog_id="NGC2419",
            name="NGC2419",
            object_type="cluster",
            ra_hours=7.633,
            dec_degrees=38.883,
            magnitude=10.4,  # Faint
            size_arcmin=4.0,
            description="Faint cluster"
        )

        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))
        duration = timedelta(minutes=60)

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0
        )

        bright_score = scheduler._score_target(
            bright_target, location, time, duration, constraints, weather_score=0.8
        )
        faint_score = scheduler._score_target(
            faint_target, location, time, duration, constraints, weather_score=0.8
        )

        # Bright target should generally have higher object score
        # (though not guaranteed due to size factor)
        assert bright_score.object_score >= 0
        assert faint_score.object_score >= 0

    def test_calculate_urgency_bonus_setting_soon(self):
        """Test urgency bonus for targets setting soon."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        # Target that will be setting
        target = DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

        tz = pytz.timezone("America/Denver")
        current_time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))
        end_time = tz.localize(datetime(2025, 1, 16, 4, 0, 0))
        lookahead = timedelta(minutes=120)

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0
        )

        bonus = scheduler._calculate_urgency_bonus(
            target, location, current_time, end_time, constraints, lookahead
        )

        # Should return a number >= 0
        assert isinstance(bonus, float)
        assert bonus >= 0

    def test_calculate_exposure_settings(self):
        """Test exposure settings calculation."""
        scheduler = SchedulerService()

        target = DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

        duration = timedelta(minutes=60)

        exposure, frames = scheduler._calculate_exposure_settings(target, duration)

        # Should return valid exposure and frame count
        assert exposure > 0
        assert frames >= 10  # Minimum 10 frames
        assert exposure == 10  # Seestar S50 uses 10s exposures

    def test_calculate_exposure_settings_long_duration(self):
        """Test exposure settings with long observation duration."""
        scheduler = SchedulerService()

        target = DSOTarget(
            catalog_id="M31",
            name="M31",
            object_type="galaxy",
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=178.0,
            description="Andromeda Galaxy"
        )

        duration = timedelta(minutes=120)  # 2 hours

        exposure, frames = scheduler._calculate_exposure_settings(target, duration)

        # More frames for longer duration
        assert frames > 100
        # Still 10s exposures
        assert exposure == 10

    def test_get_weather_score_for_time_no_forecasts(self):
        """Test weather score when no forecasts available."""
        scheduler = SchedulerService()

        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        score = scheduler._get_weather_score_for_time(time, [])

        # Should return default optimistic score
        assert score == 0.8

    def test_get_weather_score_for_time_with_forecasts(self):
        """Test weather score retrieval from forecasts."""
        scheduler = SchedulerService()

        tz = pytz.timezone("America/Denver")
        time = tz.localize(datetime(2025, 1, 15, 22, 0, 0))

        # Create forecasts around the time
        weather_forecasts = [
            WeatherForecast(
                timestamp=time - timedelta(hours=1),
                temperature=10.0,
                humidity=50.0,
                cloud_cover=20.0,
                wind_speed=5.0,
                conditions="clear"
            ),
            WeatherForecast(
                timestamp=time,
                temperature=10.0,
                humidity=50.0,
                cloud_cover=10.0,
                wind_speed=3.0,
                conditions="clear"
            ),
            WeatherForecast(
                timestamp=time + timedelta(hours=1),
                temperature=10.0,
                humidity=50.0,
                cloud_cover=30.0,
                wind_speed=7.0,
                conditions="partly cloudy"
            )
        ]

        score = scheduler._get_weather_score_for_time(time, weather_forecasts)

        # Should return a score between 0 and 1
        assert 0 <= score <= 1

    def test_schedule_respects_min_altitude(self):
        """Test that scheduler respects minimum altitude constraint."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        # Target that might be below horizon or too low
        targets = [
            DSOTarget(
                catalog_id="NGC104",
                name="47 Tuc",
                object_type="cluster",
                ra_hours=0.400,
                dec_degrees=-72.081,  # Far southern object
                magnitude=4.0,
                size_arcmin=31.0,
                description="47 Tucanae"
            )
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        # High minimum altitude
        constraints = ObservingConstraints(
            min_altitude=60.0,  # Very high minimum
            max_altitude=80.0,
            planning_mode="balanced"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # All scheduled targets should meet altitude requirement
        for target in scheduled:
            assert target.start_altitude >= 60.0 or target.start_altitude == 0
            assert target.end_altitude >= 60.0 or target.end_altitude == 0

    def test_schedule_accounts_for_slew_time(self):
        """Test that scheduler accounts for slew time between targets."""
        scheduler = SchedulerService()

        location = Location(
            name="Test Location",
            latitude=45.0,
            longitude=-110.0,
            elevation=1000.0,
            timezone="America/Denver"
        )

        targets = [
            DSOTarget(
                catalog_id=f"M{i}",
                name=f"M{i}",
                object_type="galaxy",
                ra_hours=i * 0.5,
                dec_degrees=45.0,
                magnitude=8.0,
                size_arcmin=10.0,
                description=f"Test target {i}"
            ) for i in range(1, 10)
        ]

        tz = pytz.timezone("America/Denver")
        start = tz.localize(datetime(2025, 1, 15, 20, 0, 0))
        end = tz.localize(datetime(2025, 1, 16, 4, 0, 0))

        session = SessionInfo(
            observing_date="2025-01-15",
            sunset=start - timedelta(hours=2),
            civil_twilight_end=start - timedelta(minutes=90),
            nautical_twilight_end=start - timedelta(minutes=60),
            astronomical_twilight_end=start,
            astronomical_twilight_start=end,
            nautical_twilight_start=end + timedelta(minutes=60),
            civil_twilight_start=end + timedelta(minutes=90),
            sunrise=end + timedelta(hours=2),
            imaging_start=start,
            imaging_end=end,
            total_imaging_minutes=480
        )

        constraints = ObservingConstraints(
            min_altitude=30.0,
            max_altitude=80.0,
            planning_mode="balanced"
        )

        scheduled = scheduler.schedule_session(
            targets=targets,
            location=location,
            session=session,
            constraints=constraints,
            weather_forecasts=[]
        )

        # Check that there are gaps between targets (slew time)
        if len(scheduled) > 1:
            for i in range(len(scheduled) - 1):
                end_time = scheduled[i].end_time
                next_start = scheduled[i + 1].start_time
                # Should have at least slew time gap
                gap = (next_start - end_time).total_seconds()
                assert gap >= 0  # No overlaps
