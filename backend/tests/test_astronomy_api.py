"""Tests for astronomy-specific API endpoints."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.cleardarksky_service import ClearDarkSkyForecast, CloudCover, Seeing, Transparency
from app.services.satellite_service import PassVisibility, SatellitePass
from app.services.viewing_months_service import MonthRating, ViewingMonth

client = TestClient(app)


class TestClearDarkSkyEndpoint:
    """Test ClearDarkSky weather endpoint."""

    @patch("app.services.cleardarksky_service.ClearDarkSkyService.get_forecast")
    def test_get_astronomy_weather(self, mock_get_forecast):
        """Test getting astronomy weather forecast."""
        # Mock forecast data
        mock_forecast = [
            ClearDarkSkyForecast(
                time=datetime(2025, 11, 20, 20, 0),
                cloud_cover=CloudCover.MOSTLY_CLEAR,
                transparency=Transparency.ABOVE_AVERAGE,
                seeing=Seeing.GOOD,
                temperature_c=15.0,
                wind_speed_kmh=10.0,
            )
        ]
        mock_get_forecast.return_value = mock_forecast

        response = client.get("/api/weather/astronomy?lat=40.7&lon=-74.0&hours=48")

        assert response.status_code == 200
        data = response.json()
        assert "forecast" in data
        assert len(data["forecast"]) > 0
        assert "cloud_cover" in data["forecast"][0]
        assert "transparency" in data["forecast"][0]
        assert "seeing" in data["forecast"][0]

    def test_get_astronomy_weather_invalid_coords(self):
        """Test astronomy weather with invalid coordinates."""
        response = client.get("/api/weather/astronomy?lat=999&lon=999")

        # FastAPI validates query params, so this returns 422
        assert response.status_code == 422

    def test_get_astronomy_weather_missing_params(self):
        """Test astronomy weather with missing parameters."""
        response = client.get("/api/weather/astronomy")

        assert response.status_code == 422  # Unprocessable entity


class TestSatellitePassesEndpoint:
    """Test ISS and satellite pass endpoints."""

    @patch("app.services.satellite_service.SatelliteService.get_iss_passes")
    def test_get_iss_passes(self, mock_get_passes):
        """Test getting ISS pass predictions."""
        start_time = datetime(2025, 11, 20, 19, 30)
        mock_passes = [
            SatellitePass(
                satellite_name="ISS (ZARYA)",
                start_time=start_time,
                end_time=start_time,
                max_altitude_deg=45.0,
                max_altitude_time=start_time,
                start_azimuth_deg=270.0,
                end_azimuth_deg=90.0,
                visibility=PassVisibility.EXCELLENT,
                magnitude=-3.5,
            )
        ]
        mock_get_passes.return_value = mock_passes

        response = client.get("/api/satellites/iss?lat=40.7&lon=-74.0&days=10")

        assert response.status_code == 200
        data = response.json()
        assert "passes" in data
        assert len(data["passes"]) > 0
        assert data["passes"][0]["satellite_name"] == "ISS (ZARYA)"
        assert data["passes"][0]["max_altitude_deg"] == 45.0

    @patch("app.services.satellite_service.SatelliteService.get_satellite_passes")
    def test_get_satellite_passes_by_norad_id(self, mock_get_passes):
        """Test getting satellite passes by NORAD ID."""
        start_time = datetime(2025, 11, 20, 19, 30)
        mock_passes = [
            SatellitePass(
                satellite_name="Hubble Space Telescope",
                start_time=start_time,
                end_time=start_time,
                max_altitude_deg=30.0,
                max_altitude_time=start_time,
                start_azimuth_deg=180.0,
                end_azimuth_deg=270.0,
                visibility=PassVisibility.GOOD,
                magnitude=-2.0,
            )
        ]
        mock_get_passes.return_value = mock_passes

        response = client.get("/api/satellites/passes?norad_id=20580&lat=40.7&lon=-74.0&days=5")

        assert response.status_code == 200
        data = response.json()
        assert "passes" in data
        assert len(data["passes"]) > 0

    def test_get_iss_passes_invalid_coords(self):
        """Test ISS passes with invalid coordinates."""
        response = client.get("/api/satellites/iss?lat=999&lon=999")

        # FastAPI validates query params, so this returns 422
        assert response.status_code == 422

    def test_filter_passes_by_quality(self):
        """Test filtering satellite passes by quality."""
        # This would test a filter endpoint if we add one
        pass


class TestViewingMonthsEndpoint:
    """Test best viewing months endpoint."""

    @patch("app.services.viewing_months_service.ViewingMonthsService.calculate_viewing_months")
    def test_get_viewing_months_for_object(self, mock_calculate):
        """Test getting best viewing months for an object."""
        mock_months = [
            ViewingMonth(
                month=i,
                month_name=["Jan", "Feb", "Mar"][i - 1],
                rating=MonthRating.EXCELLENT if i == 2 else MonthRating.FAIR,
                visibility_hours=8.0 if i == 2 else 4.0,
                best_time="22:00",
                notes="Good conditions",
            )
            for i in range(1, 4)
        ]
        mock_calculate.return_value = mock_months

        response = client.get("/api/viewing-months?ra_hours=0.712&dec_degrees=41.27&latitude=40.0")

        assert response.status_code == 200
        data = response.json()
        assert "months" in data
        assert len(data["months"]) > 0
        assert "month_name" in data["months"][0]
        assert "rating" in data["months"][0]

    @patch("app.services.viewing_months_service.ViewingMonthsService.calculate_viewing_months")
    def test_get_viewing_months_with_object_name(self, mock_calculate):
        """Test viewing months with object name."""
        mock_months = [
            ViewingMonth(
                month=1,
                month_name="January",
                rating=MonthRating.GOOD,
                visibility_hours=6.0,
                best_time="21:00",
                notes="Winter viewing",
            )
        ]
        mock_calculate.return_value = mock_months

        response = client.get("/api/viewing-months?ra_hours=5.919&dec_degrees=-5.39&latitude=40.0&object_name=M42")

        assert response.status_code == 200
        data = response.json()
        assert "months" in data
        assert "object_name" in data
        assert data["object_name"] == "M42"

    def test_viewing_months_missing_params(self):
        """Test viewing months with missing required parameters."""
        response = client.get("/api/viewing-months?ra_hours=0.712")

        assert response.status_code == 422  # Unprocessable entity

    def test_viewing_months_invalid_coords(self):
        """Test viewing months with invalid astronomical coordinates."""
        response = client.get("/api/viewing-months?ra_hours=25&dec_degrees=41.27&latitude=40.0")

        # FastAPI validates query params, so this returns 422
        assert response.status_code == 422


class TestViewingMonthsSummary:
    """Test viewing months summary endpoint."""

    @patch("app.services.viewing_months_service.ViewingMonthsService.calculate_viewing_months")
    @patch("app.services.viewing_months_service.ViewingMonthsService.get_viewing_summary")
    def test_get_viewing_summary(self, mock_summary, mock_calculate):
        """Test getting viewing months summary."""
        mock_months = [
            ViewingMonth(
                month=i, month_name=f"Month{i}", rating=MonthRating.EXCELLENT, visibility_hours=8.0, best_time="22:00"
            )
            for i in range(1, 13)
        ]
        mock_calculate.return_value = mock_months

        mock_summary.return_value = {
            "best_months": ["February", "March", "April"],
            "good_months_count": 6,
            "visibility_range": [["January", "February", "March"]],
            "peak_month": "February",
        }

        response = client.get("/api/viewing-months/summary?ra_hours=0.712&dec_degrees=41.27&latitude=40.0")

        assert response.status_code == 200
        data = response.json()
        assert "best_months" in data
        assert "peak_month" in data
        assert "good_months_count" in data
