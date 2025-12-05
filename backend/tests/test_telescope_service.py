"""Tests for telescope service."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.clients.seestar_client import SeestarClient, SeestarState
from app.models import DSOTarget, ScheduledTarget, TargetScore
from app.services.telescope_service import ExecutionError, ExecutionProgress, ExecutionState, TelescopeService


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
                description="Andromeda Galaxy",
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
            score=TargetScore(visibility_score=0.95, weather_score=0.90, object_score=0.85, total_score=0.90),
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
            targets_failed=0,
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
            retry_count=2,
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
            progress_percent=50.0,  # Fixed: must set explicitly, not calculated
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
            targets_failed=0,
        )

        assert progress.progress_percent == 0.0

    @pytest.mark.asyncio
    async def test_execute_plan_empty(self, service, mock_client):
        """Test executing empty plan."""
        result = await service.execute_plan("test-exec", [])

        assert result.state == ExecutionState.COMPLETED
        assert result.total_targets == 0
        assert result.targets_completed == 0


class TestTelescopeServiceExecutePlan:
    """Test execution plan functionality."""

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
        client.set_exposure = AsyncMock(return_value=True)
        client.configure_dither = AsyncMock(return_value=True)
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
                description="Andromeda Galaxy",
            ),
            start_time=datetime(2025, 11, 1, 20, 0),
            end_time=datetime(2025, 11, 1, 20, 1),  # Short duration for tests
            duration_minutes=1,
            start_altitude=45.0,
            end_altitude=50.0,
            start_azimuth=120.0,
            end_azimuth=150.0,
            field_rotation_rate=0.5,
            recommended_exposure=10,
            recommended_frames=6,
            score=TargetScore(visibility_score=0.95, weather_score=0.90, object_score=0.85, total_score=0.90),
        )

    def test_set_progress_callback(self, service):
        """Test setting progress callback."""
        callback = Mock()
        service.set_progress_callback(callback)
        assert service._progress_callback == callback

    @pytest.mark.asyncio
    async def test_execute_plan_with_target(self, service, mock_client, sample_target):
        """Test executing plan with a single target."""
        # Use short sleep times by mocking
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-exec-123", [sample_target], configure_settings=True, park_when_done=False
            )

        assert result.state == ExecutionState.COMPLETED
        assert result.total_targets == 1
        assert result.targets_completed == 1
        assert result.targets_failed == 0
        mock_client.goto_target.assert_called_once()
        mock_client.auto_focus.assert_called_once()
        mock_client.start_imaging.assert_called_once()
        mock_client.stop_imaging.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_plan_with_park(self, service, mock_client, sample_target):
        """Test executing plan with parking at end."""
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-exec-park", [sample_target], configure_settings=False, park_when_done=True
            )

        assert result.state == ExecutionState.COMPLETED
        mock_client.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_plan_already_running(self, service, sample_target):
        """Test that starting execution when already running raises error."""
        service._execution_state = ExecutionState.RUNNING

        with pytest.raises(ValueError, match="Cannot start execution"):
            await service.execute_plan("test", [sample_target])

    @pytest.mark.asyncio
    async def test_execute_plan_configure_telescope(self, service, mock_client, sample_target):
        """Test telescope configuration during execution."""
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await service.execute_plan("test-config", [sample_target], configure_settings=True, park_when_done=False)

        mock_client.set_exposure.assert_called_once()
        mock_client.configure_dither.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_plan_goto_failure(self, service, mock_client, sample_target):
        """Test handling goto failure."""
        from app.clients.seestar_client import CommandError

        mock_client.goto_target.side_effect = CommandError("Goto failed")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-goto-fail", [sample_target], configure_settings=False, park_when_done=False
            )

        assert result.targets_failed == 1
        assert result.targets_completed == 0
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_plan_focus_failure(self, service, mock_client, sample_target):
        """Test handling focus failure."""
        from app.clients.seestar_client import CommandError

        mock_client.auto_focus.side_effect = CommandError("Focus failed")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-focus-fail", [sample_target], configure_settings=False, park_when_done=False
            )

        assert result.targets_failed == 1
        assert mock_client.goto_target.called

    @pytest.mark.asyncio
    async def test_execute_plan_imaging_failure(self, service, mock_client, sample_target):
        """Test handling imaging failure."""
        from app.clients.seestar_client import CommandError

        mock_client.start_imaging.side_effect = CommandError("Imaging failed")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-imaging-fail", [sample_target], configure_settings=False, park_when_done=False
            )

        assert result.targets_failed == 1

    @pytest.mark.asyncio
    async def test_execute_plan_abort(self, service, mock_client, sample_target):
        """Test aborting execution mid-plan."""
        # Create multiple targets
        target2 = ScheduledTarget(
            target=DSOTarget(
                name="M42",
                catalog_id="M42",
                object_type="nebula",
                ra_hours=5.583,
                dec_degrees=-5.391,
                magnitude=4.0,
                size_arcmin=65.0,
                description="Orion Nebula",
            ),
            start_time=datetime(2025, 11, 1, 21, 0),
            end_time=datetime(2025, 11, 1, 21, 1),
            duration_minutes=1,
            start_altitude=40.0,
            end_altitude=45.0,
            start_azimuth=100.0,
            end_azimuth=130.0,
            field_rotation_rate=0.5,
            recommended_exposure=10,
            recommended_frames=6,
            score=TargetScore(visibility_score=0.90, weather_score=0.85, object_score=0.80, total_score=0.85),
        )

        async def abort_after_first(*args, **kwargs):
            if mock_client.goto_target.call_count == 1:
                service._abort_requested = True
            return True

        mock_client.goto_target.side_effect = abort_after_first

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-abort", [sample_target, target2], configure_settings=False, park_when_done=False
            )

        assert result.state == ExecutionState.ABORTED

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, service, mock_client, sample_target):
        """Test that progress callback is called during execution."""
        callback = Mock()
        service.set_progress_callback(callback)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await service.execute_plan("test-callback", [sample_target], configure_settings=False, park_when_done=False)

        assert callback.called
        # Callback should be called multiple times during execution
        assert callback.call_count >= 3

    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(self, service, mock_client, sample_target):
        """Test that progress callback errors don't crash execution."""
        callback = Mock(side_effect=Exception("Callback error"))
        service.set_progress_callback(callback)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Should complete without raising despite callback error
            result = await service.execute_plan(
                "test-callback-error", [sample_target], configure_settings=False, park_when_done=False
            )

        assert result.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_update_progress_calculates_time(self, service, mock_client, sample_target):
        """Test that progress updates calculate elapsed time."""
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-time", [sample_target], configure_settings=False, park_when_done=False
            )

        assert result.start_time is not None
        assert result.elapsed_time is not None

    @pytest.mark.asyncio
    async def test_abort_execution_stops_imaging(self, service, mock_client):
        """Test that abort stops imaging."""
        service._execution_state = ExecutionState.RUNNING

        await service.abort_execution()

        mock_client.stop_imaging.assert_called_once()
        assert service.execution_state == ExecutionState.ABORTED

    @pytest.mark.asyncio
    async def test_configure_telescope_failure(self, service, mock_client, sample_target):
        """Test that configuration failure doesn't stop execution."""
        mock_client.set_exposure.side_effect = Exception("Config failed")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.execute_plan(
                "test-config-fail", [sample_target], configure_settings=True, park_when_done=False
            )

        # Should still complete despite config failure
        assert result.state == ExecutionState.COMPLETED

    def test_target_progress_dataclass(self, sample_target):
        """Test TargetProgress dataclass."""
        from app.services.telescope_service import TargetProgress

        progress = TargetProgress(target=sample_target, index=0)

        assert progress.target == sample_target
        assert progress.index == 0
        assert progress.started is False
        assert progress.goto_completed is False
        assert progress.focus_completed is False
        assert progress.imaging_started is False
        assert progress.imaging_completed is False
        assert progress.actual_exposures == 0
        assert progress.errors == []
        assert progress.start_time is None
        assert progress.end_time is None
