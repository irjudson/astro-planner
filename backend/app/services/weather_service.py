"""Weather forecasting service using OpenWeatherMap API."""

from datetime import datetime, timedelta
from typing import List, Optional
import requests
import pytz

from app.models import Location, WeatherForecast
from app.core import get_settings


class WeatherService:
    """Service for fetching weather forecasts."""

    def __init__(self):
        """Initialize with API key from settings."""
        self.settings = get_settings()
        self.api_key = self.settings.openweathermap_api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/forecast"

    def get_forecast(
        self, location: Location, start_time: datetime, end_time: datetime
    ) -> List[WeatherForecast]:
        """
        Get weather forecast for a location and time range.

        Args:
            location: Observer location
            start_time: Start of forecast period
            end_time: End of forecast period

        Returns:
            List of weather forecasts
        """
        if not self.api_key:
            # Return default "unknown" forecast if no API key
            return self._generate_default_forecast(start_time, end_time)

        try:
            # Call OpenWeatherMap API
            params = {
                'lat': location.latitude,
                'lon': location.longitude,
                'appid': self.api_key,
                'units': 'metric'
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse forecast data
            forecasts = []
            tz = pytz.timezone(location.timezone)

            for item in data.get('list', []):
                # Convert timestamp
                timestamp = datetime.fromtimestamp(item['dt'], tz=pytz.UTC).astimezone(tz)

                # Only include forecasts within our time range
                if start_time <= timestamp <= end_time:
                    forecast = WeatherForecast(
                        timestamp=timestamp,
                        cloud_cover=item.get('clouds', {}).get('all', 0),
                        humidity=item.get('main', {}).get('humidity', 0),
                        temperature=item.get('main', {}).get('temp', 0),
                        wind_speed=item.get('wind', {}).get('speed', 0),
                        conditions=item.get('weather', [{}])[0].get('description', 'Unknown')
                    )
                    forecasts.append(forecast)

            return forecasts if forecasts else self._generate_default_forecast(start_time, end_time)

        except Exception as e:
            # Log error and return default forecast
            print(f"Weather API error: {e}")
            return self._generate_default_forecast(start_time, end_time)

    def _generate_default_forecast(
        self, start_time: datetime, end_time: datetime
    ) -> List[WeatherForecast]:
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
                conditions="Clear sky (estimated)"
            )
            forecasts.append(forecast)
            current_time = current_time + timedelta(hours=1)

        return forecasts

    def calculate_weather_score(self, forecast: WeatherForecast) -> float:
        """
        Calculate a weather quality score (0-1).

        Factors:
        - Cloud cover (most important)
        - Humidity (affects transparency)
        - Wind speed (affects tracking)

        Args:
            forecast: Weather forecast data

        Returns:
            Score from 0 (bad) to 1 (excellent)
        """
        # Cloud cover score (inverse)
        cloud_score = 1.0 - (forecast.cloud_cover / 100.0)

        # Humidity score (inverse, with threshold)
        # Below 60% is good, above 80% is poor
        if forecast.humidity < 60:
            humidity_score = 1.0
        elif forecast.humidity > 80:
            humidity_score = 0.3
        else:
            humidity_score = 1.0 - ((forecast.humidity - 60) / 20.0) * 0.7

        # Wind speed score (< 5 m/s is good, > 10 m/s is poor)
        if forecast.wind_speed < 5:
            wind_score = 1.0
        elif forecast.wind_speed > 10:
            wind_score = 0.5
        else:
            wind_score = 1.0 - ((forecast.wind_speed - 5) / 5.0) * 0.5

        # Weighted combination (cloud cover is most important)
        total_score = (cloud_score * 0.6) + (humidity_score * 0.25) + (wind_score * 0.15)

        return max(0.0, min(1.0, total_score))
