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

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `iscope_start_view` | ✅ | `goto_target()` | `/api/telescope/goto` | "Slew to Target" button | Main panel + sidebar |
| `scope_move` (stop) | ✅ | `stop_slew()` | `/api/telescope/stop-slew` | "Stop Motion" button | Enabled when slewing |
| `scope_park` | ✅ | `park()` | `/api/telescope/park` | "Park Telescope" button | Main panel + sidebar |
| `pi_unpark` | 🟡 | None | `/api/telescope/unpark` | None | Endpoint exists but not used |
| `scope_get_equ_coord` | 🟡 | `get_current_coordinates()` | None | None | **HIGH PRIORITY** - Need for live tracking |
| `scope_move` (slew) | 🟡 | `slew_to_coordinates()` | None | None | Alternative to iscope_start_view |
| `scope_move_to_horizon` | 🟡 | `move_to_horizon()` | None | None | Advanced feature |

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

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `iscope_start_stack` | ✅ | `start_imaging()` | `/api/telescope/start-imaging` | "Start Imaging" button | Sends exposure + gain |
| `iscope_stop_view` | ✅ | `stop_imaging()` | `/api/telescope/stop-imaging` | "Stop Imaging" button | Stops stacking |
| `set_setting` (exposure) | ✅ | `set_exposure()` | `/api/telescope/features/imaging/exposure` | Exposure input field | Before imaging starts |
| `set_setting` (dither) | ✅ | `configure_dither()` | `/api/telescope/features/imaging/dither` | None | Could add to settings |
| `iscope_get_app_state` | 🟡 | `get_app_state()` | None | None | **HIGH PRIORITY** - Progress tracking |
| `is_stacked` | 🟡 | `check_stacking_complete()` | None | None | **HIGH PRIORITY** - Completion detection |
| `set_setting` (advanced) | 🟡 | `configure_advanced_stacking()` | None | None | DBE, star correction, etc. |
| `set_setting` (manual exp) | 🟡 | `set_manual_exposure()` | None | None | Override auto-exposure |
| `set_setting` (auto exp) | 🟡 | `set_auto_exposure()` | None | None | Brightness target |

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

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `start_auto_focuse` | ✅ | `auto_focus()` | `/api/telescope/features/imaging/autofocus` | "Auto Focus" button | Main panel |
| `stop_auto_focuse` | 🟡 | `stop_autofocus()` | None | None | Should add abort button |
| `move_focuser` (absolute) | 🟡 | `move_focuser_to_position()` | `/api/telescope/features/focuser/move` | None | Manual focus control |
| `move_focuser` (relative) | 🟡 | `move_focuser_relative()` | `/api/telescope/features/focuser/move` | None | Fine adjustments |
| `reset_factory_focal_pos` | 🟡 | `reset_focuser_to_factory()` | `/api/telescope/features/focuser/factory-reset` | None | Emergency reset |

---

## 5. VIEW PLANS (AUTOMATION)

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `start_view_plan` | 🟡 | `start_view_plan()` | None | None | **PRIORITY 2** - Core automation |
| `stop_view_plan` | 🟡 | `stop_view_plan()` | None | None | Cancel running plan |
| `get_view_plan_state` | 🟡 | `get_view_plan_state()` | None | None | Monitor plan progress |

---

## 6. PLANETARY MODE

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `start_scan_planet` | 🟡 | `start_planet_scan()` | None | None | Different imaging mode |
| `set_setting` (planet) | 🟡 | `configure_planetary_imaging()` | None | None | Planet-specific params |

---

## 7. PLATE SOLVING & ANNOTATION

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `get_solve_result` | 🟡 | `get_plate_solve_result()` | None | None | Verify goto accuracy |
| `get_annotate_result` | 🟡 | `get_field_annotations()` | None | None | Identify objects in FOV |

---

## 8. SYSTEM MANAGEMENT

### Power Control

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `pi_shutdown` | ✅ | `shutdown_telescope()` | `/api/telescope/features/system/shutdown` | "Shutdown" button | Advanced Controls → System tab |
| `pi_reboot` | ✅ | `reboot_telescope()` | `/api/telescope/features/system/reboot` | "Reboot" button | Advanced Controls → System tab |

