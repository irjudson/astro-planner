"""Tests for Seestar recording/playback infrastructure."""

import pytest

from tests.fixtures import PlaybackServerContext, SeestarPlaybackServer


class TestSeestarPlayback:
    """Tests for playback system functionality."""

    @pytest.mark.asyncio
    @pytest.mark.playback
    async def test_playback_loading(self):
        """Test that recording can be loaded."""
        playback = SeestarPlaybackServer.from_recording("tests/fixtures/recordings/connection_sequence.json")

        # Verify metadata loaded
        assert playback.metadata.telescope == "Seestar S50"
        assert playback.metadata.port == 4700
        assert len(playback.interactions) == 6

        # Verify command map was built
        assert "get_verify_str" in playback._commands
        assert "verify" in playback._commands

    @pytest.mark.asyncio
    @pytest.mark.playback
    async def test_playback_context_manager(self):
        """Test playback using context manager."""
        async with PlaybackServerContext.from_recording("tests/fixtures/recordings/connection_sequence.json") as (
            host,
            port,
        ):
            # Verify server is listening
            assert host == "127.0.0.1"
            assert port > 0

            # Note: Not connecting client yet to avoid auth issues
            # Full integration test will come later

    @pytest.mark.asyncio
    @pytest.mark.playback
    async def test_playback_direct(self):
        """Test playback server lifecycle."""
        playback = SeestarPlaybackServer.from_recording("tests/fixtures/recordings/connection_sequence.json")

        # Start server
        host, port = await playback.serve()

        assert host == "127.0.0.1"
        assert port > 0

        # Stop server
        await playback.stop()

    @pytest.mark.asyncio
    @pytest.mark.playback
    async def test_command_matching(self):
        """Test that playback server can match commands to responses."""
        playback = SeestarPlaybackServer.from_recording("tests/fixtures/recordings/connection_sequence.json")

        # Test finding response for get_verify_str
        command = {"method": "get_verify_str", "id": 12345, "jsonrpc": "2.0"}
        response = playback._find_response(command)

        assert response is not None
        assert response["id"] == 12345  # ID should be updated
        assert "result" in response
        assert response["code"] == 0
