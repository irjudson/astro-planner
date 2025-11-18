"""Tests for ClearDarkSky weather service integration."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from app.services.cleardarksky_service import (
    ClearDarkSkyService,
    ClearDarkSkyForecast,
    CloudCover,
    Transparency,
    Seeing,
)


class TestClearDarkSkyEnums:
    """Test ClearDarkSky condition enums."""

    def test_cloud_cover_values(self):
        """Test cloud cover percentage ranges."""
        assert CloudCover.CLEAR.value == (0, 10)
        assert CloudCover.MOSTLY_CLEAR.value == (10, 30)
        assert CloudCover.PARTLY_CLOUDY.value == (30, 70)
        assert CloudCover.MOSTLY_CLOUDY.value == (70, 90)
        assert CloudCover.OVERCAST.value == (90, 100)

    def test_transparency_levels(self):
        """Test atmospheric transparency levels."""
        assert Transparency.EXCELLENT.value == 5
        assert Transparency.ABOVE_AVERAGE.value == 4
        assert Transparency.AVERAGE.value == 3
        assert Transparency.BELOW_AVERAGE.value == 2
        assert Transparency.POOR.value == 1

    def test_seeing_levels(self):
        """Test astronomical seeing levels."""
        assert Seeing.EXCELLENT.value == 5
        assert Seeing.GOOD.value == 4
        assert Seeing.AVERAGE.value == 3
        assert Seeing.BELOW_AVERAGE.value == 2
        assert Seeing.POOR.value == 1


class TestClearDarkSkyForecast:
    """Test ClearDarkSkyForecast model."""

    def test_forecast_creation(self):
        """Test creating a forecast entry."""
        forecast = ClearDarkSkyForecast(
            time=datetime(2025, 11, 20, 21, 0),
            cloud_cover=CloudCover.CLEAR,
            transparency=Transparency.EXCELLENT,
            seeing=Seeing.GOOD,
            temperature_c=10.0,
            wind_speed_kmh=15.0
        )
        assert forecast.cloud_cover == CloudCover.CLEAR
        assert forecast.transparency == Transparency.EXCELLENT
        assert forecast.seeing == Seeing.GOOD
        assert forecast.temperature_c == 10.0

    def test_forecast_astronomy_score(self):
        """Test calculating astronomy quality score."""
        # Excellent conditions
        forecast = ClearDarkSkyForecast(
            time=datetime(2025, 11, 20, 21, 0),
            cloud_cover=CloudCover.CLEAR,
            transparency=Transparency.EXCELLENT,
            seeing=Seeing.EXCELLENT,
            temperature_c=10.0,
            wind_speed_kmh=10.0
        )
        score = forecast.astronomy_score()
        assert score >= 0.9  # Near perfect

        # Poor conditions
        forecast_poor = ClearDarkSkyForecast(
            time=datetime(2025, 11, 20, 21, 0),
            cloud_cover=CloudCover.OVERCAST,
            transparency=Transparency.POOR,
            seeing=Seeing.POOR,
            temperature_c=10.0,
            wind_speed_kmh=40.0
        )
        score_poor = forecast_poor.astronomy_score()
        assert score_poor <= 0.3  # Very poor


class TestClearDarkSkyService:
    """Test ClearDarkSkyService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ClearDarkSkyService()

    def test_find_nearest_chart(self, service):
        """Test finding nearest ClearDarkSky chart."""
        # Test known location
        chart_id = service.find_nearest_chart(latitude=40.7, longitude=-74.0)
        assert chart_id is not None
        assert isinstance(chart_id, str)

    def test_find_nearest_chart_cache(self, service):
        """Test chart lookup caching."""
        chart_id_1 = service.find_nearest_chart(latitude=40.7, longitude=-74.0)
        chart_id_2 = service.find_nearest_chart(latitude=40.7, longitude=-74.0)
        assert chart_id_1 == chart_id_2  # Should be cached

    @patch('requests.get')
    def test_fetch_forecast_success(self, mock_get, service):
        """Test successful forecast fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<mock chart data>"
        mock_get.return_value = mock_response

        forecasts = service.fetch_forecast(chart_id="test_chart")
        assert isinstance(forecasts, list)

    @patch('requests.get')
    def test_fetch_forecast_api_error(self, mock_get, service):
        """Test handling API errors."""
        mock_get.side_effect = Exception("Network error")
        
        forecasts = service.fetch_forecast(chart_id="test_chart")
        assert forecasts == []  # Returns empty list on error

    def test_parse_chart_data(self, service):
        """Test parsing chart image data."""
        # This would need actual ClearDarkSky chart data
        # For now, test that method exists and handles errors
        result = service._parse_chart_data(b"invalid data")
        assert isinstance(result, list)

    def test_get_forecast_for_location(self, service):
        """Test getting forecast for coordinates."""
        forecasts = service.get_forecast(latitude=40.7, longitude=-74.0)
        assert isinstance(forecasts, list)
        # May be empty if no chart or parse fails, but should not error
