# Seestar S50 API Command Reference

Documentation of all available JSON-RPC commands from decompiled Seestar v3.0.0 APK.

**Protocol**: JSON-RPC 2.0 over TCP port 4700
**Format**: `{"method": "<method_name>", "params": <object|null>, "id": <number>, "jsonrpc": "2.0"}\r\n`
**Authentication**: Required via `get_verify_str` + `verify_client` (firmware 6.45+)

---

## Implementation Priority

### 🔴 PRIORITY 1: Real-Time Observation & Tracking

Essential for live observation and automated imaging.

#### ✅ Already Implemented
- `get_device_state` - Get complete device state
- `iscope_start_view` - Start viewing/goto target
- `iscope_start_stack` - Start stacking
- `iscope_stop_view` - Stop imaging/viewing
- `start_auto_focuse` - Autofocus

#### ⭐ NEEDS IMPLEMENTATION - Critical for Observation

**`scope_get_equ_coord`** - Get current RA/Dec coordinates
- **Priority**: HIGHEST - Required for real-time tracking
- **Use**: Monitor current telescope position
- **Params**: `{}`
- **Returns**: `{"ra": <hours>, "dec": <degrees>}`
- **Implementation**: Poll every 1-5 seconds during observation
- **File**: CmdMethod.java line 47

**`iscope_get_app_state`** - Get application state
- **Priority**: HIGH - Required for monitoring imaging progress
- **Use**: Check current operation status (slewing, focusing, stacking, etc.)
- **Params**: `{}`
- **Returns**: State information including stage, progress, frame counts
- **Implementation**: Poll during operations for status updates
- **File**: CmdMethod.java line 38

**`is_stacked`** - Check if stacking is complete
- **Priority**: HIGH - Know when imaging session is done
- **Use**: Determine if enough frames have been captured
- **Params**: `{}`
- **Returns**: `{"is_stacked": <boolean>}`
- **Implementation**: Check before moving to next target

**`get_solve_result`** - Get plate solve result
- **Priority**: MEDIUM - Verify goto accuracy
- **Use**: Confirm telescope is pointed at correct target
- **Params**: `{}`
- **Returns**: Plate solving results with actual RA/Dec
- **Implementation**: Call after goto completes

**`get_annotate_result`** - Get annotation results
- **Priority**: MEDIUM - Identify objects in field
- **Use**: Confirm correct target framing
- **Params**: `{}`
- **Returns**: Identified objects in current field

---

### 🟠 PRIORITY 2: View Plans & Automated Sequences

For automated multi-target observation sessions.

**`start_view_plan`** - Execute automated observation plan
- **Priority**: HIGH - Core automation feature
- **Use**: Run multi-target imaging sequences
- **Params**: Plan configuration object
- **Returns**: Success/failure
- **Notes**: View plans are the Seestar's built-in scheduling system
- **File**: Look for ViewPlanCmd or related in APK

**`stop_view_plan`** - Stop running plan
- **Priority**: HIGH
- **Use**: Cancel automated sequence
- **Params**: `{}`

**`get_view_plan_state`** - Get plan execution state
- **Priority**: HIGH
- **Use**: Monitor plan progress
- **Params**: `{}`
- **Returns**: Current plan status, target, progress

---

### 🟡 PRIORITY 3: Planetary Observation Mode

Specialized commands for planetary imaging.

**`start_scan_planet`** - Start planetary scanning
- **Priority**: MEDIUM - Planetary mode is different workflow
- **Use**: Activate planet-specific imaging mode
- **Params**: Planet configuration
- **Returns**: Success/failure
- **Notes**: Uses different stacking algorithm optimized for planets

**`set_setting` with planet-specific params**
- **Priority**: MEDIUM
- **Use**: Configure planetary imaging settings
- **Params**: `{"stack": {"capt_type": "planet", ...}}`
- **Notes**: Different exposure, gain, frame rate for planets

---

### 🟢 PRIORITY 4: Enhanced Control & Monitoring

Nice-to-have features for better control.

#### Movement & Positioning

**`scope_move`** - Direct mount movement
- **Priority**: MEDIUM
- **Use**: Slew to coordinates, stop movement, manual control
- **Params**: `{"action": "slew|stop|abort", "ra": <hours>, "dec": <degrees>}`
- **File**: CmdMethod.java line 45

**`scope_move_to_horizon`** - Move to horizon position
- **Priority**: LOW
- **Use**: Safe parking at horizon
- **Params**: Azimuth/altitude

**✅ `scope_park`** - Already implemented

#### Focus Control

**`move_focuser`** - Manual focus adjustment
- **Priority**: MEDIUM - Useful for fine-tuning
- **Use**: Move focuser to specific position or by steps
- **Params**: `{"step": <position>}` or `{"offset": <delta>}`
- **File**: CmdMethod.java line 31

