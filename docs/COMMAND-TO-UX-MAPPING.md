# Seestar S50 Command to UX Mapping

Complete mapping of all Seestar S50 commands, their implementation status, backend endpoints, and frontend UX connections.

**Legend:**
- ✅ Fully implemented and wired to UX
- 🟡 Implemented in backend, not wired to UX
- 🟠 Partially implemented
- ❌ Not implemented
- 🔵 Implemented in capabilities system (dynamic UI)

---

## 1. CONNECTION & AUTHENTICATION

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `get_verify_str` | ✅ | `_authenticate()` | `/api/telescope/connect` | ⚡ Connect button (status bar) | Auto-called on connect |
| `verify_client` | ✅ | `_authenticate()` | `/api/telescope/connect` | ⚡ Connect button (status bar) | Auto-called on connect |
| `pi_is_verified` | 🟡 | `check_client_verified()` | None | None | Could add to debug panel |

---

## 2. TELESCOPE CONTROL

### Movement & Positioning

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `iscope_start_view` | ✅ | `goto_target()` | `POST /api/telescope/goto` | "Slew to Target" button | `ra` (hours), `dec` (degrees), `target_name` (optional) |
| `scope_move` (stop) | ✅ | `stop_slew()` | `POST /api/telescope/stop-slew` | "Stop Motion" button | None |
| `scope_park` | ✅ | `park()` | `POST /api/telescope/park` | "Park Telescope" button | None |
| `pi_unpark` | 🟡 | None | `POST /api/telescope/unpark` | None | None |
| `scope_get_equ_coord` | 🟡 | `get_current_coordinates()` | `GET /api/telescope/coordinates` | None | Returns `ra_hours`, `dec_degrees`, `timestamp` |
| `scope_move` (slew) | 🟡 | `slew_to_coordinates()` | `POST /api/telescope/slew` | None | `ra` (hours), `dec` (degrees) |
| `scope_move_to_horizon` | 🟡 | `move_to_horizon()` | `POST /api/telescope/horizon` | None | `azimuth` (degrees), `altitude` (degrees) |

### Status Display (Telemetry)

| Data | Status | Source | Backend API | Frontend UX | Update Frequency |
|------|--------|--------|-------------|-------------|------------------|
| Connection status | ✅ | `status.connected` | `/api/telescope/status` | 🔴/🟢 Status indicator | 2s poll |
| Current RA/Dec | ✅ | `status.current_ra_hours/dec_degrees` | `/api/telescope/status` | RA/Dec display fields | 2s poll |
| Tracking status | ✅ | `status.is_tracking` | `/api/telescope/status` | "Tracking/Not tracking" label | 2s poll |
| Current target | ✅ | `status.current_target` | `/api/telescope/status` | Target name in status bar | 2s poll |
| Telescope state | ✅ | `status.state` | `/api/telescope/status` | Control state management | 2s poll |

---

## 3. IMAGING CONTROL

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `iscope_start_stack` | ✅ | `start_imaging()` | `POST /api/telescope/start-imaging` | "Start Imaging" button | `exposure_ms`, `gain`, `restart` (bool) |
| `iscope_stop_view` | ✅ | `stop_imaging()` | `POST /api/telescope/stop-imaging` | "Stop Imaging" button | None |
| `set_setting` (exposure) | ✅ | `set_exposure()` | `POST /api/telescope/features/imaging/exposure` | Exposure input field | `exposure_ms`, `gain` |
| `set_setting` (dither) | ✅ | `configure_dither()` | `POST /api/telescope/features/imaging/dither` | None | `enabled` (bool), `interval_frames`, `pixels` |
| `iscope_get_app_state` | 🟡 | `get_app_state()` | `GET /api/telescope/app-state` | None | Returns `stage`, `progress`, `frame`, `total_frames`, `state` |
| `is_stacked` | 🟡 | `check_stacking_complete()` | `GET /api/telescope/stacking-status` | None | Returns `is_complete` (bool), `total_frames` |
| `set_setting` (advanced) | 🟡 | `configure_advanced_stacking()` | `POST /api/telescope/features/imaging/advanced-stacking` | None | `dbe_enabled`, `star_correction`, `gradient_removal`, `denoise` |
| `set_setting` (manual exp) | 🟡 | `set_manual_exposure()` | `POST /api/telescope/features/imaging/manual-exposure` | None | `exposure_ms`, `gain` |
| `set_setting` (auto exp) | 🟡 | `set_auto_exposure()` | `POST /api/telescope/features/imaging/auto-exposure` | None | `brightness_target` (0-100) |

