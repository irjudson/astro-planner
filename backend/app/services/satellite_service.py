"""ISS and satellite pass prediction service."""

from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
import requests


class PassVisibility(Enum):
    """Satellite pass visibility quality (1-4 scale)."""
    EXCELLENT = 4
    GOOD = 3
    FAIR = 2
    POOR = 1


class SatellitePass(BaseModel):
    """Single satellite pass prediction."""

    satellite_name: str
    start_time: datetime
    end_time: datetime
    max_altitude_deg: float
    max_altitude_time: datetime
    start_azimuth_deg: float
    end_azimuth_deg: float
    visibility: PassVisibility
    magnitude: float

    def duration_minutes(self) -> float:
        """Calculate pass duration in minutes."""
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 60.0

    def quality_score(self) -> float:
        """
        Calculate overall pass quality score (0-1).

        Factors:
        - Max altitude: 50%
        - Visibility level: 30%
        - Duration: 20%
        """
        # Altitude score (normalized to 0-90 degrees)
        altitude_score = min(self.max_altitude_deg / 90.0, 1.0)

        # Visibility score (normalized to 0-1)
        visibility_score = self.visibility.value / 4.0

        # Duration score (normalized, ideal ~6 minutes)
        duration = self.duration_minutes()
        duration_score = min(duration / 6.0, 1.0)

        # Weighted average
        total_score = (
            altitude_score * 0.5 +
            visibility_score * 0.3 +
            duration_score * 0.2
        )

        return total_score


