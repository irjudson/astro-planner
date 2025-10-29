"""Main planner service that orchestrates the entire planning process."""

from datetime import datetime, timedelta
import pytz
from typing import Dict

from app.models import (
    PlanRequest, ObservingPlan, SessionInfo, Location, ObservingConstraints
)
from app.services import (
    EphemerisService, CatalogService, WeatherService,
    SchedulerService, ExportService
)


class PlannerService:
    """Main service for generating observing plans."""

    def __init__(self):
        """Initialize all required services."""
        self.ephemeris = EphemerisService()
        self.catalog = CatalogService()
        self.weather = WeatherService()
        self.scheduler = SchedulerService()
        self.exporter = ExportService()

    def generate_plan(self, request: PlanRequest) -> ObservingPlan:
        """
        Generate a complete observing plan.

        This is the main entry point that orchestrates:
        1. Calculate twilight times for the session
        2. Filter targets by object type
        3. Fetch weather forecast
        4. Schedule targets using greedy algorithm
        5. Create complete plan

        Args:
            request: Plan request with location, date, and constraints

        Returns:
            Complete observing plan
        """
        # Parse observing date and determine which night to plan for
        observing_date = datetime.fromisoformat(request.observing_date)
        tz = pytz.timezone(request.location.timezone)
        observing_date = tz.localize(observing_date) if observing_date.tzinfo is None else observing_date

        # Calculate twilight times for this date
        twilight_times = self.ephemeris.calculate_twilight_times(
            request.location, observing_date
        )

        # Create session info
        session = SessionInfo(
            observing_date=request.observing_date,
            sunset=twilight_times['sunset'],
            civil_twilight_end=twilight_times['civil_twilight_end'],
            nautical_twilight_end=twilight_times['nautical_twilight_end'],
            astronomical_twilight_end=twilight_times['astronomical_twilight_end'],
            astronomical_twilight_start=twilight_times['astronomical_twilight_start'],
            nautical_twilight_start=twilight_times['nautical_twilight_start'],
            civil_twilight_start=twilight_times['civil_twilight_start'],
            sunrise=twilight_times['sunrise'],
            imaging_start=twilight_times['astronomical_twilight_end'] + timedelta(
                minutes=request.constraints.setup_time_minutes
            ),
            imaging_end=twilight_times['astronomical_twilight_start'],
            total_imaging_minutes=0  # Will be calculated
        )

        # Calculate total imaging time
        imaging_duration = session.imaging_end - session.imaging_start
        session.total_imaging_minutes = int(imaging_duration.total_seconds() / 60)

        # Filter targets by object type
        targets = self.catalog.filter_targets(request.constraints.object_types)

        # Get weather forecast
        weather_forecast = self.weather.get_forecast(
            request.location,
            session.imaging_start,
            session.imaging_end
        )

        # Schedule targets
        scheduled_targets = self.scheduler.schedule_session(
            targets=targets,
            location=request.location,
            session=session,
            constraints=request.constraints,
            weather_forecasts=weather_forecast
        )

        # Calculate coverage
        if scheduled_targets:
            total_scheduled_time = sum(
                st.duration_minutes for st in scheduled_targets
            )
            coverage_percent = (total_scheduled_time / session.total_imaging_minutes) * 100
        else:
            coverage_percent = 0.0

        # Create complete plan
        plan = ObservingPlan(
            session=session,
            location=request.location,
            scheduled_targets=scheduled_targets,
            weather_forecast=weather_forecast,
            total_targets=len(scheduled_targets),
            coverage_percent=coverage_percent
        )

        return plan

    def calculate_twilight(self, location: Location, date: str) -> Dict[str, str]:
        """
        Calculate twilight times for a specific date and location.

        Args:
            location: Observer location
            date: ISO date string

        Returns:
            Dictionary of twilight times as ISO strings
        """
        observing_date = datetime.fromisoformat(date)
        twilight_times = self.ephemeris.calculate_twilight_times(
            location, observing_date
        )

        # Convert to ISO strings
        return {
            key: value.isoformat() for key, value in twilight_times.items()
        }
