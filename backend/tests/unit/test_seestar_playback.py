"""Tests for Seestar recording/playback infrastructure."""

import pytest

from app.clients.seestar_client import SeestarClient
from tests.fixtures import PlaybackServerContext, SeestarPlaybackServer


class TestSeestarPlayback:
    """Tests for playback system functionality."""

    @pytest.mark.asyncio
    @pytest.mark.recording("connection_sequence.json")
    async def test_playback_with_fixture(self, playback_server):
        """Test playback server using pytest fixture."""
        host, port = playback_server

        client = SeestarClient()
        await client.connect(host, port)

        # Verify connection worked
        assert client.connected

        await client.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.recording("connection_sequence.json")
    async def test_client_with_playback_fixture(self, seestar_client_with_playback):
        """Test using pre-connected client fixture."""
        client = seestar_client_with_playback

        assert client.connected
        assert client.status is not None

    @pytest.mark.asyncio
    async def test_playback_context_manager(self):
        """Test playback using context manager."""
        async with PlaybackServerContext.from_recording("tests/fixtures/recordings/connection_sequence.json") as (
            host,
            port,
        ):
            client = SeestarClient()
            await client.connect(host, port)

            assert client.connected

            await client.disconnect()

    @pytest.mark.asyncio
    async def test_playback_direct(self):
        """Test playback server directly."""
        playback = SeestarPlaybackServer.from_recording("tests/fixtures/recordings/connection_sequence.json")

        # Verify metadata loaded
        assert playback.metadata.telescope == "Seestar S50"
        assert playback.metadata.port == 4700
        assert len(playback.interactions) == 6

        # Start server
        host, port = await playback.serve()

        try:
            client = SeestarClient()
            await client.connect(host, port)

            assert client.connected

            await client.disconnect()
        finally:
            await playback.stop()