class SatelliteService:
    """Service for predicting ISS and satellite passes."""

    def __init__(self):
        """Initialize service."""
        self.api_base_url = "https://api.n2yo.com/rest/v1/satellite"
        self.timeout = 10

    def get_iss_passes(
        self,
        latitude: float,
        longitude: float,
        days: int = 10,
        min_altitude: float = 0.0
    ) -> List[SatellitePass]:
        """
        Get ISS pass predictions for location.

        Args:
            latitude: Observer latitude
            longitude: Observer longitude
            days: Number of days to predict (default 10)
            min_altitude: Minimum altitude for pass (default 0)

        Returns:
            List of visible ISS passes
        """
        # ISS NORAD ID is 25544
        return self.get_satellite_passes(
            norad_id=25544,
            satellite_name="ISS (ZARYA)",
            latitude=latitude,
            longitude=longitude,
            days=days,
            min_altitude=min_altitude
        )

    def get_satellite_passes(
        self,
        norad_id: int,
        satellite_name: str,
        latitude: float,
        longitude: float,
        days: int = 10,
        min_altitude: float = 0.0
    ) -> List[SatellitePass]:
        """
        Get satellite pass predictions.

        Args:
            norad_id: NORAD catalog ID
            satellite_name: Name of satellite
            latitude: Observer latitude
            longitude: Observer longitude
            days: Number of days to predict
            min_altitude: Minimum altitude for pass

        Returns:
            List of visible passes
        """
        try:
            # Fetch pass predictions from API
            # Note: Real implementation would need API key from n2yo.com
            # This is simplified for demonstration
            passes_data = self._fetch_passes_from_api(
                norad_id=norad_id,
                latitude=latitude,
                longitude=longitude,
                days=days,
                min_altitude=min_altitude
            )

            # Parse into SatellitePass objects
            passes = []
            for pass_data in passes_data:
                pass_obj = self._parse_pass_data(satellite_name, pass_data)
                if pass_obj:
                    passes.append(pass_obj)

            return passes

        except Exception:
            # Return empty list on error
            return []

    def _fetch_passes_from_api(
        self,
        norad_id: int,
        latitude: float,
        longitude: float,
        days: int,
        min_altitude: float
    ) -> List[dict]:
        """
        Fetch pass data from API.

        Note: This is a simplified implementation. Real usage requires
        an API key from n2yo.com and proper error handling.
        """
        url = f"{self.api_base_url}/visualpasses/{norad_id}/{latitude}/{longitude}/0/{days}/{min_altitude}"

        # In production, would add API key parameter
        # url += f"&apiKey={api_key}"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        return data.get("passes", [])

    def _parse_pass_data(
        self,
        satellite_name: str,
        pass_data: dict
    ) -> Optional[SatellitePass]:
        """Parse pass data from API response."""
        try:
            # Parse timestamps
            start_time = datetime.fromtimestamp(pass_data["startUTC"])
            end_time = datetime.fromtimestamp(pass_data["endUTC"])

            # Calculate max altitude time (midpoint approximation)
            duration = end_time - start_time
            max_alt_time = start_time + (duration / 2)

            # Get azimuth values
            start_az = float(pass_data.get("startAz", 0))
            end_az = float(pass_data.get("endAz", 0))
            max_el = float(pass_data.get("maxEl", 0))

            # Get magnitude
            magnitude = float(pass_data.get("mag", 0.0))

            # Classify visibility
            visibility = self._classify_visibility(magnitude, max_el)

            return SatellitePass(
                satellite_name=satellite_name,
                start_time=start_time,
                end_time=end_time,
                max_altitude_deg=max_el,
                max_altitude_time=max_alt_time,
                start_azimuth_deg=start_az,
                end_azimuth_deg=end_az,
                visibility=visibility,
                magnitude=magnitude
            )

        except (KeyError, ValueError):
            return None

    def _classify_visibility(
        self,
        magnitude: float,
        max_altitude: float
    ) -> PassVisibility:
        """
        Classify pass visibility based on brightness and altitude.

        Args:
            magnitude: Apparent magnitude (brighter = more negative)
            max_altitude: Maximum altitude in degrees

        Returns:
            Visibility classification
        """
        # Excellent: Very bright and high
        if magnitude < -3.0 and max_altitude >= 60:
            return PassVisibility.EXCELLENT

        # Good: Bright and reasonably high
        if magnitude < -2.0 and max_altitude >= 40:
            return PassVisibility.GOOD

        # Fair: Moderately visible
        if magnitude < 0.0 and max_altitude >= 20:
            return PassVisibility.FAIR

        # Poor: Dim or low
        return PassVisibility.POOR

    def filter_visible_passes(
        self,
        passes: List[SatellitePass],
        min_altitude: float = 20.0,
        min_visibility: PassVisibility = PassVisibility.POOR
    ) -> List[SatellitePass]:
        """
        Filter passes by minimum criteria.

        Args:
            passes: List of passes to filter
            min_altitude: Minimum altitude threshold
            min_visibility: Minimum visibility level

        Returns:
            Filtered list of passes
        """
        filtered = []
        for pass_obj in passes:
            if (pass_obj.max_altitude_deg >= min_altitude and
                pass_obj.visibility.value >= min_visibility.value):
                filtered.append(pass_obj)
        return filtered

    def get_best_passes(
        self,
        passes: List[SatellitePass],
        count: int = 5
    ) -> List[SatellitePass]:
        """
        Get best passes sorted by quality score.

        Args:
            passes: List of passes to sort
            count: Maximum number to return

        Returns:
            Top passes sorted by quality
        """
        sorted_passes = sorted(
            passes,
            key=lambda p: p.quality_score(),
            reverse=True
        )
        return sorted_passes[:count]

    def _compass_to_degrees(self, compass: str) -> float:
        """
        Convert compass direction to degrees.

        Args:
            compass: Compass direction (N, NE, E, SE, S, SW, W, NW)

        Returns:
            Azimuth in degrees (0-359)
        """
        compass_map = {
            "N": 0,
            "NNE": 22.5,
            "NE": 45,
            "ENE": 67.5,
            "E": 90,
            "ESE": 112.5,
            "SE": 135,
            "SSE": 157.5,
            "S": 180,
            "SSW": 202.5,
            "SW": 225,
            "WSW": 247.5,
            "W": 270,
            "WNW": 292.5,
            "NW": 315,
            "NNW": 337.5
        }
        return compass_map.get(compass.upper(), 0.0)