### System Info

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `get_device_state` | ✅ | `get_device_state()` | `/api/telescope/status` | "Get Info" button | System tab - shows all device state |
| `pi_get_time` | 🟡 | `get_pi_time()` | None | None | Could show in system info |
| `pi_set_time` | 🟡 | `set_pi_time()` | None | None | Time sync feature |
| `set_location` | 🟡 | `set_location()` | `/api/telescope/features/system/location` | None | GPS coordinates |
| `pi_get_info` | 🟡 | `get_pi_info()` | `/api/telescope/features/system/info` | "Get Info" button | Shows firmware, uptime, etc. |

---

## 9. HARDWARE CONTROL

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `pi_output_set2` (dew heater) | 🔵 | `set_dew_heater()` | `/api/telescope/features/hardware/dew-heater` | On/Off buttons + power slider | Hardware panel (capability-based) |
| `pi_output_set2` (DC output) | 🟡 | `set_dc_output()` | `/api/telescope/features/hardware/dc-output` | None | Generic DC control |
| `pi_output_get2` | 🟡 | `get_dc_output()` | None | None | Query DC state |

---

## 10. NETWORK & WIFI

### WiFi Client Mode

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `pi_station_scan` | 🔵 | `scan_wifi_networks()` | `/api/telescope/features/wifi/scan` | "Scan Networks" button | WiFi tab (capability-based) |
| `pi_station_select` | 🔵 | `connect_to_wifi()` | `/api/telescope/features/wifi/connect` | Network list | WiFi tab |
| `pi_station_list` | 🟡 | `list_saved_wifi_networks()` | `/api/telescope/features/wifi/saved` | Network list | WiFi tab |
| `pi_station_set` | 🟡 | `save_wifi_network()` | None | None | Save credentials |
| `pi_station_open` | 🟡 | `enable_wifi_client_mode()` | None | None | Enable station mode |
| `pi_station_close` | 🟡 | `disable_wifi_client_mode()` | None | None | Disable station mode |
| `pi_station_get_state` | 🟡 | `get_station_state()` | None | None | Query connection status |

### WiFi AP Mode

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `pi_set_ap` | 🟡 | `configure_access_point()` | None | None | Configure telescope AP |
| `set_wifi_country` | 🟡 | `set_wifi_country()` | None | None | Regulatory domain |

---

## 11. CALIBRATION

### Polar Alignment

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `check_pa_alt` | 🟡 | `check_polar_alignment()` | None | None | Check PA quality |
| `clear_polar_align` | 🟡 | `clear_polar_alignment()` | None | None | Reset PA |

### Compass

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `start_compass_calibration` | 🟡 | `start_compass_calibration()` | None | None | Start cal routine |
| `stop_compass_calibration` | 🟡 | `stop_compass_calibration()` | None | None | Abort cal |
| `get_compass_state` | 🟡 | `get_compass_state()` | None | None | Get heading |

---

## 12. IMAGE MANAGEMENT

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `get_img_file_info` | 🟡 | `get_image_file_info()` | None | "Refresh Images" button | Lists available images |
| File download (port 4801) | 🟡 | `get_stacked_image()` | None | None | Download FITS/JPEG |
| File download (port 4801) | 🟡 | `get_raw_frame()` | None | None | Download raw frames |
| Delete image | 🟡 | `delete_image()` | None | None | Remove from telescope |
| List images | 🟡 | `list_images()` | None | None | Query image catalog |
| Live preview (RTMP) | 🟡 | `get_live_preview()` | `/api/telescope/preview` | None | Real-time video frame |

---

## 13. REMOTE SESSIONS

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `remote_join` | 🟡 | `join_remote_session()` | None | None | Multi-client support |
| `remote_disjoin` | 🟡 | `leave_remote_session()` | None | None | Leave session |
| `remote_disconnect` | 🟡 | `disconnect_remote_client()` | None | None | Kick client |

---

## 14. UTILITY

