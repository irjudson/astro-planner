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
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import get_settings


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


class EventType(Enum):
    """Known event types from S50."""

    PROGRESS_UPDATE = "progress"  # Frame count, percentage updates
    STATE_CHANGE = "state"  # Device state transitions
    ERROR = "error"  # Operation errors
    IMAGE_READY = "image"  # Stacking complete, image available
    OPERATION_COMPLETE = "complete"  # Goto/focus/imaging done
    UNKNOWN = "unknown"  # Unrecognized event type


@dataclass
class SeestarEvent:
    """Represents unsolicited event from telescope."""

    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    source_command: Optional[str] = None


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
    FILE_TRANSFER_PORT = 4801  # Port 4801 for file downloads
    CONNECTION_TIMEOUT = 10.0
    COMMAND_TIMEOUT = 10.0
    RECEIVE_BUFFER_SIZE = 4096

    def __init__(self, logger: Optional[logging.Logger] = None, private_key_path: Optional[str] = None):
        """Initialize Seestar client.

        Args:
            logger: Optional logger instance. If None, creates default logger.
            private_key_path: Optional path to RSA private key file. If None, uses config setting.
        """
        self.logger = logger or logging.getLogger(__name__)

        # Store key path for lazy loading (only load when actually connecting)
        settings = get_settings()
        self._private_key_path = Path(private_key_path or settings.seestar_private_key_path)
        if not self._private_key_path.is_absolute():
            # Make relative paths relative to backend directory
            self._private_key_path = Path(__file__).parent.parent.parent / self._private_key_path

        self._private_key_pem: Optional[bytes] = None

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

        # Event streaming
        self._event_callbacks: Dict[EventType, List[Callable[[SeestarEvent], None]]] = {
            event_type: [] for event_type in EventType
        }
        self._all_events_callbacks: List[Callable[[SeestarEvent], None]] = []
        self._progress_callbacks: List[Callable[[float, Dict[str, Any]], None]] = []

    @property
    def connected(self) -> bool:
        """Check if connected to telescope."""
        return self._connected

    @property
    def status(self) -> SeestarStatus:
        """Get current telescope status."""
        return self._status

    @property
    def host(self) -> Optional[str]:
        """Get connected host."""
        return self._host

    @property
    def port(self) -> int:
        """Get connected port."""
        return self._port

    def set_status_callback(self, callback: Callable[[SeestarStatus], None]) -> None:
        """Set callback function for status updates.

        Args:
            callback: Function to call when status changes
        """
        self._status_callback = callback

    def subscribe_event(self, event_type: EventType, callback: Callable[[SeestarEvent], None]) -> None:
        """Register callback for specific event type.

        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        if callback not in self._event_callbacks[event_type]:
            self._event_callbacks[event_type].append(callback)
            self.logger.debug(f"Subscribed to {event_type.value} events")

    def unsubscribe_event(self, event_type: EventType, callback: Callable[[SeestarEvent], None]) -> None:
        """Remove event callback.

        Args:
            event_type: Type of event to stop listening for
            callback: Function to remove
        """
        if callback in self._event_callbacks[event_type]:
            self._event_callbacks[event_type].remove(callback)
            self.logger.debug(f"Unsubscribed from {event_type.value} events")

    def subscribe_all_events(self, callback: Callable[[SeestarEvent], None]) -> None:
        """Receive all telescope events.

        Args:
            callback: Function to call for any event
        """
        if callback not in self._all_events_callbacks:
            self._all_events_callbacks.append(callback)
            self.logger.debug("Subscribed to all events")

    def unsubscribe_all_events(self, callback: Callable[[SeestarEvent], None]) -> None:
        """Stop receiving all events.

        Args:
            callback: Function to remove
        """
        if callback in self._all_events_callbacks:
            self._all_events_callbacks.remove(callback)
            self.logger.debug("Unsubscribed from all events")

    def subscribe_progress(self, callback: Callable[[float, Dict[str, Any]], None]) -> None:
        """Convenience method for progress updates only.

        Callback signature: (percent_complete: float, details: dict)

        Args:
            callback: Function to call with progress updates
        """
        if callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)
            self.logger.debug("Subscribed to progress updates")

    def unsubscribe_progress(self, callback: Callable[[float, Dict[str, Any]], None]) -> None:
        """Stop receiving progress updates.

        Args:
            callback: Function to remove
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
            self.logger.debug("Unsubscribed from progress updates")

    def _update_status(self, **kwargs) -> None:
        """Update internal status and trigger callback."""
        # Log status changes to console for debugging
        if kwargs:
            self.logger.info(f"[TELESCOPE STATUS UPDATE] {kwargs}")

        for key, value in kwargs.items():
            if hasattr(self._status, key):
                setattr(self._status, key, value)

        self._status.last_update = datetime.now()

        if self._status_callback:
            try:
                self._status_callback(self._status)
            except Exception as e:
                self.logger.error(f"Error in status callback: {e}")

    def _load_private_key(self) -> None:
        """Load RSA private key for authentication.

        Only called when actually connecting to telescope.

        Raises:
            ConnectionError: If key file not found
        """
        if self._private_key_pem is not None:
            return  # Already loaded

        try:
            with open(self._private_key_path, "rb") as f:
                self._private_key_pem = f.read()
            self.logger.debug(f"Loaded Seestar private key from {self._private_key_path}")
        except FileNotFoundError:
            self.logger.error(f"Seestar private key not found at {self._private_key_path}")
            raise ConnectionError(
                f"Seestar authentication key not found at {self._private_key_path}. "
                "Please ensure the key file exists or set SEESTAR_PRIVATE_KEY_PATH environment variable."
            )

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
            self._private_key_pem, password=None, backend=default_backend()
        )

        # Sign the challenge using RSA-SHA1 (required by Seestar firmware protocol)
        # SHA1 used for RSA signing (not password hashing), required by hardware
        signature = private_key.sign(challenge_str.encode("utf-8"), padding.PKCS1v15(), hashes.SHA1())  # nosec B303

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

            # Load private key and authenticate for firmware 6.45+
            try:
                self._load_private_key()
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
            return  # This was a command response, not an event

        # Parse and dispatch as unsolicited event
        event = self._parse_event(message)
        if event:
            await self._dispatch_event(event)

    def _parse_event(self, message: Dict[str, Any]) -> Optional[SeestarEvent]:
        """Parse message as telescope event.

        Args:
            message: Raw message dict from telescope

        Returns:
            SeestarEvent if recognized, None otherwise
        """
        # Determine event type based on message structure
        method = message.get("method", "")
        result = message.get("result", {})

        event_type = EventType.UNKNOWN
        event_data = {}

        # Parse different event types
        if "progress" in result or "percent" in result:
            event_type = EventType.PROGRESS_UPDATE
            event_data = {
                "progress": result.get("progress", 0),
                "percent": result.get("percent", 0),
                "frame": result.get("frame", 0),
                "total_frames": result.get("total_frames", 0),
            }

        elif "state" in result:
            event_type = EventType.STATE_CHANGE
            event_data = {"state": result.get("state"), "stage": result.get("stage")}

        elif "error" in message or message.get("code", 0) != 0:
            event_type = EventType.ERROR
            event_data = {
                "error": message.get("error", "Unknown error"),
                "code": message.get("code", 0),
            }

        elif "stacked" in result or "image_ready" in result:
            event_type = EventType.IMAGE_READY
            event_data = {"filename": result.get("filename"), "path": result.get("path")}

        elif result.get("stage") == "Idle" or result.get("complete"):
            event_type = EventType.OPERATION_COMPLETE
            event_data = {"operation": result.get("operation"), "success": result.get("success", True)}

        # Create event
        return SeestarEvent(event_type=event_type, timestamp=datetime.now(), data=event_data, source_command=method)

    async def _dispatch_event(self, event: SeestarEvent) -> None:
        """Dispatch event to registered callbacks.

        Args:
            event: Event to dispatch
        """
        # Call all-events callbacks
        for callback in self._all_events_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in all-events callback: {e}")

        # Call event-type-specific callbacks
        for callback in self._event_callbacks.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in {event.event_type.value} callback: {e}")

        # Handle progress events specially for progress callbacks
        if event.event_type == EventType.PROGRESS_UPDATE:
            percent = event.data.get("percent", 0)
            details = event.data
            for progress_cb in self._progress_callbacks:
                try:
                    progress_cb(percent, details)
                except Exception as e:
                    self.logger.error(f"Error in progress callback: {e}")

    async def wait_for_goto_complete(self, timeout: float = 180.0) -> bool:
        """Wait for slew/goto operation to complete using events (not polling).

        Subscribes to STATE_CHANGE events and waits for telescope to enter
        TRACKING state, indicating the goto is complete.

        Args:
            timeout: Maximum time to wait in seconds (default: 3 minutes)

        Returns:
            True if goto completed successfully, False on timeout

        Example:
            await client.goto_target(10.0, 45.0, "M31")
            success = await client.wait_for_goto_complete(timeout=120.0)
            if success:
                print("Goto completed, telescope is tracking")
        """
        completion_event = asyncio.Event()
        success = False

        def state_callback(event: SeestarEvent):
            nonlocal success
            state = event.data.get("state")
            if state == SeestarState.TRACKING.value or state == "tracking":
                success = True
                completion_event.set()
            elif state in (SeestarState.CONNECTED.value, "connected", SeestarState.PARKED.value, "parked"):
                # Goto failed or was stopped
                success = False
                completion_event.set()

        # Subscribe to state change events
        self.subscribe_event(EventType.STATE_CHANGE, state_callback)

        try:
            # Wait for completion or timeout
            await asyncio.wait_for(completion_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Goto operation timed out after {timeout}s")
            success = False
        finally:
            # Clean up subscription
            self.unsubscribe_event(EventType.STATE_CHANGE, state_callback)

        return success

    async def wait_for_focus_complete(self, timeout: float = 120.0) -> tuple[bool, Optional[float]]:
        """Wait for autofocus operation to complete using events.

        Subscribes to OPERATION_COMPLETE events and waits for autofocus to finish.

        Args:
            timeout: Maximum time to wait in seconds (default: 2 minutes)

        Returns:
            Tuple of (success: bool, focus_position: Optional[float])
            - success: True if autofocus completed successfully
            - focus_position: Final focus position if available, None otherwise

        Example:
            await client.auto_focus()
            success, position = await client.wait_for_focus_complete(timeout=90.0)
            if success:
                print(f"Autofocus complete at position {position}")
        """
        completion_event = asyncio.Event()
        success = False
        focus_position = None

        def operation_callback(event: SeestarEvent):
            nonlocal success, focus_position
            operation = event.data.get("operation", "")
            if "focus" in operation.lower() or event.source_command == "auto_focus":
                success = event.data.get("success", True)
                focus_position = event.data.get("position")
                completion_event.set()

        # Subscribe to operation complete events
        self.subscribe_event(EventType.OPERATION_COMPLETE, operation_callback)

        try:
            # Wait for completion or timeout
            await asyncio.wait_for(completion_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"Autofocus operation timed out after {timeout}s")
            success = False
        finally:
            # Clean up subscription
            self.unsubscribe_event(EventType.OPERATION_COMPLETE, operation_callback)

        return success, focus_position

    async def wait_for_imaging_complete(
        self,
        expected_frames: int,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        timeout: float = 3600.0,
    ) -> bool:
        """Wait for imaging session to reach expected frame count.

        Subscribes to PROGRESS_UPDATE events and tracks frame completion.
        Optionally calls progress_callback after each frame.

        Args:
            expected_frames: Number of frames to wait for
            progress_callback: Optional callback(frame_num, total_frames, percent)
                called after each frame is stacked
            timeout: Maximum time to wait in seconds (default: 1 hour)

        Returns:
            True if expected frames reached, False on timeout or error

        Example:
            def on_progress(current, total, percent):
                print(f"Stacked {current}/{total} frames ({percent:.1f}%)")

            await client.start_imaging(restart=True)
            success = await client.wait_for_imaging_complete(
                expected_frames=50,
                progress_callback=on_progress,
                timeout=1800.0
            )
        """
        completion_event = asyncio.Event()
        success = False
        current_frame = 0

        def imaging_progress_callback(event: SeestarEvent):
            nonlocal success, current_frame
            frame = event.data.get("frame", 0)
            total = event.data.get("total_frames", expected_frames)
            percent = event.data.get("percent", 0)

            current_frame = frame

            # Call user's progress callback if provided
            if progress_callback:
                try:
                    progress_callback(frame, total, percent)
                except Exception as e:
                    self.logger.error(f"Error in user progress callback: {e}")

            # Check if we've reached expected frames
            if frame >= expected_frames:
                success = True
                completion_event.set()

        # Subscribe to progress events
        self.subscribe_event(EventType.PROGRESS_UPDATE, imaging_progress_callback)

        try:
            # Wait for completion or timeout
            await asyncio.wait_for(completion_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(
                f"Imaging session timed out after {timeout}s " f"(reached {current_frame}/{expected_frames} frames)"
            )
            success = False
        finally:
            # Clean up subscription
            self.unsubscribe_event(EventType.PROGRESS_UPDATE, imaging_progress_callback)

        return success

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
        """Park telescope at home position (azimuth=0, altitude=0).

        For Seestar, there's no explicit park command. Instead, we move
        to azimuth=0, altitude=0 which is the parked/stowed position.

        Returns:
            True if park initiated successfully

        Raises:
            CommandError: If park command fails
        """
        self.logger.info("Parking telescope (moving to 0,0)")

        self._update_status(state=SeestarState.PARKING)

        # Move to azimuth=0, altitude=0 (parked position)
        response = await self._send_command("scope_move_to_horizon", {"azimuth": 0.0, "altitude": 0.0})

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

    # ==========================================
    # Phase 10: Image Retrieval
    # ==========================================

    async def list_images(self, image_type: str = "stacked") -> List[Dict[str, Any]]:
        """List available images on telescope storage.

        Args:
            image_type: Type of images to list - "stacked", "raw", or "all"

        Returns:
            List of dicts with {filename, size, timestamp, format}

        Raises:
            CommandError: If query fails
        """
        self.logger.info(f"Listing images of type: {image_type}")

        # Use get_img_file_info to query directory
        # Seestar stores images in specific paths:
        # - Stacked images: typically in /mnt/seestar/stack/
        # - Raw frames: typically in /mnt/seestar/raw/

        images = []

        if image_type in ("stacked", "all"):
            stack_info = await self.get_image_file_info("/mnt/seestar/stack/")
            if "files" in stack_info:
                for file_info in stack_info["files"]:
                    images.append(
                        {
                            "filename": file_info.get("name", ""),
                            "size": file_info.get("size", 0),
                            "timestamp": file_info.get("timestamp", ""),
                            "format": file_info.get("format", "fits"),
                            "type": "stacked",
                        }
                    )

        if image_type in ("raw", "all"):
            raw_info = await self.get_image_file_info("/mnt/seestar/raw/")
            if "files" in raw_info:
                for file_info in raw_info["files"]:
                    images.append(
                        {
                            "filename": file_info.get("name", ""),
                            "size": file_info.get("size", 0),
                            "timestamp": file_info.get("timestamp", ""),
                            "format": file_info.get("format", "fits"),
                            "type": "raw",
                        }
                    )

        self.logger.info(f"Found {len(images)} images")
        return images

    async def get_stacked_image(self, filename: str) -> bytes:
        """Download stacked FITS/JPEG image from telescope.

        Uses file transfer protocol on port 4801.

        Args:
            filename: Name of stacked image file to download

        Returns:
            Raw image bytes

        Raises:
            ConnectionError: If file transfer connection fails
            CommandError: If download fails
        """
        self.logger.info(f"Downloading stacked image: {filename}")

        if not self._host:
            raise ConnectionError("Not connected to telescope")

        # Download file via port 4801
        image_data = await self._download_file(f"/mnt/seestar/stack/{filename}")

        self.logger.info(f"Downloaded {len(image_data)} bytes")
        return image_data

    async def get_raw_frame(self, filename: str) -> bytes:
        """Download individual raw frame from telescope.

        Uses file transfer protocol on port 4801.

        Args:
            filename: Name of raw frame file to download

        Returns:
            Raw frame bytes

        Raises:
            ConnectionError: If file transfer connection fails
            CommandError: If download fails
        """
        self.logger.info(f"Downloading raw frame: {filename}")

        if not self._host:
            raise ConnectionError("Not connected to telescope")

        # Download file via port 4801
        frame_data = await self._download_file(f"/mnt/seestar/raw/{filename}")

        self.logger.info(f"Downloaded {len(frame_data)} bytes")
        return frame_data

    async def delete_image(self, filename: str) -> bool:
        """Delete image from telescope storage.

        Args:
            filename: Full path to image file to delete

        Returns:
            True if deletion successful

        Raises:
            CommandError: If deletion fails
        """
        self.logger.info(f"Deleting image: {filename}")

        # Use system command to delete file
        # Note: This requires appropriate permissions and may not be available in all firmware versions
        response = await self._send_command("pi_execute_cmd", {"cmd": f"rm {filename}"})

        success = response.get("result") == 0
        self.logger.info(f"Delete {'successful' if success else 'failed'}")
        return success

    async def get_live_preview(self) -> bytes:
        """Capture current preview frame (RTMP stream frame grab).

        Note: This method requires RTMP stream access on ports 4554/4555.
        Currently returns empty bytes as RTMP handling requires additional dependencies.

        Returns:
            Preview frame bytes (currently empty - RTMP support pending)

        Raises:
            NotImplementedError: RTMP stream handling not yet implemented
        """
        self.logger.warning("Live preview via RTMP stream not yet implemented")
        raise NotImplementedError(
            "Live preview requires RTMP stream handling. " "Use get_stacked_image() for completed images instead."
        )

    async def _download_file(self, remote_path: str) -> bytes:
        """Download file from telescope via port 4801.

        Internal method for file transfer protocol.

        Args:
            remote_path: Full path to file on telescope

        Returns:
            File contents as bytes

        Raises:
            ConnectionError: If connection to file server fails
            CommandError: If file not found or transfer fails
        """
        if not self._host:
            raise ConnectionError("Not connected to telescope")

        self.logger.info(f"Opening file transfer connection to {self._host}:{self.FILE_TRANSFER_PORT}")

        try:
            # Open TCP connection to file transfer port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self.FILE_TRANSFER_PORT), timeout=self.CONNECTION_TIMEOUT
            )

            # Send file request (protocol may vary - this is a basic implementation)
            # Format: JSON request with file path
            request = json.dumps({"file": remote_path}) + "\n"
            writer.write(request.encode("utf-8"))
            await writer.drain()

            # Read file data
            file_data = b""
            while True:
                chunk = await reader.read(self.RECEIVE_BUFFER_SIZE)
                if not chunk:
                    break
                file_data += chunk

            writer.close()
            await writer.wait_closed()

            if not file_data:
                raise CommandError(f"File not found or empty: {remote_path}")

            self.logger.info(f"Downloaded {len(file_data)} bytes from {remote_path}")
            return file_data

        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout connecting to file server on port {self.FILE_TRANSFER_PORT}")
        except Exception as e:
            raise CommandError(f"File download failed: {str(e)}")
