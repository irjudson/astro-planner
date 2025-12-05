"""Tests for light pollution and Bortle scale calculation service."""

from unittest.mock import Mock, patch

import pytest

from app.models import Location
from app.services.light_pollution_service import BortleScale, LightPollutionData, LightPollutionService, SkyQuality


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
            latitude=40.0, longitude=-74.0, sqm=21.5, bortle_class=3, description="Rural sky", source="estimated"
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
                source="test",
            )

        with pytest.raises(ValueError):
            LightPollutionData(
                latitude=40.0,
                longitude=181.0,  # Invalid longitude
                sqm=21.5,
                bortle_class=3,
                description="Test",
                source="test",
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

    @patch("requests.get")
    def test_get_light_pollution_from_api(self, mock_get, service):
        """Test getting data from API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sqm": 20.5, "bortle": 4}
        mock_get.return_value = mock_response

        data = service.get_light_pollution(40.0, -74.0)
        assert data.sqm == 20.5
        assert data.bortle_class == 4
        assert data.source == "lightpollutionmap.info"

    @patch("requests.get")
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


class TestSkyQualityMethods:
    """Test get_sky_quality() and related methods."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return LightPollutionService()

    @pytest.fixture
    def test_location(self):
        """Create test location."""
        return Location(
            name="Test Location", latitude=45.0, longitude=-110.0, elevation=1500.0, timezone="America/Denver"
        )

    def test_get_sky_quality_dark_sky(self, service, test_location):
        """Test getting sky quality for dark sky location."""
        sky_quality = service.get_sky_quality(test_location)

        assert isinstance(sky_quality, SkyQuality)
        assert 1 <= sky_quality.bortle_class <= 9
        assert sky_quality.bortle_name is not None
        assert sky_quality.sqm_estimate > 0
        assert sky_quality.light_pollution_level in ["minimal", "moderate", "significant", "severe"]
        assert sky_quality.visibility_description is not None
        assert isinstance(sky_quality.suitable_for, list)
        assert len(sky_quality.suitable_for) > 0
        assert sky_quality.limiting_magnitude > 0
        assert sky_quality.milky_way_visibility in ["spectacular", "visible", "barely visible", "not visible"]
        assert sky_quality.light_pollution_source in ["estimated", "lightpollutionmap.info"]

    def test_get_sky_quality_urban(self, service):
        """Test getting sky quality for urban location."""
        # New York City
        location = Location(
            name="NYC", latitude=40.7128, longitude=-74.0060, elevation=10.0, timezone="America/New_York"
        )

        sky_quality = service.get_sky_quality(location)

        # Urban location should have high Bortle class
        assert sky_quality.bortle_class >= 7
        assert sky_quality.light_pollution_level in ["significant", "severe"]
        assert sky_quality.limiting_magnitude < 5.0
        assert "moon" in sky_quality.suitable_for or "planets" in sky_quality.suitable_for

    def test_calculate_limiting_magnitude(self, service):
        """Test limiting magnitude calculation for each Bortle class."""
        # Bortle 1 should have highest limiting magnitude
        mag_1 = service._calculate_limiting_magnitude(1)
        assert mag_1 == 7.6

        # Bortle 5 should be middle
        mag_5 = service._calculate_limiting_magnitude(5)
        assert mag_5 == 5.6

        # Bortle 9 should have lowest limiting magnitude
        mag_9 = service._calculate_limiting_magnitude(9)
        assert mag_9 == 3.5

        # Check descending order
        assert mag_1 > mag_5 > mag_9

    def test_assess_milky_way_visibility(self, service):
        """Test Milky Way visibility assessment."""
        assert service._assess_milky_way_visibility(1) == "spectacular"
        assert service._assess_milky_way_visibility(2) == "spectacular"
        assert service._assess_milky_way_visibility(3) == "visible"
        assert service._assess_milky_way_visibility(4) == "visible"
        assert service._assess_milky_way_visibility(5) == "barely visible"
        assert service._assess_milky_way_visibility(6) == "barely visible"
        assert service._assess_milky_way_visibility(7) == "not visible"
        assert service._assess_milky_way_visibility(8) == "not visible"
        assert service._assess_milky_way_visibility(9) == "not visible"

    def test_categorize_light_pollution(self, service):
        """Test light pollution categorization."""
        assert service._categorize_light_pollution(1) == "minimal"
        assert service._categorize_light_pollution(2) == "minimal"
        assert service._categorize_light_pollution(3) == "moderate"
        assert service._categorize_light_pollution(4) == "moderate"
        assert service._categorize_light_pollution(5) == "significant"
        assert service._categorize_light_pollution(6) == "significant"
        assert service._categorize_light_pollution(7) == "severe"
        assert service._categorize_light_pollution(8) == "severe"
        assert service._categorize_light_pollution(9) == "severe"

    def test_get_visibility_description(self, service):
        """Test visibility description generation."""
        desc_1 = service._get_visibility_description(1)
        assert "Exceptional" in desc_1 or "ideal" in desc_1

        desc_5 = service._get_visibility_description(5)
        assert "Suburban" in desc_5

        desc_9 = service._get_visibility_description(9)
        assert "Inner city" in desc_9 or "severely limited" in desc_9

    def test_get_suitable_object_types(self, service):
        """Test suitable object types for different Bortle classes."""
        # Bortle 1-3: All object types (singular form to match database)
        objects_1 = service._get_suitable_object_types(1)
        assert "galaxy" in objects_1
        assert "nebula" in objects_1
        assert "cluster" in objects_1
        assert "planetary_nebula" in objects_1
        assert "planet" in objects_1
        assert "comet" in objects_1

        # Bortle 4-5: Limited to brighter objects
        objects_5 = service._get_suitable_object_types(5)
        assert "cluster" in objects_5
        assert "planet" in objects_5
        assert "galaxy" in objects_5
        assert "nebula" in objects_5

        # Bortle 8-9: Only brightest objects
        objects_9 = service._get_suitable_object_types(9)
        assert "planet" in objects_9
        assert "moon" in objects_9
        assert "galaxy" not in objects_9  # Galaxies not suitable in cities


class TestObservingRecommendations:
    """Test get_observing_recommendations() method."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return LightPollutionService()

    @pytest.fixture
    def dark_sky_quality(self):
        """Create dark sky quality object."""
        return SkyQuality(
            bortle_class=2,
            bortle_name="Typical truly dark site",
            sqm_estimate=21.7,
            light_pollution_level="minimal",
            visibility_description="Excellent dark sky",
            suitable_for=["galaxies", "nebulae", "clusters", "planets", "moon"],
            limiting_magnitude=7.1,
            milky_way_visibility="spectacular",
            light_pollution_source="estimated",
        )

    @pytest.fixture
    def urban_sky_quality(self):
        """Create urban sky quality object."""
        return SkyQuality(
            bortle_class=8,
            bortle_name="City sky",
            sqm_estimate=17.5,
            light_pollution_level="severe",
            visibility_description="City sky - only brightest objects",
            suitable_for=["planets", "moon", "bright stars"],
            limiting_magnitude=4.1,
            milky_way_visibility="not visible",
            light_pollution_source="estimated",
        )

    def test_get_observing_recommendations_dark_sky(self, service, dark_sky_quality):
        """Test recommendations for dark sky location."""
        recommendations = service.get_observing_recommendations(dark_sky_quality)

        assert "overall_rating" in recommendations
        assert recommendations["overall_rating"] == "excellent"

        assert "best_for" in recommendations
        assert len(recommendations["best_for"]) > 0

        assert "avoid" in recommendations
        # Dark sky should have nothing to avoid
        assert len(recommendations["avoid"]) == 0

        assert "tips" in recommendations
        assert len(recommendations["tips"]) > 0

    def test_get_observing_recommendations_urban(self, service, urban_sky_quality):
        """Test recommendations for urban location."""
        recommendations = service.get_observing_recommendations(urban_sky_quality)

        assert recommendations["overall_rating"] == "poor"

        # Urban sky should have objects to avoid
        assert len(recommendations["avoid"]) > 0
        assert "all deep sky objects" in recommendations["avoid"][0] or "galaxies" in recommendations["avoid"]

        # Should have tips for urban observing
        assert len(recommendations["tips"]) > 0

    def test_get_overall_rating(self, service):
        """Test overall rating assignment."""
        assert service._get_overall_rating(1) == "excellent"
        assert service._get_overall_rating(2) == "excellent"
        assert service._get_overall_rating(3) == "good"
        assert service._get_overall_rating(4) == "good"
        assert service._get_overall_rating(5) == "fair"
        assert service._get_overall_rating(6) == "fair"
        assert service._get_overall_rating(7) == "poor"
        assert service._get_overall_rating(8) == "poor"
        assert service._get_overall_rating(9) == "poor"

    def test_get_objects_to_avoid(self, service):
        """Test objects to avoid recommendations."""
        # Dark sky - nothing to avoid
        avoid_1 = service._get_objects_to_avoid(1)
        assert len(avoid_1) == 0

        # Suburban - some objects difficult
        avoid_5 = service._get_objects_to_avoid(5)
        assert len(avoid_5) > 0
        assert "faint galaxies" in avoid_5 or "planetary nebulae" in avoid_5

        # Urban - most objects difficult
        avoid_9 = service._get_objects_to_avoid(9)
        assert len(avoid_9) > 0
        assert "all deep sky objects" in avoid_9[0] or "brightest" in avoid_9[0]

    def test_get_observing_tips(self, service):
        """Test observing tips generation."""
        # Dark sky tips
        tips_1 = service._get_observing_tips(1)
        assert len(tips_1) > 0
        assert any("wide-field" in tip or "dark skies" in tip for tip in tips_1)

        # Suburban tips
        tips_5 = service._get_observing_tips(5)
        assert len(tips_5) > 0
        assert any("filter" in tip or "planets" in tip for tip in tips_5)

        # Urban tips
        tips_9 = service._get_observing_tips(9)
        assert len(tips_9) > 0
        assert any("traveling" in tip or "darker skies" in tip or "Double stars" in tip for tip in tips_9)
