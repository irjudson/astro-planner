"""API endpoint tests.

These tests require database services (PostgreSQL) to run.
They are marked as integration tests and skipped on macOS CI.
"""

from datetime import datetime

import pytest

from app.models.capture_models import CaptureHistory

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def sample_location():
    """Sample location data."""
    return {
        "name": "Three Forks, MT",
        "latitude": 45.9183,
        "longitude": -111.5433,
        "elevation": 1234.0,
        "timezone": "America/Denver",
    }


@pytest.fixture
def sample_plan_request(sample_location):
    """Sample plan request."""
    return {
        "location": sample_location,
        "observing_date": datetime.now().strftime("%Y-%m-%d"),
        "constraints": {
            "min_altitude": 30.0,
            "max_altitude": 80.0,
            "setup_time_minutes": 15,
            "object_types": ["galaxy", "nebula", "cluster"],
            "planning_mode": "balanced",
        },
    }


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test that health check returns correct status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "astro-planner-api"
        assert "version" in data


class TestTargetEndpoints:
    """Test target-related endpoints."""

    def test_list_targets(self, client):
        """Test listing all targets."""

        response = client.get("/api/targets")
        assert response.status_code == 200
        targets = response.json()
        assert isinstance(targets, list)
        assert len(targets) > 0

        # Check first target structure
        target = targets[0]
        assert "name" in target
        assert "catalog_id" in target
        assert "object_type" in target
        assert "ra_hours" in target
        assert "dec_degrees" in target

    def test_get_specific_target(self, client):
        """Test getting a specific target by ID."""

        target_id = "M31"
        response = client.get(f"/api/targets/{target_id}")
        assert response.status_code == 200
        target = response.json()
        assert target["catalog_id"] == target_id
        # OpenNGC catalog uses catalog IDs as names (M31, NGC224, etc.)
        assert target["name"] == "M31"

    def test_get_nonexistent_target(self, client):
        """Test getting a target that doesn't exist."""
        response = client.get("/api/targets/NONEXISTENT")
        assert response.status_code == 404

    def test_targets_include_capture_history(self, client, override_get_db):
        """Test that targets endpoint includes capture history."""
        db_session = override_get_db
        # Create capture history for M31
        capture = CaptureHistory(
            catalog_id="M31",
            total_exposure_seconds=7200,
            total_frames=720,
            total_sessions=3
        )
        db_session.add(capture)
        db_session.commit()

        response = client.get("/api/targets?limit=20")
        assert response.status_code == 200

        targets = response.json()
        m31 = next((t for t in targets if t['catalog_id'] == 'M31'), None)

        assert m31 is not None
        assert 'capture_history' in m31
        assert m31['capture_history']['total_exposure_seconds'] == 7200
        assert m31['capture_history']['total_sessions'] == 3

    def test_targets_without_capture_history(self, client):
        """Test targets without capture history show null."""
        response = client.get("/api/targets?limit=20")
        assert response.status_code == 200

        targets = response.json()
        # Most targets won't have capture history
        target_without_history = next(
            (t for t in targets if t.get('capture_history') is None),
            None
        )
        assert target_without_history is not None


class TestTwilightEndpoint:
    """Test twilight calculation endpoint."""

    def test_calculate_twilight(self, client, sample_location):
        """Test twilight calculation."""
        date = datetime.now().strftime("%Y-%m-%d")
        response = client.post(f"/api/twilight?date={date}", json=sample_location)
        assert response.status_code == 200
        data = response.json()

        # Check all required fields
        required_fields = [
            "sunset",
            "civil_twilight_end",
            "nautical_twilight_end",
            "astronomical_twilight_end",
            "astronomical_twilight_start",
            "nautical_twilight_start",
            "civil_twilight_start",
            "sunrise",
        ]
        for field in required_fields:
            assert field in data
            assert data[field] is not None

    @pytest.mark.skip(reason="Input validation not yet implemented - TODO: Add Pydantic validators for lat/lon range")
    def test_twilight_with_invalid_location(self, client):
        """Test twilight calculation with invalid location.

        TODO: This test should pass once we add input validation.
        Expected behavior: API should return 400/422 for invalid coordinates.
        """
        invalid_location = {
            "name": "Invalid",
            "latitude": 999.0,  # Invalid latitude
            "longitude": 0.0,
            "elevation": 0.0,
            "timezone": "UTC",
        }
        date = datetime.now().strftime("%Y-%m-%d")
        response = client.post(f"/api/twilight?date={date}", json=invalid_location)
        assert response.status_code in [400, 422]


