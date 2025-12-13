"""Main planner service that orchestrates the entire planning process."""

import time
from datetime import datetime, timedelta
from typing import Dict

import pytz
from sqlalchemy.orm import Session

from app.models import Location, ObservingPlan, PlanRequest, SessionInfo
from app.services import CatalogService, EphemerisService, ExportService, SchedulerService, WeatherService
from app.services.comet_service import CometService
from app.services.image_preview_service import ImagePreviewService
from app.services.light_pollution_service import LightPollutionService


class PlannerService:
    """Main service for generating observing plans."""

    def __init__(self, db: Session):
        """Initialize all required services."""
        self.ephemeris = EphemerisService()
        self.catalog = CatalogService(db)
        self.comet_service = CometService(db)
        self.weather = WeatherService()
        self.scheduler = SchedulerService()
        self.exporter = ExportService()
        self.light_pollution = LightPollutionService()
        self.image_preview = ImagePreviewService()

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
        twilight_times = self.ephemeris.calculate_twilight_times(request.location, observing_date)

        # Determine imaging window based on daytime_planning flag
        if request.constraints.daytime_planning:
            # Daytime planning: observe from sunrise to sunset on the SAME day
            # twilight_times gives us sunset on observing_date and sunrise on observing_date+1
            # For daytime planning, we need sunrise on observing_date, so get previous day's twilight
            prev_day = observing_date - timedelta(days=1)
            prev_twilight = self.ephemeris.calculate_twilight_times(request.location, prev_day)
            # Use sunrise from "next day" of previous twilight (which is our observing_date)
            # and sunset from current day
            imaging_start = prev_twilight["sunrise"] + timedelta(minutes=request.constraints.setup_time_minutes)
            imaging_end = twilight_times["sunset"]
        else:
            # Normal nighttime planning: observe during astronomical darkness
            imaging_start = twilight_times["astronomical_twilight_end"] + timedelta(
                minutes=request.constraints.setup_time_minutes
            )
            imaging_end = twilight_times["astronomical_twilight_start"]

        # Create session info
        session = SessionInfo(
            observing_date=request.observing_date,
            sunset=twilight_times["sunset"],
            civil_twilight_end=twilight_times["civil_twilight_end"],
            nautical_twilight_end=twilight_times["nautical_twilight_end"],
            astronomical_twilight_end=twilight_times["astronomical_twilight_end"],
            astronomical_twilight_start=twilight_times["astronomical_twilight_start"],
            nautical_twilight_start=twilight_times["nautical_twilight_start"],
            civil_twilight_start=twilight_times["civil_twilight_start"],
            sunrise=twilight_times["sunrise"],
            imaging_start=imaging_start,
            imaging_end=imaging_end,
            total_imaging_minutes=0,  # Will be calculated
        )

        # Calculate total imaging time
        imaging_duration = session.imaging_end - session.imaging_start
        session.total_imaging_minutes = int(imaging_duration.total_seconds() / 60)

        # Get sky quality for location (for filtering and display)
        sky_quality = None
        sky_quality_dict = None
        try:
            sky_quality = self.light_pollution.get_sky_quality(request.location)
            # Convert to dict for JSON serialization
            sky_quality_dict = sky_quality.model_dump()
        except Exception as e:
            print(f"Warning: Failed to get sky quality: {e}")

        # Filter targets by object type
        # Limit to brighter objects (mag < 12) and top 200 candidates for performance
        # Seestar S50 works best with magnitude 8-11 targets anyway
        t0 = time.time()
        targets = self.catalog.filter_targets(
            object_types=request.constraints.object_types,
            max_magnitude=12.0,  # Practical limit for Seestar S50
            limit=200,  # Enough variety while keeping performance fast
        )
        print(f"[TIMING] Target filtering: {time.time() - t0:.2f}s ({len(targets)} targets)")

        # Apply sky quality filtering if available
        if sky_quality and sky_quality.suitable_for:
            # Filter targets based on sky quality suitability
            # Keep targets whose object type is in the suitable_for list
            suitable_types = set(sky_quality.suitable_for)
            original_count = len(targets)
            targets = [t for t in targets if t.object_type in suitable_types]
            filtered_count = original_count - len(targets)
            if filtered_count > 0:
                print(
                    f"Sky quality filtering: removed {filtered_count} targets unsuitable for Bortle {sky_quality.bortle_class} conditions"
                )

        # Populate image URLs for targets
        # NOTE: Images are now fetched lazily by frontend to avoid blocking plan generation
        # The image_preview service is still used via /api/images/targets/{catalog_id} endpoint
        t1 = time.time()
        for target in targets:
            if not target.image_url:
                # Set URL pattern that frontend can use to fetch image on-demand
                sanitized_id = target.catalog_id.replace(" ", "_").replace("/", "_").replace(":", "_")
                target.image_url = f"/api/images/targets/{sanitized_id}"
        print(f"[TIMING] Image URL assignment: {time.time() - t1:.2f}s ({len(targets)} targets)")

        # Add visible comets if "comet" is in object types
        if request.constraints.object_types and "comet" in request.constraints.object_types:
            try:
                # Get visible comets during the observing session
                # Use midpoint of imaging window for visibility check
                midpoint_time = session.imaging_start + (session.imaging_end - session.imaging_start) / 2
                # Convert to naive UTC datetime for comet service
                midpoint_utc = midpoint_time.astimezone(pytz.UTC).replace(tzinfo=None)

                visible_comets = self.comet_service.get_visible_comets(
                    location=request.location,
                    time_utc=midpoint_utc,
                    min_altitude=request.constraints.min_altitude_degrees,
                    max_magnitude=12.0,  # Same limit as DSO targets
                )

                # Convert comet visibility objects to DSOTarget format for scheduler compatibility
                # This is a simplified conversion - comets need special handling for moving targets
                for comet_vis in visible_comets:
                    from app.models import DSOTarget

                    comet_target = DSOTarget(
                        catalog_name="Comet",
                        catalog_id=comet_vis.comet.designation,
                        common_name=comet_vis.comet.name or comet_vis.comet.designation,
                        object_type="comet",
                        ra_hours=comet_vis.ephemeris.ra_hours,
                        dec_degrees=comet_vis.ephemeris.dec_degrees,
                        magnitude=comet_vis.ephemeris.magnitude,
                        size_arcmin=None,  # Comets vary
                        constellation=None,  # Would need to compute
                        notes=f"Distance: {comet_vis.ephemeris.helio_distance_au:.2f} AU from Sun, {comet_vis.ephemeris.geo_distance_au:.2f} AU from Earth",
                    )
                    targets.append(comet_target)
            except Exception as e:
                # Log error but don't fail the entire plan
                print(f"Warning: Failed to add comets to plan: {e}")

        # Get weather forecast
        t2 = time.time()
        weather_forecast = self.weather.get_forecast(request.location, session.imaging_start, session.imaging_end)
        print(f"[TIMING] Weather forecast: {time.time() - t2:.2f}s")

        # Schedule targets
        t3 = time.time()
        scheduled_targets = self.scheduler.schedule_session(
            targets=targets,
            location=request.location,
            session=session,
            constraints=request.constraints,
            weather_forecasts=weather_forecast,
        )
        print(f"[TIMING] Scheduler: {time.time() - t3:.2f}s ({len(scheduled_targets)} scheduled)")

        # Calculate coverage
        if scheduled_targets:
            total_scheduled_time = sum(st.duration_minutes for st in scheduled_targets)
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
            coverage_percent=coverage_percent,
            sky_quality=sky_quality_dict,
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
        twilight_times = self.ephemeris.calculate_twilight_times(location, observing_date)

        # Convert to ISO strings
        return {key: value.isoformat() for key, value in twilight_times.items()}
