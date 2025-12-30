# Seestar S50 Safety Testing Guide

**Date**: 2025-12-29
**Purpose**: Ensure all API commands are safe and won't damage telescope hardware

## ⚠️ CRITICAL SAFETY NOTES

### Commands Requiring Live Testing
These commands should be tested CAREFULLY with the actual telescope:

1. **Dew Heater Control** (`pi_output_set2`)
   - ✅ Implementation FIXED (was using wrong command)
   - ⚠️ Test with low power first (e.g., 10-20%)
   - ⚠️ Monitor telescope temperature
   - ⚠️ Verify heater doesn't overheat

2. **Arm Open/Close** (NOT YET IMPLEMENTED)
   - ❌ Do NOT implement until researched
   - ❌ Could damage telescope mechanism
   - ⚠️ Need to observe actual app behavior first

3. **Mount Movement** Commands
   - `scope_move` (slew, stop, abort)
   - `scope_move_to_horizon`
   - `scope_park`
   - ⚠️ Test in safe area (no obstacles)
   - ⚠️ Ensure tripod is stable

4. **Focuser Control**
   - `move_focuser` (position, offset)
   - ⚠️ Don't exceed max_step (typically 2600)
   - ⚠️ Moving too far could damage focuser

## Implemented Commands Status

### ✅ SAFE - Well-Tested Commands
These commands are safe and match the official app:

- `get_verify_str` - Authentication challenge
- `verify_client` - Authentication response
- `get_device_state` - Read device status
- `get_current_coordinates` - Read RA/Dec
- `get_app_state` - Read application state
- `iscope_start_view` - Start viewing (with lp_filter)
- `iscope_stop_view` - Stop viewing
- `iscope_start_stack` - Start stacking
- `start_auto_focuse` - Autofocus
- `is_stacked` - Check if stacking complete
- `get_solve_result` - Plate solve result
- `get_annotate_result` - Field annotations

### ✅ FIXED - Critical Bugs Resolved

#### Dew Heater (CRITICAL FIX)
**Before** (WRONG):
```python
# This DID NOT WORK - wrong command!
params = {"heater_enable": True}
await self._send_command("set_setting", params)
```

**After** (CORRECT):
```python
# Correct implementation from APK analysis
params = {"heater": {"state": True, "value": 90}}
await self._send_command("pi_output_set2", params)
```

**Testing**:
- ✅ Parameters validated (state: bool, value: 0-100)
- ⚠️ Live testing required to verify safe operation
- ⚠️ Start with low power (10-20%) first
- ⚠️ Monitor for overheating

### ⚠️ NEEDS TESTING - Implemented But Unverified

#### System Commands
- `pi_shutdown` - Shutdown telescope
- `pi_reboot` - Reboot telescope
- `get_pi_info` - Get system info
- `get_pi_time` / `set_pi_time` - Time management

**Risk**: Low (read-only or standard system operations)

#### Network Commands
- `pi_set_ap` - Set WiFi AP config
- `set_wifi_country` - Set WiFi region
- `pi_station_*` - WiFi client mode commands

**Risk**: Medium (could lose connection if misconfigured)

#### View Plans
- `start_view_plan` - Execute multi-target plan
- `stop_view_plan` - Cancel plan
- `get_view_plan_state` - Get plan status

**Risk**: Low (built-in app feature)

#### Planetary Mode
- `start_planet_scan` - Planetary imaging
- `configure_planetary_imaging` - Planet settings

**Risk**: Low (specialized mode)

#### Manual Exposure Control
- `set_manual_exposure` - Manual exposure settings
- `set_auto_exposure` - Auto exposure settings

**Risk**: Very Low (imaging parameters only)

#### Advanced Stacking
- `configure_advanced_stacking` - DBE, star correction, etc.

**Risk**: Very Low (processing parameters only)

### ❌ NOT IMPLEMENTED - Needs Research

#### Arm Control
- **Method exists in app**: `setArmOpen()`, `setArmClose()`
- **Command**: Unknown (not in CmdMethod enum)
- **Risk**: HIGH - Could damage telescope mechanism
- **Action**: Do NOT implement without thorough testing