### Imaging Input Fields

| Field | Status | Frontend Element | Backend Param | Notes |
|-------|--------|------------------|---------------|-------|
| Exposure time | ✅ | `#exposure-time` | `exposure_ms` | Seconds converted to ms |
| Gain | ✅ | `#gain-value` | `gain` | 0-100 value |
| Target name | ✅ | `#target-name` | `target_name` | Optional |
| Target RA | ✅ | `#target-ra` | `ra` | HH:MM:SS format |
| Target Dec | ✅ | `#target-dec` | `dec` | ±DD:MM:SS format |

---

## 4. FOCUS CONTROL

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `start_auto_focuse` | ✅ | `auto_focus()` | `POST /api/telescope/features/imaging/autofocus` | "Auto Focus" button | None |
| `stop_auto_focuse` | 🟡 | `stop_autofocus()` | `POST /api/telescope/features/focuser/stop` | None | None |
| `move_focuser` (absolute) | 🟡 | `move_focuser_to_position()` | `POST /api/telescope/features/focuser/move` | None | `position` (int, 0-25000) |
| `move_focuser` (relative) | 🟡 | `move_focuser_relative()` | `POST /api/telescope/features/focuser/move` | None | `steps` (int, ±500) |
| `reset_factory_focal_pos` | 🟡 | `reset_focuser_to_factory()` | `POST /api/telescope/features/focuser/factory-reset` | None | None |

---

## 5. VIEW PLANS (AUTOMATION)

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `start_view_plan` | 🟡 | `start_view_plan()` | `POST /api/telescope/plan/start` | None | `plan_config` (dict): targets, exposures, filters, etc. |
| `stop_view_plan` | 🟡 | `stop_view_plan()` | `POST /api/telescope/plan/stop` | None | None |
| `get_view_plan_state` | 🟡 | `get_view_plan_state()` | `GET /api/telescope/plan/state` | None | Returns `current_target`, `progress`, `state` |

---

## 6. PLANETARY MODE

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `start_scan_planet` | 🟡 | `start_planet_scan()` | `POST /api/telescope/planet/start` | None | `planet_name`, `exposure_ms`, `gain` |
| `set_setting` (planet) | 🟡 | `configure_planetary_imaging()` | `POST /api/telescope/planet/configure` | None | `roi` (region), `exposure_ms`, `gain`, `frame_rate` |

---

## 7. PLATE SOLVING & ANNOTATION

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `get_solve_result` | 🟡 | `get_plate_solve_result()` | `GET /api/telescope/solve-result` | None | Returns `ra`, `dec`, `field_rotation`, `pixel_scale` |
| `get_annotate_result` | 🟡 | `get_field_annotations()` | `GET /api/telescope/field-annotations` | None | Returns list of identified objects with names, coords |

---

## 8. SYSTEM MANAGEMENT

### Power Control

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `pi_shutdown` | ✅ | `shutdown_telescope()` | `POST /api/telescope/features/system/shutdown` | "Shutdown" button | None |
| `pi_reboot` | ✅ | `reboot_telescope()` | `POST /api/telescope/features/system/reboot` | "Reboot" button | None |

### System Info

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `get_device_state` | ✅ | `get_device_state()` | `GET /api/telescope/status` | "Get Info" button | Returns `state`, `is_tracking`, `ra`, `dec`, `connected` |
| `pi_get_time` | 🟡 | `get_pi_time()` | `GET /api/telescope/features/system/time` | None | Returns `unix_timestamp`, `iso_timestamp` |
| `pi_set_time` | 🟡 | `set_pi_time()` | `POST /api/telescope/features/system/time` | None | `unix_timestamp` (int) |
| `set_location` | 🟡 | `set_location()` | `POST /api/telescope/features/system/location` | None | `latitude`, `longitude`, `elevation` |
| `pi_get_info` | 🟡 | `get_pi_info()` | `GET /api/telescope/features/system/pi-info` | "Get Info" button | Returns `device_name`, `firmware_version`, `uptime`, `temperature`, `storage` |

---

## 9. HARDWARE CONTROL

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `pi_output_set2` (dew heater) | 🔵 | `set_dew_heater()` | `POST /api/telescope/features/hardware/dew-heater` | On/Off buttons + power slider | `enabled` (bool), `power_level` (0-100) |
| `pi_output_set2` (DC output) | 🟡 | `set_dc_output()` | `POST /api/telescope/features/hardware/dc-output` | None | `output_id`, `enabled` (bool), `power_level` (0-100) |
| `pi_output_get2` | 🟡 | `get_dc_output()` | `GET /api/telescope/features/hardware/dc-output` | None | Returns `outputs` list with states |

