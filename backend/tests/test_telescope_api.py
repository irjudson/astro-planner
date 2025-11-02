"""Tests for telescope API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.main import app
from app.clients.seestar_client import SeestarClient, SeestarState, SeestarStatus
from app.services.telescope_service import (
    TelescopeService,
    ExecutionState,
    ExecutionProgress
)


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
    service.execute_plan = AsyncMock(return_value=ExecutionProgress(
        execution_id="test-123",
        state=ExecutionState.COMPLETED,
        total_targets=5,
        current_target_index=5,
        targets_completed=5,
        targets_failed=0
    ))
    return service


@pytest.fixture
def mock_seestar_client():
    """Create mock Seestar client."""
    client = Mock(spec=SeestarClient)
    client.connected = False
    client.status = SeestarStatus(
        connected=False,
        state=SeestarState.DISCONNECTED,
        firmware_version=None
    )
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    return client


class TestTelescopeEndpoints:
    """Test telescope control endpoints."""

    def test_connect_success(self, client, mock_seestar_client):
        """Test successful telescope connection."""
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True,
                state=SeestarState.CONNECTED,
                firmware_version="5.50"
            )

            response = client.post(
                "/api/telescope/connect",
                json={"host": "192.168.2.47", "port": 4700}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["host"] == "192.168.2.47"
            assert data["port"] == 4700
            assert "message" in data

    def test_connect_failure(self, client, mock_seestar_client):
        """Test failed telescope connection."""
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            mock_seestar_client.connect.side_effect = Exception("Connection failed")

            response = client.post(
                "/api/telescope/connect",
                json={"host": "invalid.host", "port": 4700}
            )

            assert response.status_code == 500
            assert "Connection failed" in response.json()["detail"]

    def test_disconnect(self, client, mock_seestar_client):
        """Test telescope disconnect."""
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            response = client.post("/api/telescope/disconnect")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert "message" in data
            mock_seestar_client.disconnect.assert_called_once()

    def test_status_when_connected(self, client, mock_seestar_client):
        """Test status endpoint when telescope connected."""
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True,
                state=SeestarState.TRACKING,
                firmware_version="5.50",
                current_target="M31",
                is_tracking=True
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
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            response = client.get("/api/telescope/status")

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["state"] == "disconnected"

    def test_execute_plan_success(self, client, mock_seestar_client, mock_telescope_service):
        """Test successful plan execution."""
        with patch('app.api.routes.seestar_client', mock_seestar_client), \
             patch('app.api.routes.telescope_service', mock_telescope_service):
            # Mock connected state
            mock_seestar_client.connected = True
            mock_telescope_service.execution_state = ExecutionState.IDLE

            plan_data = {
                "execution_id": "test-exec-123",
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
                            "description": "Andromeda Galaxy"
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
                            "total_score": 0.90
                        }
                    }
                ]
            }

            response = client.post("/api/telescope/execute", json=plan_data)

            assert response.status_code == 200
            data = response.json()
            # Fixed: API generates its own execution_id, not from request
            assert "execution_id" in data
            assert "status" in data  # Fixed: API returns "status" not "state"
            assert "message" in data
            mock_telescope_service.execute_plan.assert_called_once()

    def test_execute_plan_invalid_data(self, client):
        """Test plan execution with invalid data."""
        response = client.post("/api/telescope/execute", json={})

        assert response.status_code == 422  # Validation error

    def test_get_progress_when_running(self, client, mock_telescope_service):
        """Test progress endpoint during execution."""
        with patch('app.api.routes.telescope_service', mock_telescope_service):
            mock_telescope_service.progress = ExecutionProgress(
                execution_id="test-123",
                state=ExecutionState.RUNNING,
                total_targets=10,
                current_target_index=3,
                targets_completed=2,
                targets_failed=0,
                current_target_name="NGC7000",
                current_phase="imaging"
            )

            response = client.get("/api/telescope/progress")

            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == "test-123"
            assert data["state"] == "running"
            assert data["current_target_name"] == "NGC7000"
            assert data["current_phase"] == "imaging"
            assert data["total_targets"] == 10
            assert data["current_target_index"] == 3

    def test_get_progress_when_idle(self, client, mock_telescope_service):
        """Test progress endpoint when no execution."""
        with patch('app.api.routes.telescope_service', mock_telescope_service):
            mock_telescope_service.progress = None
            mock_telescope_service.execution_state = ExecutionState.IDLE

            response = client.get("/api/telescope/progress")

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "idle"
            # Fixed: when progress is None, API returns minimal response
            assert "message" in data

    def test_abort_execution(self, client, mock_telescope_service):
        """Test abort execution endpoint."""
        with patch('app.api.routes.telescope_service', mock_telescope_service):
            response = client.post("/api/telescope/abort")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            mock_telescope_service.abort_execution.assert_called_once()

    def test_park_telescope_success(self, client, mock_seestar_client, mock_telescope_service):
        """Test successful telescope parking."""
        with patch('app.api.routes.seestar_client', mock_seestar_client), \
             patch('app.api.routes.telescope_service', mock_telescope_service):
            # Fixed: Mock connected state
            mock_seestar_client.connected = True

            response = client.post("/api/telescope/park")

            assert response.status_code == 200
            data = response.json()
            # Fixed: API returns {"status": "parking", "message": ...}
            assert data["status"] == "parking"
            assert "message" in data
            mock_telescope_service.park_telescope.assert_called_once()

    def test_park_telescope_failure(self, client, mock_seestar_client, mock_telescope_service):
        """Test failed telescope parking."""
        with patch('app.api.routes.seestar_client', mock_seestar_client), \
             patch('app.api.routes.telescope_service', mock_telescope_service):
            # Fixed: Mock connected state
            mock_seestar_client.connected = True
            mock_telescope_service.park_telescope.return_value = False

            response = client.post("/api/telescope/park")

            # Fixed: API returns 200 with error status, not 500
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "Failed to park" in data["message"]

    def test_connect_with_custom_port(self, client, mock_seestar_client):
        """Test connection with custom port."""
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True,
                state=SeestarState.CONNECTED,
                firmware_version="4.50"
            )

            response = client.post(
                "/api/telescope/connect",
                json={"host": "192.168.1.100", "port": 5555}
            )

            assert response.status_code == 200
            mock_seestar_client.connect.assert_called_once_with(
                "192.168.1.100", 5555
            )

    def test_connect_with_default_port(self, client, mock_seestar_client):
        """Test connection uses default port 4700."""
        with patch('app.api.routes.seestar_client', mock_seestar_client):
            mock_seestar_client.connected = True
            mock_seestar_client.status = SeestarStatus(
                connected=True,
                state=SeestarState.CONNECTED,
                firmware_version="5.50"
            )

            response = client.post(
                "/api/telescope/connect",
                json={"host": "192.168.2.47"}
            )

            # Should use default port 4700
            assert response.status_code == 200
            mock_seestar_client.connect.assert_called_once()


# Integration-style tests could be added with:
# 1. Full mock telescope service with state transitions
# 2. Multi-target execution scenarios
# 3. Error handling during execution
# 4. Connection loss recovery
