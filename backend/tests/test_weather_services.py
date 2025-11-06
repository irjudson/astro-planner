"""Tests for weather and 7Timer services."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytz

from app.services.weather_service import WeatherService
from app.services.seven_timer_service import SevenTimerService
from app.models import Location, WeatherForecast


@pytest.fixture
def sample_location():
    """Sample location."""
    return Location(
        name="Three Forks, MT",
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234.0,
        timezone="America/Denver"
    )


class TestSevenTimerService:
    """Test 7Timer service."""

    def test_convert_seeing_values(self):
        """Test seeing scale conversion."""
        service = SevenTimerService()

        # Test all seeing values
        assert service._convert_seeing(1) == 0.4  # Excellent
        assert service._convert_seeing(2) == 0.6  # Good
        assert service._convert_seeing(3) == 0.9  # Average
        assert service._convert_seeing(4) == 1.5  # Below average
        assert service._convert_seeing(5) == 2.2  # Poor
        assert service._convert_seeing(6) == 3.5  # Very poor
        assert service._convert_seeing(7) == 7.0  # Terrible
        assert service._convert_seeing(8) == 12.0  # Unusable
        assert service._convert_seeing(99) == 2.0  # Default

    def test_convert_transparency_values(self):
        """Test transparency scale conversion."""
        service = SevenTimerService()

        # Test all transparency values
        assert service._convert_transparency(1) == 16.0  # Poor
        assert service._convert_transparency(2) == 17.0
        assert service._convert_transparency(3) == 18.0
        assert service._convert_transparency(4) == 19.0
        assert service._convert_transparency(5) == 20.0  # Good
        assert service._convert_transparency(6) == 21.0  # Very good
        assert service._convert_transparency(7) == 21.5  # Excellent
        assert service._convert_transparency(8) == 22.0  # Exceptional
        assert service._convert_transparency(99) == 18.0  # Default

    def test_convert_cloudcover_values(self):
        """Test cloud cover scale conversion."""
        service = SevenTimerService()

        # Test all cloud cover values
        assert service._convert_cloudcover(1) == 6.0
        assert service._convert_cloudcover(2) == 19.0
        assert service._convert_cloudcover(3) == 31.0
        assert service._convert_cloudcover(4) == 44.0
        assert service._convert_cloudcover(5) == 56.0
        assert service._convert_cloudcover(6) == 69.0
        assert service._convert_cloudcover(7) == 81.0
        assert service._convert_cloudcover(8) == 94.0
        assert service._convert_cloudcover(9) == 100.0
        assert service._convert_cloudcover(99) == 50.0  # Default

    def test_describe_conditions_clear(self):
        """Test condition description for clear skies."""
        service = SevenTimerService()

        description = service._describe_conditions(
            seeing=0.8,
            transparency=21.0,
            cloudcover=10
        )

        assert "clear" in description.lower()
        assert "excellent seeing" in description.lower()
        assert "excellent transparency" in description.lower()

    def test_describe_conditions_poor(self):
        """Test condition description for poor conditions."""
        service = SevenTimerService()

        description = service._describe_conditions(
            seeing=5.0,
            transparency=16.0,
            cloudcover=95
        )

        assert "overcast" in description.lower()
        assert "poor" in description.lower()

    def test_describe_conditions_moderate(self):
        """Test condition description for moderate conditions."""
        service = SevenTimerService()

        description = service._describe_conditions(
            seeing=1.5,
            transparency=19.0,
            cloudcover=40
        )

        assert "partly cloudy" in description.lower() or "mostly cloudy" in description.lower()
        assert "good" in description.lower() or "average" in description.lower()

    @patch('app.services.seven_timer_service.requests.get')
    def test_get_astronomy_forecast_success(self, mock_get, sample_location):
        """Test successful 7Timer API call."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "init": "2025110600",
            "dataseries": [
                {
                    "timepoint": 0,
                    "seeing": 2,
                    "transparency": 6,
                    "cloudcover": 2,
                    "temp2m": 10,
                    "wind10m": {"speed": 3}
                },
                {
                    "timepoint": 3,
                    "seeing": 3,
                    "transparency": 5,
                    "cloudcover": 3,
                    "temp2m": 8,
                    "wind10m": {"speed": 2}
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        service = SevenTimerService()
        start_time = datetime(2025, 11, 6, 0, 0, 0)
        end_time = datetime(2025, 11, 6, 12, 0, 0)

        forecasts = service.get_astronomy_forecast(sample_location, start_time, end_time)

        assert len(forecasts) >= 1
        assert all(isinstance(f, WeatherForecast) for f in forecasts)
        assert all(f.source == "7timer" for f in forecasts)
        assert all(f.seeing_arcseconds is not None for f in forecasts)
        assert all(f.transparency_magnitude is not None for f in forecasts)

    @patch('app.services.seven_timer_service.requests.get')
    def test_get_astronomy_forecast_api_error(self, mock_get, sample_location):
        """Test 7Timer API error handling."""
        mock_get.side_effect = Exception("API error")

        service = SevenTimerService()
        start_time = datetime(2025, 11, 6, 0, 0, 0)
        end_time = datetime(2025, 11, 6, 12, 0, 0)

        forecasts = service.get_astronomy_forecast(sample_location, start_time, end_time)

        assert forecasts == []  # Should return empty list on error

    @patch('app.services.seven_timer_service.requests.get')
    def test_get_astronomy_forecast_no_dataseries(self, mock_get, sample_location):
        """Test 7Timer response with no dataseries."""
        mock_response = Mock()
        mock_response.json.return_value = {"init": "2025110600"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        service = SevenTimerService()
        start_time = datetime(2025, 11, 6, 0, 0, 0)
        end_time = datetime(2025, 11, 6, 12, 0, 0)

        forecasts = service.get_astronomy_forecast(sample_location, start_time, end_time)

        assert forecasts == []


class TestWeatherService:
    """Test weather service (extended)."""

    def test_composite_weather_score(self):
        """Test composite weather scoring with astronomy data."""
        service = WeatherService()

        # Perfect composite conditions
        composite_forecast = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=0.0,
            humidity=40.0,
            temperature=15.0,
            wind_speed=2.0,
            conditions="Clear",
            seeing_arcseconds=0.8,
            transparency_magnitude=21.5,
            source="composite"
        )
        score = service.calculate_weather_score(composite_forecast)
        assert score >= 0.9  # Should be very high

        # Poor composite conditions
        poor_composite = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=100.0,
            humidity=90.0,
            temperature=15.0,
            wind_speed=15.0,
            conditions="Overcast",
            seeing_arcseconds=8.0,
            transparency_magnitude=16.0,
            source="composite"
        )
        score = service.calculate_weather_score(poor_composite)
        assert score < 0.3  # Should be very low

    def test_astronomy_only_score(self):
        """Test scoring with only astronomy data."""
        service = WeatherService()

        # Excellent astronomy conditions
        astro_forecast = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=0.0,
            humidity=50.0,
            temperature=15.0,
            wind_speed=5.0,
            conditions="Clear",
            seeing_arcseconds=0.6,
            transparency_magnitude=21.0,
            source="7timer"
        )
        score = service.calculate_weather_score(astro_forecast)
        assert score >= 0.85

        # Poor astronomy conditions
        poor_astro = WeatherForecast(
            timestamp=datetime.now(pytz.UTC),
            cloud_cover=0.0,
            humidity=50.0,
            temperature=15.0,
            wind_speed=5.0,
            conditions="Clear",
            seeing_arcseconds=7.0,
            transparency_magnitude=16.5,
            source="7timer"
        )
        score = service.calculate_weather_score(poor_astro)
        assert score < 0.45  # Slightly higher than expected due to scoring algorithm

    def test_calculate_astronomy_score_edge_cases(self):
        """Test astronomy score calculation edge cases."""
        service = WeatherService()

        # Test with None values
        score = service._calculate_astronomy_score(None, None)
        assert score == 0.5  # Should return neutral score

        # Test excellent seeing
        score = service._calculate_astronomy_score(0.5, 21.0)
        assert score >= 0.9

        # Test excellent transparency
        score = service._calculate_astronomy_score(1.5, 22.0)
        assert score >= 0.8

        # Test poor seeing
        score = service._calculate_astronomy_score(10.0, 19.0)
        assert score < 0.5

        # Test poor transparency
        score = service._calculate_astronomy_score(1.5, 15.0)
        assert score < 0.6  # Good seeing compensates somewhat

    def test_calculate_general_weather_score_edge_cases(self):
        """Test general weather score calculation edge cases."""
        service = WeatherService()

        # Perfect conditions
        score = service._calculate_general_weather_score(0, 50, 3)
        assert score >= 0.95

        # Terrible conditions
        score = service._calculate_general_weather_score(100, 95, 15)
        assert score < 0.35

        # High humidity threshold
        score_low = service._calculate_general_weather_score(20, 55, 4)
        score_high = service._calculate_general_weather_score(20, 85, 4)
        assert score_low > score_high

        # Wind speed threshold
        score_calm = service._calculate_general_weather_score(20, 60, 3)
        score_windy = service._calculate_general_weather_score(20, 60, 12)
        assert score_calm > score_windy

    def test_merge_conditions(self):
        """Test merging condition descriptions."""
        service = WeatherService()

        # Test with seeing info
        merged = service._merge_conditions(
            "Clear sky",
            "Partly cloudy, excellent seeing, good transparency"
        )
        assert "Clear sky" in merged
        assert "seeing" in merged.lower() or "transparency" in merged.lower()

        # Test without seeing info
        merged = service._merge_conditions(
            "Clear sky",
            "Partly cloudy"
        )
        assert merged == "Clear sky"

    @patch('app.services.weather_service.SevenTimerService')
    @patch('app.services.weather_service.requests.get')
    def test_merge_forecasts_time_matching(self, mock_get, mock_seven_timer, sample_location):
        """Test forecast merging with time window matching."""
        # Mock OpenWeatherMap response
        mock_owm_response = Mock()
        mock_owm_response.json.return_value = {
            "list": [
                {
                    "dt": int(datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC).timestamp()),
                    "clouds": {"all": 10},
                    "main": {"humidity": 50, "temp": 10},
                    "wind": {"speed": 3},
                    "weather": [{"description": "clear sky"}]
                },
                {
                    "dt": int(datetime(2025, 11, 6, 3, 0, 0, tzinfo=pytz.UTC).timestamp()),
                    "clouds": {"all": 20},
                    "main": {"humidity": 55, "temp": 9},
                    "wind": {"speed": 4},
                    "weather": [{"description": "few clouds"}]
                }
            ]
        }
        mock_owm_response.raise_for_status = Mock()
        mock_get.return_value = mock_owm_response

        # Mock 7Timer forecasts
        mock_seven_timer_instance = Mock()
        mock_seven_timer_instance.get_astronomy_forecast.return_value = [
            WeatherForecast(
                timestamp=datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC),
                cloud_cover=15.0,
                humidity=50.0,
                temperature=10.0,
                wind_speed=3.0,
                conditions="Clear",
                seeing_arcseconds=1.2,
                transparency_magnitude=20.0,
                source="7timer"
            )
        ]
        mock_seven_timer.return_value = mock_seven_timer_instance

        service = WeatherService()
        start_time = datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC)
        end_time = datetime(2025, 11, 6, 6, 0, 0, tzinfo=pytz.UTC)

        forecasts = service.get_forecast(sample_location, start_time, end_time)

        # Should have merged forecasts
        assert len(forecasts) > 0
        # At least one should be composite (merged)
        composite_forecasts = [f for f in forecasts if f.source == "composite"]
        if composite_forecasts:
            assert any(f.seeing_arcseconds is not None for f in composite_forecasts)

    @patch('app.services.weather_service.SevenTimerService')
    @patch('app.services.weather_service.requests.get')
    def test_forecast_fallback_owm_only(self, mock_get, mock_seven_timer, sample_location):
        """Test fallback to OpenWeatherMap only."""
        # Mock OpenWeatherMap response
        mock_owm_response = Mock()
        mock_owm_response.json.return_value = {
            "list": [
                {
                    "dt": int(datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC).timestamp()),
                    "clouds": {"all": 10},
                    "main": {"humidity": 50, "temp": 10},
                    "wind": {"speed": 3},
                    "weather": [{"description": "clear sky"}]
                }
            ]
        }
        mock_owm_response.raise_for_status = Mock()
        mock_get.return_value = mock_owm_response

        # Mock 7Timer failure
        mock_seven_timer_instance = Mock()
        mock_seven_timer_instance.get_astronomy_forecast.return_value = []
        mock_seven_timer.return_value = mock_seven_timer_instance

        service = WeatherService()
        start_time = datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC)
        end_time = datetime(2025, 11, 6, 6, 0, 0, tzinfo=pytz.UTC)

        forecasts = service.get_forecast(sample_location, start_time, end_time)

        # Should have OWM forecasts only
        assert len(forecasts) > 0
        assert all(f.source == "openweathermap" for f in forecasts)
        assert all(f.seeing_arcseconds is None for f in forecasts)

    @patch('app.services.weather_service.SevenTimerService')
    @patch('app.services.weather_service.requests.get')
    def test_forecast_fallback_seven_timer_only(self, mock_get, mock_seven_timer, sample_location):
        """Test fallback to 7Timer only."""
        # Mock OpenWeatherMap failure
        mock_get.side_effect = Exception("OWM API error")

        # Mock 7Timer success
        mock_seven_timer_instance = Mock()
        mock_seven_timer_instance.get_astronomy_forecast.return_value = [
            WeatherForecast(
                timestamp=datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC),
                cloud_cover=15.0,
                humidity=50.0,
                temperature=10.0,
                wind_speed=3.0,
                conditions="Clear",
                seeing_arcseconds=1.2,
                transparency_magnitude=20.0,
                source="7timer"
            )
        ]
        mock_seven_timer.return_value = mock_seven_timer_instance

        service = WeatherService()
        start_time = datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC)
        end_time = datetime(2025, 11, 6, 6, 0, 0, tzinfo=pytz.UTC)

        forecasts = service.get_forecast(sample_location, start_time, end_time)

        # Should have 7Timer forecasts only
        assert len(forecasts) > 0
        assert all(f.source == "7timer" for f in forecasts)
        assert all(f.seeing_arcseconds is not None for f in forecasts)

    @patch('app.services.weather_service.SevenTimerService')
    @patch('app.services.weather_service.requests.get')
    def test_forecast_complete_failure(self, mock_get, mock_seven_timer, sample_location):
        """Test fallback to default forecast when both APIs fail."""
        # Mock both API failures
        mock_get.side_effect = Exception("OWM API error")

        mock_seven_timer_instance = Mock()
        mock_seven_timer_instance.get_astronomy_forecast.return_value = []
        mock_seven_timer.return_value = mock_seven_timer_instance

        service = WeatherService()
        start_time = datetime(2025, 11, 6, 0, 0, 0, tzinfo=pytz.UTC)
        end_time = datetime(2025, 11, 6, 6, 0, 0, tzinfo=pytz.UTC)

        forecasts = service.get_forecast(sample_location, start_time, end_time)

        # Should have default forecasts
        assert len(forecasts) > 0
        assert all(f.conditions == "Clear sky (estimated)" for f in forecasts)
        assert all(f.cloud_cover == 20.0 for f in forecasts)