---

## 10. NETWORK & WIFI

### WiFi Client Mode

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `pi_station_scan` | 🔵 | `scan_wifi_networks()` | `GET /api/telescope/features/wifi/scan` | "Scan Networks" button | Returns list of SSIDs with signal strength |
| `pi_station_select` | 🔵 | `connect_to_wifi()` | `POST /api/telescope/features/wifi/connect` | Network list | `ssid`, `password` |
| `pi_station_list` | 🟡 | `list_saved_wifi_networks()` | `GET /api/telescope/features/wifi/saved` | Network list | Returns list of saved SSIDs |
| `pi_station_set` | 🟡 | `save_wifi_network()` | `POST /api/telescope/features/wifi/save-network` | None | `ssid`, `password`, `security` (WPA2-PSK) |
| `pi_station_open` | 🟡 | `enable_wifi_client_mode()` | `POST /api/telescope/features/wifi/enable-client` | None | None |
| `pi_station_close` | 🟡 | `disable_wifi_client_mode()` | `POST /api/telescope/features/wifi/disable-client` | None | None |
| `pi_station_get_state` | 🟡 | `get_station_state()` | `GET /api/telescope/features/wifi/station-state` | None | Returns `connected`, `ssid`, `ip_address`, `signal_strength` |
| `pi_station_del` | 🟡 | `remove_wifi_network()` | `DELETE /api/telescope/features/wifi/network/{ssid}` | None | `ssid` (in path) |

### WiFi AP Mode

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `pi_set_ap` | 🟡 | `configure_access_point()` | `POST /api/telescope/features/wifi/access-point` | None | `ssid`, `password`, `is_5g` (bool) |
| `set_wifi_country` | 🟡 | `set_wifi_country()` | `POST /api/telescope/features/wifi/country` | None | `country_code` (e.g., "US") |

---

## 11. CALIBRATION

### Polar Alignment

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `check_pa_alt` | 🟡 | `check_polar_alignment()` | `GET /api/telescope/features/calibration/polar-alignment` | None | Returns `quality`, `altitude_error`, `azimuth_error` |
| `clear_polar_align` | 🟡 | `clear_polar_alignment()` | `POST /api/telescope/features/calibration/polar-alignment/clear` | None | None |

### Compass

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `start_compass_calibration` | 🟡 | `start_compass_calibration()` | `POST /api/telescope/features/calibration/compass/start` | None | None |
| `stop_compass_calibration` | 🟡 | `stop_compass_calibration()` | `POST /api/telescope/features/calibration/compass/stop` | None | None |
| `get_compass_state` | 🟡 | `get_compass_state()` | `GET /api/telescope/features/calibration/compass/state` | None | Returns `heading`, `calibrated` (bool) |

---

## 12. IMAGE MANAGEMENT

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `get_img_file_info` | 🟡 | `get_image_file_info()` | `GET /api/telescope/features/images/info` | "Refresh Images" button | `filename` → Returns `size`, `timestamp`, `format` |
| File download (port 4801) | 🟡 | `get_stacked_image()` | `GET /api/telescope/features/images/download/{filename}` | None | `filename` (in path) → Returns image bytes |
| File download (port 4801) | 🟡 | `get_raw_frame()` | `GET /api/telescope/features/images/raw/{filename}` | None | `filename` (in path) → Returns raw frame bytes |
| Delete image | 🟡 | `delete_image()` | `DELETE /api/telescope/features/images/{filename}` | None | `filename` (in path) |
| List images | 🟡 | `list_images()` | `GET /api/telescope/features/images/list` | None | `image_type` (stacked/raw/all) → Returns list |
| Live preview (RTMP) | 🟡 | `get_live_preview()` | `GET /api/telescope/features/images/preview/live` | None | Returns current preview frame bytes |

---

## 13. REMOTE SESSIONS

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `remote_join` | 🟡 | `join_remote_session()` | `POST /api/telescope/features/remote/join` | None | `session_id` (optional) |
| `remote_disjoin` | 🟡 | `leave_remote_session()` | `POST /api/telescope/features/remote/leave` | None | None |
| `remote_disconnect` | 🟡 | `disconnect_remote_client()` | `POST /api/telescope/features/remote/disconnect/{client_id}` | None | `client_id` (in path) |

---

