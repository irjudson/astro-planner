# Seestar S50 Protocol Specification

Based on analysis of the seestar_alp project, this document describes the TCP protocol used to communicate with the Seestar S50 smart telescope.

## Connection Details

- **Protocol**: TCP socket (not WebSocket)
- **Default Host**: `seestar.local` (or IP address like `192.168.x.x`)
- **Port**: 5555 (default control port)
- **Message Format**: JSON with `\r\n` line terminator

### Connection Sequence

1. **Optional UDP Broadcast** (for guest mode):
   - Port: 4720
   - Message: `{"id":1,"method":"scan_iscope","params":""}`
   - This satisfies the Seestar's guest mode requirements

2. **TCP Connection**:
   - Connect to `host:5555`
   - Set timeout (recommended: 10s)

## Message Protocol

### Request Format
```json
{
  "method": "command_name",
  "params": {...},
  "id": integer_command_id
}
```

Messages must be terminated with `\r\n`.

### Response Format (Success)
```json
{
  "jsonrpc": "2.0",
  "Timestamp": "6671.087397143",
  "method": "command_name",
  "result": 0,
  "code": 0,
  "id": integer_command_id
}
```

### Response Format (Error)
```json
{
  "jsonrpc": "2.0",
  "Timestamp": "6671.332490709",
  "method": "command_name",
  "error": "fail to operate",
  "code": 207,
  "id": integer_command_id
}
```

### Error Codes
- `203`: Equipment is moving
- `207`: Failed to operate
- Others TBD

## Key Commands for Telescope Control

### 1. Goto Target with Start View
Start viewing mode and slew to target coordinates.

**Method**: `iscope_start_view`

**Parameters**:
```json
{
  "mode": "star",
  "target_ra_dec": [ra_hours, dec_degrees],
  "target_name": "M31",
  "lp_filter": false
}
```

**Example**:
```json
{
  "method": "iscope_start_view",
  "params": {
    "mode": "star",
    "target_ra_dec": [14.1286, 19.0814],
    "target_name": "M31",
    "lp_filter": false
  },
  "id": 10001
}
```

### 2. Direct Goto (Slew Only)
Slew telescope to coordinates without starting imaging.

**Method**: `scope_goto`

**Parameters**: `[ra_hours, dec_degrees]`

**Example**:
```json
{
  "method": "scope_goto",
  "params": [14.1286, 19.0814],
  "id": 10002
}
```

### 3. Start Stacking (Imaging)
Begin taking and stacking exposures.

**Method**: `iscope_start_stack`

**Parameters**:
```json
{
  "restart": true
}
```

**Example**:
```json
{
  "method": "iscope_start_stack",
  "params": {"restart": true},
  "id": 10003
}
```

### 4. Stop Current Operation
Stop slewing, imaging, or other operations.

**Method**: `iscope_stop_view`

**Parameters**:
```json
{
  "stage": "AutoGoto"  // or "Stack"
}
```

**Example - Stop Imaging**:
```json
{
  "method": "iscope_stop_view",
  "params": {"stage": "Stack"},
  "id": 10004
}
```

**Example - Stop Goto**:
```json
{
  "method": "iscope_stop_view",
  "params": {"stage": "AutoGoto"},
  "id": 10005
}
```

### 5. Auto Focus
Perform automatic focusing.

**Method**: `start_auto_focuse` (note the spelling)

**Parameters**: `{}`

**Example**:
```json
{
  "method": "start_auto_focuse",
  "params": {},
  "id": 10006
}
```

### 6. Get Device State
Query current telescope status.

**Method**: `get_device_state`

**Parameters**: `{}` (all state) or `{"keys": ["key_name"]}` (specific keys)

**Example - All State**:
```json
{
  "method": "get_device_state",
  "params": {},
  "id": 10007
}
```

**Example - Specific Keys**:
```json
{
  "method": "get_device_state",
  "params": {"keys": ["location_lon_lat"]},
  "id": 10008
}
```

### 7. Configure Settings
Set telescope configuration parameters.

**Method**: `set_setting`

**Parameters**: Various configuration objects

**Example - Exposure Settings**:
```json
{
  "method": "set_setting",
  "params": {
    "exp_ms": {
      "stack_l": 10000,
      "continuous": 500
    }
  },
  "id": 10009
}
```

**Example - Dither Settings**:
```json
{
  "method": "set_setting",
  "params": {
    "stack_dither": {
      "pix": 50,
      "interval": 10,
      "enable": true
    }
  },
  "id": 10010
}
```

**Example - Other Settings**:
```json
{
  "method": "set_setting",
  "params": {
    "auto_af": false,
    "stack_after_goto": false,
    "auto_3ppa_calib": true,
    "auto_power_off": false,
    "frame_calib": true
  },
  "id": 10011
}
```

### 8. Get Current Settings
Retrieve current telescope settings.

**Method**: `get_setting`

**Parameters**: `{}`

**Example**:
```json
{
  "method": "get_setting",
  "params": {},
  "id": 10012
}
```

### 9. Park Telescope
Park the telescope at home position.

**Method**: `scope_park`

**Parameters**: `{}`

**Example**:
```json
{
  "method": "scope_park",
  "params": {},
  "id": 10013
}
```

## Workflow for Automated Imaging

For the astronomus application, the typical workflow would be:

1. **Connect** to telescope via TCP socket
2. **Send UDP intro** (optional, for guest mode)
3. **Get device state** to verify connection
4. **Configure settings** (exposure time, dither, etc.)
5. For each target in the plan:
   - **Goto target** using `iscope_start_view`
   - Wait for goto to complete (monitor device state)
   - **Auto focus** using `start_auto_focuse`
   - Wait for focus to complete
   - **Start stacking** using `iscope_start_stack`
   - Image for specified duration
   - **Stop stacking** using `iscope_stop_view`
6. **Park telescope** when complete

## State Monitoring

The seestar_alp implementation uses event states to track operations:
- `AutoGoto` - Slewing to target
- `AutoFocus` - Focusing
- `Stack` - Imaging/stacking
- `DarkLibrary` - Creating dark frames
- `ScopeHome` - Parking

These states transition through: `start` → `working` → `complete` or `fail`

## Response Handling

The protocol is **synchronous request-response**:
- Send message with unique `id`
- Wait for response with matching `id`
- Timeout after ~10 seconds if no response
- Check for `error` field in response

## Additional Notes

- **Coordinates**: RA in decimal hours (0-24), Dec in decimal degrees (-90 to +90)
- **Exposure Times**: In milliseconds (ms)
- **Auto-incrementing IDs**: Command IDs should increment with each message
- **Reconnection**: If connection drops, send UDP intro again before reconnecting
- **Thread Safety**: The socket is not thread-safe; use locking for concurrent access
