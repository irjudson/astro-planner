"""Service for calculating best viewing months for celestial objects."""

from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import math
import calendar


class MonthRating(Enum):
    """Viewing quality rating for a month (1-5 scale)."""
    EXCELLENT = 5
    GOOD = 4
    FAIR = 3
    POOR = 2
    NOT_VISIBLE = 1


class ViewingMonth(BaseModel):
    """Viewing conditions for a specific month."""

    month: int  # 1-12
    month_name: str
    rating: MonthRating
    visibility_hours: float
    best_time: str
    notes: Optional[str] = None

    def is_good_month(self) -> bool:
        """Check if this is a good viewing month."""
        return self.rating.value >= MonthRating.GOOD.value


class ViewingMonthsService:
    """Service for calculating best viewing months for deep sky objects."""

    def __init__(self):
        """Initialize service."""
        self.month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

    def calculate_viewing_months(
        self,
        ra_hours: float,
        dec_degrees: float,
        latitude: float,
        object_name: Optional[str] = None
    ) -> List[ViewingMonth]:
        """
        Calculate best viewing months for an object.

        Args:
            ra_hours: Right ascension in hours (0-24)
            dec_degrees: Declination in degrees (-90 to +90)
            latitude: Observer latitude
            object_name: Optional name for notes

        Returns:
            List of 12 ViewingMonth objects (one per month)
        """
        months = []

        for month in range(1, 13):
            # Calculate viewing conditions for this month
            viewing_month = self._calculate_month_conditions(
                ra_hours=ra_hours,
                dec_degrees=dec_degrees,
                latitude=latitude,
                month=month,
                object_name=object_name
            )
            months.append(viewing_month)

        return months

    def _calculate_month_conditions(
        self,
        ra_hours: float,
        dec_degrees: float,
        latitude: float,
        month: int,
        object_name: Optional[str]
    ) -> ViewingMonth:
        """Calculate viewing conditions for a specific month."""
        # Check if object is visible from this latitude
        if not self._is_visible_from_latitude(dec_degrees, latitude):
            return ViewingMonth(
                month=month,
                month_name=self._get_month_name(month),
                rating=MonthRating.NOT_VISIBLE,
                visibility_hours=0.0,
                best_time="N/A",
                notes="Object never rises above horizon"
            )

        # Calculate maximum altitude at transit
        max_altitude = self._calculate_altitude_at_transit(dec_degrees, latitude)

        # Calculate visibility hours for this month
        visibility_hours = self._calculate_visibility_hours(
            dec_degrees, latitude, month
        )

        # Determine if object transits during evening hours
        is_evening = self._is_evening_object(ra_hours, month)

        # Rate the viewing quality
        rating = self._rate_viewing_quality(
            max_altitude, visibility_hours, is_evening
        )

        # Calculate best observation time
        best_time = self._calculate_best_observation_time(ra_hours, month)

        # Generate notes
        notes = self._generate_notes(
            max_altitude, is_evening, self._get_season_for_month(month)
        )

        return ViewingMonth(
            month=month,
            month_name=self._get_month_name(month),
            rating=rating,
            visibility_hours=visibility_hours,
            best_time=best_time,
            notes=notes
        )

    def _is_visible_from_latitude(
        self,
        dec_degrees: float,
        latitude: float
    ) -> bool:
        """Check if object can be seen from given latitude."""
        # Object is circumpolar if: dec > (90 - latitude)
        # Object never rises if: dec < -(90 - latitude)

        # For simplicity, check if object gets at least 10° above horizon
        min_dec = -(90 - latitude) + 10
        return dec_degrees > min_dec

    def _calculate_altitude_at_transit(
        self,
        dec_degrees: float,
        latitude: float
    ) -> float:
        """Calculate maximum altitude when object transits meridian."""
        # At transit: altitude = 90 - |latitude - declination|
        altitude = 90 - abs(latitude - dec_degrees)
        return max(0, min(90, altitude))

    def _calculate_visibility_hours(
        self,
        dec_degrees: float,
        latitude: float,
        month: int
    ) -> float:
        """Calculate hours object is above horizon and visible."""
        # Simplified calculation based on hour angle
        # More sophisticated would account for twilight, moon phase, etc.

        lat_rad = math.radians(latitude)
        dec_rad = math.radians(dec_degrees)

        # Calculate hour angle when object is at 20° altitude
        min_alt_rad = math.radians(20)  # Minimum useful altitude

        try:
            cos_ha = (math.sin(min_alt_rad) - math.sin(lat_rad) * math.sin(dec_rad)) / \
                     (math.cos(lat_rad) * math.cos(dec_rad))

            # Clamp to valid range
            cos_ha = max(-1, min(1, cos_ha))

            hour_angle = math.degrees(math.acos(cos_ha))
            hours = (hour_angle / 15.0) * 2  # Convert to hours, both sides of meridian

            # Adjust for season (longer nights in winter)
            season_factor = self._get_season_night_length_factor(month, latitude)
            hours = hours * season_factor

            return max(0, min(12, hours))

        except (ValueError, ZeroDivisionError):
            return 0.0

    def _get_season_night_length_factor(self, month: int, latitude: float) -> float:
        """Get night length factor for season."""
        # Northern hemisphere
        if latitude > 0:
            if month in [12, 1, 2]:  # Winter - longer nights
                return 1.2
            elif month in [6, 7, 8]:  # Summer - shorter nights
                return 0.8
        # Southern hemisphere
        else:
            if month in [6, 7, 8]:  # Winter - longer nights
                return 1.2
            elif month in [12, 1, 2]:  # Summer - shorter nights
                return 0.8

        return 1.0  # Spring/Fall

    def _is_evening_object(self, ra_hours: float, month: int) -> bool:
        """Check if object transits during evening hours (7pm-midnight)."""
        # Calculate approximate LST at 9pm for mid-month
        # Rough approximation: LST ≈ month * 2 hours

        evening_lst = (month - 1) * 2  # Approximate LST at evening
        diff = abs(ra_hours - evening_lst)

        # Account for wrap-around
        if diff > 12:
            diff = 24 - diff

        return diff < 6  # Within 6 hours of transit at evening

    def _rate_viewing_quality(
        self,
        altitude: float,
        visibility_hours: float,
        is_evening: bool
    ) -> MonthRating:
        """Rate viewing quality for the month."""
        score = 0

        # Altitude contribution (0-3 points)
        if altitude >= 70:
            score += 3
        elif altitude >= 50:
            score += 2
        elif altitude >= 30:
            score += 1

        # Visibility hours contribution (0-2 points)
        if visibility_hours >= 8:
            score += 2
        elif visibility_hours >= 5:
            score += 1

        # Evening bonus (0-1 point)
        if is_evening:
            score += 1

        # Map score to rating
        if score >= 5:
            return MonthRating.EXCELLENT
        elif score >= 4:
            return MonthRating.GOOD
        elif score >= 2:
            return MonthRating.FAIR
        elif score >= 1:
            return MonthRating.POOR
        else:
            return MonthRating.NOT_VISIBLE

    def _calculate_best_observation_time(
        self,
        ra_hours: float,
        month: int
    ) -> str:
        """Calculate best observation time for month."""
        # Approximate LST at 9pm for month
        evening_lst = (month - 1) * 2

        # Calculate when object transits
        hours_until_transit = ra_hours - evening_lst

        # Adjust for wrap-around
        while hours_until_transit < -12:
            hours_until_transit += 24
        while hours_until_transit > 12:
            hours_until_transit -= 24

        # Best time is around transit
        best_hour = 21 + int(hours_until_transit)

        # Normalize to 0-23
        while best_hour < 0:
            best_hour += 24
        while best_hour >= 24:
            best_hour -= 24

        return f"{best_hour:02d}:00"

    def _generate_notes(
        self,
        altitude: float,
        is_evening: bool,
        season: str
    ) -> str:
        """Generate viewing notes."""
        notes = []

        if altitude >= 70:
            notes.append("Object high in sky")
        elif altitude >= 50:
            notes.append("Good altitude")
        elif altitude >= 30:
            notes.append("Moderate altitude")
        else:
            notes.append("Low on horizon")

        if is_evening:
            notes.append("visible in evening hours")
        else:
            notes.append("best after midnight")

        notes.append(f"({season})")

        return ", ".join(notes)

    def _get_season_for_month(self, month: int) -> str:
        """Get season name for month (Northern Hemisphere)."""
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"

    def _get_month_name(self, month: int) -> str:
        """Get month name from number."""
        return self.month_names[month - 1]

    def get_best_months(
        self,
        months: List[ViewingMonth],
        count: int = 3
    ) -> List[ViewingMonth]:
        """
        Get best viewing months sorted by quality.

        Args:
            months: List of viewing months
            count: Number of best months to return

        Returns:
            Top months sorted by rating and visibility
        """
        # Sort by rating value (descending), then visibility hours
        sorted_months = sorted(
            months,
            key=lambda m: (m.rating.value, m.visibility_hours),
            reverse=True
        )

        return sorted_months[:count]

    def get_viewing_summary(
        self,
        months: List[ViewingMonth]
    ) -> Dict:
        """
        Generate viewing summary.

        Args:
            months: List of viewing months

        Returns:
            Dictionary with summary information
        """
        good_months = [m for m in months if m.is_good_month()]
        best_months = self.get_best_months(months, count=3)

        visibility_ranges = []
        current_range = []

        for month in months:
            if month.rating.value >= MonthRating.FAIR.value:
                current_range.append(month.month_name)
            else:
                if current_range:
                    visibility_ranges.append(current_range)
                    current_range = []

        if current_range:
            visibility_ranges.append(current_range)

        return {
            "best_months": [m.month_name for m in best_months],
            "good_months_count": len(good_months),
            "visibility_range": visibility_ranges,
            "peak_month": best_months[0].month_name if best_months else None
        }
