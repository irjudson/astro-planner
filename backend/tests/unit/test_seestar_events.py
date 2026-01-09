"""Tests for Seestar event streaming system."""

import asyncio
from datetime import datetime

import pytest

from app.clients.seestar_client import EventType, SeestarClient, SeestarEvent


class TestSeestarEventSystem:
    """Tests for event parsing, subscription, and dispatch."""

    @pytest.fixture
    def client(self):
        """Create test client instance."""
        return SeestarClient()

    def test_event_types(self):
        """Test that all expected event types exist."""
        assert EventType.PROGRESS_UPDATE
        assert EventType.STATE_CHANGE
        assert EventType.ERROR
        assert EventType.IMAGE_READY
        assert EventType.OPERATION_COMPLETE
        assert EventType.UNKNOWN

    def test_event_dataclass(self):
        """Test SeestarEvent dataclass creation."""
        event = SeestarEvent(
            event_type=EventType.PROGRESS_UPDATE, timestamp=datetime.now(), data={"percent": 50}, source_command="test"
        )

        assert event.event_type == EventType.PROGRESS_UPDATE
        assert event.data["percent"] == 50
        assert event.source_command == "test"

    def test_parse_progress_event(self, client):
        """Test parsing progress update message."""
        message = {
            "jsonrpc": "2.0",
            "method": "imaging_progress",
            "result": {"progress": 10, "percent": 20, "frame": 5, "total_frames": 50},
        }

        event = client._parse_event(message)

        assert event is not None
        assert event.event_type == EventType.PROGRESS_UPDATE
        assert event.data["progress"] == 10
        assert event.data["percent"] == 20
        assert event.data["frame"] == 5
        assert event.data["total_frames"] == 50

    def test_parse_state_change_event(self, client):
        """Test parsing state change message."""
        message = {"jsonrpc": "2.0", "method": "state_update", "result": {"state": "tracking", "stage": "idle"}}

        event = client._parse_event(message)

        assert event is not None
        assert event.event_type == EventType.STATE_CHANGE
        assert event.data["state"] == "tracking"
        assert event.data["stage"] == "idle"

    def test_parse_error_event(self, client):
        """Test parsing error message."""
        message = {"jsonrpc": "2.0", "method": "command_failed", "error": "Operation failed", "code": 203}

        event = client._parse_event(message)

        assert event is not None
        assert event.event_type == EventType.ERROR
        assert event.data["error"] == "Operation failed"
        assert event.data["code"] == 203

    def test_parse_image_ready_event(self, client):
        """Test parsing image ready message."""
        message = {
            "jsonrpc": "2.0",
            "method": "stacking_complete",
            "result": {"stacked": True, "filename": "image.fits"},
        }

        event = client._parse_event(message)

        assert event is not None
        assert event.event_type == EventType.IMAGE_READY
        assert event.data["filename"] == "image.fits"

    def test_parse_operation_complete_event(self, client):
        """Test parsing operation complete message."""
        message = {"jsonrpc": "2.0", "method": "focus_complete", "result": {"complete": True, "operation": "autofocus"}}

        event = client._parse_event(message)

        assert event is not None
        assert event.event_type == EventType.OPERATION_COMPLETE
        assert event.data["operation"] == "autofocus"
        assert event.data["success"] is True

    def test_subscribe_event(self, client):
        """Test subscribing to specific event type."""
        callback_called = []

        def callback(event):
            callback_called.append(event)

        client.subscribe_event(EventType.PROGRESS_UPDATE, callback)

        assert callback in client._event_callbacks[EventType.PROGRESS_UPDATE]

    def test_unsubscribe_event(self, client):
        """Test unsubscribing from event type."""

        def callback(event):
            pass

        client.subscribe_event(EventType.PROGRESS_UPDATE, callback)
        client.unsubscribe_event(EventType.PROGRESS_UPDATE, callback)

        assert callback not in client._event_callbacks[EventType.PROGRESS_UPDATE]

    def test_subscribe_all_events(self, client):
        """Test subscribing to all events."""
        callback_called = []

        def callback(event):
            callback_called.append(event)

        client.subscribe_all_events(callback)

        assert callback in client._all_events_callbacks

    def test_subscribe_progress(self, client):
        """Test subscribing to progress-only updates."""
        progress_updates = []

        def callback(percent, details):
            progress_updates.append((percent, details))

        client.subscribe_progress(callback)

        assert callback in client._progress_callbacks

    @pytest.mark.asyncio
    async def test_dispatch_event_to_type_callback(self, client):
        """Test that events are dispatched to type-specific callbacks."""
        events_received = []

        def callback(event):
            events_received.append(event)

        client.subscribe_event(EventType.PROGRESS_UPDATE, callback)

        # Create and dispatch a progress event
        event = SeestarEvent(
            event_type=EventType.PROGRESS_UPDATE, timestamp=datetime.now(), data={"percent": 50}, source_command="test"
        )

        await client._dispatch_event(event)

        assert len(events_received) == 1
        assert events_received[0] == event

    @pytest.mark.asyncio
    async def test_dispatch_event_to_all_events_callback(self, client):
        """Test that events are dispatched to all-events callbacks."""
        events_received = []

        def callback(event):
            events_received.append(event)

        client.subscribe_all_events(callback)

        # Create and dispatch various events
        event1 = SeestarEvent(event_type=EventType.PROGRESS_UPDATE, timestamp=datetime.now(), data={})
        event2 = SeestarEvent(event_type=EventType.STATE_CHANGE, timestamp=datetime.now(), data={})

        await client._dispatch_event(event1)
        await client._dispatch_event(event2)

        assert len(events_received) == 2

    @pytest.mark.asyncio
    async def test_dispatch_progress_to_progress_callback(self, client):
        """Test that progress events trigger progress callbacks."""
        progress_updates = []

        def callback(percent, details):
            progress_updates.append((percent, details))

        client.subscribe_progress(callback)

        # Create and dispatch a progress event
        event = SeestarEvent(
            event_type=EventType.PROGRESS_UPDATE,
            timestamp=datetime.now(),
            data={"percent": 75, "frame": 15, "total_frames": 20},
        )

        await client._dispatch_event(event)

        assert len(progress_updates) == 1
        assert progress_updates[0][0] == 75
        assert progress_updates[0][1]["frame"] == 15

    @pytest.mark.asyncio
    async def test_dispatch_handles_callback_exceptions(self, client):
        """Test that callback exceptions don't break event dispatch."""

        def bad_callback(event):
            raise Exception("Callback error")

        def good_callback(event):
            good_callback.called = True

        good_callback.called = False

        client.subscribe_all_events(bad_callback)
        client.subscribe_all_events(good_callback)

        event = SeestarEvent(event_type=EventType.PROGRESS_UPDATE, timestamp=datetime.now(), data={})

        # Should not raise exception
        await client._dispatch_event(event)

        # Good callback should still be called
        assert good_callback.called is True

    @pytest.mark.asyncio
    async def test_wait_for_goto_complete_success(self, client):
        """Test wait_for_goto_complete with successful goto."""

        # Mock the state change event after a delay
        async def send_tracking_event():
            await asyncio.sleep(0.1)
            event = SeestarEvent(
                event_type=EventType.STATE_CHANGE,
                timestamp=datetime.now(),
                data={"state": "tracking"},
                source_command="goto_target",
            )
            await client._dispatch_event(event)

        # Start sending event in background
        asyncio.create_task(send_tracking_event())

        # Wait for goto to complete
        success = await client.wait_for_goto_complete(timeout=1.0)

        assert success is True

    @pytest.mark.asyncio
    async def test_wait_for_goto_complete_timeout(self, client):
        """Test wait_for_goto_complete times out."""
        # Don't send any events - should timeout
        success = await client.wait_for_goto_complete(timeout=0.2)

        assert success is False

    @pytest.mark.asyncio
    async def test_wait_for_focus_complete_success(self, client):
        """Test wait_for_focus_complete with successful focus."""

        async def send_focus_complete_event():
            await asyncio.sleep(0.1)
            event = SeestarEvent(
                event_type=EventType.OPERATION_COMPLETE,
                timestamp=datetime.now(),
                data={"operation": "autofocus", "success": True, "position": 1234.5},
                source_command="auto_focus",
            )
            await client._dispatch_event(event)

        asyncio.create_task(send_focus_complete_event())

        success, position = await client.wait_for_focus_complete(timeout=1.0)

        assert success is True
        assert position == 1234.5

    @pytest.mark.asyncio
    async def test_wait_for_imaging_complete_success(self, client):
        """Test wait_for_imaging_complete with frame progression."""
        progress_calls = []

        def progress_callback(frame, total, percent):
            progress_calls.append((frame, total, percent))

        async def send_frame_events():
            for i in range(1, 6):
                await asyncio.sleep(0.05)
                event = SeestarEvent(
                    event_type=EventType.PROGRESS_UPDATE,
                    timestamp=datetime.now(),
                    data={"frame": i, "total_frames": 5, "percent": i * 20},
                )
                await client._dispatch_event(event)

        asyncio.create_task(send_frame_events())

        success = await client.wait_for_imaging_complete(
            expected_frames=5, progress_callback=progress_callback, timeout=2.0
        )

        assert success is True
        assert len(progress_calls) == 5
        assert progress_calls[-1] == (5, 5, 100)