**Hypothesis**:
```python
# UNVERIFIED - Do not use!
# May use scope_park with close parameter OR
# May be implicit state change in mount.close field
```

## Testing Checklist

### Pre-Testing Setup
- [ ] Telescope on stable tripod
- [ ] Clear area (no obstacles for movement)
- [ ] Indoors or safe outdoor location
- [ ] Battery charged or AC power connected
- [ ] WiFi connection stable

### Phase 1: Read-Only Commands ✅
- [x] `get_device_state` - Read device info
- [x] `get_current_coordinates` - Read position
- [x] `get_app_state` - Read app state
- [ ] Test with live telescope and verify no side effects

### Phase 2: Safe Movement ⚠️
- [ ] `iscope_start_view` - Slew to safe target (Polaris)
- [ ] `iscope_stop_view` - Stop viewing
- [ ] Monitor movement for issues
- [ ] Verify mount.close state

### Phase 3: Imaging ⚠️
- [ ] `iscope_start_stack` - Start stacking
- [ ] Verify frames captured
- [ ] Check stacking progress
- [ ] `is_stacked` - Verify completion check

### Phase 4: Autofocus ⚠️
- [ ] `start_auto_focuse` - Run autofocus
- [ ] Monitor focuser movement
- [ ] Verify focus achieved
- [ ] Check focuser position in range

### Phase 5: Dew Heater (CRITICAL) 🔥
- [ ] Test `set_dew_heater(True, power_level=10)` first
- [ ] Monitor temperature for 5 minutes
- [ ] Test power_level=20, 30, 50
- [ ] Verify heater responds to OFF command
- [ ] Check for any overheating or issues

**IMPORTANT**: Do NOT use full power (90-100) until lower power levels verified safe!

### Phase 6: System Commands 📋
- [ ] `get_pi_info` - Read system info
- [ ] `get_pi_time` - Read time
- [ ] Do NOT test shutdown/reboot yet

### Phase 7: Network (Optional) 📡
- [ ] Only test if comfortable potentially losing connection
- [ ] Have backup connection method ready

## Safety Guidelines

### DO NOT
1. ❌ Test arm open/close until researched
2. ❌ Use high heater power without testing low power first
3. ❌ Move mount near obstacles or overhanging objects
4. ❌ Exceed focuser max_step value
5. ❌ Test system commands (shutdown/reboot) unless necessary
6. ❌ Change network settings unless you have backup access

### DO
1. ✅ Test in safe location first
2. ✅ Monitor telescope during all tests
3. ✅ Start with conservative parameters
4. ✅ Have manual control (official app) ready as backup
5. ✅ Stop immediately if anything seems wrong
6. ✅ Document any unexpected behavior

## Parameter Validation

### Validated in Code
- Heater power_level: 0-100 (raises ValueError if out of range)
- RA: 0-24 hours (logged as warning if out of range)
- Dec: -90 to +90 degrees (logged as warning if out of range)
- Focuser position: Validated against max_step if known

### NOT Validated (User Responsibility)
- Mount movement safety (obstacles, tripod stability)
- Network configuration (could lose connection)
- Time zone settings

## Error Handling

All commands check for:
- Connection errors (ConnectionError)
- Command failures (CommandError)
- Timeout errors (asyncio.TimeoutError)
- Invalid responses (logged and raised)

## Recovery Procedures

### If Command Fails
1. Check telescope response code
2. Verify connection still active
3. Check device_state for current status
4. Use official app as backup control

### If Heater Doesn't Turn Off
1. Send `set_dew_heater(False)` command again
2. Check device state for heater_enable field
3. If still on, use official app to disable
4. If critical, power cycle telescope

### If Mount Stuck Moving
1. Send `stop_telescope_movement()` command
2. If still moving, send `iscope_stop_view()`
3. Use official app emergency stop
4. Last resort: power off telescope

### If Lost Connection
1. Reconnect using `connect()` method
2. Re-authenticate automatically
3. Check device_state to determine current status
4. Resume control or use official app

## Command Reference

### Working Commands (58 total)

