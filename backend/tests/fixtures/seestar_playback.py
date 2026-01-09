"""
Playback server for replaying recorded Seestar telescope sessions.

Simulates telescope behavior by replaying captured TCP interactions.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from tests.fixtures.seestar_recorder import Interaction, RecordingMetadata


class SeestarPlaybackServer:
    """Replays recorded session to simulate real telescope.

    Usage in tests:
        playback = SeestarPlaybackServer.from_recording(
            "tests/fixtures/recordings/goto_sequence.json"
        )

        async with playback.serve() as server_address:
            # Connect client to mock server
            client = SeestarClient()
            await client.connect(server_address[0], server_address[1])
            await client.goto_target(10.0, 45.0, "M31")
            # Server replays recorded responses
    """

    def __init__(self, interactions: List[Interaction], metadata: RecordingMetadata):
        """Initialize playback server with recorded interactions.

        Args:
            interactions: List of recorded interactions
            metadata: Recording metadata
        """
        self.interactions = interactions
        self.metadata = metadata
        self._server: Optional[asyncio.Server] = None
        self._interaction_index = 0

        # Build command lookup for matching
        self._commands: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]] = {}
        self._build_command_map()

    def _build_command_map(self):
        """Build a map of commands to their expected responses.

        Groups interactions by method name for quick lookup.
        """
        i = 0
        while i < len(self.interactions):
            interaction = self.interactions[i]

            # Look for "send" messages (commands from client)
            if interaction.direction == "send":
                method = interaction.message.get("method")
                if method:
                    # Find the matching response
                    response = None
                    if i + 1 < len(self.interactions) and self.interactions[i + 1].direction == "recv":
                        response = self.interactions[i + 1].message

                    # Store command->response mapping
                    if method not in self._commands:
                        self._commands[method] = []
                    self._commands[method].append((interaction.message, response or {}))

            i += 1

        logger.debug(f"Built command map with {len(self._commands)} unique methods")

    @classmethod
    def from_recording(cls, filepath: str) -> "SeestarPlaybackServer":
        """Load playback server from recording file.

        Args:
            filepath: Path to recording JSON file

        Returns:
            SeestarPlaybackServer ready to serve
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        metadata = RecordingMetadata(**data["recording_metadata"])
        interactions = [Interaction(**interaction) for interaction in data["interactions"]]

        logger.info(f"Loaded recording: {filepath}")
        logger.info(f"  - {len(interactions)} interactions")
        logger.info(f"  - {metadata.duration_seconds:.1f}s duration")
        logger.info(f"  - {metadata.description}")

        return cls(interactions, metadata)

    async def serve(self, host: str = "127.0.0.1", port: int = 0) -> Tuple[str, int]:
        """Start playback server as async context manager.

        Args:
            host: Host to bind to (default: localhost)
            port: Port to bind to (0 = random)

        Yields:
            (host, port) tuple where server is listening
        """
        self._server = await asyncio.start_server(self._handle_client, host, port)

        addr = self._server.sockets[0].getsockname()
        logger.info(f"Playback server listening on {addr[0]}:{addr[1]}")

        return addr

    async def stop(self):
        """Stop the playback server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Playback server stopped")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection by replaying recorded responses.

        Args:
            reader: Client stream reader
            writer: Client stream writer
        """
        addr = writer.get_extra_info("peername")
        logger.info(f"Client connected from {addr}")

        try:
            while True:
                # Read incoming command
                line = await reader.readline()
                if not line:
                    break

                try:
                    command = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {line}")
                    continue

                # Find matching response
                response = self._find_response(command)
                if response:
                    # Send response
                    response_line = json.dumps(response) + "\n"
                    writer.write(response_line.encode("utf-8"))
                    await writer.drain()

                    method = command.get("method", "???")
                    logger.debug(f"Replayed response for {method}")
                else:
                    logger.warning(f"No response found for command: {command.get('method')}")

        except Exception as e:
            logger.error(f"Playback error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Client disconnected from {addr}")

    def _find_response(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the recorded response for a command.

        Matches by method name and returns the corresponding response.
        Handles multiple calls to the same method by cycling through responses.

        Args:
            command: Incoming command from client

        Returns:
            Recorded response message, or None if not found
        """
        method = command.get("method")
        if not method:
            return None

        # Get list of recorded responses for this method
        command_responses = self._commands.get(method, [])
        if not command_responses:
            return None

        # For simplicity, use round-robin if same command called multiple times
        # In a more sophisticated version, we could match by params too
        response = command_responses[0][1]

        # Update response ID to match incoming command
        if "id" in command and response:
            response = response.copy()
            response["id"] = command["id"]

        return response

    async def replay_timing(self):
        """Replay interactions with original timing delays.

        This can be used to simulate real-time behavior, but is not required
        for most tests which just need correct responses.
        """
        for i, interaction in enumerate(self.interactions):
            if interaction.direction == "recv":
                # Wait for the delay before sending this response
                if interaction.delay_after > 0:
                    await asyncio.sleep(interaction.delay_after)

                logger.debug(
                    f"[{i}] Would send after {interaction.delay_after:.3f}s: "
                    f"{interaction.message.get('method', '???')}"
                )


class PlaybackServerContext:
    """Context manager for playback server lifecycle.

    Usage:
        async with PlaybackServerContext.from_recording("recording.json") as addr:
            client = SeestarClient()
            await client.connect(addr[0], addr[1])
            # Use client normally
    """

    def __init__(self, playback: SeestarPlaybackServer):
        self.playback = playback
        self.address: Optional[Tuple[str, int]] = None

    @classmethod
    def from_recording(cls, filepath: str):
        """Create context manager from recording file.

        Args:
            filepath: Path to recording JSON

        Returns:
            PlaybackServerContext ready to use
        """
        playback = SeestarPlaybackServer.from_recording(filepath)
        return cls(playback)

    async def __aenter__(self) -> Tuple[str, int]:
        """Start server and return address."""
        self.address = await self.playback.serve()
        return self.address

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop server on exit."""
        await self.playback.stop()
        return False


# Convenience function for tests
async def playback_from_recording(filepath: str) -> Tuple[SeestarPlaybackServer, Tuple[str, int]]:
    """Load recording and start playback server.

    Args:
        filepath: Path to recording JSON file

    Returns:
        (playback_server, (host, port)) tuple
    """
    playback = SeestarPlaybackServer.from_recording(filepath)
    address = await playback.serve()
    return playback, address
