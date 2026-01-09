"""
Session recorder for capturing live Seestar telescope interactions.

Records TCP sessions for later playback in tests without hardware.
"""

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class Interaction:
    """Represents a single message exchange."""

    timestamp: float  # Relative to session start
    direction: str  # "send" or "recv"
    message: Dict[str, Any]  # JSON message
    delay_after: float  # Time until next message


@dataclass
class RecordingMetadata:
    """Metadata about the recording session."""

    telescope: str = "Seestar S50"
    firmware_version: str = ""
    recorded_at: str = ""
    duration_seconds: float = 0.0
    description: str = ""
    host: str = ""
    port: int = 0


class SeestarSessionRecorder:
    """Records live TCP session with real telescope for playback testing.

    Usage:
        recorder = SeestarSessionRecorder()
        async with recorder.intercept_connection("192.168.2.47", 4700):
            # Run actual telescope operations
            client = SeestarClient()
            await client.connect()
            await client.goto_target(10.0, 45.0, "Test")

        # Save recording
        recorder.save("tests/fixtures/recordings/goto_sequence.json")
    """

    def __init__(self, description: str = ""):
        """Initialize recorder.

        Args:
            description: Human-readable description of what's being recorded
        """
        self.interactions: List[Interaction] = []
        self.metadata = RecordingMetadata(description=description)
        self._start_time: Optional[float] = None
        self._last_timestamp: float = 0.0
        self._proxy_task: Optional[asyncio.Task] = None
        self._client_reader: Optional[asyncio.StreamReader] = None
        self._client_writer: Optional[asyncio.StreamWriter] = None
        self._server_reader: Optional[asyncio.StreamReader] = None
        self._server_writer: Optional[asyncio.StreamWriter] = None

    async def intercept_connection(self, host: str, port: int):
        """Context manager that proxies and records a connection.

        Args:
            host: Real telescope hostname/IP
            port: Real telescope port (usually 4700)

        Yields:
            (proxy_host, proxy_port) tuple to connect to instead of real telescope
        """
        self.metadata.host = host
        self.metadata.port = port
        self.metadata.recorded_at = datetime.now().isoformat()
        self._start_time = time.time()

        # Start proxy server
        server = await asyncio.start_server(self._handle_proxy_connection, "127.0.0.1", 0)

        addr = server.sockets[0].getsockname()
        logger.info(f"Recording proxy listening on {addr[0]}:{addr[1]}")
        logger.info(f"Will forward to real telescope at {host}:{port}")

        try:
            yield addr
        finally:
            server.close()
            await server.wait_closed()

            # Calculate duration
            if self._start_time:
                self.metadata.duration_seconds = time.time() - self._start_time

            logger.info(
                f"Recording complete: {len(self.interactions)} interactions "
                f"over {self.metadata.duration_seconds:.1f}s"
            )

    async def _handle_proxy_connection(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Handle incoming client connection by proxying to real telescope."""
        self._client_reader = client_reader
        self._client_writer = client_writer

        try:
            # Connect to real telescope
            self._server_reader, self._server_writer = await asyncio.open_connection(
                self.metadata.host, self.metadata.port
            )

            logger.info("Connected to real telescope, starting recording")

            # Bidirectional proxy
            client_to_server = asyncio.create_task(self._proxy_client_to_server())
            server_to_client = asyncio.create_task(self._proxy_server_to_client())

            # Wait for either direction to close
            done, pending = await asyncio.wait(
                [client_to_server, server_to_client], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining task
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Proxy error: {e}")
        finally:
            # Close connections
            if self._server_writer:
                self._server_writer.close()
                await self._server_writer.wait_closed()
            client_writer.close()
            await client_writer.wait_closed()

    async def _proxy_client_to_server(self):
        """Forward messages from client to server, recording sends."""
        if not self._client_reader or not self._server_writer:
            return

        while True:
            try:
                # Read JSON-RPC message (newline-delimited)
                line = await self._client_reader.readline()
                if not line:
                    break

                # Parse and record
                try:
                    message = json.loads(line.decode("utf-8"))
                    self._record_interaction("send", message)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse client message: {line}")

                # Forward to server
                self._server_writer.write(line)
                await self._server_writer.drain()

            except Exception as e:
                logger.error(f"Client->Server proxy error: {e}")
                break

    async def _proxy_server_to_client(self):
        """Forward messages from server to client, recording receives."""
        if not self._server_reader or not self._client_writer:
            return

        while True:
            try:
                # Read JSON-RPC message
                line = await self._server_reader.readline()
                if not line:
                    break

                # Parse and record
                try:
                    message = json.loads(line.decode("utf-8"))
                    self._record_interaction("recv", message)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse server message: {line}")

                # Forward to client
                self._client_writer.write(line)
                await self._client_writer.drain()

            except Exception as e:
                logger.error(f"Server->Client proxy error: {e}")
                break

    def _record_interaction(self, direction: str, message: Dict[str, Any]):
        """Record a message interaction with timing.

        Args:
            direction: "send" or "recv"
            message: Parsed JSON message
        """
        if not self._start_time:
            return

        now = time.time()
        timestamp = now - self._start_time

        # Calculate delay since last interaction
        delay_after = 0.0
        if self.interactions:
            delay_after = timestamp - self._last_timestamp

        interaction = Interaction(timestamp=timestamp, direction=direction, message=message, delay_after=delay_after)

        self.interactions.append(interaction)
        self._last_timestamp = timestamp

        # Log for debugging
        method = message.get("method", message.get("result", "???"))
        logger.debug(f"[{timestamp:.3f}s] {direction.upper()}: {method}")

    def save(self, filepath: str, description: Optional[str] = None):
        """Save recording to JSON file.

        Args:
            filepath: Path to save recording (e.g., "tests/fixtures/recordings/goto.json")
            description: Optional description to override metadata
        """
        if description:
            self.metadata.description = description

        # Convert to JSON-serializable format
        recording = {
            "recording_metadata": asdict(self.metadata),
            "interactions": [asdict(interaction) for interaction in self.interactions],
        }

        # Ensure directory exists
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save with pretty formatting
        with open(path, "w") as f:
            json.dump(recording, f, indent=2)

        logger.info(f"Saved recording to {filepath}")
        logger.info(f"  - {len(self.interactions)} interactions")
        logger.info(f"  - {self.metadata.duration_seconds:.1f}s duration")

    @classmethod
    def load(cls, filepath: str) -> "SeestarSessionRecorder":
        """Load recording from JSON file.

        Args:
            filepath: Path to recording file

        Returns:
            SeestarSessionRecorder with loaded interactions
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        recorder = cls()
        recorder.metadata = RecordingMetadata(**data["recording_metadata"])
        recorder.interactions = [Interaction(**interaction) for interaction in data["interactions"]]

        return recorder
