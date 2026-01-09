# Seestar Telescope Session Recordings

This directory contains recorded TCP sessions with real Seestar S50 telescopes. These recordings can be replayed in tests to validate the SeestarClient without needing physical hardware.

## Available Recordings

### `connection_sequence.json`
- **Description**: Simple connection and authentication sequence
- **Duration**: 2.5s
- **Interactions**: 6 (3 commands, 3 responses)
- **Use case**: Basic connection tests, authentication validation

## Creating New Recordings

### Using the Interactive Recording Script

The easiest way to create new recordings is with the interactive script:

```bash
# Basic recording
python scripts/record_seestar_session.py \
  --name my_recording \
  --host 192.168.2.47 \
  --description "Description of what this records"

# Example: Record a goto sequence
python scripts/record_seestar_session.py \
  --name goto_m31 \
  --host 192.168.2.47 \
  --description "Goto M31 and wait for tracking"
```

The script will:
1. Start a recording proxy between your client and the telescope
2. Present an interactive command prompt
3. Record all traffic as you execute commands
4. Save the complete session when you type `quit`

### Available Commands in Interactive Mode

- `status` - Show telescope status
- `goto <ra> <dec> <name>` - Slew to coordinates
- `focus` - Start autofocus
- `imaging` - Start imaging session
- `stop` - Stop current operation
- `park` - Park telescope
- `info` - Get system info
- `quit` - End recording and save

### Programmatic Recording

You can also record programmatically:

```python
from tests.fixtures.seestar_recorder import SeestarSessionRecorder
from app.clients.seestar_client import SeestarClient

recorder = SeestarSessionRecorder(description="My test scenario")

async with recorder.intercept_connection("192.168.2.47", 4700) as (host, port):
    client = SeestarClient()
    await client.connect(host, port)

    # Perform operations
    await client.goto_target(10.0, 45.0, "Test Target")
    await client.auto_focus()

    await client.disconnect()

# Save recording
recorder.save("tests/fixtures/recordings/my_scenario.json")
```

## Using Recordings in Tests

### Method 1: Using pytest fixtures with marker

```python
import pytest
from app.clients.seestar_client import SeestarClient

@pytest.mark.recording("connection_sequence.json")
async def test_connection(playback_server):
    """Test connection using recorded session."""
    host, port = playback_server

    client = SeestarClient()
    await client.connect(host, port)

    assert client.connected
    await client.disconnect()
```

### Method 2: Using connected client fixture

```python
@pytest.mark.recording("connection_sequence.json")
async def test_with_client(seestar_client_with_playback):
    """Test with pre-connected client."""
    client = seestar_client_with_playback

    assert client.connected
    # Client auto-disconnects after test
```

### Method 3: Context manager

```python
from tests.fixtures import PlaybackServerContext

async def test_playback():
    async with PlaybackServerContext.from_recording(
        "tests/fixtures/recordings/connection_sequence.json"
    ) as (host, port):
        client = SeestarClient()
        await client.connect(host, port)
        # Test operations
        await client.disconnect()
```

## Recording File Format

Recordings are JSON files with this structure:

```json
{
  "recording_metadata": {
    "telescope": "Seestar S50",
    "firmware_version": "6.45",
    "recorded_at": "2026-01-09T14:00:00Z",
    "duration_seconds": 2.5,
    "description": "Description",
    "host": "192.168.2.47",
    "port": 4700
  },
  "interactions": [
    {
      "timestamp": 0.0,
      "direction": "send",
      "message": { "method": "command", "id": 10000, "jsonrpc": "2.0" },
      "delay_after": 0.15
    },
    {
      "timestamp": 0.15,
      "direction": "recv",
      "message": { "jsonrpc": "2.0", "result": {}, "code": 0, "id": 10000 },
      "delay_after": 0.0
    }
  ]
}
```

Each interaction has:
- **timestamp**: Time relative to session start (seconds)
- **direction**: `"send"` (client → telescope) or `"recv"` (telescope → client)
- **message**: The JSON-RPC message
- **delay_after**: Time until next interaction (for timing reproduction)

## Best Practices

1. **Keep recordings focused** - One recording per test scenario
2. **Use descriptive names** - `goto_m31_success.json` not `test1.json`
3. **Add clear descriptions** - Explain what the recording demonstrates
4. **Test edge cases** - Record both success and error scenarios
5. **Keep recordings small** - Trim unnecessary interactions
6. **Version control** - Commit recordings to git for team use

## Standard Test Scenarios

These recordings are recommended for comprehensive test coverage:

- [x] `connection_sequence.json` - Basic connection/auth
- [ ] `goto_success.json` - Successful slew to target
- [ ] `goto_failure_moving.json` - Goto rejected (already moving)
- [ ] `imaging_session.json` - Full imaging workflow
- [ ] `autofocus_session.json` - Autofocus operation
- [ ] `park_sequence.json` - Park telescope
- [ ] `plan_execution.json` - Multi-target observation plan
- [ ] `error_scenarios.json` - Various error conditions

## Troubleshooting

### Recording is empty
- Ensure telescope is powered on and accessible
- Check firewall rules allow TCP connections
- Verify telescope IP address is correct

### Playback doesn't match commands
- Command order may differ from recording
- Use more specific recordings for complex sequences
- Check that command parameters match exactly

### Tests fail with playback but work with real hardware
- Timing differences may reveal race conditions
- Check for commands not in recording
- Verify response IDs match request IDs

## Contributing Recordings

When adding new recordings:

1. Record with latest firmware version
2. Add entry to "Available Recordings" section above
3. Include description, duration, and use case
4. Test that playback works in at least one test
5. Commit recording to git
