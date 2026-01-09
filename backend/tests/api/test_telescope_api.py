"""Tests for telescope API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.clients.seestar_client import SeestarClient, SeestarState, SeestarStatus
from app.main import app
from app.services.telescope_service import ExecutionProgress, ExecutionState, TelescopeService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_telescope_service():
    """Create mock telescope service."""
    service = Mock(spec=TelescopeService)
    service.execution_state = ExecutionState.IDLE
    service.progress = None
    service.park_telescope = AsyncMock(return_value=True)
    service.abort_execution = AsyncMock()
    service.execute_plan = AsyncMock(
        return_value=ExecutionProgress(
            execution_id="test-123",
            state=ExecutionState.COMPLETED,
            total_targets=5,
            current_target_index=5,
            targets_completed=5,
            targets_failed=0,
        )
    )
    return service


@pytest.fixture
def mock_seestar_client():
    """Create mock Seestar client."""
    client = Mock(spec=SeestarClient)
    client.connected = False
    client.status = SeestarStatus(connected=False, state=SeestarState.DISCONNECTED, firmware_version=None)
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    return client


class TestTelescopeEndpoints:
    """Test telescope control endpoints."""

    def test_connect_success(self, client, mock_seestar_client):
        """Test successful telescope connection."""
        with patch("app.api.routes.SeestarClient", return_value=mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True, state=SeestarState.CONNECTED, firmware_version="5.50"
            )

            response = client.post("/api/telescope/connect", json={"host": "192.168.2.47", "port": 4700})

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["host"] == "192.168.2.47"
            assert data["port"] == 4700
            assert "message" in data
            mock_seestar_client.connect.assert_called_once_with("192.168.2.47", 4700)

    def test_connect_failure(self, client, mock_seestar_client):
        """Test failed telescope connection."""
        with patch("app.api.routes.SeestarClient", return_value=mock_seestar_client):
            mock_seestar_client.connect = AsyncMock(side_effect=Exception("Connection failed"))

            response = client.post("/api/telescope/connect", json={"host": "invalid.host", "port": 4700})

            assert response.status_code == 500
            assert "Connection failed" in response.json()["detail"]

    def test_disconnect(self, client, mock_seestar_client):
        """Test telescope disconnect."""
        with patch("app.api.routes.seestar_client", mock_seestar_client):
            response = client.post("/api/telescope/disconnect")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert "message" in data
            mock_seestar_client.disconnect.assert_called_once()

    def test_status_when_connected(self, client, mock_seestar_client):
        """Test status endpoint when telescope connected."""
        with patch("app.api.routes.seestar_client", mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True,
                state=SeestarState.TRACKING,
                firmware_version="5.50",
                current_target="M31",
                is_tracking=True,
            )

            response = client.get("/api/telescope/status")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["state"] == "tracking"
            assert data["firmware_version"] == "5.50"
            assert data["current_target"] == "M31"
            assert data["is_tracking"] is True

    def test_status_when_disconnected(self, client, mock_seestar_client):
        """Test status endpoint when telescope disconnected."""
        with patch("app.api.routes.seestar_client", mock_seestar_client):
            response = client.get("/api/telescope/status")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["state"] == "disconnected"

    def test_execute_plan_success(self, client, mock_seestar_client):
        """Test successful plan execution."""
        # Mock database session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No active execution

        # Mock Celery task
        mock_task = MagicMock()
        mock_task.id = "celery-task-123"
        mock_task.delay.return_value = mock_task

        with (
            patch("app.api.routes.seestar_client", mock_seestar_client),
            patch("app.database.SessionLocal", return_value=mock_db),
            patch("app.tasks.telescope_tasks.execute_observation_plan_task", mock_task),
        ):
            # Mock connected state
            mock_seestar_client.connected = True
            mock_seestar_client.host = "192.168.2.47"
            mock_seestar_client.port = 4700

            plan_data = {
                "scheduled_targets": [
                    {
                        "target": {
                            "name": "M31",
                            "catalog_id": "M31",
                            "object_type": "galaxy",
                            "ra_hours": 0.7122,
                            "dec_degrees": 41.269,
                            "magnitude": 3.4,
                            "size_arcmin": 190.0,
                            "description": "Andromeda Galaxy",
                        },
                        "start_time": "2025-11-01T20:00:00",
                        "end_time": "2025-11-01T23:00:00",
                        "duration_minutes": 180,
                        "start_altitude": 45.0,
                        "end_altitude": 50.0,
                        "start_azimuth": 120.0,
                        "end_azimuth": 150.0,
                        "field_rotation_rate": 0.5,
                        "recommended_exposure": 10,
                        "recommended_frames": 180,
                        "score": {
                            "visibility_score": 0.95,
                            "weather_score": 0.90,
                            "object_score": 0.85,
                            "total_score": 0.90,
                        },
                    }
                ]
            }

            response = client.post("/api/telescope/execute", json=plan_data)

            assert response.status_code == 200
            data = response.json()
            assert "execution_id" in data
            assert data["status"] == "started"
            assert "message" in data
            assert data["total_targets"] == 1

    def test_execute_plan_invalid_data(self, client):
        """Test plan execution with invalid data."""
        response = client.post("/api/telescope/execute", json={})

        assert response.status_code == 422  # Validation error

    def test_get_progress_when_running(self, client):
        """Test progress endpoint during execution."""

        # Mock the database session and execution record
        mock_execution = MagicMock()
        mock_execution.execution_id = "test-123"
        mock_execution.state = "running"
        mock_execution.total_targets = 10
        mock_execution.current_target_index = 3
        mock_execution.targets_completed = 2
        mock_execution.targets_failed = 0
        mock_execution.current_target_name = "NGC7000"
        mock_execution.current_phase = "imaging"
        mock_execution.started_at = datetime.now()
        mock_execution.error_message = None
        mock_execution.elapsed_seconds = 120  # 2 minutes elapsed
        mock_execution.estimated_remaining_seconds = 600  # 10 minutes remaining

        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.first.return_value = mock_execution

        with patch("app.database.SessionLocal", return_value=mock_db):
            response = client.get("/api/telescope/progress")

            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == "test-123"
            assert data["state"] == "running"
            assert data["current_target_name"] == "NGC7000"
            assert data["current_phase"] == "imaging"
            assert data["total_targets"] == 10
            assert data["current_target_index"] == 3

    def test_get_progress_when_idle(self, client):
        """Test progress endpoint when no execution."""
        # Mock the database session - no execution records
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.first.return_value = None

        with patch("app.database.SessionLocal", return_value=mock_db):
            response = client.get("/api/telescope/progress")

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "idle"
            # When no execution exists, API returns minimal response
            assert "message" in data

    def test_abort_execution(self, client):
        """Test abort execution endpoint."""
        # Mock the database session with an active execution
        mock_execution = MagicMock()
        mock_execution.execution_id = "test-123"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_execution

        # Mock the Celery abort task
        mock_abort_task = MagicMock()

        with (
            patch("app.database.SessionLocal", return_value=mock_db),
            patch("app.tasks.telescope_tasks.abort_observation_plan_task", mock_abort_task),
        ):
            response = client.post("/api/telescope/abort")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            mock_abort_task.delay.assert_called_once_with("test-123")

    def test_park_telescope_success(self, client, mock_seestar_client):
        """Test successful telescope parking."""
        with patch("app.api.routes.seestar_client", mock_seestar_client):
            # Mock connected state and park method
            mock_seestar_client.connected = True
            mock_seestar_client.park = AsyncMock(return_value=True)

            response = client.post("/api/telescope/park")

            assert response.status_code == 200
            data = response.json()
            # API returns {"status": "parking", "message": ...}
            assert data["status"] == "parking"
            assert "message" in data
            mock_seestar_client.park.assert_called_once()

    def test_park_telescope_failure(self, client, mock_seestar_client):
        """Test failed telescope parking."""
        with patch("app.api.routes.seestar_client", mock_seestar_client):
            # Mock connected state and park method returning False
            mock_seestar_client.connected = True
            mock_seestar_client.park = AsyncMock(return_value=False)

            response = client.post("/api/telescope/park")

            # API returns 200 with error status, not 500
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "Failed to park" in data["message"]

    def test_connect_with_custom_port(self, client, mock_seestar_client):
        """Test connection with custom port."""
        with patch("app.api.routes.SeestarClient", return_value=mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True, state=SeestarState.CONNECTED, firmware_version="4.50"
            )

            response = client.post("/api/telescope/connect", json={"host": "192.168.1.100", "port": 5555})

            assert response.status_code == 200
            mock_seestar_client.connect.assert_called_once_with("192.168.1.100", 5555)

    def test_connect_with_default_port(self, client, mock_seestar_client):
        """Test connection uses default port 4700."""
        with patch("app.api.routes.SeestarClient", return_value=mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True, state=SeestarState.CONNECTED, firmware_version="5.50"
            )

            response = client.post("/api/telescope/connect", json={"host": "192.168.2.47"})

            # Should use default port 4700
            assert response.status_code == 200
            mock_seestar_client.connect.assert_called_once_with("192.168.2.47", 4700)


# Integration-style tests could be added with:
# 1. Full mock telescope service with state transitions
# 2. Multi-target execution scenarios
# 3. Error handling during execution
# 4. Connection loss recovery