**`reset_factory_focal_pos`** - Reset to factory focus
- **Priority**: LOW
- **Use**: Return to default focus position
- **Params**: `{}`

**✅ `start_auto_focuse`** - Already implemented
**✅ `stop_auto_focuse`** - Need to implement

#### Imaging Settings

**✅ `set_setting`** - Already implemented (exposure, dither)
- Need to expand for additional settings:
  - `{"stack": {"dbe": <bool>}}` - Dark background extraction
  - `{"stack": {"star_correction": <bool>}}` - Star correction
  - `{"stack": {"airplane_line_removal": <bool>}}` - Satellite trail removal
  - `{"stack": {"drizzle2x": <bool>}}` - 2x drizzle upsampling
  - `{"stack": {"save_discrete_frame": <bool>}}` - Save individual frames
  - `{"stack": {"capt_num": <int>}}` - Number of frames to capture
  - `{"ae_bri_percent": <float>}` - Auto-exposure brightness target
  - `{"manual_exp": <bool>}` - Manual exposure mode
  - `{"isp_exp_ms": <float>}` - Manual exposure time
  - `{"isp_gain": <float>}` - Manual gain

---

### 🔵 PRIORITY 5: System Management

Operational commands for device management.

#### System Control

**`pi_shutdown`** - Shutdown telescope
- **Priority**: MEDIUM - Clean shutdown
- **Use**: Power down device safely
- **Params**: `{}`
- **File**: CmdMethod.java line 78

**`pi_reboot`** - Reboot telescope
- **Priority**: MEDIUM - Recovery from errors
- **Use**: Restart device
- **Params**: `{}`

**`pi_get_time`** - Get system time
- **Priority**: LOW - Useful for time sync
- **Params**: `{}`

**`pi_set_time`** - Set system time
- **Priority**: LOW
- **Params**: `{"time": <unix_timestamp>}`

#### File Management

**`get_img_file_info`** - Get image file information
- **Priority**: MEDIUM - Track captured images
- **Use**: List and download captured FITS/images
- **Params**: File path or query
- **Returns**: File metadata (size, timestamp, exposure info)
- **File**: CmdMethod.java line 71

**File Transfer Protocol**
- **Port**: 4801 (FILE port from DevicePort.java)
- **Use**: Download captured images
- **Priority**: MEDIUM - Retrieve images for processing

#### Network Management

**`pi_set_ap`** - Set WiFi AP configuration
- **Priority**: LOW
- **Use**: Configure telescope's WiFi access point
- **Params**: `{"ssid": <string>, "passwd": <string>, "is_5g": <bool>}`

**`pi_station_*`** - WiFi station management
- `pi_station_open` - Enable WiFi client mode
- `pi_station_close` - Disable WiFi client mode
- `pi_station_scan` - Scan for networks
- `pi_station_select` - Connect to network
- `pi_station_set` - Save network credentials
- `pi_station_list` - List saved networks
- **Priority**: LOW - Advanced networking

**`set_wifi_country`** - Set WiFi regulatory domain
- **Priority**: LOW
- **Params**: `{"country": <country_code>}`

---

### 🟣 PRIORITY 6: Calibration & Alignment

Precision setup commands.

#### Polar Alignment

**`check_pa_alt`** - Check polar alignment altitude
- **Priority**: MEDIUM - Important for accurate tracking
- **Use**: Verify polar alignment quality
- **Params**: `{}`
- **Returns**: Alignment error in arc-minutes

**`clear_polar_align`** - Clear polar alignment
- **Priority**: LOW
- **Use**: Reset alignment and re-do
- **Params**: `{}`

**3-Point Polar Alignment**
- Multiple commands for automated 3PPA
- **Priority**: LOW - Advanced feature
- **Notes**: Requires specific sequence of moves and plate solves

#### Compass Calibration

**`start_compass_calibration`** - Start compass calibration
- **Priority**: LOW
- **Use**: Calibrate internal compass
- **Params**: `{}`

**`stop_compass_calibration`** - Stop compass calibration
- **Priority**: LOW

**`get_compass_state`** - Get compass state
- **Priority**: LOW
- **Returns**: Compass heading, calibration status

---

### ⚪ PRIORITY 7: Utility & Convenience

Nice-to-have features.

**`play_sound`** - Play notification sound
- **Priority**: LOW - User feedback
- **Use**: Audio notifications for events
- **Params**: `{"sound": <sound_type>}` or `{"volume": <level>}`
- **File**: CmdMethod.java line 56

**`iscope_cancel_view`** - Cancel current view
- **Priority**: LOW - Alternative to stop
- **Use**: Abort current operation
- **Params**: `{}`

