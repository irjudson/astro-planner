"""Tests for Seestar S50 client."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.clients.seestar_client import (
    CommandError,
    ConnectionError,
    SeestarClient,
    SeestarState,
    SeestarStatus,
    TimeoutError,
)


class TestSeestarClient:
    """Test suite for SeestarClient."""

    @pytest.fixture
    def client(self):
        """Create test client instance."""
        return SeestarClient()

    def test_init(self, client):
        """Test client initialization."""
        assert not client.connected
        assert client.status.state == SeestarState.DISCONNECTED
        assert client.status.connected is False

    @pytest.mark.asyncio
    async def test_connect_timeout(self, client):
        """Test connection timeout."""
        with pytest.raises(ConnectionError, match="Failed to connect"):
            # Use invalid host to trigger connection error
            await client.connect("invalid.host.test", port=9999)

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, client):
        """Test disconnect when not connected (should not raise error)."""
        await client.disconnect()
        assert not client.connected

    def test_command_when_not_connected(self, client):
        """Test sending command when not connected."""

        async def test():
            with pytest.raises(ConnectionError, match="Not connected"):
                await client._send_command("test_method")

        asyncio.run(test())

    def test_status_updates(self, client):
        """Test status property returns current status."""
        status = client.status
        assert isinstance(status, SeestarStatus)
        assert status.connected is False
        assert status.state == SeestarState.DISCONNECTED

    def test_connected_property(self, client):
        """Test connected property."""
        assert client.connected is False
        # Simulate connection
        client._connected = True
        assert client.connected is True

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, client):
        """Test disconnect cleans up resources."""
        # Simulate partial connection state
        client._connected = True
        mock_writer = Mock()
        mock_writer.close = Mock()
        mock_writer.wait_closed = AsyncMock()
        client._writer = mock_writer

        await client.disconnect()

        assert not client.connected
        assert client._writer is None  # Should be cleared
        mock_writer.close.assert_called_once()

    def test_state_enum_values(self):
        """Test SeestarState enum has expected values."""
        assert SeestarState.DISCONNECTED.value == "disconnected"
        assert SeestarState.CONNECTED.value == "connected"
        assert SeestarState.SLEWING.value == "slewing"
        assert SeestarState.TRACKING.value == "tracking"
        assert SeestarState.FOCUSING.value == "focusing"
        assert SeestarState.IMAGING.value == "imaging"

    def test_custom_exceptions(self):
        """Test custom exception classes."""
        conn_err = ConnectionError("test")
        assert str(conn_err) == "test"
        assert isinstance(conn_err, Exception)

        cmd_err = CommandError("test")
        assert str(cmd_err) == "test"

        timeout_err = TimeoutError("test")
        assert str(timeout_err) == "test"

    @pytest.mark.asyncio
    async def test_status_callback(self, client):
        """Test status callback mechanism."""
        callback_called = []

        def status_callback(status):
            callback_called.append(status)

        client.set_status_callback(status_callback)

        # Trigger a status update
        client._update_status(connected=True, state=SeestarState.CONNECTED)

        assert len(callback_called) == 1
        assert callback_called[0].connected is True


# Note: Full integration tests would require either:
# 1. A real Seestar S50 telescope
# 2. A mock TCP server simulating the Seestar protocol
# 3. The seestar_alp simulator if available

# The tests above cover the basic functionality using mocks