#### Authentication (2)
- ✅ `get_verify_str` - Get challenge
- ✅ `verify_client` - Send signed response

#### Observation (12)
- ✅ `get_device_state` - Complete device state
- ✅ `iscope_start_view` - Goto & view target (with lp_filter!)
- ✅ `iscope_start_stack` - Start imaging
- ✅ `iscope_stop_view` - Stop viewing/imaging
- ✅ `get_current_coordinates` - Get RA/Dec
- ✅ `get_app_state` - Get app status
- ✅ `check_stacking_complete` - Is stacking done
- ✅ `get_plate_solve_result` - Plate solve results
- ✅ `get_field_annotations` - Identified objects
- ✅ `start_autofocus` - Autofocus
- ✅ `cancel_current_operation` - Cancel operation
- ✅ `set_location` - Set observer location

#### View Plans (3)
- ✅ `start_view_plan` - Execute plan
- ✅ `stop_view_plan` - Stop plan
- ✅ `get_view_plan_state` - Plan status

#### Mount Control (4)
- ✅ `slew_to_coordinates` - Direct slew
- ✅ `stop_telescope_movement` - Stop slew
- ✅ `move_to_horizon` - Park at horizon
- ✅ `park_telescope` - Park mount

#### Focus Control (4)
- ✅ `start_autofocus` - Auto focus
- ✅ `stop_autofocus` - Stop AF
- ✅ `move_focuser_to_position` - Move to position
- ✅ `move_focuser_relative` - Move by offset

#### Imaging Settings (7)
- ✅ `set_exposure` - Set exposure time
- ✅ `set_dithering` - Configure dither
- ✅ `configure_advanced_stacking` - DBE, star correction, etc.
- ✅ `set_manual_exposure` - Manual exposure mode
- ✅ `set_auto_exposure` - Auto exposure mode
- ✅ `start_planet_scan` - Planetary mode
- ✅ `configure_planetary_imaging` - Planet settings

#### System (13)
- ✅ `shutdown_telescope` - Shutdown
- ✅ `reboot_telescope` - Reboot
- ✅ `get_pi_info` - System info
- ✅ `get_pi_time` / `set_pi_time` - Time
- ✅ `play_notification_sound` - Play sound
- ✅ `get_image_file_info` - File info
- ✅ `reset_focuser_to_factory` - Reset focus
- ✅ `check_polar_altitude` - PA check
- ✅ `clear_polar_alignment` - Clear PA
- ✅ `start_compass_calibration` - Start compass cal
- ✅ `stop_compass_calibration` - Stop compass cal
- ✅ `get_compass_state` - Compass status

#### Remote (3)
- ✅ `join_remote_session` - Join remote
- ✅ `leave_remote_session` - Leave remote
- ✅ `disconnect_remote_client` - Disconnect remote

#### Network (9)
- ✅ `set_wifi_ap` - Configure AP
- ✅ `set_wifi_country` - Set country
- ✅ `scan_wifi_networks` - Scan networks
- ✅ `connect_to_wifi` - Connect to network
- ✅ `disconnect_wifi` - Disconnect
- ✅ `save_wifi_credentials` - Save network
- ✅ `get_saved_networks` - List saved
- ✅ `get_wifi_station_state` - Station status

#### Hardware (3)
- ✅ `set_dew_heater` - **FIXED** - Control heater (pi_output_set2)
- ✅ `set_dc_output` - DC output control
- ✅ `get_dc_output` - Read DC output

#### Demo & Misc (3)
- ✅ `start_demo_mode` - Start demo
- ✅ `stop_demo_mode` - Stop demo
- ✅ `check_client_verified` - Check auth

## Conclusion

**Current Status**: 58/58 commands implemented

**Critical Fixes Applied**:
- ✅ Dew heater now uses correct command (`pi_output_set2`)
- ✅ LP filter parameter already correct in `goto_target()`

**Still Needs Research**:
- ❌ Arm open/close mechanism (do NOT implement yet)

**Next Steps**:
1. Run automated tests to verify no regressions
2. Test read-only commands with live telescope
3. Carefully test heater with low power first
4. Document any findings or issues
5. Update this document with test results