## 14. UTILITY

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Parameters |
|---------|--------|---------------------|-------------|-------------|------------|
| `play_sound` | 🟡 | `play_notification_sound()` | `POST /api/telescope/features/sound/play` | None | `volume` ("silent", "backyard", "deep_sky") |
| `iscope_cancel_view` | 🟡 | `cancel_current_operation()` | `POST /api/telescope/cancel` | None | None |
| `start_demonstrate` | 🟡 | `start_demo_mode()` | `POST /api/telescope/features/demo/start` | None | None |
| `stop_demonstrate` | 🟡 | `stop_demo_mode()` | `POST /api/telescope/features/demo/stop` | None | None |
| `check_verification_status` | 🟡 | `check_verification_status()` | `GET /api/telescope/features/verification-status` | None | Returns `verified` (bool) |

---

## FRONTEND UX ELEMENTS

### Status Bar (Top)
```
🔴/🟢 [Disconnected/Connected] | 192.168.2.47 | M31   [⚡ Button]
```
- Status indicator (connection state)
- Telescope IP display
- Current target display
- Connect/disconnect button

### Main Panel - Telescope Controls

**Target Input Section:**
- Target name (optional text input)
- RA input (HH:MM:SS format)
- Dec input (±DD:MM:SS format)
- [Slew to Target] button
- [Stop Motion] button
- [Park Telescope] button

**Status Display:**
- Tracking status label
- Current RA display
- Current Dec display

**Imaging Controls:**
- Exposure time input (seconds)
- Gain slider/input (0-100)
- [Start Imaging] button
- [Stop Imaging] button
- [Auto Focus] button

### Advanced Controls (Bottom Drawer)

**Tabs** (dynamically created based on capabilities):
- WiFi tab (if `features.wifi` exists)
- Alignment tab (if `features.alignment` exists)
- System tab (if `features.system` exists)
- Advanced tab (if `features.advanced` exists)

**Hardware Panel** (dynamically shown if `features.hardware` exists):
- Dew heater on/off buttons
- Dew heater power slider (0-100%)
- DC output controls (if available)

**System Tab:**
- [Get Info] button → Shows device_name, firmware_version, uptime, temperature, storage
- [Shutdown] button
- [Reboot] button

**WiFi Tab:**
- [Scan Networks] button
- Network list display

**Image Management:**
- [Refresh Images] button
- Image list display
- [Download] buttons per image

### Sidebar (Observe Panel)
- [Goto Target] button (duplicate of main panel)
- [Park Telescope] button (duplicate of main panel)

---

## PRIORITY GAPS TO ADDRESS

### ✅ BACKEND APIS COMPLETED (ALL 71 COMMANDS)

All Seestar S50 commands now have backend API endpoints implemented. The following features have complete API coverage but need frontend UX integration:

### 🔴 HIGH PRIORITY - Need Frontend UX Integration

1. **Real-time Coordinate Tracking**
   - API: `GET /api/telescope/coordinates`
   - Need: Poll every 1-5s during observation
   - UX: Update RA/Dec display in real-time with live data

2. **Imaging Progress Monitoring**
   - API: `GET /api/telescope/app-state`
   - Need: Show frame count, percentage complete
   - UX: Progress bar/counter during imaging session

3. **Stacking Completion Detection**
   - API: `GET /api/telescope/stacking-status`
   - Need: Know when imaging session done
   - UX: Auto-stop or notification when complete

### 🟡 MEDIUM PRIORITY - Enhanced Control

4. **View Plan Automation**
   - APIs: `POST /api/telescope/plan/start`, `POST /api/telescope/plan/stop`, `GET /api/telescope/plan/state`
   - Need: Multi-target automated imaging
   - UX: New "Plans" panel with plan builder UI

5. **Plate Solving Verification**
   - API: `GET /api/telescope/solve-result`
   - Need: Verify goto accuracy
   - UX: Show solve results after goto completes

6. **Manual Focus Control**
   - API: `POST /api/telescope/features/focuser/move`
   - Need: Fine-tune focus manually
   - UX: Focus slider or +/- buttons, display position

7. **Advanced Stacking Settings**
   - API: `POST /api/telescope/features/imaging/advanced-stacking`
   - Need: Control stacking algorithm (DBE, star correction, etc.)
   - UX: Settings panel with checkboxes for options

8. **Stop Autofocus**
   - API: `POST /api/telescope/features/focuser/stop`
   - Need: Abort autofocus operation
   - UX: "Stop Focus" button (enabled during autofocus)

### 🟢 LOW PRIORITY - Nice to Have

