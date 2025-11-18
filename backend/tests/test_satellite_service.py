"""Tests for ISS and satellite pass prediction service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.satellite_service import (
    SatelliteService,
    SatellitePass,
    PassVisibility,
)


class TestPassVisibility:
    """Test PassVisibility enum."""

    def test_visibility_levels(self):
        """Test visibility level values."""
        assert PassVisibility.EXCELLENT.value == 4
        assert PassVisibility.GOOD.value == 3
        assert PassVisibility.FAIR.value == 2
        assert PassVisibility.POOR.value == 1


class TestSatellitePass:
    """Test SatellitePass model."""

    def test_pass_creation(self):
        """Test creating a satellite pass."""
        start_time = datetime(2025, 11, 20, 19, 30)
        pass_obj = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=6),
            max_altitude_deg=45.0,
            max_altitude_time=start_time + timedelta(minutes=3),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            visibility=PassVisibility.EXCELLENT,
            magnitude=-3.5
        )
        assert pass_obj.satellite_name == "ISS (ZARYA)"
        assert pass_obj.max_altitude_deg == 45.0
        assert pass_obj.visibility == PassVisibility.EXCELLENT
        assert pass_obj.magnitude == -3.5

    def test_pass_duration(self):
        """Test calculating pass duration."""
        start_time = datetime(2025, 11, 20, 19, 30)
        pass_obj = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=6),
            max_altitude_deg=45.0,
            max_altitude_time=start_time + timedelta(minutes=3),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            visibility=PassVisibility.GOOD,
            magnitude=-2.0
        )
        duration = pass_obj.duration_minutes()
        assert duration == 6.0

    def test_pass_quality_excellent(self):
        """Test pass quality score for excellent pass."""
        start_time = datetime(2025, 11, 20, 19, 30)
        pass_obj = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=6),
            max_altitude_deg=75.0,  # High altitude
            max_altitude_time=start_time + timedelta(minutes=3),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            visibility=PassVisibility.EXCELLENT,
            magnitude=-4.0  # Very bright
        )
        quality = pass_obj.quality_score()
        assert quality >= 0.8  # Should be high quality

    def test_pass_quality_poor(self):
        """Test pass quality score for poor pass."""
        start_time = datetime(2025, 11, 20, 19, 30)
        pass_obj = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=2),
            max_altitude_deg=15.0,  # Low altitude
            max_altitude_time=start_time + timedelta(minutes=1),
            start_azimuth_deg=270.0,
            end_azimuth_deg=280.0,
            visibility=PassVisibility.POOR,
            magnitude=1.0  # Dim
        )
        quality = pass_obj.quality_score()
        assert quality <= 0.3  # Should be low quality


class TestSatelliteService:
    """Test SatelliteService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return SatelliteService()

    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert hasattr(service, 'get_iss_passes')
        assert hasattr(service, 'get_satellite_passes')

    @patch('requests.get')
    def test_get_iss_passes_success(self, mock_get, service):
        """Test successfully fetching ISS passes."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {"passescount": 2},
            "passes": [
                {
                    "startUTC": 1732134000,
                    "endUTC": 1732134360,
                    "mag": -3.5,
                    "startAz": 270,
                    "startAzCompass": "W",
                    "maxAz": 0,
                    "maxAzCompass": "N",
                    "endAz": 90,
                    "endAzCompass": "E",
                    "maxEl": 45
                },
                {
                    "startUTC": 1732140000,
                    "endUTC": 1732140300,
                    "mag": -2.0,
                    "startAz": 180,
                    "startAzCompass": "S",
                    "maxAz": 270,
                    "maxAzCompass": "W",
                    "endAz": 0,
                    "endAzCompass": "N",
                    "maxEl": 30
                }
            ]
        }
        mock_get.return_value = mock_response

        passes = service.get_iss_passes(
            latitude=40.7,
            longitude=-74.0,
            days=3
        )

        assert len(passes) == 2
        assert all(isinstance(p, SatellitePass) for p in passes)
        assert passes[0].satellite_name == "ISS (ZARYA)"
        assert passes[0].max_altitude_deg == 45

    @patch('requests.get')
    def test_get_iss_passes_api_error(self, mock_get, service):
        """Test handling API errors gracefully."""
        mock_get.side_effect = Exception("Network error")

        passes = service.get_iss_passes(
            latitude=40.7,
            longitude=-74.0,
            days=3
        )

        assert passes == []  # Returns empty list on error

    def test_filter_visible_passes(self, service):
        """Test filtering passes by minimum altitude."""
        start_time = datetime(2025, 11, 20, 19, 30)

        high_pass = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=6),
            max_altitude_deg=45.0,
            max_altitude_time=start_time + timedelta(minutes=3),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            visibility=PassVisibility.GOOD,
            magnitude=-3.0
        )

        low_pass = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time + timedelta(hours=6),
            end_time=start_time + timedelta(hours=6, minutes=3),
            max_altitude_deg=12.0,
            max_altitude_time=start_time + timedelta(hours=6, minutes=1.5),
            start_azimuth_deg=180.0,
            end_azimuth_deg=200.0,
            visibility=PassVisibility.POOR,
            magnitude=1.0
        )

        all_passes = [high_pass, low_pass]
        filtered = service.filter_visible_passes(all_passes, min_altitude=20.0)

        assert len(filtered) == 1
        assert filtered[0].max_altitude_deg == 45.0

    def test_classify_visibility_excellent(self, service):
        """Test classifying excellent visibility."""
        visibility = service._classify_visibility(
            magnitude=-4.0,
            max_altitude=70.0
        )
        assert visibility == PassVisibility.EXCELLENT

    def test_classify_visibility_poor(self, service):
        """Test classifying poor visibility."""
        visibility = service._classify_visibility(
            magnitude=2.0,
            max_altitude=15.0
        )
        assert visibility == PassVisibility.POOR

    def test_get_best_passes(self, service):
        """Test getting best passes sorted by quality."""
        start_time = datetime(2025, 11, 20, 19, 30)

        excellent_pass = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=6),
            max_altitude_deg=75.0,
            max_altitude_time=start_time + timedelta(minutes=3),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            visibility=PassVisibility.EXCELLENT,
            magnitude=-4.0
        )

        fair_pass = SatellitePass(
            satellite_name="ISS (ZARYA)",
            start_time=start_time + timedelta(hours=12),
            end_time=start_time + timedelta(hours=12, minutes=4),
            max_altitude_deg=30.0,
            max_altitude_time=start_time + timedelta(hours=12, minutes=2),
            start_azimuth_deg=180.0,
            end_azimuth_deg=270.0,
            visibility=PassVisibility.FAIR,
            magnitude=-1.5
        )

        all_passes = [fair_pass, excellent_pass]  # Intentionally out of order
        best = service.get_best_passes(all_passes, count=2)

        assert len(best) == 2
        assert best[0].visibility == PassVisibility.EXCELLENT
        assert best[1].visibility == PassVisibility.FAIR

    def test_compass_to_degrees(self, service):
        """Test converting compass directions to degrees."""
        assert service._compass_to_degrees("N") == 0
        assert service._compass_to_degrees("E") == 90
        assert service._compass_to_degrees("S") == 180
        assert service._compass_to_degrees("W") == 270
        assert service._compass_to_degrees("NE") == 45
        assert service._compass_to_degrees("SW") == 225
