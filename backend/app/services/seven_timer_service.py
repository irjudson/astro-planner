"""7Timer API service for astronomy-specific weather data.

This service fetches seeing and transparency forecasts from 7Timer,
which provides astronomy-optimized weather predictions.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import requests

from app.models import Location, WeatherForecast


class SevenTimerService:
    """Service for fetching astronomy weather data from 7Timer API.

    7Timer provides astronomy-specific forecasts including:
    - Seeing: Atmospheric stability in arcseconds (lower is better)
    - Transparency: Sky clarity as limiting magnitude (higher is better)
    - Cloud cover: Cloud coverage in percentage

    API Documentation: http://www.7timer.info/doc.php?lang=en
    """

    BASE_URL = "http://www.7timer.info/bin/astro.php"
    REQUEST_TIMEOUT = 10  # seconds

    # 7Timer transparency scale to limiting magnitude conversion
    # Based on 7Timer documentation and typical dark sky conditions
    TRANSPARENCY_TO_MAGNITUDE = {
        1: 16.0,  # <0.3 mag loss - poor transparency
        2: 17.0,  # 0.3-0.4 mag loss
        3: 18.0,  # 0.4-0.5 mag loss
        4: 19.0,  # 0.5-0.6 mag loss
        5: 20.0,  # 0.6-0.7 mag loss - good
        6: 21.0,  # 0.7-0.85 mag loss - very good
        7: 21.5,  # 0.85-1.0 mag loss - excellent
        8: 22.0,  # >1.0 mag loss - exceptional
    }

    # 7Timer cloudcover scale to percentage
    CLOUDCOVER_TO_PERCENT = {
        1: 6,    # 0%-6%
        2: 19,   # 6%-19%
        3: 31,   # 19%-31%
        4: 44,   # 31%-44%
        5: 56,   # 44%-56%
        6: 69,   # 56%-69%
        7: 81,   # 69%-81%
        8: 94,   # 81%-94%
        9: 100,  # 94%-100%
    }

    def __init__(self):
        """Initialize 7Timer service."""
        self.logger = logging.getLogger(__name__)

    def get_astronomy_forecast(
        self,
        location: Location,
        start_time: datetime,
        end_time: datetime
    ) -> List[WeatherForecast]:
        """Get astronomy-specific weather forecast from 7Timer.

        Args:
            location: Observer location
            start_time: Start of forecast window
            end_time: End of forecast window

        Returns:
            List of WeatherForecast objects with astronomy data
        """
        try:
            # Build API request parameters
            params = {
                "lon": round(location.longitude, 4),
                "lat": round(location.latitude, 4),
                "ac": 0,  # Altitude correction (0 for default)
                "unit": "metric",
                "output": "json",
                "tzshift": 0,  # UTC
            }

            self.logger.info(
                f"Fetching 7Timer forecast for {location.name} "
                f"({location.latitude}, {location.longitude})"
            )

            # Make API request
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            # Parse forecast data
            forecasts = self._parse_forecast_data(
                data,
                location,
                start_time,
                end_time
            )

            self.logger.info(f"Retrieved {len(forecasts)} 7Timer forecast periods")
            return forecasts

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"7Timer API request failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error processing 7Timer data: {e}", exc_info=True)
            return []

    def _parse_forecast_data(
        self,
        data: Dict[str, Any],
        location: Location,
        start_time: datetime,
        end_time: datetime
    ) -> List[WeatherForecast]:
        """Parse 7Timer API response into WeatherForecast objects.

        Args:
            data: JSON response from 7Timer API
            location: Observer location
            start_time: Start of forecast window
            end_time: End of forecast window

        Returns:
            List of WeatherForecast objects
        """
        forecasts = []

        if "dataseries" not in data:
            self.logger.warning("No dataseries in 7Timer response")
            return forecasts

        # Get init time (forecast generation time)
        init_str = data.get("init", "")
        try:
            # Parse init time: format is YYYYMMDDHH
            init_time = datetime.strptime(init_str, "%Y%m%d%H")
        except ValueError:
            self.logger.warning(f"Could not parse init time: {init_str}")
            init_time = datetime.utcnow()

        # Process each forecast period (3-hour intervals)
        for period in data["dataseries"]:
            try:
                # Calculate timestamp from timepoint (hours from init)
                timepoint = period.get("timepoint", 0)
                timestamp = init_time + timedelta(hours=timepoint)

                # Filter to requested time range
                if timestamp < start_time or timestamp > end_time:
                    continue

                # Extract astronomy-specific data
                seeing_raw = period.get("seeing", 3)  # arcseconds (1-8 scale)
                transparency_raw = period.get("transparency", 4)  # 1-8 scale
                cloudcover_raw = period.get("cloudcover", 5)  # 1-9 scale

                # Convert scales to usable values
                seeing_arcsec = self._convert_seeing(seeing_raw)
                transparency_mag = self._convert_transparency(transparency_raw)
                cloudcover_pct = self._convert_cloudcover(cloudcover_raw)

                # Get basic weather data (may not be present in astro endpoint)
                temp = period.get("temp2m", 10)  # Celsius
                wind_speed = period.get("wind10m", {}).get("speed", 0)  # m/s

                # Create WeatherForecast with astronomy data
                forecast = WeatherForecast(
                    timestamp=timestamp,
                    cloud_cover=cloudcover_pct,
                    humidity=50.0,  # Not provided by 7Timer astro endpoint
                    temperature=temp,
                    wind_speed=wind_speed,
                    conditions=self._describe_conditions(
                        seeing_arcsec,
                        transparency_mag,
                        cloudcover_pct
                    ),
                    seeing_arcseconds=seeing_arcsec,
                    transparency_magnitude=transparency_mag,
                    source="7timer"
                )

                forecasts.append(forecast)

            except Exception as e:
                self.logger.warning(f"Error parsing forecast period: {e}")
                continue

        return forecasts

    def _convert_seeing(self, seeing_raw: int) -> float:
        """Convert 7Timer seeing scale to arcseconds.

        7Timer seeing scale:
        1 = <0.5" (excellent)
        2 = 0.5-0.75" (good)
        3 = 0.75-1" (average)
        4 = 1-2" (below average)
        5 = 2-2.5" (poor)
        6 = 2.5-5" (very poor)
        7 = 5-10" (terrible)
        8 = >10" (unusable)

        Args:
            seeing_raw: 7Timer seeing value (1-8)

        Returns:
            Seeing in arcseconds (approximate midpoint)
        """
        seeing_map = {
            1: 0.4,
            2: 0.6,
            3: 0.9,
            4: 1.5,
            5: 2.2,
            6: 3.5,
            7: 7.0,
            8: 12.0,
        }
        return seeing_map.get(seeing_raw, 2.0)  # Default to 2" (typical)

    def _convert_transparency(self, transparency_raw: int) -> float:
        """Convert 7Timer transparency scale to limiting magnitude.

        Args:
            transparency_raw: 7Timer transparency value (1-8)

        Returns:
            Limiting magnitude (approximate)
        """
        return self.TRANSPARENCY_TO_MAGNITUDE.get(transparency_raw, 18.0)

    def _convert_cloudcover(self, cloudcover_raw: int) -> float:
        """Convert 7Timer cloud cover scale to percentage.

        Args:
            cloudcover_raw: 7Timer cloud cover value (1-9)

        Returns:
            Cloud cover percentage (0-100)
        """
        return float(self.CLOUDCOVER_TO_PERCENT.get(cloudcover_raw, 50))

    def _describe_conditions(
        self,
        seeing: float,
        transparency: float,
        cloudcover: float
    ) -> str:
        """Generate human-readable conditions description.

        Args:
            seeing: Seeing in arcseconds
            transparency: Transparency as limiting magnitude
            cloudcover: Cloud cover percentage

        Returns:
            Conditions description string
        """
        # Describe seeing
        if seeing < 1.0:
            seeing_desc = "Excellent seeing"
        elif seeing < 2.0:
            seeing_desc = "Good seeing"
        elif seeing < 3.0:
            seeing_desc = "Average seeing"
        else:
            seeing_desc = "Poor seeing"

        # Describe transparency
        if transparency >= 21.0:
            trans_desc = "excellent transparency"
        elif transparency >= 19.0:
            trans_desc = "good transparency"
        elif transparency >= 17.0:
            trans_desc = "moderate transparency"
        else:
            trans_desc = "poor transparency"

        # Describe clouds
        if cloudcover < 20:
            cloud_desc = "clear"
        elif cloudcover < 50:
            cloud_desc = "partly cloudy"
        elif cloudcover < 80:
            cloud_desc = "mostly cloudy"
        else:
            cloud_desc = "overcast"

        return f"{cloud_desc.capitalize()}, {seeing_desc.lower()}, {trans_desc}"