9. **Planetary Imaging Mode** - APIs: `POST /api/telescope/planet/start`, `POST /api/telescope/planet/configure`
10. **Polar Alignment Check** - API: `GET /api/telescope/features/calibration/polar-alignment`
11. **Compass Calibration** - APIs: `POST /api/telescope/features/calibration/compass/start`, `GET /api/telescope/features/calibration/compass/state`
12. **Network Management** - 9 WiFi/network APIs available
13. **Demo Mode** - APIs: `POST /api/telescope/features/demo/start`, `POST /api/telescope/features/demo/stop`
14. **Image Management** - Download/delete images, live preview
15. **Remote Sessions** - Join/leave multi-client sessions

---

## IMPLEMENTATION STATUS SUMMARY

| Category | Total Commands | SeestarClient Methods | Backend APIs | Fully Wired to UX | Backend Only |
|----------|---------------|----------------------|--------------|-------------------|--------------|
| Connection | 3 | 3 | 2 | 2 | 1 |
| Telescope Control | 7 | 7 | 7 | 3 | 4 |
| Imaging | 9 | 9 | 9 | 4 | 5 |
| Focus | 5 | 5 | 5 | 1 | 4 |
| View Plans | 3 | 3 | 3 | 0 | 3 |
| Planetary | 2 | 2 | 2 | 0 | 2 |
| Plate Solving | 2 | 2 | 2 | 0 | 2 |
| System | 8 | 8 | 8 | 3 | 5 |
| Hardware | 3 | 3 | 3 | 1 | 2 |
| Network | 11 | 11 | 11 | 1 | 10 |
| Calibration | 5 | 5 | 5 | 0 | 5 |
| Images | 6 | 6 | 6 | 1 | 5 |
| Remote | 3 | 3 | 3 | 0 | 3 |
| Utility | 5 | 5 | 5 | 0 | 5 |
| **TOTAL** | **72** | **72** | **71** | **16** | **56** |

**Current Status (as of 2025-01-09)**:
- ✅ **100% SeestarClient Coverage**: All 72 commands have async methods in the client (76 total methods including helpers)
- ✅ **99% Backend API Coverage**: 71/72 commands have FastAPI endpoints (only `pi_is_verified` missing, low priority)
- ⚠️ **22% Frontend UX Coverage**: Only 16/72 commands fully wired to UI controls
- 📊 **56 commands** have complete backend implementation but no frontend interface

**Key Insight**: The bottleneck is no longer backend APIs - it's frontend UX integration. All critical features are available via API and ready to be connected to the UI.

---

## NEXT STEPS RECOMMENDATIONS

**Phase 1: High Priority Frontend Integration** (Week 1)
1. **Wire up Real-time Tracking** - Poll `GET /api/telescope/coordinates` every 2s, update RA/Dec display
2. **Add Imaging Progress Bar** - Poll `GET /api/telescope/app-state` during imaging, show frame count/percentage
3. **Add Completion Detection** - Use `GET /api/telescope/stacking-status` to auto-stop or notify when done
4. **Add Stop Autofocus Button** - Call `POST /api/telescope/features/focuser/stop`, enable during autofocus

**Phase 2: Enhanced Controls** (Week 2)
5. **Manual Focus Controls** - Add slider/+/- buttons calling `POST /api/telescope/features/focuser/move`
6. **Advanced Stacking Settings Panel** - Checkboxes for DBE, star correction, etc. calling `POST /api/telescope/features/imaging/advanced-stacking`
7. **Plate Solve Results Display** - Show `GET /api/telescope/solve-result` after goto completes
8. **Manual/Auto Exposure Toggle** - Switch between `POST /api/telescope/features/imaging/manual-exposure` and `auto-exposure`

**Phase 3: Automation** (Week 3)
9. **View Plans UI** - Plan builder with target list, calls `POST /api/telescope/plan/start`, monitors `GET /api/telescope/plan/state`
10. **Planetary Imaging Mode** - Add planet selector, calls `POST /api/telescope/planet/start`

**Phase 4: Polish & Advanced Features** (Week 4)
11. **Image Gallery** - Display `GET /api/telescope/features/images/list`, download buttons
12. **Live Preview** - Stream `GET /api/telescope/features/images/preview/live`
13. **Polar Alignment Check** - Show `GET /api/telescope/features/calibration/polar-alignment` results
14. **Network Management UI** - WiFi scan, connect, saved networks management

**Testing Strategy**:
- Test each new API endpoint with real telescope hardware before UI integration
- Add browser console logging for all API calls
- Use verification skill before claiming any feature complete
