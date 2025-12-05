"""Seestar S50 TCP client for direct telescope control.

This module provides a low-level client for communicating with the Seestar S50
smart telescope over TCP sockets using its native JSON protocol.

Protocol documentation: docs/seestar-protocol-spec.md
"""

import asyncio
import json
import logging
import socket
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional


class SeestarState(Enum):
    """Telescope operation states."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    SLEWING = "slewing"
    TRACKING = "tracking"
    FOCUSING = "focusing"
    IMAGING = "imaging"
    PARKING = "parking"
    PARKED = "parked"
    ERROR = "error"


@dataclass
class SeestarStatus:
    """Current telescope status."""

    connected: bool
    state: SeestarState
    current_ra_hours: Optional[float] = None
    current_dec_degrees: Optional[float] = None
    current_target: Optional[str] = None
    firmware_version: Optional[str] = None
    is_tracking: bool = False
    last_error: Optional[str] = None
    last_update: Optional[datetime] = None


class SeestarClientError(Exception):
    """Base exception for Seestar client errors."""

    pass


class ConnectionError(SeestarClientError):
    """Raised when connection to telescope fails."""

    pass


class CommandError(SeestarClientError):
    """Raised when a telescope command fails."""

    pass


class TimeoutError(SeestarClientError):
    """Raised when a command times out."""

    pass


class SeestarClient:
    """TCP client for Seestar S50 smart telescope.

    Provides low-level communication with the Seestar S50 using its native
    JSON-over-TCP protocol. Handles message formatting, ID tracking, and
    response matching.

    Example usage:
        client = SeestarClient()
        await client.connect("seestar.local")
        await client.goto_target(12.5, 45.3, "M31")
        await client.start_imaging()
        # ... image for some time ...
        await client.stop_imaging()
        await client.disconnect()
    """

    DEFAULT_PORT = 4700  # Port 4700 for firmware v5.x (was 5555 for v4.x)
    UDP_DISCOVERY_PORT = 4720
    CONNECTION_TIMEOUT = 10.0
    COMMAND_TIMEOUT = 10.0
    RECEIVE_BUFFER_SIZE = 4096

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize Seestar client.

        Args:
            logger: Optional logger instance. If None, creates default logger.
        """
        self.logger = logger or logging.getLogger(__name__)

        # Connection state
        self._socket: Optional[socket.socket] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._host: Optional[str] = None
        self._port = self.DEFAULT_PORT

        # Message handling
        self._command_id = 10000  # Start at 10000 like seestar_alp
        self._pending_responses: Dict[int, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None

        # State tracking
        self._status = SeestarStatus(connected=False, state=SeestarState.DISCONNECTED)
        self._operation_states: Dict[str, str] = {}

        # Callbacks
        self._status_callback: Optional[Callable[[SeestarStatus], None]] = None

    @property
    def connected(self) -> bool:
        """Check if connected to telescope."""
        return self._connected

    @property
    def status(self) -> SeestarStatus:
        """Get current telescope status."""
        return self._status

    def set_status_callback(self, callback: Callable[[SeestarStatus], None]) -> None:
        """Set callback function for status updates.

        Args:
            callback: Function to call when status changes
        """
        self._status_callback = callback

    def _update_status(self, **kwargs) -> None:
        """Update internal status and trigger callback."""
        for key, value in kwargs.items():
            if hasattr(self._status, key):
                setattr(self._status, key, value)

        self._status.last_update = datetime.now()

        if self._status_callback:
            try:
                self._status_callback(self._status)
            except Exception as e:
                self.logger.error(f"Error in status callback: {e}")

    async def _send_udp_discovery(self) -> None:
        """Send UDP discovery broadcast for guest mode."""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1.0)

            # Send discovery message
            message = {"id": 1, "method": "scan_iscope", "params": ""}
            message_bytes = json.dumps(message).encode()

            addr = (self._host, self.UDP_DISCOVERY_PORT)
            self.logger.info(f"Sending UDP discovery to {addr}")
            sock.sendto(message_bytes, addr)

            # Try to receive response (optional)
            try:
                data, addr = sock.recvfrom(1024)
                self.logger.info(f"Received UDP response from {addr}: {data.decode()}")
            except socket.timeout:
                self.logger.debug("No UDP response (this is normal)")

            sock.close()

        except Exception as e:
            self.logger.warning(f"UDP discovery failed (non-critical): {e}")

    async def connect(self, host: str, port: int = DEFAULT_PORT) -> bool:
        """Connect to Seestar S50 telescope.

        Args:
            host: Hostname or IP address (e.g., "seestar.local" or "192.168.1.100")
            port: TCP port (default: 4700 for firmware v5.x)

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            self.logger.warning("Already connected")
            return True

        self._host = host
        self._port = port

        try:
            # Send UDP discovery first (for guest mode)
            await self._send_udp_discovery()

            # Establish TCP connection
            self.logger.info(f"Connecting to Seestar at {host}:{port}")

            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=self.CONNECTION_TIMEOUT
            )

            self._connected = True
            self._update_status(connected=True, state=SeestarState.CONNECTED)

            # Start receive task
            self._receive_task = asyncio.create_task(self._receive_loop())

            self.logger.info("Connected to Seestar S50")

            # Query initial status
            try:
                await self.get_device_state()
            except Exception as e:
                self.logger.warning(f"Failed to get initial device state: {e}")

            return True

        except asyncio.TimeoutError:
            raise ConnectionError(f"Connection timeout to {host}:{port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {host}:{port}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from telescope."""
        if not self._connected:
            return

        self.logger.info("Disconnecting from Seestar")

        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Close writer
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self._connected = False
        self._reader = None
        self._writer = None
        self._pending_responses.clear()

        self._update_status(connected=False, state=SeestarState.DISCONNECTED)

        self.logger.info("Disconnected from Seestar")

    async def _receive_loop(self) -> None:
        """Background task to receive and process messages from telescope."""
        try:
            while self._connected:
                # Read until newline
                line = await self._reader.readline()
                if not line:
                    self.logger.error("Connection closed by telescope")
                    break

                # Parse message
                try:
                    message = json.loads(line.decode().strip())
                    await self._handle_message(message)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON received: {line}, error: {e}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")

        except asyncio.CancelledError:
            self.logger.debug("Receive loop cancelled")
        except Exception as e:
            self.logger.error(f"Receive loop error: {e}")
            self._update_status(state=SeestarState.ERROR, last_error=str(e))
        finally:
            if self._connected:
                await self.disconnect()

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Process received message from telescope.

        Args:
            message: Parsed JSON message
        """
        # Log message
        method = message.get("method", "unknown")
        msg_id = message.get("id")

        if method == "scope_get_equ_coord":
            self.logger.debug(f"Received: {message}")
        else:
            self.logger.info(f"Received: {message}")

        # Check if this is a response to a pending command
        if msg_id is not None and msg_id in self._pending_responses:
            future = self._pending_responses.pop(msg_id)
            if not future.done():
                future.set_result(message)

        # Update internal state based on events
        # (Could parse Event messages here if needed)

    async def _send_command(self, method: str, params: Any = None, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Send command to telescope and wait for response.

        Args:
            method: Command method name
            params: Command parameters (dict, list, or None)
            timeout: Command timeout in seconds (default: COMMAND_TIMEOUT)

        Returns:
            Response message dict

        Raises:
            ConnectionError: If not connected
            TimeoutError: If command times out
            CommandError: If command returns error
        """
        if not self._connected:
            raise ConnectionError("Not connected to telescope")

        # Generate command ID
        cmd_id = self._command_id
        self._command_id += 1

        # Build message
        message = {"method": method, "id": cmd_id}
        if params is not None:
            message["params"] = params

        # Create future for response
        future = asyncio.Future()
        self._pending_responses[cmd_id] = future

        # Send message
        message_json = json.dumps(message) + "\r\n"

        if method == "scope_get_equ_coord":
            self.logger.debug(f"Sending: {message_json.strip()}")
        else:
            self.logger.info(f"Sending: {message_json.strip()}")

        try:
            self._writer.write(message_json.encode())
            await self._writer.drain()
        except Exception as e:
            self._pending_responses.pop(cmd_id, None)
            raise ConnectionError(f"Failed to send command: {e}")

        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=timeout or self.COMMAND_TIMEOUT)
        except asyncio.TimeoutError:
            self._pending_responses.pop(cmd_id, None)
            raise TimeoutError(f"Command timeout: {method}")

        # Check for error in response
        if "error" in response:
            error_msg = response.get("error", "Unknown error")
            error_code = response.get("code", 0)
            raise CommandError(f"Command failed: {error_msg} (code {error_code})")

        return response

    # ========================================================================
    # Telescope Control Commands
    # ========================================================================

    async def goto_target(
        self, ra_hours: float, dec_degrees: float, target_name: str = "Target", use_lp_filter: bool = False
    ) -> bool:
        """Slew telescope to target and start viewing.

        Args:
            ra_hours: Right ascension in decimal hours (0-24)
            dec_degrees: Declination in decimal degrees (-90 to 90)
            target_name: Name of target for display
            use_lp_filter: Whether to use light pollution filter

        Returns:
            True if goto initiated successfully

        Raises:
            CommandError: If goto command fails
        """
        self.logger.info(f"Goto target: {target_name} at RA={ra_hours}h, Dec={dec_degrees}°")

        params = {
            "mode": "star",
            "target_ra_dec": [ra_hours, dec_degrees],
            "target_name": target_name,
            "lp_filter": use_lp_filter,
        }

        self._update_status(state=SeestarState.SLEWING, current_target=target_name)

        response = await self._send_command("iscope_start_view", params)

        self.logger.info(f"Goto response: {response}")
        return response.get("result") == 0

    async def start_imaging(self, restart: bool = True) -> bool:
        """Start stacking/imaging.

        Args:
            restart: Whether to restart stacking from scratch

        Returns:
            True if imaging started successfully

        Raises:
            CommandError: If start imaging fails
        """
        self.logger.info(f"Starting imaging (restart={restart})")

        params = {"restart": restart}

        self._update_status(state=SeestarState.IMAGING)

        response = await self._send_command("iscope_start_stack", params)

        self.logger.info(f"Start imaging response: {response}")
        return response.get("result") == 0

    async def stop_imaging(self) -> bool:
        """Stop current imaging/stacking.

        Returns:
            True if stop successful

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping imaging")

        params = {"stage": "Stack"}

        self._update_status(state=SeestarState.TRACKING)

        response = await self._send_command("iscope_stop_view", params)

        self.logger.info(f"Stop imaging response: {response}")
        return response.get("result") == 0

    async def stop_slew(self) -> bool:
        """Stop current slew/goto operation.

        Returns:
            True if stop successful

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping slew")

        params = {"stage": "AutoGoto"}

        response = await self._send_command("iscope_stop_view", params)

        self.logger.info(f"Stop slew response: {response}")
        return response.get("result") == 0

    async def auto_focus(self) -> bool:
        """Perform automatic focusing.

        Returns:
            True if focus initiated successfully

        Raises:
            CommandError: If focus command fails
        """
        self.logger.info("Starting auto focus")

        self._update_status(state=SeestarState.FOCUSING)

        response = await self._send_command("start_auto_focuse")

        self.logger.info(f"Auto focus response: {response}")
        return response.get("result") == 0

    async def park(self) -> bool:
        """Park telescope at home position.

        Returns:
            True if park initiated successfully

        Raises:
            CommandError: If park command fails
        """
        self.logger.info("Parking telescope")

        self._update_status(state=SeestarState.PARKING)

        response = await self._send_command("scope_park")

        self.logger.info(f"Park response: {response}")
        return response.get("result") == 0

    async def get_device_state(self, keys: Optional[list] = None) -> Dict[str, Any]:
        """Get current device state.

        Args:
            keys: Optional list of specific keys to query

        Returns:
            Device state dict

        Raises:
            CommandError: If query fails
        """
        params = {"keys": keys} if keys else {}

        response = await self._send_command("get_device_state", params)

        result = response.get("result", {})

        # Update internal status from result
        if "device" in result:
            device = result["device"]
            if "firmware_ver_string" in device:
                self._update_status(firmware_version=device["firmware_ver_string"])

        return result

    async def set_exposure(self, stack_exposure_ms: int = 10000, continuous_exposure_ms: int = 500) -> bool:
        """Set exposure times.

        Args:
            stack_exposure_ms: Stacking exposure in milliseconds (default: 10000 = 10s)
            continuous_exposure_ms: Continuous/preview exposure in ms (default: 500)

        Returns:
            True if setting successful

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting exposure: stack={stack_exposure_ms}ms, continuous={continuous_exposure_ms}ms")

        params = {"exp_ms": {"stack_l": stack_exposure_ms, "continuous": continuous_exposure_ms}}

        response = await self._send_command("set_setting", params)

        self.logger.info(f"Set exposure response: {response}")
        return response.get("result") == 0

    async def configure_dither(self, enabled: bool = True, pixels: int = 50, interval: int = 10) -> bool:
        """Configure dithering settings.

        Args:
            enabled: Whether dithering is enabled
            pixels: Dither distance in pixels
            interval: Number of frames between dither

        Returns:
            True if setting successful

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Configuring dither: enabled={enabled}, pixels={pixels}, interval={interval}")

        params = {"stack_dither": {"enable": enabled, "pix": pixels, "interval": interval}}

        response = await self._send_command("set_setting", params)

        self.logger.info(f"Configure dither response: {response}")
        return response.get("result") == 0
