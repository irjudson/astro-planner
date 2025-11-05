"""Telescope service for orchestrating observation plan execution.

This service provides high-level control of the Seestar S50 telescope,
coordinating the execution of scheduled observation plans.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from app.clients.seestar_client import SeestarClient, SeestarState, CommandError, TimeoutError as SeestarTimeoutError
from app.models import ScheduledTarget


class ExecutionState(Enum):
    """Execution state for observation plan."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass
class ExecutionError:
    """Error encountered during execution."""
    timestamp: datetime
    target_index: int
    target_name: str
    phase: str  # "goto", "focus", "imaging", etc.
    error_message: str
    retry_count: int = 0


@dataclass
class TargetProgress:
    """Progress tracking for a single target."""
    target: ScheduledTarget
    index: int
    started: bool = False
    goto_completed: bool = False
    focus_completed: bool = False
    imaging_started: bool = False
    imaging_completed: bool = False
    actual_exposures: int = 0
    errors: List[ExecutionError] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class ExecutionProgress:
    """Overall execution progress."""
    execution_id: str
    state: ExecutionState
    total_targets: int
    current_target_index: int
    targets_completed: int
    targets_failed: int
    current_target_name: Optional[str] = None
    current_phase: Optional[str] = None
    progress_percent: float = 0.0
    start_time: Optional[datetime] = None
    estimated_end_time: Optional[datetime] = None
    elapsed_time: Optional[timedelta] = None
    estimated_remaining: Optional[timedelta] = None
    errors: List[ExecutionError] = field(default_factory=list)
    target_progress: List[TargetProgress] = field(default_factory=list)