class TestPlanEndpoint:
    """Test plan generation endpoint."""

    @pytest.mark.slow
    def test_generate_plan_success(self, client, sample_plan_request):
        """Test successful plan generation."""

        response = client.post("/api/plan", json=sample_plan_request)
        assert response.status_code == 200
        plan = response.json()

        # Check plan structure
        assert "session" in plan
        assert "location" in plan
        assert "scheduled_targets" in plan
        assert "weather_forecast" in plan
        assert "total_targets" in plan
        assert "coverage_percent" in plan

        # Check session info
        session = plan["session"]
        assert "observing_date" in session
        assert "imaging_start" in session
        assert "imaging_end" in session
        assert "total_imaging_minutes" in session

    @pytest.mark.slow
    def test_generate_plan_all_planning_modes(self, client, sample_plan_request):
        """Test plan generation with all planning modes."""

        modes = ["balanced", "quality", "quantity"]

        for mode in modes:
            sample_plan_request["constraints"]["planning_mode"] = mode
            response = client.post("/api/plan", json=sample_plan_request)
            assert response.status_code == 200
            plan = response.json()
            assert plan["total_targets"] >= 0

    @pytest.mark.slow
    def test_generate_plan_different_object_types(self, client, sample_plan_request):
        """Test plan generation with different object type filters."""

        object_type_combinations = [
            ["galaxy"],
            ["nebula"],
            ["cluster"],
            ["galaxy", "nebula"],
            ["galaxy", "nebula", "cluster", "planetary_nebula"],
        ]

        for object_types in object_type_combinations:
            sample_plan_request["constraints"]["object_types"] = object_types
            response = client.post("/api/plan", json=sample_plan_request)
            assert response.status_code == 200
            plan = response.json()
            assert isinstance(plan["scheduled_targets"], list)

    @pytest.mark.skip(reason="Date validation not yet implemented - TODO: Add Pydantic date validators")
    def test_generate_plan_with_invalid_date(self, client, sample_plan_request):
        """Test plan generation with invalid date.

        TODO: This test should pass once we add input validation.
        Expected behavior: API should return 422 for invalid date format.
        """
        sample_plan_request["observing_date"] = "invalid-date"
        response = client.post("/api/plan", json=sample_plan_request)
        assert response.status_code == 422


@pytest.mark.slow
class TestExportEndpoint:
    """Test plan export endpoint."""

    @pytest.fixture
    def sample_plan(self, client, sample_plan_request):
        """Generate a sample plan for export testing."""
        response = client.post("/api/plan", json=sample_plan_request)
        assert response.status_code == 200
        return response.json()

    def test_export_json(self, client, sample_plan):
        """Test JSON export."""
        response = client.post("/api/export?format=json", json=sample_plan)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_export_seestar_plan(self, client, sample_plan):
        """Test Seestar Plan Mode export."""
        response = client.post("/api/export?format=seestar_plan", json=sample_plan)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "seestar_plan_v1" in data["data"]

    def test_export_seestar_alp(self, client, sample_plan):
        """Test Seestar ALP export."""
        response = client.post("/api/export?format=seestar_alp", json=sample_plan)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "Seestar S50 Observing Plan" in data["data"]

    def test_export_text(self, client, sample_plan):
        """Test text export."""
        response = client.post("/api/export?format=text", json=sample_plan)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0

    def test_export_csv(self, client, sample_plan):
        """Test CSV export."""
        response = client.post("/api/export?format=csv", json=sample_plan)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "Target Name,Catalog ID" in data["data"]

    def test_export_invalid_format(self, client, sample_plan):
        """Test export with invalid format."""
        response = client.post("/api/export?format=invalid", json=sample_plan)
        assert response.status_code in [400, 422]
