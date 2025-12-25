"""Tests for best viewing months calculator."""


import pytest

from app.services.viewing_months_service import MonthRating, ViewingMonth, ViewingMonthsService


class TestMonthRating:
    """Test MonthRating enum."""

    def test_rating_values(self):
        """Test month rating values."""
        assert MonthRating.EXCELLENT.value == 5
        assert MonthRating.GOOD.value == 4
        assert MonthRating.FAIR.value == 3
        assert MonthRating.POOR.value == 2
        assert MonthRating.NOT_VISIBLE.value == 1


class TestViewingMonth:
    """Test ViewingMonth model."""

    def test_viewing_month_creation(self):
        """Test creating a viewing month."""
        month = ViewingMonth(
            month=3,
            month_name="March",
            rating=MonthRating.EXCELLENT,
            visibility_hours=8.5,
            best_time="22:00",
            notes="Object high in sky during evening hours",
        )
        assert month.month == 3
        assert month.month_name == "March"
        assert month.rating == MonthRating.EXCELLENT
        assert month.visibility_hours == 8.5

    def test_is_good_month_excellent(self):
        """Test identifying excellent viewing month."""
        month = ViewingMonth(
            month=3, month_name="March", rating=MonthRating.EXCELLENT, visibility_hours=8.5, best_time="22:00"
        )
        assert month.is_good_month() is True

    def test_is_good_month_poor(self):
        """Test identifying poor viewing month."""
        month = ViewingMonth(
            month=6, month_name="June", rating=MonthRating.POOR, visibility_hours=2.0, best_time="03:00"
        )
        assert month.is_good_month() is False


class TestViewingMonthsService:
    """Test ViewingMonthsService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ViewingMonthsService()

    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert hasattr(service, "calculate_viewing_months")

    def test_calculate_viewing_months_for_object(self, service):
        """Test calculating viewing months for deep sky object."""
        # M31 Andromeda Galaxy - best viewed in fall
        months = service.calculate_viewing_months(
            ra_hours=0.712, dec_degrees=41.27, latitude=40.0, object_name="M31"  # 00h 42m
        )

        assert len(months) == 12
        assert all(isinstance(m, ViewingMonth) for m in months)

        # Fall months (Sep, Oct, Nov) should be good for M31
        fall_months = [m for m in months if m.month in [9, 10, 11]]
        assert any(m.rating.value >= MonthRating.GOOD.value for m in fall_months)

    def test_calculate_viewing_months_circumpolar(self, service):
        """Test viewing months for circumpolar object."""
        # Polaris - visible year-round from northern hemisphere
        months = service.calculate_viewing_months(
            ra_hours=2.530, dec_degrees=89.26, latitude=40.0, object_name="Polaris"  # Near north celestial pole
        )

        # All months should have some visibility
        assert all(m.rating != MonthRating.NOT_VISIBLE for m in months)

    def test_get_best_months(self, service):
        """Test getting best viewing months."""
        months = service.calculate_viewing_months(ra_hours=5.919, dec_degrees=-5.39, latitude=40.0)  # Orion Nebula

        best = service.get_best_months(months, count=3)
        assert len(best) <= 3

        # Should be sorted by rating/visibility
        for i in range(len(best) - 1):
            assert best[i].rating.value >= best[i + 1].rating.value

    def test_calculate_altitude_at_transit(self, service):
        """Test calculating maximum altitude at meridian transit."""
        # Object at declination +40°, observer at latitude 40°
        # Should transit at altitude 90° (zenith)
        altitude = service._calculate_altitude_at_transit(dec_degrees=40.0, latitude=40.0)
        assert 85 <= altitude <= 90

        # Object at declination 0°, observer at latitude 40°
        # Should transit at altitude 50°
        altitude = service._calculate_altitude_at_transit(dec_degrees=0.0, latitude=40.0)
        assert 48 <= altitude <= 52

    def test_is_visible_from_latitude(self, service):
        """Test checking if object is visible from latitude."""
        # Object at dec +50° should be visible from lat 40°
        assert service._is_visible_from_latitude(dec_degrees=50.0, latitude=40.0) is True

        # Object at dec -60° should not be visible from lat 40°
        assert service._is_visible_from_latitude(dec_degrees=-60.0, latitude=40.0) is False

    def test_calculate_visibility_hours(self, service):
        """Test calculating hours object is above horizon."""
        # Object at high declination should be visible many hours
        hours = service._calculate_visibility_hours(dec_degrees=60.0, latitude=40.0, month=6)  # Summer
        assert hours > 10  # Visible most of night

        # Object at low declination should have fewer visible hours
        hours = service._calculate_visibility_hours(dec_degrees=-20.0, latitude=40.0, month=6)
        assert hours < 8

    def test_rate_viewing_quality(self, service):
        """Test rating viewing quality."""
        # High altitude, many visible hours = excellent
        rating = service._rate_viewing_quality(altitude=70.0, visibility_hours=10.0, is_evening=True)
        assert rating == MonthRating.EXCELLENT

        # Low altitude, few hours = poor
        rating = service._rate_viewing_quality(altitude=25.0, visibility_hours=3.0, is_evening=False)
        assert rating in [MonthRating.POOR, MonthRating.NOT_VISIBLE]

    def test_get_season_for_month(self, service):
        """Test getting season for month."""
        assert service._get_season_for_month(1) == "Winter"
        assert service._get_season_for_month(4) == "Spring"
        assert service._get_season_for_month(7) == "Summer"
        assert service._get_season_for_month(10) == "Fall"

    def test_month_names(self, service):
        """Test month name conversion."""
        assert service._get_month_name(1) == "January"
        assert service._get_month_name(6) == "June"
        assert service._get_month_name(12) == "December"

    def test_calculate_best_observation_time(self, service):
        """Test calculating best observation time for month."""
        # Winter month - object transits at midnight should be best around 21:00-00:00
        time = service._calculate_best_observation_time(ra_hours=6.0, month=1)  # Roughly midnight in winter
        assert time is not None
        assert ":" in time

    def test_viewing_months_summary(self, service):
        """Test generating viewing months summary."""
        months = service.calculate_viewing_months(ra_hours=5.919, dec_degrees=-5.39, latitude=40.0, object_name="M42")

        summary = service.get_viewing_summary(months)
        assert "best_months" in summary
        assert "visibility_range" in summary
        assert len(summary["best_months"]) >= 1