class TelescopeService:
    """High-level service for telescope control and plan execution.

    Orchestrates observation plan execution by coordinating goto, focus,
    and imaging operations for each scheduled target.
    """

    # Execution parameters
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds
    FOCUS_TIMEOUT = 120.0  # 2 minutes
    GOTO_TIMEOUT = 180.0  # 3 minutes
    SETTLE_TIME = 2.0  # seconds to settle after operations

    def __init__(self, client: SeestarClient, logger: Optional[logging.Logger] = None):
        """Initialize telescope service.

        Args:
            client: Connected Seestar client instance
            logger: Optional logger instance
        """
        self.client = client
        self.logger = logger or logging.getLogger(__name__)

        # Execution state
        self._execution_id: Optional[str] = None
        self._execution_state = ExecutionState.IDLE
        self._execution_task: Optional[asyncio.Task] = None
        self._targets: List[ScheduledTarget] = []
        self._progress: Optional[ExecutionProgress] = None
        self._abort_requested = False

        # Callbacks
        self._progress_callback: Optional[Callable[[ExecutionProgress], None]] = None

    @property
    def execution_state(self) -> ExecutionState:
        """Get current execution state."""
        return self._execution_state

    @property
    def progress(self) -> Optional[ExecutionProgress]:
        """Get current execution progress."""
        return self._progress

    def set_progress_callback(self, callback: Callable[[ExecutionProgress], None]) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function to call when progress changes
        """
        self._progress_callback = callback

    def _update_progress(self, **kwargs) -> None:
        """Update execution progress and trigger callback."""
        if not self._progress:
            return

        for key, value in kwargs.items():
            if hasattr(self._progress, key):
                setattr(self._progress, key, value)

        # Calculate elapsed and remaining time
        if self._progress.start_time:
            self._progress.elapsed_time = datetime.now() - self._progress.start_time

            # Estimate remaining time based on progress
            if self._progress.progress_percent > 0:
                total_estimated = self._progress.elapsed_time / (self._progress.progress_percent / 100.0)
                self._progress.estimated_remaining = total_estimated - self._progress.elapsed_time
                self._progress.estimated_end_time = datetime.now() + self._progress.estimated_remaining

        # Trigger callback
        if self._progress_callback:
            try:
                self._progress_callback(self._progress)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")

    async def execute_plan(
        self,
        execution_id: str,
        targets: List[ScheduledTarget],
        configure_settings: bool = True,
        park_when_done: bool = True
    ) -> ExecutionProgress:
        """Execute an observation plan.

        Args:
            execution_id: Unique ID for this execution
            targets: List of scheduled targets to execute
            configure_settings: Whether to configure telescope settings first

        Returns:
            Final execution progress

        Raises:
            ValueError: If execution is already running
        """
        if self._execution_state not in [ExecutionState.IDLE, ExecutionState.COMPLETED, ExecutionState.ABORTED, ExecutionState.ERROR]:
            raise ValueError(f"Cannot start execution: current state is {self._execution_state}")

        self.logger.info(f"Starting execution {execution_id} with {len(targets)} targets")

        # Initialize execution state
        self._execution_id = execution_id
        self._targets = targets
        self._abort_requested = False

        self._progress = ExecutionProgress(
            execution_id=execution_id,
            state=ExecutionState.STARTING,
            total_targets=len(targets),
            current_target_index=-1,
            targets_completed=0,
            targets_failed=0,
            start_time=datetime.now(),
            target_progress=[
                TargetProgress(target=target, index=i)
                for i, target in enumerate(targets)
            ]
        )

        self._execution_state = ExecutionState.STARTING
        self._update_progress(state=ExecutionState.STARTING)

        try:
            # Configure telescope if requested
            if configure_settings:
                await self._configure_telescope()

            # Execute each target
            self._execution_state = ExecutionState.RUNNING
            self._update_progress(state=ExecutionState.RUNNING)

            for i, target in enumerate(targets):
                if self._abort_requested:
                    self.logger.info("Execution aborted by user")
                    self._execution_state = ExecutionState.ABORTED
                    self._update_progress(state=ExecutionState.ABORTED)
                    break

                self._update_progress(
                    current_target_index=i,
                    current_target_name=target.target.name,
                    progress_percent=(i / len(targets)) * 100.0
                )

                # Execute target
                success = await self._execute_target(i, target)

                if success:
                    self._progress.targets_completed += 1
                else:
                    self._progress.targets_failed += 1

                self._update_progress(
                    targets_completed=self._progress.targets_completed,
                    targets_failed=self._progress.targets_failed
                )

            # Execution complete
            if self._execution_state == ExecutionState.RUNNING:
                self._execution_state = ExecutionState.COMPLETED
                self._update_progress(
                    state=ExecutionState.COMPLETED,
                    progress_percent=100.0
                )

            # Park telescope if requested
            if park_when_done and self._execution_state == ExecutionState.COMPLETED:
                self.logger.info("Parking telescope as requested")
                self._update_progress(current_phase="Parking telescope")
                try:
                    await self.park_telescope()
                    self.logger.info("Telescope parked successfully")
                except Exception as e:
                    self.logger.warning(f"Failed to park telescope: {e}")

            self.logger.info(
                f"Execution {execution_id} finished: "
                f"{self._progress.targets_completed} completed, "
                f"{self._progress.targets_failed} failed"
            )

        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            self._execution_state = ExecutionState.ERROR
            self._update_progress(state=ExecutionState.ERROR)

        return self._progress

    async def _configure_telescope(self) -> None:
        """Configure telescope settings before execution."""
        self.logger.info("Configuring telescope settings")
        self._update_progress(current_phase="Configuring telescope")

        try:
            # Set exposure time (10 seconds for stacking)
            await self.client.set_exposure(stack_exposure_ms=10000)

            # Configure dithering
            await self.client.configure_dither(
                enabled=True,
                pixels=50,
                interval=10
            )

            self.logger.info("Telescope configuration complete")

        except Exception as e:
            self.logger.warning(f"Failed to configure telescope: {e}")

    async def _execute_target(self, index: int, target: ScheduledTarget) -> bool:
        """Execute a single scheduled target.

        Args:
            index: Target index in execution plan
            target: Scheduled target to execute

        Returns:
            True if target executed successfully
        """
        target_progress = self._progress.target_progress[index]
        target_progress.started = True
        target_progress.start_time = datetime.now()

        self.logger.info(
            f"Executing target {index + 1}/{len(self._targets)}: "
            f"{target.target.name} ({target.target.catalog_id})"
        )

        try:
            # Phase 1: Goto target
            self._update_progress(current_phase="Slewing to target")
            if not await self._goto_target_with_retry(target_progress, target):
                return False

            # Phase 2: Auto focus
            self._update_progress(current_phase="Auto focusing")
            if not await self._auto_focus_with_retry(target_progress):
                return False

            # Phase 3: Image target
            self._update_progress(current_phase="Imaging")
            if not await self._image_target_with_retry(target_progress, target):
                return False

            # Success!
            target_progress.end_time = datetime.now()
            self.logger.info(f"Target {target.target.name} completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to execute target {target.target.name}: {e}")
            error = ExecutionError(
                timestamp=datetime.now(),
                target_index=index,
                target_name=target.target.name,
                phase="execution",
                error_message=str(e)
            )
            target_progress.errors.append(error)
            self._progress.errors.append(error)
            return False

    async def _goto_target_with_retry(
        self,
        progress: TargetProgress,
        target: ScheduledTarget
    ) -> bool:
        """Goto target with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                await self.client.goto_target(
                    ra_hours=target.target.ra_hours,
                    dec_degrees=target.target.dec_degrees,
                    target_name=target.target.name
                )

                # Wait for goto to complete (simplified - would monitor state in production)
                await asyncio.sleep(self.SETTLE_TIME)

                progress.goto_completed = True
                self.logger.info(f"Goto completed for {target.target.name}")
                return True

            except (CommandError, SeestarTimeoutError) as e:
                self.logger.warning(f"Goto attempt {attempt + 1} failed: {e}")

                error = ExecutionError(
                    timestamp=datetime.now(),
                    target_index=progress.index,
                    target_name=target.target.name,
                    phase="goto",
                    error_message=str(e),
                    retry_count=attempt
                )
                progress.errors.append(error)

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    self._progress.errors.append(error)
                    return False

        return False

    async def _auto_focus_with_retry(self, progress: TargetProgress) -> bool:
        """Auto focus with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                await self.client.auto_focus()

                # Wait for focus to complete (simplified)
                await asyncio.sleep(self.SETTLE_TIME)

                progress.focus_completed = True
                self.logger.info("Auto focus completed")
                return True

            except (CommandError, SeestarTimeoutError) as e:
                self.logger.warning(f"Focus attempt {attempt + 1} failed: {e}")

                error = ExecutionError(
                    timestamp=datetime.now(),
                    target_index=progress.index,
                    target_name=progress.target.target.name,
                    phase="focus",
                    error_message=str(e),
                    retry_count=attempt
                )
                progress.errors.append(error)

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    self._progress.errors.append(error)
                    return False

        return False

    async def _image_target_with_retry(
        self,
        progress: TargetProgress,
        target: ScheduledTarget
    ) -> bool:
        """Image target with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                # Start imaging
                await self.client.start_imaging(restart=True)
                progress.imaging_started = True

                # Image for specified duration
                duration_seconds = target.duration.total_seconds()
                self.logger.info(f"Imaging for {duration_seconds}s")

                # Wait for imaging duration
                # In production, would monitor state and count exposures
                await asyncio.sleep(duration_seconds)

                # Stop imaging
                await self.client.stop_imaging()

                progress.imaging_completed = True
                progress.actual_exposures = target.exposure_count
                self.logger.info("Imaging completed")
                return True

            except (CommandError, SeestarTimeoutError) as e:
                self.logger.warning(f"Imaging attempt {attempt + 1} failed: {e}")

                error = ExecutionError(
                    timestamp=datetime.now(),
                    target_index=progress.index,
                    target_name=progress.target.target.name,
                    phase="imaging",
                    error_message=str(e),
                    retry_count=attempt
                )
                progress.errors.append(error)

                if attempt < self.MAX_RETRIES - 1:
                    # Try to stop imaging before retry
                    try:
                        await self.client.stop_imaging()
                    except:
                        pass

                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    self._progress.errors.append(error)
                    return False

        return False

    async def abort_execution(self) -> None:
        """Abort current execution."""
        if self._execution_state not in [ExecutionState.RUNNING, ExecutionState.STARTING]:
            self.logger.warning(f"Cannot abort: execution state is {self._execution_state}")
            return

        self.logger.info("Aborting execution")
        self._abort_requested = True

        # Stop current imaging if running
        try:
            await self.client.stop_imaging()
        except:
            pass

        self._execution_state = ExecutionState.ABORTED
        self._update_progress(state=ExecutionState.ABORTED)

    async def park_telescope(self) -> bool:
        """Park telescope at home position.

        Returns:
            True if park successful
        """
        try:
            await self.client.park()
            return True
        except Exception as e:
            self.logger.error(f"Failed to park telescope: {e}")
            return False
