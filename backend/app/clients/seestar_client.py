"""Seestar S50 TCP client for direct telescope control.

This module provides a low-level client for communicating with the Seestar S50
smart telescope over TCP sockets using its native JSON protocol.

Protocol documentation: docs/seestar-protocol-spec.md
"""

import asyncio
import base64
import json
import logging
import socket
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


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

    DEFAULT_PORT = 4700  # Port 4700 for firmware v6.x JSON-RPC
    UDP_DISCOVERY_PORT = 4720
    CONNECTION_TIMEOUT = 10.0
    COMMAND_TIMEOUT = 10.0
    RECEIVE_BUFFER_SIZE = 4096

    # RSA private key for firmware 6.45+ authentication
    # This key is embedded in the Seestar app's native library and used for signing challenges
    SEESTAR_RSA_KEY_REMOVED_FROM_HISTORY = """-----BEGIN PRIVATE KEY-----
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
-----END PRIVATE KEY-----"""

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

    def _sign_challenge(self, challenge_str: str) -> str:
        """Sign authentication challenge using RSA private key.

        This implements the authentication mechanism required by firmware 6.45+.
        The challenge is signed (not encrypted) using RSA-SHA1.

        Args:
            challenge_str: Challenge string from get_verify_str

        Returns:
            Base64-encoded signature
        """
        # Load the private key
        private_key = serialization.load_pem_private_key(
            self.SEESTAR_RSA_KEY_REMOVED_FROM_HISTORY.encode(), password=None, backend=default_backend()
        )

        # Sign the challenge using RSA-SHA1 (required by Seestar firmware protocol)
        # nosec B303 - SHA1 used for RSA signing (not password hashing), required by hardware
        signature = private_key.sign(challenge_str.encode("utf-8"), padding.PKCS1v15(), hashes.SHA1())

        # Return base64-encoded signature
        return base64.b64encode(signature).decode("utf-8")

    async def _authenticate(self) -> None:
        """Perform 2-step authentication for firmware 6.45+.

        Step 1: Request challenge string via get_verify_str
        Step 2: Sign challenge and send via verify_client

        Raises:
            ConnectionError: If authentication fails
        """
        try:
            # Step 1: Get challenge string
            self.logger.info("Requesting authentication challenge...")
            challenge_response = await self._send_command("get_verify_str")

            challenge_str = challenge_response.get("result", {}).get("str", "")
            if not challenge_str:
                raise ConnectionError(f"No challenge string in response: {challenge_response}")

            self.logger.debug(f"Received challenge: {challenge_str}")

            # Step 2: Sign challenge and send verification
            self.logger.info("Signing challenge and authenticating...")
            signed_challenge = self._sign_challenge(challenge_str)

            verify_params = {"sign": signed_challenge, "data": challenge_str}

            verify_response = await self._send_command("verify_client", verify_params)

            # Check result
            result_code = verify_response.get("result", verify_response.get("code", -1))
            if result_code != 0:
                error = verify_response.get("error", "unknown error")
                raise ConnectionError(f"Authentication failed: {error} (code {result_code})")

            self.logger.info("Authentication successful")

        except Exception as e:
            raise ConnectionError(f"Authentication error: {e}")

    async def _send_udp_discovery(self) -> None:
        """Send UDP discovery broadcast for guest mode."""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1.0)

            # Send discovery message with app version for firmware 6.45 compatibility
            message = {
                "id": 1,
                "method": "scan_iscope",
                "params": "",
                "app_version": "3.0.0",  # Pretend to be latest app version
                "protocol_version": "6.45",  # Match firmware version exactly
            }
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

            # Authenticate for firmware 6.45+
            try:
                await self._authenticate()
            except Exception as e:
                await self.disconnect()
                raise ConnectionError(f"Authentication failed: {e}")

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

        # Build message with version info for firmware 6.x compatibility
        message = {"method": method, "id": cmd_id, "jsonrpc": "2.0"}  # Add JSON-RPC version
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

    # ========================================================================
    # Phase 1: Real-Time Observation & Tracking
    # ========================================================================

    async def get_current_coordinates(self) -> Dict[str, float]:
        """Get current telescope RA/Dec coordinates.

        Returns:
            Dict with 'ra' (hours) and 'dec' (degrees)

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("scope_get_equ_coord", {})

        result = response.get("result", {})

        # Update internal status
        if "ra" in result and "dec" in result:
            self._update_status(current_ra_hours=result["ra"], current_dec_degrees=result["dec"])

        return {"ra": result.get("ra", 0.0), "dec": result.get("dec", 0.0)}

    async def get_app_state(self) -> Dict[str, Any]:
        """Get current application/operation state.

        Returns detailed state including:
        - stage: Current operation stage (AutoGoto, AutoFocus, Stack, etc.)
        - state: Current state within stage
        - progress: Operation progress information
        - frame_count: Number of frames captured
        - etc.

        Returns:
            Application state dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("iscope_get_app_state", {})

        result = response.get("result", {})

        # Update internal status based on stage
        stage = result.get("stage")
        if stage == "AutoGoto":
            self._update_status(state=SeestarState.SLEWING)
        elif stage == "AutoFocus":
            self._update_status(state=SeestarState.FOCUSING)
        elif stage == "Stack":
            self._update_status(state=SeestarState.IMAGING)
        elif stage == "Idle":
            self._update_status(state=SeestarState.TRACKING)

        return result

    async def check_stacking_complete(self) -> bool:
        """Check if stacking is complete.

        Returns:
            True if stacking has finished

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("is_stacked", {})

        return response.get("result", {}).get("is_stacked", False)

    async def get_plate_solve_result(self) -> Dict[str, Any]:
        """Get plate solving result.

        Returns plate solve information including:
        - Actual solved RA/Dec
        - Field rotation
        - Solve status
        - Error information if solve failed

        Returns:
            Plate solve result dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("get_solve_result", {})

        return response.get("result", {})

    async def get_field_annotations(self) -> Dict[str, Any]:
        """Get annotations for objects in current field of view.

        Returns information about identified objects including:
        - Catalog objects (stars, galaxies, nebulae)
        - Object coordinates
        - Object names and identifiers

        Returns:
            Annotation results dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("get_annotate_result", {})

        return response.get("result", {})

    # ========================================================================
    # Phase 2: View Plans & Automated Sequences
    # ========================================================================

    async def start_view_plan(self, plan_config: Dict[str, Any]) -> bool:
        """Execute an automated observation plan.

        Starts a multi-target imaging sequence based on plan configuration.

        Args:
            plan_config: Plan configuration dict with targets, exposures, etc.

        Returns:
            True if plan started successfully

        Raises:
            CommandError: If plan start fails
        """
        self.logger.info(f"Starting view plan: {plan_config}")

        response = await self._send_command("start_view_plan", plan_config)

        self.logger.info(f"Start view plan response: {response}")
        return response.get("result") == 0

    async def stop_view_plan(self) -> bool:
        """Stop/cancel running observation plan.

        Returns:
            True if plan stopped successfully

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping view plan")

        response = await self._send_command("stop_view_plan", {})

        self.logger.info(f"Stop view plan response: {response}")
        return response.get("result") == 0

    async def get_view_plan_state(self) -> Dict[str, Any]:
        """Get current view plan execution state.

        Returns plan progress information including:
        - Current target
        - Targets completed
        - Overall progress
        - Estimated time remaining

        Returns:
            View plan state dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("get_view_plan_state", {})

        return response.get("result", {})

    # ========================================================================
    # Phase 3: Planetary Observation Mode
    # ========================================================================

    async def start_planet_scan(self, planet_name: str, exposure_ms: int = 30, gain: float = 100.0) -> bool:
        """Start planetary imaging mode.

        Uses specialized stacking optimized for planetary imaging.

        Args:
            planet_name: Name of planet to image
            exposure_ms: Exposure time in milliseconds (shorter for planets)
            gain: Camera gain (higher for planets)

        Returns:
            True if planetary mode started successfully

        Raises:
            CommandError: If start fails
        """
        self.logger.info(f"Starting planet scan: {planet_name}, exp={exposure_ms}ms, gain={gain}")

        params = {
            "planet": planet_name,
            "exposure_ms": exposure_ms,
            "gain": gain,
        }

        response = await self._send_command("start_scan_planet", params)

        self.logger.info(f"Start planet scan response: {response}")
        return response.get("result") == 0

    async def configure_planetary_imaging(
        self,
        frame_count: int = 1000,
        save_frames: bool = True,
        denoise: bool = True,
    ) -> bool:
        """Configure settings for planetary imaging.

        Args:
            frame_count: Number of frames to capture
            save_frames: Save individual frames for stacking
            denoise: Apply denoising to planetary images

        Returns:
            True if settings applied successfully

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Configuring planetary imaging: frames={frame_count}, save={save_frames}, denoise={denoise}")

        params = {
            "stack": {
                "capt_type": "planet",
                "capt_num": frame_count,
                "save_discrete_frame": save_frames,
                "wide_denoise": denoise,
            }
        }

        response = await self._send_command("set_setting", params)

        self.logger.info(f"Configure planetary imaging response: {response}")
        return response.get("result") == 0

    # ========================================================================
    # Phase 4: Enhanced Control
    # ========================================================================

    async def slew_to_coordinates(self, ra_hours: float, dec_degrees: float) -> bool:
        """Slew telescope to specific RA/Dec coordinates.

        Direct mount movement command (lower level than goto_target).

        Args:
            ra_hours: Right ascension in hours
            dec_degrees: Declination in degrees

        Returns:
            True if slew initiated successfully

        Raises:
            CommandError: If slew command fails
        """
        self.logger.info(f"Slewing to RA={ra_hours}h, Dec={dec_degrees}°")

        params = {"action": "slew", "ra": ra_hours, "dec": dec_degrees}

        self._update_status(state=SeestarState.SLEWING)

        response = await self._send_command("scope_move", params)

        self.logger.info(f"Slew response: {response}")
        return response.get("result") == 0

    async def stop_telescope_movement(self) -> bool:
        """Stop any telescope movement immediately.

        Emergency stop for mount movement.

        Returns:
            True if stop successful

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping telescope movement")

        params = {"action": "stop"}

        response = await self._send_command("scope_move", params)

        self.logger.info(f"Stop movement response: {response}")
        return response.get("result") == 0

    async def move_focuser_to_position(self, position: int) -> bool:
        """Move focuser to specific position.

        Args:
            position: Focuser position (0 to max_step, typically 0-2600)

        Returns:
            True if move initiated successfully

        Raises:
            CommandError: If move fails
        """
        self.logger.info(f"Moving focuser to position {position}")

        params = {"step": position}

        self._update_status(state=SeestarState.FOCUSING)

        response = await self._send_command("move_focuser", params)

        self.logger.info(f"Move focuser response: {response}")
        return response.get("result") == 0

    async def move_focuser_relative(self, offset: int) -> bool:
        """Move focuser by relative offset.

        Args:
            offset: Steps to move (positive = out, negative = in)

        Returns:
            True if move initiated successfully

        Raises:
            CommandError: If move fails
        """
        self.logger.info(f"Moving focuser by offset {offset}")

        params = {"offset": offset}

        self._update_status(state=SeestarState.FOCUSING)

        response = await self._send_command("move_focuser", params)

        self.logger.info(f"Move focuser response: {response}")
        return response.get("result") == 0

    async def stop_autofocus(self) -> bool:
        """Stop autofocus operation.

        Returns:
            True if stop successful

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping autofocus")

        response = await self._send_command("stop_auto_focuse", {})

        self.logger.info(f"Stop autofocus response: {response}")
        return response.get("result") == 0

    async def configure_advanced_stacking(
        self,
        dark_background_extraction: bool = False,
        star_correction: bool = True,
        airplane_removal: bool = False,
        drizzle_2x: bool = False,
    ) -> bool:
        """Configure advanced stacking options.

        Args:
            dark_background_extraction: Enable DBE for light pollution removal
            star_correction: Enable star shape correction
            airplane_removal: Remove satellite/airplane trails
            drizzle_2x: Enable 2x drizzle upsampling

        Returns:
            True if settings applied successfully

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(
            f"Configuring advanced stacking: dbe={dark_background_extraction}, "
            f"star_corr={star_correction}, airplane={airplane_removal}, drizzle={drizzle_2x}"
        )

        params = {
            "stack": {
                "dbe": dark_background_extraction,
                "star_correction": star_correction,
                "airplane_line_removal": airplane_removal,
                "drizzle2x": drizzle_2x,
            }
        }

        response = await self._send_command("set_setting", params)

        self.logger.info(f"Configure advanced stacking response: {response}")
        return response.get("result") == 0

    async def set_manual_exposure(self, exposure_ms: float, gain: float) -> bool:
        """Set manual exposure and gain.

        Args:
            exposure_ms: Exposure time in milliseconds
            gain: Camera gain

        Returns:
            True if settings applied successfully

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting manual exposure: {exposure_ms}ms, gain={gain}")

        params = {
            "manual_exp": True,
            "isp_exp_ms": exposure_ms,
            "isp_gain": gain,
        }

        response = await self._send_command("set_setting", params)

        self.logger.info(f"Set manual exposure response: {response}")
        return response.get("result") == 0

    async def set_auto_exposure(self, brightness_target: float = 50.0) -> bool:
        """Enable auto exposure with brightness target.

        Args:
            brightness_target: Target brightness percentage (0-100)

        Returns:
            True if settings applied successfully

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting auto exposure: brightness={brightness_target}%")

        params = {
            "manual_exp": False,
            "ae_bri_percent": brightness_target,
        }

        response = await self._send_command("set_setting", params)

        self.logger.info(f"Set auto exposure response: {response}")
        return response.get("result") == 0

    # ========================================================================
    # Phase 5+: System Management & Utilities
    # ========================================================================

    async def shutdown_telescope(self) -> bool:
        """Safely shutdown the telescope.

        Returns:
            True if shutdown initiated successfully

        Raises:
            CommandError: If shutdown fails
        """
        self.logger.info("Initiating telescope shutdown")

        response = await self._send_command("pi_shutdown", {})

        self.logger.info(f"Shutdown response: {response}")
        return response.get("result") == 0

    async def reboot_telescope(self) -> bool:
        """Reboot the telescope.

        Returns:
            True if reboot initiated successfully

        Raises:
            CommandError: If reboot fails
        """
        self.logger.info("Initiating telescope reboot")

        response = await self._send_command("pi_reboot", {})

        self.logger.info(f"Reboot response: {response}")
        return response.get("result") == 0

    async def play_notification_sound(self, volume: str = "backyard") -> bool:
        """Play notification sound on telescope.

        Args:
            volume: Volume level ("silent", "backyard", "outdoor")

        Returns:
            True if sound played successfully

        Raises:
            CommandError: If play fails
        """
        self.logger.info(f"Playing notification sound at volume: {volume}")

        params = {"volume": volume}

        response = await self._send_command("play_sound", params)

        self.logger.info(f"Play sound response: {response}")
        return response.get("result") == 0

    async def get_image_file_info(self, file_path: str = "") -> Dict[str, Any]:
        """Get information about captured image files.

        Args:
            file_path: Optional specific file path to query

        Returns:
            File information dict

        Raises:
            CommandError: If query fails
        """
        params = {"path": file_path} if file_path else {}

        response = await self._send_command("get_img_file_info", params)

        return response.get("result", {})

    async def cancel_current_operation(self) -> bool:
        """Cancel current view/operation.

        Alternative to stop commands.

        Returns:
            True if cancel successful

        Raises:
            CommandError: If cancel fails
        """
        self.logger.info("Canceling current operation")

        response = await self._send_command("iscope_cancel_view", {})

        self.logger.info(f"Cancel operation response: {response}")
        return response.get("result") == 0

    async def set_location(self, longitude: float, latitude: float) -> bool:
        """Set user location for telescope calculations.

        Args:
            longitude: Longitude in degrees (-180 to 180, west is negative)
            latitude: Latitude in degrees (-90 to 90)

        Returns:
            True if location set successfully

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting location: lon={longitude}, lat={latitude}")

        params = {"lon_lat": [longitude, latitude]}

        response = await self._send_command("set_user_location", params)

        self.logger.info(f"Set location response: {response}")
        return response.get("result") == 0

    async def move_to_horizon(self, azimuth: float, altitude: float) -> bool:
        """Move telescope to horizon coordinates.

        Args:
            azimuth: Azimuth in degrees (0-360)
            altitude: Altitude in degrees (0-90)

        Returns:
            True if move initiated successfully

        Raises:
            CommandError: If move fails
        """
        self.logger.info(f"Moving to horizon: az={azimuth}°, alt={altitude}°")

        params = {"azimuth": azimuth, "altitude": altitude}

        self._update_status(state=SeestarState.SLEWING)

        response = await self._send_command("scope_move_to_horizon", params)

        self.logger.info(f"Move to horizon response: {response}")
        return response.get("result") == 0

    async def reset_focuser_to_factory(self) -> bool:
        """Reset focuser to factory default position.

        Returns:
            True if reset successful

        Raises:
            CommandError: If reset fails
        """
        self.logger.info("Resetting focuser to factory position")

        response = await self._send_command("reset_factory_focal_pos", {})

        self.logger.info(f"Reset focuser response: {response}")
        return response.get("result") == 0

    async def check_polar_alignment(self) -> Dict[str, Any]:
        """Check polar alignment quality.

        Returns polar alignment information including error in arc-minutes.

        Returns:
            Polar alignment status dict

        Raises:
            CommandError: If check fails
        """
        response = await self._send_command("check_pa_alt", {})

        return response.get("result", {})

    async def clear_polar_alignment(self) -> bool:
        """Clear polar alignment calibration.

        Returns:
            True if clear successful

        Raises:
            CommandError: If clear fails
        """
        self.logger.info("Clearing polar alignment")

        response = await self._send_command("clear_polar_align", {})

        self.logger.info(f"Clear polar alignment response: {response}")
        return response.get("result") == 0

    async def start_compass_calibration(self) -> bool:
        """Start compass calibration procedure.

        Returns:
            True if calibration started successfully

        Raises:
            CommandError: If start fails
        """
        self.logger.info("Starting compass calibration")

        response = await self._send_command("start_compass_calibration", {})

        self.logger.info(f"Start compass calibration response: {response}")
        return response.get("result") == 0

    async def stop_compass_calibration(self) -> bool:
        """Stop compass calibration procedure.

        Returns:
            True if stop successful

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping compass calibration")

        response = await self._send_command("stop_compass_calibration", {})

        self.logger.info(f"Stop compass calibration response: {response}")
        return response.get("result") == 0

    async def get_compass_state(self) -> Dict[str, Any]:
        """Get compass heading and calibration state.

        Returns:
            Compass state dict with heading and calibration status

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("get_compass_state", {})

        return response.get("result", {})

    # ========================================================================
    # Phase 6: Remote Connection Management
    # ========================================================================

    async def join_remote_session(self, session_id: str = "") -> bool:
        """Join a remote observation session.

        Allows multiple clients to control the telescope.

        Args:
            session_id: Optional session identifier

        Returns:
            True if join successful

        Raises:
            CommandError: If join fails
        """
        self.logger.info(f"Joining remote session: {session_id}")

        params = {"session_id": session_id} if session_id else {}

        response = await self._send_command("remote_join", params)

        self.logger.info(f"Join remote session response: {response}")
        return response.get("result") == 0

    async def leave_remote_session(self) -> bool:
        """Leave current remote session.

        Returns:
            True if leave successful

        Raises:
            CommandError: If leave fails
        """
        self.logger.info("Leaving remote session")

        response = await self._send_command("remote_disjoin", {})

        self.logger.info(f"Leave remote session response: {response}")
        return response.get("result") == 0

    async def disconnect_remote_client(self, client_id: str = "") -> bool:
        """Disconnect a remote client.

        Args:
            client_id: Optional client identifier to disconnect

        Returns:
            True if disconnect successful

        Raises:
            CommandError: If disconnect fails
        """
        self.logger.info(f"Disconnecting remote client: {client_id}")

        params = {"client_id": client_id} if client_id else {}

        response = await self._send_command("remote_disconnect", params)

        self.logger.info(f"Disconnect remote client response: {response}")
        return response.get("result") == 0

    # ========================================================================
    # Phase 7: Network/WiFi Management
    # ========================================================================

    async def configure_access_point(self, ssid: str, password: str, is_5g: bool = True) -> bool:
        """Configure WiFi access point settings.

        Args:
            ssid: Access point SSID
            password: Access point password
            is_5g: Use 5GHz band (True) or 2.4GHz (False)

        Returns:
            True if configuration successful

        Raises:
            CommandError: If configuration fails
        """
        self.logger.info(f"Configuring AP: {ssid}, 5G={is_5g}")

        params = {"ssid": ssid, "passwd": password, "is_5g": is_5g}

        response = await self._send_command("pi_set_ap", params)

        self.logger.info(f"Configure AP response: {response}")
        return response.get("result") == 0

    async def set_wifi_country(self, country_code: str) -> bool:
        """Set WiFi regulatory country/region.

        Args:
            country_code: Two-letter country code (e.g., "US", "GB", "JP")

        Returns:
            True if setting successful

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting WiFi country: {country_code}")

        params = {"country": country_code}

        response = await self._send_command("set_wifi_country", params)

        self.logger.info(f"Set WiFi country response: {response}")
        return response.get("result") == 0

    async def enable_wifi_client_mode(self) -> bool:
        """Enable WiFi client/station mode.

        Allows telescope to connect to existing WiFi networks.

        Returns:
            True if enabled successfully

        Raises:
            CommandError: If enable fails
        """
        self.logger.info("Enabling WiFi client mode")

        response = await self._send_command("pi_station_open", {})

        self.logger.info(f"Enable WiFi client response: {response}")
        return response.get("result") == 0

    async def disable_wifi_client_mode(self) -> bool:
        """Disable WiFi client/station mode.

        Returns to AP-only mode.

        Returns:
            True if disabled successfully

        Raises:
            CommandError: If disable fails
        """
        self.logger.info("Disabling WiFi client mode")

        response = await self._send_command("pi_station_close", {})

        self.logger.info(f"Disable WiFi client response: {response}")
        return response.get("result") == 0

    async def scan_wifi_networks(self) -> Dict[str, Any]:
        """Scan for available WiFi networks.

        Returns:
            Dict with list of available networks

        Raises:
            CommandError: If scan fails
        """
        self.logger.info("Scanning for WiFi networks")

        response = await self._send_command("pi_station_scan", {})

        return response.get("result", {})

    async def connect_to_wifi(self, ssid: str) -> bool:
        """Connect to a WiFi network.

        Network must already be saved with credentials.

        Args:
            ssid: Network SSID to connect to

        Returns:
            True if connection initiated successfully

        Raises:
            CommandError: If connection fails
        """
        self.logger.info(f"Connecting to WiFi: {ssid}")

        params = {"ssid": ssid}

        response = await self._send_command("pi_station_select", params)

        self.logger.info(f"Connect to WiFi response: {response}")
        return response.get("result") == 0

    async def save_wifi_network(self, ssid: str, password: str, security: str = "WPA2-PSK") -> bool:
        """Save WiFi network credentials.

        Args:
            ssid: Network SSID
            password: Network password
            security: Security type (WPA2-PSK, WPA-PSK, WEP, etc.)

        Returns:
            True if saved successfully

        Raises:
            CommandError: If save fails
        """
        self.logger.info(f"Saving WiFi network: {ssid}")

        params = {"ssid": ssid, "passwd": password, "security": security}

        response = await self._send_command("pi_station_set", params)

        self.logger.info(f"Save WiFi network response: {response}")
        return response.get("result") == 0

    async def list_saved_wifi_networks(self) -> Dict[str, Any]:
        """List saved WiFi networks.

        Returns:
            Dict with list of saved networks

        Raises:
            CommandError: If list fails
        """
        response = await self._send_command("pi_station_list", {})

        return response.get("result", {})

    async def remove_wifi_network(self, ssid: str) -> bool:
        """Remove saved WiFi network.

        Args:
            ssid: Network SSID to remove

        Returns:
            True if removed successfully

        Raises:
            CommandError: If remove fails
        """
        self.logger.info(f"Removing WiFi network: {ssid}")

        params = {"ssid": ssid}

        response = await self._send_command("pi_station_remove", params)

        self.logger.info(f"Remove WiFi network response: {response}")
        return response.get("result") == 0

    # ========================================================================
    # Phase 8: Raspberry Pi System Commands
    # ========================================================================

    async def get_pi_info(self) -> Dict[str, Any]:
        """Get Raspberry Pi system information.

        Returns info about CPU, memory, disk, temperature, etc.

        Returns:
            System information dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("pi_get_info", {})

        return response.get("result", {})

    async def get_pi_time(self) -> Dict[str, Any]:
        """Get Raspberry Pi system time.

        Returns:
            Time information dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("pi_get_time", {})

        return response.get("result", {})

    async def set_pi_time(self, unix_timestamp: int) -> bool:
        """Set Raspberry Pi system time.

        Args:
            unix_timestamp: Unix timestamp (seconds since epoch)

        Returns:
            True if time set successfully

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting Pi time: {unix_timestamp}")

        params = {"time": unix_timestamp}

        response = await self._send_command("pi_set_time", params)

        self.logger.info(f"Set Pi time response: {response}")
        return response.get("result") == 0

    async def get_station_state(self) -> Dict[str, Any]:
        """Get WiFi station state.

        Returns connection status, signal strength, IP address, etc.

        Returns:
            Station state dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("pi_station_state", {})

        return response.get("result", {})

    # ========================================================================
    # Phase 9: Hardware Control (Dew Heater, Filters, Accessories)
    # ========================================================================

    async def set_dew_heater(self, enabled: bool, power_level: int = 90) -> bool:
        """Control dew heater via pi_output_set2.

        CRITICAL: Uses pi_output_set2, NOT set_setting!
        From APK analysis: BaseDeviceViewModel.java:1310

        Args:
            enabled: True to enable heater, False to disable
            power_level: Heater power level 0-100 (default: 90, same as official app)

        Returns:
            True if setting successful

        Raises:
            CommandError: If setting fails
        """
        if not 0 <= power_level <= 100:
            raise ValueError(f"Power level must be 0-100, got {power_level}")

        self.logger.info(f"Setting dew heater: {'ON' if enabled else 'OFF'} at {power_level}% power")

        # Correct implementation from APK decompilation
        params = {"heater": {"state": enabled, "value": power_level}}

        response = await self._send_command("pi_output_set2", params)

        self.logger.info(f"Set dew heater response: {response}")
        return response.get("result") == 0

    async def set_dc_output(self, output_config: Dict[str, Any]) -> bool:
        """Set DC output configuration for accessories.

        Controls external devices via DC output ports.

        Args:
            output_config: Output configuration dict
                Example: {"port": 1, "enabled": True, "voltage": 12}

        Returns:
            True if setting successful

        Raises:
            CommandError: If setting fails
        """
        self.logger.info(f"Setting DC output: {output_config}")

        response = await self._send_command("pi_output_set2", output_config)

        self.logger.info(f"Set DC output response: {response}")
        return response.get("result") == 0

    async def get_dc_output(self) -> Dict[str, Any]:
        """Get current DC output configuration.

        Returns:
            DC output state dict

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("pi_output_get2", {})

        return response.get("result", {})

    # ========================================================================
    # Phase 10: Demo Mode & Miscellaneous
    # ========================================================================

    async def start_demo_mode(self) -> bool:
        """Start demonstration/exhibition mode.

        Simulates telescope movements without actually moving hardware.

        Returns:
            True if demo mode started successfully

        Raises:
            CommandError: If start fails
        """
        self.logger.info("Starting demo mode")

        response = await self._send_command("start_demonstrate", {})

        self.logger.info(f"Start demo mode response: {response}")
        return response.get("result") == 0

    async def stop_demo_mode(self) -> bool:
        """Stop demonstration/exhibition mode.

        Returns:
            True if demo mode stopped successfully

        Raises:
            CommandError: If stop fails
        """
        self.logger.info("Stopping demo mode")

        response = await self._send_command("stop_demonstrate", {})

        self.logger.info(f"Stop demo mode response: {response}")
        return response.get("result") == 0

    async def check_client_verified(self) -> bool:
        """Check if current client is verified/authenticated.

        Returns:
            True if client is verified

        Raises:
            CommandError: If query fails
        """
        response = await self._send_command("pi_is_verified", {})

        return response.get("result", {}).get("is_verified", False)
