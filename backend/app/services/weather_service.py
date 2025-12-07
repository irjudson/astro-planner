"""Weather forecasting service using OpenWeatherMap and 7Timer APIs."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytz
import requests

from app.core import get_settings
from app.models import Location, WeatherForecast
from app.services.seven_timer_service import SevenTimerService


class WeatherService:
    """Service for fetching weather forecasts from multiple sources.

    Combines general weather data from OpenWeatherMap with astronomy-specific
    data from 7Timer for comprehensive observing condition forecasts.
    """

    def __init__(self):
        """Initialize with API key from settings and 7Timer service."""
        self.settings = get_settings()
        self.api_key = self.settings.openweathermap_api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/forecast"
        self.seven_timer = SevenTimerService()
        self.logger = logging.getLogger(__name__)

    def get_forecast(self, location: Location, start_time: datetime, end_time: datetime) -> List[WeatherForecast]:
        """
        Get comprehensive weather forecast combining multiple sources.

        Fetches data from:
        1. OpenWeatherMap - General weather (clouds, humidity, temperature, wind)
        2. 7Timer - Astronomy-specific (seeing, transparency)

        Args:
            location: Observer location
            start_time: Start of forecast period
            end_time: End of forecast period

        Returns:
            List of merged weather forecasts with astronomy data
        """
        self.logger.info(f"Fetching weather forecast for {location.name} " f"from {start_time} to {end_time}")

        # Fetch from both sources
        owm_forecasts = self._get_openweathermap_forecast(location, start_time, end_time)
        seven_timer_forecasts = self.seven_timer.get_astronomy_forecast(location, start_time, end_time)

        # Merge forecasts
        merged_forecasts = self._merge_forecasts(owm_forecasts, seven_timer_forecasts)

        self.logger.info(f"Generated {len(merged_forecasts)} merged forecast periods")

        # Return merged forecasts or default if both failed
        return merged_forecasts if merged_forecasts else self._generate_default_forecast(start_time, end_time)

    def _get_openweathermap_forecast(
        self, location: Location, start_time: datetime, end_time: datetime
    ) -> List[WeatherForecast]:
        """Get general weather forecast from OpenWeatherMap.

        Args:
            location: Observer location
            start_time: Start of forecast period
            end_time: End of forecast period

        Returns:
            List of weather forecasts from OpenWeatherMap
        """
        if not self.api_key:
            self.logger.warning("No OpenWeatherMap API key configured")
            return []

        try:
            # Call OpenWeatherMap API
            params = {"lat": location.latitude, "lon": location.longitude, "appid": self.api_key, "units": "metric"}

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse forecast data
            forecasts = []
            tz = pytz.timezone(location.timezone)

            for item in data.get("list", []):
                # Convert timestamp
                timestamp = datetime.fromtimestamp(item["dt"], tz=pytz.UTC).astimezone(tz)

                # Only include forecasts within our time range
                if start_time <= timestamp <= end_time:
                    forecast = WeatherForecast(
                        timestamp=timestamp,
                        cloud_cover=item.get("clouds", {}).get("all", 0),
                        humidity=item.get("main", {}).get("humidity", 0),
                        temperature=item.get("main", {}).get("temp", 0),
                        wind_speed=item.get("wind", {}).get("speed", 0),
                        conditions=item.get("weather", [{}])[0].get("description", "Unknown"),
                        source="openweathermap",
                    )
                    forecasts.append(forecast)

            self.logger.info(f"Retrieved {len(forecasts)} OpenWeatherMap forecasts")
            return forecasts

        except Exception as e:
            self.logger.warning(f"OpenWeatherMap API error: {e}")
            return []

    def _merge_forecasts(
        self, owm_forecasts: List[WeatherForecast], seven_timer_forecasts: List[WeatherForecast]
    ) -> List[WeatherForecast]:
        """Merge forecasts from both sources.

        Matches forecasts by timestamp and combines data, prioritizing
        7Timer's astronomy-specific data with OpenWeatherMap's detailed
        general weather information.

        Args:
            owm_forecasts: OpenWeatherMap forecasts
            seven_timer_forecasts: 7Timer astronomy forecasts

        Returns:
            List of merged forecasts with data from both sources
        """
        if not owm_forecasts and not seven_timer_forecasts:
            return []

        # If only one source available, return that
        if not owm_forecasts:
            return seven_timer_forecasts
        if not seven_timer_forecasts:
            return owm_forecasts

        # Create lookup dictionary for 7Timer data by hour
        seven_timer_by_hour: Dict[datetime, WeatherForecast] = {}
        for forecast in seven_timer_forecasts:
            # Round to nearest 3 hours for matching
            hour_key = forecast.timestamp.replace(minute=0, second=0, microsecond=0)
            hour_key = hour_key.replace(hour=(hour_key.hour // 3) * 3)
            seven_timer_by_hour[hour_key] = forecast

        # Merge OWM forecasts with 7Timer data
        merged = []
        for owm_forecast in owm_forecasts:
            # Find matching 7Timer forecast (within 3-hour window)
            hour_key = owm_forecast.timestamp.replace(minute=0, second=0, microsecond=0)
            hour_key = hour_key.replace(hour=(hour_key.hour // 3) * 3)

            seven_timer_match = seven_timer_by_hour.get(hour_key)

            if seven_timer_match:
                # Merge data: OWM general weather + 7Timer astronomy data
                merged_forecast = WeatherForecast(
                    timestamp=owm_forecast.timestamp,
                    cloud_cover=owm_forecast.cloud_cover,  # Use OWM cloud data (more detailed)
                    humidity=owm_forecast.humidity,
                    temperature=owm_forecast.temperature,
                    wind_speed=owm_forecast.wind_speed,
                    conditions=self._merge_conditions(owm_forecast.conditions, seven_timer_match.conditions),
                    seeing_arcseconds=seven_timer_match.seeing_arcseconds,
                    transparency_magnitude=seven_timer_match.transparency_magnitude,
                    source="composite",
                )
                merged.append(merged_forecast)
            else:
                # No 7Timer match, use OWM only
                merged.append(owm_forecast)

        return merged

    def _merge_conditions(self, owm_cond: str, seven_timer_cond: str) -> str:
        """Merge condition descriptions from both sources.

        Args:
            owm_cond: OpenWeatherMap conditions
            seven_timer_cond: 7Timer conditions

        Returns:
            Merged conditions description
        """
        # Extract key parts from 7Timer (seeing/transparency)
        if "seeing" in seven_timer_cond.lower():
            # Add seeing info to OWM conditions
            seeing_part = seven_timer_cond.split(",")[1:]  # Skip cloud part
            if seeing_part:
                return f"{owm_cond}, {', '.join(seeing_part)}"

        return owm_cond

    def _generate_default_forecast(self, start_time: datetime, end_time: datetime) -> List[WeatherForecast]:
        """
        Generate a default forecast when API is unavailable.

        Returns optimistic conditions for planning purposes.
        """
        forecasts = []
        current_time = start_time

        # Generate hourly forecasts
        while current_time <= end_time:
            forecast = WeatherForecast(
                timestamp=current_time,
                cloud_cover=20.0,  # Optimistic
                humidity=50.0,
                temperature=10.0,
                wind_speed=2.0,
                conditions="Clear sky (estimated)",
            )
            forecasts.append(forecast)
            current_time = current_time + timedelta(hours=1)

        return forecasts

    def calculate_weather_score(self, forecast: WeatherForecast) -> float:
        """
        Calculate a composite weather quality score (0-1).

        Uses different scoring strategies based on available data:

        1. **Composite (7Timer + OpenWeatherMap)** - 60% astronomy + 40% general:
           - Astronomy metrics (60%): Seeing (30%) + Transparency (30%)
           - General weather (40%): Cloud cover (24%) + Humidity (10%) + Wind (6%)

        2. **7Timer only** - 100% astronomy metrics:
           - Seeing (50%) + Transparency (50%)

        3. **OpenWeatherMap only** - 100% general weather:
           - Cloud cover (60%) + Humidity (25%) + Wind (15%)

        Args:
            forecast: Weather forecast data

        Returns:
            Score from 0 (bad) to 1 (excellent)
        """
        has_astronomy = forecast.seeing_arcseconds is not None and forecast.transparency_magnitude is not None

        # Cloud cover score is always factored in - no astronomy is possible through clouds
        cloud_score = max(0.0, 1.0 - (forecast.cloud_cover / 100.0))

        if has_astronomy and forecast.source == "composite":
            # Composite scoring: 40% cloud + 35% astronomy + 25% general
            astronomy_score = self._calculate_astronomy_score(
                forecast.seeing_arcseconds, forecast.transparency_magnitude
            )
            general_score = self._calculate_general_weather_score(
                forecast.cloud_cover, forecast.humidity, forecast.wind_speed
            )
            total_score = (cloud_score * 0.4) + (astronomy_score * 0.35) + (general_score * 0.25)

        elif has_astronomy:
            # 7Timer data - cloud cover + astronomy metrics
            # Cloud cover is most important (50%), then astronomy conditions (50%)
            astronomy_score = self._calculate_astronomy_score(
                forecast.seeing_arcseconds, forecast.transparency_magnitude
            )
            total_score = (cloud_score * 0.5) + (astronomy_score * 0.5)

        else:
            # OpenWeatherMap only - general weather metrics
            total_score = self._calculate_general_weather_score(
                forecast.cloud_cover, forecast.humidity, forecast.wind_speed
            )

        return max(0.0, min(1.0, total_score))

    def _calculate_astronomy_score(self, seeing: Optional[float], transparency: Optional[float]) -> float:
        """Calculate score based on astronomy-specific metrics.

        Args:
            seeing: Atmospheric seeing in arcseconds (lower is better)
            transparency: Sky transparency as limiting magnitude (higher is better)

        Returns:
            Astronomy quality score (0-1)
        """
        # Seeing score (arcseconds - lower is better)
        # Excellent: <1", Good: 1-2", Average: 2-3", Poor: >3"
        if seeing is None:
            seeing_score = 0.5  # Default neutral
        elif seeing < 1.0:
            seeing_score = 1.0
        elif seeing < 2.0:
            seeing_score = 0.8
        elif seeing < 3.0:
            seeing_score = 0.5
        else:
            seeing_score = max(0.2, 1.0 - (seeing - 3.0) / 7.0)  # Linear decay to 0.2

        # Transparency score (limiting magnitude - higher is better)
        # Excellent: >21, Good: 19-21, Average: 17-19, Poor: <17
        if transparency is None:
            transparency_score = 0.5  # Default neutral
        elif transparency >= 21.0:
            transparency_score = 1.0
        elif transparency >= 19.0:
            transparency_score = 0.7 + (transparency - 19.0) / 2.0 * 0.3
        elif transparency >= 17.0:
            transparency_score = 0.4 + (transparency - 17.0) / 2.0 * 0.3
        else:
            transparency_score = max(0.2, transparency / 17.0 * 0.4)

        # Equal weighting for astronomy metrics
        return (seeing_score + transparency_score) / 2.0

    def _calculate_general_weather_score(self, cloud_cover: float, humidity: float, wind_speed: float) -> float:
        """Calculate score based on general weather metrics.

        Args:
            cloud_cover: Cloud cover percentage (0-100)
            humidity: Humidity percentage (0-100)
            wind_speed: Wind speed in m/s

        Returns:
            General weather quality score (0-1)
        """
        # Cloud cover score (inverse)
        cloud_score = 1.0 - (cloud_cover / 100.0)

        # Humidity score (inverse, with threshold)
        # Below 60% is good, above 80% is poor
        if humidity < 60:
            humidity_score = 1.0
        elif humidity > 80:
            humidity_score = 0.3
        else:
            humidity_score = 1.0 - ((humidity - 60) / 20.0) * 0.7

        # Wind speed score (< 5 m/s is good, > 10 m/s is poor)
        if wind_speed < 5:
            wind_score = 1.0
        elif wind_speed > 10:
            wind_score = 0.5
        else:
            wind_score = 1.0 - ((wind_speed - 5) / 5.0) * 0.5

        # Weighted combination (cloud cover is most important)
        return (cloud_score * 0.6) + (humidity_score * 0.25) + (wind_score * 0.15)
