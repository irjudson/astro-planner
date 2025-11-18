"""Tests for light pollution and Bortle scale calculation service."""

import pytest
from unittest.mock import Mock, patch
from app.services.light_pollution_service import (
    LightPollutionService,
    BortleScale,
    LightPollutionData,
)


class TestBortleScale:
    """Test Bortle scale classification."""

    def test_bortle_scale_from_sqm_class_1(self):
        """Test classification of excellent dark sky (Bortle 1)."""
        assert BortleScale.from_sqm(21.9) == 1
        assert BortleScale.from_sqm(22.0) == 1

    def test_bortle_scale_from_sqm_class_2(self):
        """Test classification of typical dark sky (Bortle 2)."""
        assert BortleScale.from_sqm(21.7) == 2
        assert BortleScale.from_sqm(21.8) == 2

    def test_bortle_scale_from_sqm_class_3(self):
        """Test classification of rural sky (Bortle 3)."""
        assert BortleScale.from_sqm(21.3) == 3
        assert BortleScale.from_sqm(21.5) == 3

    def test_bortle_scale_from_sqm_class_4(self):
        """Test classification of rural/suburban transition (Bortle 4)."""
        assert BortleScale.from_sqm(20.5) == 4
        assert BortleScale.from_sqm(21.0) == 4

    def test_bortle_scale_from_sqm_class_5(self):
        """Test classification of suburban sky (Bortle 5)."""
        assert BortleScale.from_sqm(19.5) == 5
        assert BortleScale.from_sqm(20.0) == 5

    def test_bortle_scale_from_sqm_class_6(self):
        """Test classification of bright suburban (Bortle 6)."""
        assert BortleScale.from_sqm(18.5) == 6
        assert BortleScale.from_sqm(19.0) == 6

    def test_bortle_scale_from_sqm_class_7(self):
        """Test classification of suburban/urban transition (Bortle 7)."""
        assert BortleScale.from_sqm(18.0) == 7
        assert BortleScale.from_sqm(18.3) == 7

    def test_bortle_scale_from_sqm_class_8(self):
        """Test classification of city sky (Bortle 8)."""
        assert BortleScale.from_sqm(17.0) == 8
        assert BortleScale.from_sqm(17.5) == 8

    def test_bortle_scale_from_sqm_class_9(self):
        """Test classification of inner city (Bortle 9)."""
        assert BortleScale.from_sqm(16.0) == 9
        assert BortleScale.from_sqm(13.0) == 9

    def test_bortle_scale_description(self):
        """Test getting description for Bortle class."""
        assert "Excellent dark-sky site" in BortleScale.get_description(1)
        assert "Typical truly dark site" in BortleScale.get_description(2)
        assert "Rural sky" in BortleScale.get_description(3)
        assert "Rural/suburban transition" in BortleScale.get_description(4)
        assert "Suburban sky" in BortleScale.get_description(5)
        assert "Bright suburban sky" in BortleScale.get_description(6)
        assert "Suburban/urban transition" in BortleScale.get_description(7)
        assert "City sky" in BortleScale.get_description(8)
        assert "Inner-city sky" in BortleScale.get_description(9)

    def test_bortle_scale_sqm_range(self):
        """Test getting SQM range for Bortle class."""
        sqm_min, sqm_max = BortleScale.get_sqm_range(1)
        assert sqm_min == 21.9
        assert sqm_max == 22.0

        sqm_min, sqm_max = BortleScale.get_sqm_range(5)
        assert sqm_min == 19.5
        assert sqm_max == 20.4


class TestLightPollutionData:
    """Test LightPollutionData model."""

    def test_light_pollution_data_creation(self):
        """Test creating light pollution data."""
        data = LightPollutionData(
            latitude=40.0,
            longitude=-74.0,
            sqm=21.5,
            bortle_class=3,
            description="Rural sky",
            source="estimated"
        )
        assert data.latitude == 40.0
        assert data.longitude == -74.0
        assert data.sqm == 21.5
        assert data.bortle_class == 3
        assert data.description == "Rural sky"
        assert data.source == "estimated"

    def test_light_pollution_data_validation(self):
        """Test data validation."""
        with pytest.raises(ValueError):
            LightPollutionData(
                latitude=91.0,  # Invalid latitude
                longitude=-74.0,
                sqm=21.5,
                bortle_class=3,
                description="Test",
                source="test"
            )

        with pytest.raises(ValueError):
            LightPollutionData(
                latitude=40.0,
                longitude=181.0,  # Invalid longitude
                sqm=21.5,
                bortle_class=3,
                description="Test",
                source="test"
            )


class TestLightPollutionService:
    """Test LightPollutionService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return LightPollutionService()

    def test_get_light_pollution_estimated(self, service):
        """Test fallback estimation when API unavailable."""
        # Test remote location (low population)
        data = service.get_light_pollution(45.0, -110.0)  # Montana
        assert data is not None
        assert data.latitude == 45.0
        assert data.longitude == -110.0
        assert data.bortle_class <= 4  # Should estimate dark sky
        assert data.source == "estimated"

    def test_get_light_pollution_city_estimated(self, service):
        """Test estimation for known urban area."""
        # New York City
        data = service.get_light_pollution(40.7128, -74.0060)
        assert data is not None
        assert data.bortle_class >= 7  # Urban area
        assert data.source == "estimated"

    @patch('requests.get')
    def test_get_light_pollution_from_api(self, mock_get, service):
        """Test getting data from API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sqm': 20.5,
            'bortle': 4
        }
        mock_get.return_value = mock_response

        data = service.get_light_pollution(40.0, -74.0)
        assert data.sqm == 20.5
        assert data.bortle_class == 4
        assert data.source == "lightpollutionmap.info"

    @patch('requests.get')
    def test_get_light_pollution_api_timeout(self, mock_get, service):
        """Test handling API timeout."""
        mock_get.side_effect = Exception("Timeout")

        data = service.get_light_pollution(40.0, -74.0)
        assert data is not None
        assert data.source == "estimated"

    def test_estimate_bortle_from_coordinates(self, service):
        """Test Bortle estimation algorithm."""
        # Remote location
        bortle = service._estimate_bortle_from_coordinates(45.0, -110.0)
        assert 1 <= bortle <= 4

        # Major city
        bortle = service._estimate_bortle_from_coordinates(40.7128, -74.0060)
        assert bortle >= 7

    def test_calculate_sqm_from_bortle(self, service):
        """Test SQM calculation from Bortle class."""
        sqm = service._calculate_sqm_from_bortle(1)
        assert 21.9 <= sqm <= 22.0

        sqm = service._calculate_sqm_from_bortle(5)
        assert 19.5 <= sqm <= 20.4

        sqm = service._calculate_sqm_from_bortle(9)
        assert 13.0 <= sqm <= 16.9
