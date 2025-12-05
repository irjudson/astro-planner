"""Observing session scheduler using greedy algorithm with urgency lookahead."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.core import get_settings
from app.models import DSOTarget, Location, ObservingConstraints, ScheduledTarget, SessionInfo, TargetScore
from app.services.ephemeris_service import EphemerisService
from app.services.weather_service import WeatherService


class SchedulerService:
    """Service for scheduling observing sessions."""

    def __init__(self):
        """Initialize scheduler with required services."""
        self.ephemeris = EphemerisService()
        self.weather = WeatherService()
        self.settings = get_settings()

    def schedule_session(
        self,
        targets: List[DSOTarget],
        location: Location,
        session: SessionInfo,
        constraints: ObservingConstraints,
        weather_forecasts: List,
    ) -> List[ScheduledTarget]:
        """
        Schedule targets for an observing session using greedy algorithm.

        Algorithm:
        1. Start at imaging_start time
        2. For each time slot, score all available targets
        3. Apply urgency-based lookahead (targets setting soon get priority)
        4. Select best target and schedule it
        5. Account for slew time between targets
        6. Continue until imaging_end or no more targets

        Args:
            targets: List of candidate targets
            location: Observer location
            session: Session information with times
            constraints: Observing constraints
            weather_forecasts: Weather forecast list

        Returns:
            List of scheduled targets
        """
        scheduled = []
        current_time = session.imaging_start
        slew_time = timedelta(seconds=self.settings.slew_time_seconds)

        # Adjust parameters based on planning mode
        planning_mode = constraints.planning_mode
        if planning_mode == "quality":
            # Quality mode: longer exposures, fewer targets, stricter scoring
            min_duration = timedelta(minutes=45)
            max_duration = timedelta(minutes=180)  # Cap at 3 hours
            min_score_threshold = 0.7
            max_targets_per_night = 8
        elif planning_mode == "quantity":
            # Quantity mode: shorter exposures, more targets, lenient scoring
            min_duration = timedelta(minutes=15)
            max_duration = timedelta(minutes=45)  # Cap at 45 minutes
            min_score_threshold = 0.5
            max_targets_per_night = 20
        else:  # balanced
            # Balanced mode: middle ground
            min_duration = timedelta(minutes=self.settings.min_target_duration_minutes)
            max_duration = timedelta(minutes=90)  # Cap at 1.5 hours
            min_score_threshold = 0.6
            max_targets_per_night = 15

        # Track which targets have been observed
        observed_targets = set()

        while current_time < session.imaging_end and len(scheduled) < max_targets_per_night:
            # Find best target for current time
            best_target, duration, target_score = self._find_best_target(
                targets=targets,
                location=location,
                current_time=current_time,
                end_time=session.imaging_end,
                constraints=constraints,
                weather_forecasts=weather_forecasts,
                observed_targets=observed_targets,
            )

            if best_target is None or duration < min_duration or target_score < min_score_threshold:
                # No suitable targets, advance time
                current_time += timedelta(minutes=5)
                continue

            # Cap duration based on planning mode
            if duration > max_duration:
                duration = max_duration

            # Calculate positions and field rotation
            start_alt, start_az = self.ephemeris.calculate_position(best_target, location, current_time)
            end_time = current_time + duration
            end_alt, end_az = self.ephemeris.calculate_position(best_target, location, end_time)

            # Field rotation rate at midpoint
            mid_time = current_time + (duration / 2)
            rotation_rate = self.ephemeris.calculate_field_rotation_rate(best_target, location, mid_time)

            # Calculate recommended exposure settings
            recommended_exposure, recommended_frames = self._calculate_exposure_settings(best_target, duration)

            # Get weather score for this time
            weather_score = self._get_weather_score_for_time(current_time, weather_forecasts)

            # Calculate full score
            target_score = self._score_target(best_target, location, current_time, duration, constraints, weather_score)

            # Create scheduled target
            scheduled_target = ScheduledTarget(
                target=best_target,
                start_time=current_time,
                end_time=end_time,
                duration_minutes=int(duration.total_seconds() / 60),
                start_altitude=start_alt,
                end_altitude=end_alt,
                start_azimuth=start_az,
                end_azimuth=end_az,
                field_rotation_rate=rotation_rate,
                recommended_exposure=recommended_exposure,
                recommended_frames=recommended_frames,
                score=target_score,
            )

            scheduled.append(scheduled_target)
            observed_targets.add(best_target.catalog_id)

            # Advance time (target duration + slew time)
            current_time = end_time + slew_time

        return scheduled

    def _find_best_target(
        self,
        targets: List[DSOTarget],
        location: Location,
        current_time: datetime,
        end_time: datetime,
        constraints: ObservingConstraints,
        weather_forecasts: List,
        observed_targets: set,
    ) -> Tuple[Optional[DSOTarget], timedelta, float]:
        """
        Find the best target for the current time using urgency-based scoring.

        Args:
            targets: Candidate targets
            location: Observer location
            current_time: Current time
            end_time: Session end time
            constraints: Observing constraints
            weather_forecasts: Weather forecasts
            observed_targets: Set of already observed target IDs

        Returns:
            Tuple of (best target, recommended duration, total score)
        """
        best_target = None
        best_score = -1
        best_duration = timedelta(0)

        lookahead = timedelta(minutes=self.settings.lookahead_minutes)

        for target in targets:
            # Skip already observed targets
            if target.catalog_id in observed_targets:
                continue

            # Check if target is visible now
            if not self.ephemeris.is_target_visible(
                target, location, current_time, constraints.min_altitude, constraints.max_altitude
            ):
                continue

            # Calculate how long target will remain visible
            duration = self._calculate_visibility_duration(target, location, current_time, end_time, constraints)

            if duration < timedelta(minutes=self.settings.min_target_duration_minutes):
                continue

            # Get weather score
            weather_score = self._get_weather_score_for_time(current_time, weather_forecasts)

            # Score the target
            score_data = self._score_target(target, location, current_time, duration, constraints, weather_score)

            # Apply urgency bonus (targets setting soon get priority)
            urgency_bonus = self._calculate_urgency_bonus(
                target, location, current_time, end_time, constraints, lookahead
            )

            total_score = score_data.total_score + urgency_bonus

            if total_score > best_score:
                best_score = total_score
                best_target = target
                best_duration = duration

        return best_target, best_duration, best_score

    def _calculate_visibility_duration(
        self,
        target: DSOTarget,
        location: Location,
        start_time: datetime,
        end_time: datetime,
        constraints: ObservingConstraints,
    ) -> timedelta:
        """
        Calculate how long a target remains visible within constraints.

        Uses binary search to efficiently find when the target sets below
        minimum altitude, reducing complexity from O(n) to O(log n) where
        n is the number of time steps in the observing window.
        """
        # First check if target is visible at start (should be, but verify)
        if not self.ephemeris.is_target_visible(
            target, location, start_time, constraints.min_altitude, constraints.max_altitude
        ):
            return timedelta(0)

        # Check if target stays visible until session end
        if self.ephemeris.is_target_visible(
            target, location, end_time, constraints.min_altitude, constraints.max_altitude
        ):
            return end_time - start_time

        # Binary search to find when target becomes invisible
        # Search with 1-minute precision
        low = start_time
        high = end_time
        precision = timedelta(minutes=1)

        while (high - low) > precision:
            mid = low + (high - low) / 2

            if self.ephemeris.is_target_visible(
                target, location, mid, constraints.min_altitude, constraints.max_altitude
            ):
                # Still visible at mid, search later half
                low = mid
            else:
                # Not visible at mid, search earlier half
                high = mid

        return low - start_time

    def _score_target(
        self,
        target: DSOTarget,
        location: Location,
        time: datetime,
        duration: timedelta,
        constraints: ObservingConstraints,
        weather_score: float,
    ) -> TargetScore:
        """
        Calculate composite score for a target.

        Components:
        - Visibility score (40%): altitude, duration, field rotation
        - Weather score (30%): from weather service
        - Object score (30%): brightness, size match

        Args:
            target: Target to score
            location: Observer location
            time: Observation time
            duration: Observation duration
            constraints: Observing constraints
            weather_score: Weather quality score

        Returns:
            TargetScore with component scores
        """
        # Visibility score
        alt, az = self.ephemeris.calculate_position(target, location, time)

        # Altitude score (prefer 45-65 degrees)
        if self.settings.optimal_min_altitude <= alt <= self.settings.optimal_max_altitude:
            altitude_score = 1.0
        elif alt < self.settings.optimal_min_altitude:
            altitude_score = (alt - constraints.min_altitude) / (
                self.settings.optimal_min_altitude - constraints.min_altitude
            )
        else:
            altitude_score = 1.0 - (alt - self.settings.optimal_max_altitude) / (
                constraints.max_altitude - self.settings.optimal_max_altitude
            )

        # Field rotation score (lower is better)
        rotation_rate = self.ephemeris.calculate_field_rotation_rate(target, location, time)
        if rotation_rate < 0.5:
            rotation_score = 1.0
        elif rotation_rate > 2.0:
            rotation_score = 0.3
        else:
            rotation_score = 1.0 - ((rotation_rate - 0.5) / 1.5) * 0.7

        # Duration score (longer is better, up to a point)
        duration_minutes = duration.total_seconds() / 60
        if duration_minutes > 120:
            duration_score = 1.0
        else:
            duration_score = duration_minutes / 120.0

        visibility_score = altitude_score * 0.5 + rotation_score * 0.3 + duration_score * 0.2

        # Object score
        # Brightness score (brighter is better, up to mag 10)
        if target.magnitude < 6:
            brightness_score = 1.0
        elif target.magnitude > 10:
            brightness_score = 0.3
        else:
            brightness_score = 1.0 - ((target.magnitude - 6) / 4) * 0.7

        # Size score (prefer objects that fit well in FOV)
        fov_diag = ((self.settings.seestar_fov_width**2 + self.settings.seestar_fov_height**2) ** 0.5) * 60  # arcmin
        size_ratio = target.size_arcmin / fov_diag

        if 0.3 < size_ratio < 1.2:
            size_score = 1.0
        elif size_ratio < 0.1:
            size_score = 0.4  # Too small
        elif size_ratio > 3.0:
            size_score = 0.5  # Too large
        else:
            if size_ratio < 0.3:
                size_score = 0.4 + (size_ratio / 0.3) * 0.6
            else:
                size_score = 1.0 - ((size_ratio - 1.2) / 1.8) * 0.5

        object_score = brightness_score * 0.6 + size_score * 0.4

        # Combined score
        total_score = visibility_score * 0.4 + weather_score * 0.3 + object_score * 0.3

        return TargetScore(
            visibility_score=visibility_score,
            weather_score=weather_score,
            object_score=object_score,
            total_score=total_score,
        )

    def _calculate_urgency_bonus(
        self,
        target: DSOTarget,
        location: Location,
        current_time: datetime,
        end_time: datetime,
        constraints: ObservingConstraints,
        lookahead: timedelta,
    ) -> float:
        """
        Calculate urgency bonus for targets setting soon.

        Targets that will set within the lookahead window get a bonus.
        """
        # Check if target will still be visible after lookahead
        future_time = current_time + lookahead

        if future_time > end_time:
            return 0.0

        is_visible_now = self.ephemeris.is_target_visible(
            target, location, current_time, constraints.min_altitude, constraints.max_altitude
        )
        is_visible_later = self.ephemeris.is_target_visible(
            target, location, future_time, constraints.min_altitude, constraints.max_altitude
        )

        # If target is setting within lookahead, give urgency bonus
        if is_visible_now and not is_visible_later:
            return 0.2  # 20% bonus
        else:
            return 0.0

    def _calculate_exposure_settings(self, target: DSOTarget, duration: timedelta) -> Tuple[int, int]:
        """
        Calculate recommended exposure time and frame count.

        Based on object brightness and available time.

        Args:
            target: Target object
            duration: Available observation time

        Returns:
            Tuple of (exposure_seconds, frame_count)
        """
        # Base exposure on magnitude
        # Seestar S50 max exposure is 10s, use 10s for all targets
        exposure = 10

        # Calculate how many frames fit in duration
        # Account for readout time (assume 2s overhead per frame)
        total_seconds = duration.total_seconds()
        time_per_frame = exposure + 2
        frame_count = int(total_seconds / time_per_frame)

        # Minimum 10 frames for stacking
        frame_count = max(10, frame_count)

        return exposure, frame_count

    def _get_weather_score_for_time(self, time: datetime, weather_forecasts: List) -> float:
        """Get weather score for a specific time from forecasts."""
        if not weather_forecasts:
            return 0.8  # Default optimistic score

        # Find closest forecast
        closest_forecast = min(weather_forecasts, key=lambda f: abs((f.timestamp - time).total_seconds()))

        return self.weather.calculate_weather_score(closest_forecast)
