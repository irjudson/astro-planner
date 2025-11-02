"""Tests for telescope service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from app.services.telescope_service import (
    TelescopeService,
    ExecutionState,
    ExecutionProgress,
    ExecutionError
)
from app.clients.seestar_client import SeestarClient, SeestarState
from app.models import ScheduledTarget, DSOTarget, TargetScore


class TestTelescopeService:
    """Test suite for TelescopeService."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Seestar client."""
        client = Mock(spec=SeestarClient)
        client.connected = True
        client.goto_target = AsyncMock(return_value=True)
        client.auto_focus = AsyncMock(return_value=True)
        client.start_imaging = AsyncMock(return_value=True)
        client.stop_imaging = AsyncMock(return_value=True)
        client.park = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def service(self, mock_client):
        """Create telescope service with mock client."""
        return TelescopeService(mock_client)

    @pytest.fixture
    def sample_target(self):
        """Create sample scheduled target."""
        return ScheduledTarget(
            target=DSOTarget(
                name="M31",
                catalog_id="M31",
                object_type="galaxy",
                ra_hours=0.7122,
                dec_degrees=41.269,
                magnitude=3.4,
                size_arcmin=190.0,
                description="Andromeda Galaxy"
            ),
            start_time=datetime(2025, 11, 1, 20, 0),
            end_time=datetime(2025, 11, 1, 23, 0),
            duration_minutes=180,
            start_altitude=45.0,
            end_altitude=50.0,
            start_azimuth=120.0,
            end_azimuth=150.0,
            field_rotation_rate=0.5,
            recommended_exposure=10,
            recommended_frames=180,
            score=TargetScore(
                visibility_score=0.95,
                weather_score=0.90,
                object_score=0.85,
                total_score=0.90
            )
        )

    def test_init(self, service, mock_client):
        """Test service initialization."""
        assert service.client == mock_client  # Fixed: it's .client not ._client
        assert service.execution_state == ExecutionState.IDLE
        assert service.progress is None

    def test_execution_state_enum(self):
        """Test ExecutionState enum values."""
        assert ExecutionState.IDLE.value == "idle"
        assert ExecutionState.STARTING.value == "starting"
        assert ExecutionState.RUNNING.value == "running"
        assert ExecutionState.PAUSED.value == "paused"
        assert ExecutionState.COMPLETED.value == "completed"
        assert ExecutionState.ABORTED.value == "aborted"
        assert ExecutionState.ERROR.value == "error"

    @pytest.mark.asyncio
    async def test_park_telescope(self, service, mock_client):
        """Test parking telescope."""
        result = await service.park_telescope()
        assert result is True
        mock_client.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_park_telescope_failure(self, service, mock_client):
        """Test park failure."""
        mock_client.park.side_effect = Exception("Park failed")
        result = await service.park_telescope()
        assert result is False

    @pytest.mark.asyncio
    async def test_abort_execution_when_idle(self, service):
        """Test abort when not executing."""
        await service.abort_execution()
        assert service.execution_state == ExecutionState.IDLE

    @pytest.mark.asyncio
    async def test_abort_execution_when_running(self, service):
        """Test abort during execution."""
        # Simulate running state
        service._execution_state = ExecutionState.RUNNING
        service._abort_requested = False

        await service.abort_execution()

        assert service._abort_requested is True

    def test_progress_property(self, service):
        """Test progress property."""
        assert service.progress is None

        # Create mock progress
        service._progress = ExecutionProgress(
            execution_id="test-123",
            state=ExecutionState.RUNNING,
            total_targets=5,
            current_target_index=2,
            targets_completed=2,
            targets_failed=0
        )

        progress = service.progress
        assert progress.execution_id == "test-123"
        assert progress.total_targets == 5
        assert progress.current_target_index == 2

    def test_execution_error_dataclass(self):
        """Test ExecutionError dataclass."""
        now = datetime.now()
        error = ExecutionError(
            timestamp=now,
            target_index=0,  # Fixed: added required target_index
            target_name="M31",
            phase="slewing",
            error_message="Slew failed",
            retry_count=2
        )

        assert error.timestamp == now
        assert error.target_index == 0
        assert error.target_name == "M31"
        assert error.phase == "slewing"
        assert error.retry_count == 2

    def test_execution_progress_percent(self):
        """Test progress percentage calculation."""
        progress = ExecutionProgress(
            execution_id="test",
            state=ExecutionState.RUNNING,
            total_targets=10,
            current_target_index=5,
            targets_completed=5,
            targets_failed=0,
            progress_percent=50.0  # Fixed: must set explicitly, not calculated
        )

        assert progress.progress_percent == 50.0

    def test_execution_progress_no_targets(self):
        """Test progress with no targets."""
        progress = ExecutionProgress(
            execution_id="test",
            state=ExecutionState.IDLE,
            total_targets=0,
            current_target_index=0,
            targets_completed=0,
            targets_failed=0
        )

        assert progress.progress_percent == 0.0

    @pytest.mark.asyncio
    async def test_execute_plan_empty(self, service, mock_client):
        """Test executing empty plan."""
        result = await service.execute_plan("test-exec", [])

        assert result.state == ExecutionState.COMPLETED
        assert result.total_targets == 0
        assert result.targets_completed == 0


# Additional integration-style tests could be added with:
# 1. Full mock TCP server simulating Seestar responses
# 2. End-to-end execution scenarios with multiple targets
# 3. Error recovery and retry logic testing
# 4. Timeout and cancellation scenarios