**`pi_output_set2` / `pi_output_get2`** - Control DC outputs
- **Priority**: LOW - Advanced hardware control
- **Use**: Control dew heater, auxiliary devices
- **Params**: Output configuration
- **Notes**: For controlling external devices via DC ports

**`remote_join` / `remote_disjoin` / `remote_disconnect`**
- **Priority**: LOW - Multi-client management
- **Use**: Remote observation sessions
- **Notes**: Allow multiple clients, remote control

**`start_demonstrate` / `stop_demonstrate`**
- **Priority**: LOW - Demo mode
- **Use**: Exhibition/demo mode without actual movement

**`pi_encrypt`**
- **Priority**: UNKNOWN - Need to investigate
- **Use**: Encryption-related functionality

---

## Authentication Commands

**✅ `get_verify_str`** - Implemented
**✅ `verify_client`** - Implemented

**`pi_is_verified`** - Check verification status
- **Priority**: LOW - Validation only
- **Returns**: `{"is_verified": <bool>}`

---

## Command Categories Summary

| Category | Total | Implemented | Priority 1-2 | Priority 3-4 | Priority 5-7 |
|----------|-------|-------------|--------------|--------------|--------------|
| Authentication | 3 | 2 | 0 | 0 | 1 |
| Observation | 12 | 5 | 5 | 0 | 2 |
| Mount Control | 4 | 1 | 1 | 1 | 1 |
| Focus | 4 | 1 | 0 | 1 | 2 |
| Settings | 2 | 2 | 0 | 0 | 0 |
| Plans | 3 | 0 | 3 | 0 | 0 |
| Planetary | 2 | 0 | 0 | 2 | 0 |
| System | 15 | 0 | 0 | 0 | 15 |
| Calibration | 6 | 0 | 0 | 0 | 6 |
| Utility | 7 | 0 | 0 | 0 | 7 |
| **TOTAL** | **58** | **11** | **9** | **4** | **34** |

---

## Implementation Roadmap

### Phase 1: Real-Time Observation (Priority 1)
1. ✅ Authentication (completed)
2. ⭐ `scope_get_equ_coord` - Real-time coordinate tracking
3. ⭐ `iscope_get_app_state` - Operation status monitoring
4. ⭐ `is_stacked` - Completion detection
5. `get_solve_result` - Goto verification
6. `get_annotate_result` - Target identification

### Phase 2: Automated Sequences (Priority 2)
1. `start_view_plan` - Execute plans
2. `stop_view_plan` - Cancel plans
3. `get_view_plan_state` - Monitor plans

### Phase 3: Planetary Mode (Priority 3)
1. `start_scan_planet` - Planetary imaging
2. Expand `set_setting` for planetary params

### Phase 4: Enhanced Control (Priority 4)
1. `scope_move` - Direct mount control
2. `move_focuser` - Manual focus
3. `stop_auto_focuse` - Focus abort
4. Expand `set_setting` for advanced imaging params

### Future Phases (Priority 5-7)
- System management
- File transfer protocol
- Calibration commands
- Utility features

---

## Port Reference

| Port | Service | Use |
|------|---------|-----|
| 4700 | SOCKET | JSON-RPC control (main API) |
| 4554 | RTMP | Video stream (telephoto) |
| 4555 | RTMP_WIDE | Video stream (wide angle) |
| 4800 | PIC | Image transmission (telephoto) |
| 4804 | PIC_WIDE | Image transmission (wide angle) |
| 4801 | FILE | File transfers |
| 4350 | FW_SOCKET | Firmware socket |
| 4361 | FW_UPLOAD | Firmware upload |
| 8080 | HTTP | HTTP services (localhost) |

---

## Response Format

All commands return JSON-RPC 2.0 responses:

```json
{
  "jsonrpc": "2.0",
  "method": "<method_name>",
  "result": <result_object|0>,
  "code": 0,
  "id": <request_id>,
  "Timestamp": "<device_timestamp>"
}
```

**Success**: `"code": 0` and/or `"result": 0` (for commands) or result object (for queries)
**Error**: `"error": <error_message>` and/or `"code": <error_code>`

---

## Source Files

Decompiled from Seestar v3.0.0 APK:
- **CmdMethod.java** - Complete command list
- **DevicePort.java** - Port definitions
- **MainSocket.java** - Socket management
- **VerifyClientParam.java** - Authentication params
- **GetVerifyStrResult.java** - Challenge response

APK Location: `/tmp/seestar_v3_decompiled/`

---

## Notes

- Commands are case-sensitive
- All communication requires `\r\n` line terminator
- Authentication required for all commands (firmware 6.45+)
- Some commands may require specific device states (e.g., can't stack while slewing)
- Timestamp format appears to be device uptime in seconds
- Multi-client support exists but master/slave roles not fully documented