| Command | Status | SeestarClient Method | Backend API | Frontend UX | Notes |
|---------|--------|---------------------|-------------|-------------|-------|
| `play_sound` | 🟡 | `play_notification_sound()` | None | None | Audio feedback |
| `iscope_cancel_view` | 🟡 | `cancel_current_operation()` | `/api/telescope/abort` | None | Emergency stop |
| `start_demonstrate` | 🟡 | `start_demo_mode()` | None | None | Demo mode |
| `stop_demonstrate` | 🟡 | `stop_demo_mode()` | None | None | Exit demo mode |

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

### 🔴 HIGH PRIORITY - Missing Critical Features

1. **Real-time Coordinate Tracking**
   - Command: `scope_get_equ_coord`
   - Status: Implemented in client, no API endpoint
   - Need: Poll every 1-5s during observation
   - UX: Update RA/Dec display in real-time

2. **Imaging Progress Monitoring**
   - Command: `iscope_get_app_state`
   - Status: Implemented in client, no API endpoint
   - Need: Show frame count, percentage complete
   - UX: Progress bar/counter during imaging

3. **Stacking Completion Detection**
   - Command: `is_stacked`
   - Status: Implemented in client, no API endpoint
   - Need: Know when imaging session done
   - UX: Auto-stop or notification

### 🟡 MEDIUM PRIORITY - Enhanced Control

4. **View Plan Automation**
   - Commands: `start_view_plan`, `stop_view_plan`, `get_view_plan_state`
   - Status: Implemented in client, no API endpoints
   - Need: Multi-target automated imaging
   - UX: New "Plans" panel with plan builder

5. **Plate Solving Verification**
   - Command: `get_solve_result`
   - Status: Implemented in client, no API endpoint
   - Need: Verify goto accuracy
   - UX: Show solve results after goto

6. **Manual Focus Control**
   - Commands: `move_focuser` (absolute/relative)
   - Status: Implemented in client, has API endpoint
   - Need: Fine-tune focus manually
   - UX: Focus slider or +/- buttons

7. **Advanced Stacking Settings**
   - Command: `set_setting` (DBE, star correction, etc.)
   - Status: Implemented in client, no API endpoint
   - Need: Control stacking algorithm
   - UX: Settings panel with checkboxes

### 🟢 LOW PRIORITY - Nice to Have

8. **Planetary Imaging Mode**
9. **Polar Alignment Check**
10. **Compass Calibration**
11. **Network Management**
12. **Demo Mode**

---

## IMPLEMENTATION STATUS SUMMARY

| Category | Total Commands | Fully Wired | Backend Only | Not Implemented |
|----------|---------------|-------------|--------------|-----------------|
| Connection | 3 | 2 | 1 | 0 |
| Telescope Control | 7 | 3 | 4 | 0 |
| Imaging | 9 | 4 | 5 | 0 |
| Focus | 5 | 1 | 4 | 0 |
| View Plans | 3 | 0 | 3 | 0 |
| Planetary | 2 | 0 | 2 | 0 |
| Plate Solving | 2 | 0 | 2 | 0 |
| System | 8 | 3 | 5 | 0 |
| Hardware | 3 | 1 | 2 | 0 |
| Network | 11 | 1 | 10 | 0 |
| Calibration | 5 | 0 | 5 | 0 |
| Images | 6 | 1 | 5 | 0 |
| Remote | 3 | 0 | 3 | 0 |
| Utility | 4 | 0 | 4 | 0 |
| **TOTAL** | **71** | **16** | **55** | **0** |

**Key Insight**: All commands are implemented in `SeestarClient` (76 async methods), but only 16 are fully wired to the UX. There are 55 commands with backend implementations but no frontend interface.

---

## NEXT STEPS RECOMMENDATIONS

1. **Add Real-time Tracking** - Wire up `scope_get_equ_coord` for live RA/Dec updates
2. **Add Progress Monitoring** - Wire up `iscope_get_app_state` for imaging progress
3. **Add Completion Detection** - Wire up `is_stacked` to know when done
4. **Create Plans UI** - Build interface for view plan automation
5. **Add Manual Focus Controls** - Slider or +/- buttons for focuser
6. **Expand Settings Panel** - Advanced stacking options (DBE, etc.)
7. **Add Plate Solve Display** - Show solve results after goto
8. **Add Stop Autofocus** - Abort button for focus operations
