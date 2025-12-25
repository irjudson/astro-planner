"""Integration tests for sky quality filtering in plan generation.

These tests require database services (PostgreSQL) to run.
They are marked as integration tests and skipped on macOS CI.
"""

import pytest

# Mark all tests in this file as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.slow]

from app.models import Location, ObservingConstraints, PlanRequest
from app.services.planner_service import PlannerService


@pytest.fixture
def test_db(override_get_db):
    """Fixture for test database session."""
    return override_get_db


class TestSkyQualityIntegration:
    """Test sky quality integration in the full planning workflow."""

    def test_plan_includes_sky_quality(self, test_db):
        """Test that generated plans include sky quality information."""
        # Arrange: Create a plan request for a dark sky location
        request = PlanRequest(
            location=Location(
                name="Three Forks, MT", latitude=45.92, longitude=-111.28, elevation=1234.0, timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(min_altitude=30.0, object_types=["galaxy", "nebula", "cluster"]),
        )

        # Act: Generate plan
        planner = PlannerService(test_db)
        plan = planner.generate_plan(request)

        # Assert: Plan should include sky quality
        assert plan.sky_quality is not None, "Plan should include sky quality data"
        assert "bortle_class" in plan.sky_quality
        assert "suitable_for" in plan.sky_quality
        assert "sqm_estimate" in plan.sky_quality

    def test_dark_sky_includes_all_object_types(self, test_db):
        """Test that dark sky locations allow all object types."""
        # Arrange: Dark sky location (Three Forks, MT - expected Bortle 1-3)
        request = PlanRequest(
            location=Location(
                name="Three Forks, MT", latitude=45.92, longitude=-111.28, elevation=1234.0, timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(
                min_altitude=30.0, object_types=["galaxy", "nebula", "cluster", "planetary_nebula"]
            ),
        )

        # Act: Generate plan
        planner = PlannerService(test_db)
        plan = planner.generate_plan(request)

        # Assert: Should have excellent sky quality
        assert plan.sky_quality["bortle_class"] <= 3, "Three Forks should be Bortle 1-3"
        suitable_types = plan.sky_quality["suitable_for"]
        assert "galaxy" in suitable_types
        assert "nebula" in suitable_types
        assert "cluster" in suitable_types
        assert "planetary_nebula" in suitable_types

    def test_light_polluted_sky_filters_objects(self, test_db):
        """Test that light polluted locations filter unsuitable objects."""
        # Arrange: Light polluted location (NYC - expected Bortle 8-9)
        request = PlanRequest(
            location=Location(
                name="New York City", latitude=40.7128, longitude=-74.0060, elevation=10.0, timezone="America/New_York"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(min_altitude=30.0, object_types=["galaxy", "nebula", "cluster"]),
        )

        # Act: Generate plan
        planner = PlannerService(test_db)
        plan = planner.generate_plan(request)

        # Assert: Should have poor sky quality with limited object types
        assert plan.sky_quality["bortle_class"] >= 8, "NYC should be Bortle 8-9"
        suitable_types = plan.sky_quality["suitable_for"]
        assert "galaxy" not in suitable_types, "Galaxies not visible in city sky"
        assert len(suitable_types) <= 2, "City sky should only have planet/moon"

    def test_suburban_sky_allows_bright_objects(self, test_db):
        """Test that suburban locations allow bright objects."""
        # Arrange: Suburban location (Denver area - expected Bortle 4-9)
        # Note: Denver city center is heavily light polluted (Bortle 8-9)
        request = PlanRequest(
            location=Location(
                name="Denver Suburbs",
                latitude=39.7392,
                longitude=-104.9903,
                elevation=1655.0,
                timezone="America/Denver",
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(min_altitude=30.0, object_types=["galaxy", "nebula", "cluster"]),
        )

        # Act: Generate plan
        planner = PlannerService(test_db)
        plan = planner.generate_plan(request)

        # Assert: Should have moderate to poor sky quality for city center
        bortle = plan.sky_quality["bortle_class"]
        assert 4 <= bortle <= 9, "Denver area should be Bortle 4-9"
        suitable_types = plan.sky_quality["suitable_for"]

        # In poor light pollution, fewer object types are suitable
        # But at least some basic objects should still be visible
        assert len(suitable_types) >= 1, "Should have at least one suitable object type"

    def test_object_types_are_singular(self, test_db):
        """Test that suitable_for list contains singular object types matching database."""
        # Arrange
        request = PlanRequest(
            location=Location(
                name="Test Location", latitude=45.0, longitude=-110.0, elevation=1000.0, timezone="America/Denver"
            ),
            observing_date="2025-01-15",
            constraints=ObservingConstraints(min_altitude=30.0, object_types=["galaxy", "nebula"]),
        )

        # Act
        planner = PlannerService(test_db)
        plan = planner.generate_plan(request)

        # Assert: All object types should be singular to match database schema
        suitable_types = plan.sky_quality["suitable_for"]
        for obj_type in suitable_types:
            assert obj_type in [
                "galaxy",
                "nebula",
                "cluster",
                "planetary_nebula",
                "planet",
                "moon",
                "comet",
                "asteroid",
            ], f"Object type '{obj_type}' should be singular"

            # Should not have plural forms
            assert obj_type not in [
                "galaxies",
                "nebulae",
                "clusters",
                "planetary_nebulae",
                "planets",
                "moons",
                "comets",
                "asteroids",
            ], f"Object type should not be plural: {obj_type}"

    def test_sky_quality_affects_scheduled_targets(self, test_db):
        """Test that sky quality filtering affects which targets get scheduled."""
        # Arrange: Two locations with different sky quality
        dark_location = Location(
            name="Dark Site", latitude=45.92, longitude=-111.28, elevation=1234.0, timezone="America/Denver"
        )

        city_location = Location(
            name="City", latitude=40.7128, longitude=-74.0060, elevation=10.0, timezone="America/New_York"
        )

        constraints = ObservingConstraints(min_altitude=30.0, object_types=["galaxy", "nebula", "cluster"])

        # Act: Generate plans for both locations
        planner = PlannerService(test_db)

        dark_plan = planner.generate_plan(
            PlanRequest(location=dark_location, observing_date="2025-01-15", constraints=constraints)
        )

        city_plan = planner.generate_plan(
            PlanRequest(location=city_location, observing_date="2025-01-15", constraints=constraints)
        )

        # Assert: Dark site should have more targets than city
        # (because more object types are suitable)
        assert (
            dark_plan.total_targets >= city_plan.total_targets
        ), "Dark sky site should have at least as many targets as city"

        # Dark site should have galaxies, city should not
        dark_types = {t.target.object_type for t in dark_plan.scheduled_targets}
        city_types = {t.target.object_type for t in city_plan.scheduled_targets}

        if "galaxy" in dark_types:
            assert "galaxy" not in city_types, "City plan should not include galaxies"
