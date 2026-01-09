# Observe View Redesign - Design Specification

**Date:** 2025-01-01
**Status:** Approved for Implementation
**Goal:** Redesign the Observe tab to integrate capture history, file transfer, comprehensive telescope control, and create a professional observatory-style control center.

---

## 1. Overview

The redesigned Observe view transforms the existing execution-focused interface into a comprehensive control center that:

- Integrates capture history with real-time observation
- Provides full telescope control (60+ operations)
- Manages imaging library and file transfers
- Displays live telemetry and device status
- Organizes advanced controls in an accessible but non-intrusive way

**Architecture:** Three-zone split-view layout with collapsible bottom drawer for advanced features.

**Tech Stack:**
- Frontend: Vanilla JavaScript (matching existing codebase)
- Styling: CSS with CSS variables for theming
- Backend: FastAPI REST API (existing)
- Real-time: HTTP polling (2s for execution, 1s for telemetry) with WebSocket fallback

---

## 2. Overall Layout Structure

### Three-Zone Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Astro Planner - Observe Tab                       │
├──────────────┬──────────────────────────────────────────────┤
│              │  Main View Selector (tabs):                 │
│              │  [Execution] [Library] [Telemetry] [Live]   │
│              ├──────────────────────────────────────────────┤
│  Left        │                                              │
│  Sidebar     │         Right Main Area                      │
│              │      (context switches based on tab)         │
│  - Connect   │                                              │
│  - Execute   │                                              │
│  - Imaging   │                                              │
│  - Telescope │                                              │
│  - Hardware  │                                              │
│  - Quick Ref │                                              │
│              │                                              │
├──────────────┴──────────────────────────────────────────────┤
│  Bottom Drawer (collapsible): Advanced Controls            │
│  [Advanced Imaging] [System] [WiFi] [Calibration]         │
└─────────────────────────────────────────────────────────────┘
```

### Zone Specifications

**Left Sidebar (~280-320px fixed):**
- Grouped collapsible sections for control categories
- Always visible on desktop, scrollable if needed
- Color-coded section headers
- Status indicators (connection, dew heater, etc.)
- Hamburger menu on mobile/tablet

**Right Main Area (flexible width):**
- Tabbed interface with 4 main views
- Content switches based on active tab
- Full width utilization
- Responsive grid layouts

**Bottom Drawer (collapsible, ~200-300px when open):**
- Slides up from bottom when needed
- Tabbed for organization
- Can be pinned open or auto-collapses
- Keyboard shortcut: `Ctrl+D` to toggle

---

## 3. Left Sidebar - Control Sections

### Section 1: Connection
**Always expanded by default**

```
🔌 Connection
├─ IP Address: [192.168.2.47      ]
├─ Port: [4700] (default)
├─ [Connect] / [Disconnect] button
├─ Status: ● Connected | Firmware: v6.45
└─ Signal strength indicator
```

**Controls:**
- Text input for IP address (validates format)
- Number input for port (default 4700)
- Connect/Disconnect toggle button (changes based on state)
- Status indicator with color (green=connected, yellow=connecting, gray=disconnected, red=error)
- Firmware version display (from device state)

### Section 2: Execution
**Collapsible, expanded by default**

```
⚡ Execution
├─ Current Plan: "Winter DSO Session"
├─ Targets: 5 | Duration: 4.5h
├─ [▶ Execute Plan] (primary, large)
├─ [⏹ Abort] (danger)
├─ [🏠 Park] (secondary)
└─ Quick status: Ready / Executing / Parked
```

**Controls:**
- Plan name display (clickable to show plan details)
- Summary stats (target count, total duration)
- Execute button (primary, disabled when disconnected or no plan)
- Abort button (danger, enabled only during execution)
- Park button (secondary, enabled when connected)
- Status badge showing current state

**API Calls:**
- Execute: `POST /api/telescope/execute`
- Abort: `POST /api/telescope/abort`
- Park: `POST /api/telescope/park`

### Section 3: Imaging Controls
**Collapsible**

```
📷 Imaging
├─ [▶ Start] [⏹ Stop]
├─ Exposure:
│  ├─ Stack: [10] sec
│  └─ Preview: [0.5] sec
├─ Dither: ☑ On | [50] px | Every [10] frames
├─ Gain: Auto ○ Manual ○ Value: [100]
├─ Filter: ○ LP ○ Clear
└─ [⚙ Advanced Stacking...] → opens bottom drawer
```

**Controls:**
- Start/Stop imaging buttons
- Exposure time inputs (stack and preview)
- Dither toggle with pixel amount and interval
- Gain mode (auto/manual) with value slider
- Filter selection (light pollution / clear)
- Advanced settings link (opens bottom drawer)

**API Calls:**
- Start: `POST /api/telescope/command/start_imaging`
- Stop: `POST /api/telescope/command/stop_imaging`
- Settings: `POST /api/telescope/command/set_exposure`, `configure_dither`

### Section 4: Telescope Controls
**Collapsible**

```
🔭 Telescope
├─ Quick Actions:
│  ├─ [Auto Focus]
│  ├─ [Stop Slew]
│  └─ [Emergency Stop]
├─ Manual Goto:
│  ├─ RA: [12.5] h
│  ├─ Dec: [45.3] °
│  └─ [Slew]
├─ Horizon Goto:
│  ├─ Az: [180] °
│  ├─ Alt: [30] °
│  └─ [Slew]
└─ [🧭 Calibration...] → bottom drawer
```

**Controls:**
- Auto Focus button (one-click)
- Stop Slew button (emergency stop slewing)
- Emergency Stop button (stops all motion)
- Manual goto inputs (RA/Dec equatorial coordinates)
- Horizon goto inputs (Alt/Az horizontal coordinates)
- Slew buttons (execute goto commands)
- Calibration link (opens bottom drawer)

**API Calls:**
- Focus: `POST /api/telescope/command/auto_focus`
- Stop Slew: `POST /api/telescope/command/stop_slew`
- Emergency: `POST /api/telescope/command/stop_telescope_movement`
- Goto: `POST /api/telescope/command/goto_target` or `slew_to_coordinates`
- Horizon: `POST /api/telescope/command/move_to_horizon`

### Section 5: Hardware
**Collapsible**

```
🔧 Hardware
├─ Dew Heater:
│  ├─ ○ Off ● On
│  └─ Power: [90]% ──────●───
├─ Focus:
│  ├─ Position: [1250] / 2600
│  ├─ [-100] [-10] [+10] [+100]
│  └─ [Reset to Factory]
└─ DC Outputs: [Configure...] → bottom drawer
```

**Controls:**
- Dew heater toggle (on/off)
- Power level slider (0-100%)
- Focus position display (current/max)
- Focus adjustment buttons (coarse and fine)
- Reset focuser button
- DC outputs configuration link

**API Calls:**
- Dew Heater: `POST /api/telescope/command/set_dew_heater`
- Focus: `POST /api/telescope/command/move_focuser_relative`
- Reset: `POST /api/telescope/command/reset_focuser_to_factory`

### Section 6: Quick Reference
**Collapsible, compact**

```
ℹ️ Info
├─ Current Target: M31
├─ RA/Dec: 0.7h / +41.3°
├─ Altitude: 52° (good)
├─ Frames: 45 / 100
└─ Session: 1.2h / 2.0h
```

**Display Only:**
- Current target name
- Current coordinates
- Altitude with quality indicator
- Frame progress
- Session time elapsed/total

**Data Source:** Real-time telemetry from `GET /api/telescope/status` and `progress`

---

## 4. Right Main Area - Tab Views

### Tab 1: Execution View
**Active during plan execution, shows progress and capture history integration**

**Components:**

**Execution Status Banner**
```
┌─ Execution Status Banner ─────────────────────────────┐
│ 🔭 EXECUTING PLAN                           Progress   │
│ Current: M31 Andromeda Galaxy                   45%    │
│ Phase: Stacking (Frame 45/100)              ━━━━━○──   │
│ Target 2 of 5 | Elapsed: 1h 15m | Remaining: 1h 30m   │
└────────────────────────────────────────────────────────┘
```
- Large, prominent banner when executing
- Animated pulsing telescope icon
- Current target name and progress percentage
- Current phase (slewing, focusing, stacking, etc.)
- Progress bar with visual indicator
- Target number, elapsed time, estimated remaining

**Timeline View**
```
┌─ Timeline View ───────────────────────────────────────┐
│ ✓ M42 Orion (45m) → CURRENT: M31 (2h) → M33 (1.5h)... │
│ [====DONE====][======●======>[........][......]       │
└────────────────────────────────────────────────────────┘
```
- Horizontal timeline showing all targets
- Completed targets marked with checkmarks
- Current target highlighted
- Upcoming targets shown in sequence
- Visual progress bar spanning entire plan

**Current Target Detail**
```
┌─ Current Target Detail ───────────────────────────────┐
│ M31 - Andromeda Galaxy                                 │
│ RA: 0.7h | Dec: +41.3° | Alt: 52° | Type: Galaxy     │
│                                                        │
│ Capture History:                                       │
│   Total Exposure: 8.5 hours (720 frames, 12 sessions) │
│   Best Quality: FWHM 2.1" | 2847 stars                │
│   Status: 🟢 Complete (target: 6h)                    │
│   Last Captured: 2025-12-28                           │
│                                                        │
│ Tonight's Progress:                                    │
│   Frames: 45 / 100                                     │
│   Stacked: 38 good, 7 rejected                        │
│   Current FWHM: 2.3" | Stars: 2654                    │
│   [View Recent Frames →]                               │
└────────────────────────────────────────────────────────┘
```
- Target name and basic info (coordinates, type)
- **Capture History Section:**
  - Total exposure accumulated across all sessions
  - Best quality metrics achieved
  - Completion status with color coding
  - Last imaging date
- **Tonight's Progress Section:**
  - Current session frame count
  - Quality metrics for current run
  - Rejection statistics
  - Link to view frame details

**Upcoming Targets**
```
┌─ Upcoming Targets ────────────────────────────────────┐
│ Next: M33 Triangulum (1.5h) - Alt: 45° at 22:30      │
│       📊 History: 3.2h total | Status: Needs more data│
│ Then: NGC 891 (2h) - Alt: 38° at 00:00               │
│       📊 History: None | Status: New target            │
└────────────────────────────────────────────────────────┘
```
- Shows next 2-3 targets in queue
- Scheduled altitude and time
- Capture history summary for each
- Status indicators

**API Calls:**
- Progress: `GET /api/telescope/progress` (poll every 2s during execution)
- Target History: `GET /api/captures/{catalog_id}` (load once per target)
- Plan: `GET /api/plans/{id}` (load on execution start)

### Tab 2: Library View
**Browse and manage all captured data**

**Components:**

**Toolbar**
```
┌─ Capture Library ─────────────────────────────────────┐
│ [Search: ____] [Filter: All ▾] [Sort: Recent ▾]       │
│ [Sync Files] [Transfer from Seestar]                  │
```
- Search box (filters by target name, catalog ID)
- Filter dropdown (All, Complete, Needs More Data, New)
- Sort dropdown (Recent, Name, Total Exposure, Quality)
- Sync Files button (refreshes library from database)
- Transfer button (triggers file download from Seestar)

**Target Grid**
```
│ ┌─ M31 Andromeda ──────────────┐ ┌─ M42 Orion ──────┐│
│ │ 🟢 Complete                   │ │ 🟡 Needs More    ││
│ │ 8.5h | 720 frames | 12 sess. │ │ 2.1h | 210 fr... ││
│ │ FWHM: 2.1" | Quality: ⭐⭐⭐⭐⭐ │ │ FWHM: 2.8"      ││
│ │ Last: 2025-12-28              │ │ Last: 2025-12-2 ││
│ │ [View] [Process] [Export]    │ │ [View] [Process]││
│ └───────────────────────────────┘ └──────────────────┘│
```
- Grid of target cards (responsive: 1-4 columns based on width)
- Status indicator with color (🟢 Complete, 🟡 Needs More, 🔴 New)
- Key statistics (exposure, frames, sessions)
- Quality metrics (FWHM, star rating)
- Last capture date
- Action buttons (View details, Process, Export)

**File Transfer Status**
```
File Transfer Status:
Last sync: 2 hours ago | 156 files | 12.3 GB
[Progress Bar] Transferring: M31_2025-01-01_045.fit (23/50 files)
```
- Shows last sync time and statistics
- Live progress bar during transfer
- Current file being transferred
- File count progress

**API Calls:**
- Load Library: `GET /api/captures` (paginated)
- Transfer Files: `POST /api/captures/transfer`
- Transfer Progress: Poll `GET /api/captures/transfer/status` (every 1s during transfer)
- View Target: `GET /api/captures/{catalog_id}/files`

### Tab 3: Telemetry View
**Live technical data from telescope**

**Components:**

**Current Position**
```
┌─ Current Position ────────────────────────────────────┐
│ RA: 0.712h (00:42:43) | Dec: +41.269° (+41°16'08")   │
│ Alt: 52.3° | Az: 123.5° | Tracking: ✓ Good          │
│ Update rate: 1 Hz | Last update: 0.1s ago            │
└────────────────────────────────────────────────────────┘
```
- Current RA/Dec in both decimal and HMS/DMS format
- Altitude and azimuth
- Tracking status
- Update frequency and recency

**Plate Solve Result**
```
┌─ Plate Solve Result ──────────────────────────────────┐
│ ✓ Solved successfully                                  │
│ Target: M31 | Offset: 2.3 arcmin                      │
│ Field Rotation: 0.5° | Match: 95% confidence          │
│ [Re-solve] [Center Target]                            │
└────────────────────────────────────────────────────────┘
```
- Solve status (success/failed)
- Target identification
- Pointing offset from intended target
- Field rotation
- Confidence level
- Re-solve button
- Center target button (corrects pointing)

**Field Annotations**
```
┌─ Field Annotations ───────────────────────────────────┐
│ Objects in field:                                      │
│ • M31 (Andromeda Galaxy) - Center                     │
│ • M32 (NGC 221) - 15' South                           │
│ • M110 (NGC 205) - 35' Northwest                      │
│ • HD 3969 (Star, Mag 6.2) - 8' East                   │
│ [Show Star Chart] [Export Field Data]                 │
└────────────────────────────────────────────────────────┘
```
- List of identified objects in current field
- Object names and types
- Positions relative to center
- Magnitude for stars
- Star chart link
- Export button

**Device Status**
```
┌─ Device Status ───────────────────────────────────────┐
│ Firmware: v6.45 | CPU: 45% | Temp: 38°C              │
│ Storage: 128 GB free / 256 GB | Battery: N/A (AC)    │
│ WiFi: Connected (Signal: -45 dBm)                     │
│ Dew Heater: On (90%) | Focus: 1250 / 2600            │
└────────────────────────────────────────────────────────┘
```
- Firmware version
- System stats (CPU, temp)
- Storage capacity
- Power status
- Network status
- Hardware state (dew heater, focuser)

**API Calls:**
- Position: `POST /api/telescope/command/get_current_coordinates` (poll 1s)
- Device State: `POST /api/telescope/command/get_device_state` (poll 1s)
- Plate Solve: `POST /api/telescope/command/get_plate_solve_result` (on demand)
- Annotations: `POST /api/telescope/command/get_field_annotations` (on demand)

### Tab 4: Live View
**Embedded telescope camera feed**

```
┌─ Telescope Camera Feed ───────────────────────────────┐
│                                                        │
│          [Live camera preview/iframe]                  │
│                                                        │
│ Exposure: 0.5s | Gain: Auto | Binning: 1x1           │
│ [Open Full Screen] [Download Frame] [Settings]        │
└────────────────────────────────────────────────────────┘
```
- Live camera preview (iframe or direct embed)
- Current camera settings display
- Full screen button (opens dedicated Live View tab)
- Download current frame button
- Settings button (quick access to exposure/gain)

**Implementation:** Reuses existing Live View tab infrastructure, embedded in iframe or as link.

---

## 5. Bottom Drawer - Advanced Controls

### Drawer Header
```
[⬆ Advanced Controls ▼] Last used: Advanced Stacking
────────────────────────────────────────────────────────
```
- Expandable/collapsible with click or `Ctrl+D`
- Shows last active tab
- Notification badge when attention needed

### Tab 1: Advanced Stacking

```
┌─ Advanced Stacking Settings ──────────────────────────┐
│ Dark Background Extraction (DBE):                      │
│   ☑ Enable | Smoothness: [50]% ──●────────           │
│                                                        │
│ Star Correction:                                       │
│   ☑ Enable | Aggressiveness: [75]% ────●───          │
│                                                        │
│ Image Enhancement:                                     │
│   ☑ Airplane/Satellite Removal                        │
│   ☑ Drizzle 2x (increases resolution)                 │
│   ☐ Wide Field Denoise                                │
│                                                        │
│ Rejection Settings:                                    │
│   Algorithm: [Sigma Clipping ▾]                       │
│   Threshold: [3.0] sigma                               │
│   Min frames: [3]                                      │
│                                                        │
│ [Apply Settings] [Reset to Default] [Save Preset]     │
└────────────────────────────────────────────────────────┘
```

**Controls:**
- DBE toggle and smoothness slider
- Star correction toggle and aggressiveness slider
- Enhancement checkboxes (airplane removal, drizzle, denoise)
- Rejection algorithm dropdown
- Threshold and minimum frames inputs
- Apply, reset, and save preset buttons

**API Calls:**
- Apply: `POST /api/telescope/command/configure_advanced_stacking`

### Tab 2: System Management

```
┌─ System Controls ─────────────────────────────────────┐
│ Power Management:                                      │
│   [🔌 Shutdown Telescope] [🔄 Reboot Telescope]       │
│   ⚠️ Warning: Will interrupt any active imaging        │
│                                                        │
│ System Information:                                    │
│   Uptime: 3d 14h 23m                                  │
│   CPU Usage: 45% | Memory: 2.1GB / 4GB               │
│   Temperature: 38°C (Normal)                          │
│   Storage: 128GB free / 256GB total                   │
│                                                        │
│ Time & Location:                                       │
│   System Time: 2025-01-01 22:45:30 UTC               │
│   Location: 45.52°N, 122.68°W                        │
│   [Set Time] [Set Location]                           │
│                                                        │
│ Notifications:                                         │
│   Volume: ○ Silent ● Backyard ○ Outdoor              │
│   [🔊 Test Sound]                                     │
└────────────────────────────────────────────────────────┘
```

**Controls:**
- Shutdown and reboot buttons (with confirmation modal)
- System info display (read-only, updates every 5s)
- Set time button (opens datetime picker, syncs with computer)
- Set location button (opens coordinate input or uses browser geolocation)
- Notification volume radio buttons
- Test sound button

**API Calls:**
- Shutdown: `POST /api/telescope/command/shutdown_telescope`
- Reboot: `POST /api/telescope/command/reboot_telescope`
- Get Info: `POST /api/telescope/command/get_pi_info`
- Set Time: `POST /api/telescope/command/set_pi_time`
- Set Location: `POST /api/telescope/command/set_location`
- Play Sound: `POST /api/telescope/command/play_notification_sound`

### Tab 3: WiFi & Network

```
┌─ WiFi Management ─────────────────────────────────────┐
│ Access Point Mode:                                     │
│   SSID: [Seestar_S50_____] 5GHz: ☑                   │
│   Password: [**********]                               │
│   [Update AP Settings]                                 │
│                                                        │
│ Client Mode:                                           │
│   Status: ○ Disabled ● Enabled                        │
│   Connected to: "HomeNetwork"                         │
│   Signal: -45 dBm (Excellent) ▂▄▆█                    │
│   IP: 192.168.1.47                                    │
│                                                        │
│ Available Networks:                                    │
│   ┌─────────────────────────────────┐                 │
│   │ ● HomeNetwork      [Connect]    │                 │
│   │ ● GuestWiFi        [Connect]    │                 │
│   │ ○ Neighbor5G       [Connect]    │                 │
│   └─────────────────────────────────┘                 │
│   [Scan Networks] [Forget Network]                    │
│                                                        │
│ Region: [US ▾] (WiFi regulatory domain)              │
└────────────────────────────────────────────────────────┘
```

**Controls:**
- AP configuration (SSID, password, 5GHz toggle)
- Client mode toggle
- Network list with signal strength
- Connect/disconnect buttons per network
- Scan networks button (refreshes list)
- Forget network button
- Region dropdown

**API Calls:**
- Configure AP: `POST /api/telescope/command/configure_access_point`
- Enable Client: `POST /api/telescope/command/enable_wifi_client_mode`
- Scan: `POST /api/telescope/command/scan_wifi_networks`
- Connect: `POST /api/telescope/command/connect_to_wifi`
- Save Network: `POST /api/telescope/command/save_wifi_network`
- Remove: `POST /api/telescope/command/remove_wifi_network`
- Set Country: `POST /api/telescope/command/set_wifi_country`

### Tab 4: Calibration & Alignment

```
┌─ Calibration Tools ───────────────────────────────────┐
│ Polar Alignment:                                       │
│   Status: Last checked 2025-12-30                     │
│   Error: 2.3 arcmin (Good)                            │
│   [Check Alignment] [Clear Calibration]               │
│                                                        │
│ Compass Calibration:                                   │
│   Heading: 123.5° (ESE)                               │
│   Calibrated: ✓ Yes | Last: 2025-12-28                │
│   [Start Calibration] [Stop] [Check Status]           │
│   ℹ️ Rotate telescope slowly during calibration        │
│                                                        │
│ Focuser:                                               │
│   Current: 1250 / 2600                                │
│   Factory Default: 1300                               │
│   [Reset to Factory Position]                         │
│   ⚠️ Will move focuser, pause imaging first            │
└────────────────────────────────────────────────────────┘
```

**Controls:**
- Check polar alignment button (runs check, displays error)
- Clear calibration button (resets polar alignment)
- Compass calibration start/stop buttons
- Compass status display
- Focuser reset button (with warning)

**API Calls:**
- Check PA: `POST /api/telescope/command/check_polar_alignment`
- Clear PA: `POST /api/telescope/command/clear_polar_alignment`
- Start Compass: `POST /api/telescope/command/start_compass_calibration`
- Stop Compass: `POST /api/telescope/command/stop_compass_calibration`
- Get Compass: `POST /api/telescope/command/get_compass_state`
- Reset Focuser: `POST /api/telescope/command/reset_focuser_to_factory`

### Tab 5: Hardware & Accessories

```
┌─ Hardware Configuration ──────────────────────────────┐
│ DC Output Ports:                                       │
│   Port 1: ○ Off ● On | Voltage: [12V ▾]              │
│           Label: [Guide Camera_______]                │
│   Port 2: ● Off ○ On | Voltage: [5V ▾]               │
│           Label: [USB Hub____________]                │
│   [Apply Configuration]                                │
│                                                        │
│ Remote Session:                                        │
│   Session ID: [ABC123________]                        │
│   Status: ○ Not in session                            │
│   [Join Session] [Leave Session]                      │
│   Connected Clients: 0                                │
│   [View Clients] [Disconnect Client]                  │
│                                                        │
│ Demo Mode:                                             │
│   ○ Disabled ● Enabled (simulates telescope)          │
│   [Toggle Demo Mode]                                   │
│   ℹ️ For testing without hardware                      │
└────────────────────────────────────────────────────────┘
```

**Controls:**
- DC output toggles, voltage dropdowns, and labels
- Apply configuration button
- Remote session ID input and status
- Join/leave session buttons
- Client management buttons
- Demo mode toggle

**API Calls:**
- DC Output: `POST /api/telescope/command/set_dc_output`, `get_dc_output`
- Join Session: `POST /api/telescope/command/join_remote_session`
- Leave Session: `POST /api/telescope/command/leave_remote_session`
- Disconnect Client: `POST /api/telescope/command/disconnect_remote_client`
- Demo Mode: `POST /api/telescope/command/start_demo_mode`, `stop_demo_mode`

---

## 6. Data Flow & State Management

### API Integration

**Telescope Control Endpoints:**
```
POST   /api/telescope/connect              # Connect to telescope
POST   /api/telescope/disconnect           # Disconnect
GET    /api/telescope/status               # Get status (poll 1s)
POST   /api/telescope/execute              # Execute plan
POST   /api/telescope/abort                # Abort execution
POST   /api/telescope/park                 # Park telescope
GET    /api/telescope/progress             # Get progress (poll 2s)
POST   /api/telescope/command/{cmd}        # Generic command proxy
```

**Capture Library Endpoints:**
```
GET    /api/captures                       # List all capture history
GET    /api/captures/{catalog_id}          # Get target history
GET    /api/captures/{catalog_id}/files    # Get files for target
GET    /api/captures/files/all             # All output files
POST   /api/captures/transfer              # Trigger file transfer
```

**Enhanced Targets:**
```
GET    /api/targets?include_history=true   # Targets with capture history
```

**Plans:**
```
GET    /api/plans                          # List saved plans
POST   /api/plans/{id}/execute             # Execute saved plan
```

### State Management

**Global State Object:**
```javascript
const observeState = {
  connection: {
    status: 'disconnected',  // disconnected | connecting | connected
    host: '192.168.2.47',
    port: 4700,
    firmware: null,
    lastUpdate: null,
    signalStrength: null
  },

  execution: {
    isExecuting: false,
    currentPlan: null,
    currentTarget: null,
    currentTargetIndex: 0,
    totalTargets: 0,
    currentPhase: null,     // slewing | focusing | stacking | complete
    progress: 0,            // 0-100
    startTime: null,
    elapsedSeconds: 0,
    estimatedRemainingSeconds: 0,
    framesCurrent: 0,
    framesTotal: 0,
    errors: []
  },

  library: {
    targets: [],            // Array of capture history objects
    filteredTargets: [],    // After search/filter applied
    filters: {
      search: '',
      status: 'all',        // all | complete | needs_more | new
      sortBy: 'recent'      // recent | name | exposure | quality
    },
    loading: false,
    transferStatus: {
      inProgress: false,
      currentFile: null,
      filesCompleted: 0,
      filesTotal: 0,
      lastSyncTime: null
    }
  },

  telemetry: {
    position: {
      ra: 0,              // Hours
      dec: 0,             // Degrees
      alt: 0,             // Degrees
      az: 0               // Degrees
    },
    deviceState: {},      // Full device state object
    plateSolve: null,     // Plate solve result
    annotations: [],      // Field annotations
    lastUpdate: null
  },

  controls: {
    imaging: {
      stackExposure: 10,
      previewExposure: 0.5,
      gain: 100,
      gainAuto: true,
      filter: 'clear',    // clear | lp
      dither: {
        enabled: true,
        pixels: 50,
        interval: 10
      }
    },
    dewHeater: {
      enabled: false,
      power: 90
    },
    focus: {
      position: 0,
      max: 2600
    },
    advancedStacking: {
      dbe: false,
      dbeSmooth: 50,
      starCorrection: false,
      starAggressiveness: 75,
      airplaneRemoval: false,
      drizzle: false,
      denoise: false
    }
  },

  ui: {
    activeMainTab: 'execution',  // execution | library | telemetry | live
    drawerOpen: false,
    drawerActiveTab: 'stacking', // stacking | system | wifi | calibration | hardware
    sidebarCollapsed: false,
    activeSidebarSection: {
      connection: true,
      execution: true,
      imaging: false,
      telescope: false,
      hardware: false,
      info: false
    }
  }
};
```

### Update Patterns

**Connection Updates:**
```javascript
// On connect button click
async function connectTelescope() {
  observeState.connection.status = 'connecting';
  updateConnectionUI();

  try {
    const response = await fetch('/api/telescope/connect', {
      method: 'POST',
      body: JSON.stringify({
        host: observeState.connection.host,
        port: observeState.connection.port
      })
    });

    if (response.ok) {
      observeState.connection.status = 'connected';
      const data = await response.json();
      observeState.connection.firmware = data.firmware;
      startTelemetryPolling();
    } else {
      observeState.connection.status = 'disconnected';
      showError('Connection failed');
    }
  } catch (error) {
    observeState.connection.status = 'disconnected';
    showError('Network error: ' + error.message);
  }

  updateConnectionUI();
}
```

**Execution Updates (Polling):**
```javascript
let executionPollInterval = null;

function startExecutionPolling() {
  executionPollInterval = setInterval(async () => {
    try {
      const response = await fetch('/api/telescope/progress');
      const data = await response.json();

      observeState.execution.currentTarget = data.current_target;
      observeState.execution.currentPhase = data.phase;
      observeState.execution.progress = data.progress_percent;
      observeState.execution.framesCurrent = data.frames_current;
      observeState.execution.framesTotal = data.frames_total;
      observeState.execution.estimatedRemainingSeconds = data.estimated_remaining;

      updateExecutionUI();
    } catch (error) {
      console.error('Failed to fetch progress:', error);
    }
  }, 2000); // Poll every 2 seconds
}

function stopExecutionPolling() {
  if (executionPollInterval) {
    clearInterval(executionPollInterval);
    executionPollInterval = null;
  }
}
```

**Library Updates:**
```javascript
async function loadCaptureLibrary() {
  observeState.library.loading = true;
  updateLibraryUI();

  try {
    const response = await fetch('/api/captures');
    const data = await response.json();

    observeState.library.targets = data;
    applyLibraryFilters();
  } catch (error) {
    showError('Failed to load library: ' + error.message);
  } finally {
    observeState.library.loading = false;
    updateLibraryUI();
  }
}

function applyLibraryFilters() {
  let filtered = [...observeState.library.targets];

  // Apply search
  if (observeState.library.filters.search) {
    const search = observeState.library.filters.search.toLowerCase();
    filtered = filtered.filter(t =>
      t.catalog_id.toLowerCase().includes(search) ||
      t.name?.toLowerCase().includes(search)
    );
  }

  // Apply status filter
  if (observeState.library.filters.status !== 'all') {
    filtered = filtered.filter(t => t.status === observeState.library.filters.status);
  }

  // Apply sort
  switch (observeState.library.filters.sortBy) {
    case 'recent':
      filtered.sort((a, b) => new Date(b.last_captured_at) - new Date(a.last_captured_at));
      break;
    case 'name':
      filtered.sort((a, b) => a.catalog_id.localeCompare(b.catalog_id));
      break;
    case 'exposure':
      filtered.sort((a, b) => b.total_exposure_seconds - a.total_exposure_seconds);
      break;
    case 'quality':
      filtered.sort((a, b) => (b.best_fwhm || 999) - (a.best_fwhm || 999));
      break;
  }

  observeState.library.filteredTargets = filtered;
  updateLibraryUI();
}
```

**Telemetry Updates (Fast Polling):**
```javascript
let telemetryPollInterval = null;

function startTelemetryPolling() {
  telemetryPollInterval = setInterval(async () => {
    try {
      // Get multiple data points in parallel
      const [statusResponse, coordsResponse] = await Promise.all([
        fetch('/api/telescope/status'),
        fetch('/api/telescope/command/get_current_coordinates', { method: 'POST' })
      ]);

      const status = await statusResponse.json();
      const coords = await coordsResponse.json();

      observeState.telemetry.position = coords;
      observeState.telemetry.deviceState = status;
      observeState.telemetry.lastUpdate = Date.now();

      updateTelemetryUI();
    } catch (error) {
      console.error('Telemetry update failed:', error);
    }
  }, 1000); // Poll every 1 second
}
```

### Error Handling

**Connection Errors:**
```javascript
async function handleConnectionError(error) {
  // Show user-friendly error
  showToast('Connection Error: ' + error.message, 'error');

  // Auto-retry with exponential backoff
  let retryCount = 0;
  const maxRetries = 3;

  while (retryCount < maxRetries) {
    await sleep(Math.pow(2, retryCount) * 1000);

    try {
      await connectTelescope();
      showToast('Reconnected successfully', 'success');
      return;
    } catch (retryError) {
      retryCount++;
    }
  }

  // Final failure
  observeState.connection.status = 'disconnected';
  showError('Unable to connect after multiple attempts. Please check your network and telescope.');
}
```

**API Errors:**
```javascript
async function handleAPIError(endpoint, error, context) {
  console.error(`API Error [${endpoint}]:`, error);

  // Show inline error near affected control
  if (context.element) {
    showInlineError(context.element, error.message);
  }

  // Offer retry for transient errors
  if (error.status >= 500 || error.status === 0) {
    showRetryButton(context.element, () => context.retryFunction());
  }

  // Log to browser console for debugging
  console.group('API Error Details');
  console.log('Endpoint:', endpoint);
  console.log('Error:', error);
  console.log('Context:', context);
  console.groupEnd();
}
```

**Telescope Errors:**
```javascript
function handleTelescopeError(error) {
  // Parse telescope-specific error
  const errorCode = error.code || 'UNKNOWN';
  const errorMessage = error.message || 'An unknown error occurred';

  // Show prominent error banner
  showErrorBanner({
    title: 'Telescope Error',
    message: errorMessage,
    code: errorCode,
    actions: [
      { label: 'Reconnect', action: reconnectTelescope },
      { label: 'Park & Abort', action: parkAndAbort },
      { label: 'Dismiss', action: dismissError }
    ]
  });

  // Update execution state
  if (observeState.execution.isExecuting) {
    observeState.execution.errors.push({
      timestamp: Date.now(),
      code: errorCode,
      message: errorMessage
    });
    updateExecutionUI();
  }

  // Log full error for support
  console.error('Telescope Error:', {
    code: errorCode,
    message: errorMessage,
    state: observeState,
    timestamp: new Date().toISOString()
  });
}
```

### Performance Optimizations

**Debouncing:**
```javascript
// Debounce slider adjustments
function debounceDewHeaterPower(power) {
  clearTimeout(this.dewHeaterDebounce);

  // Update UI immediately for responsiveness
  observeState.controls.dewHeater.power = power;
  updateDewHeaterUI();

  // Send to telescope after 500ms of no changes
  this.dewHeaterDebounce = setTimeout(async () => {
    await fetch('/api/telescope/command/set_dew_heater', {
      method: 'POST',
      body: JSON.stringify({
        enabled: observeState.controls.dewHeater.enabled,
        power_level: power
      })
    });
  }, 500);
}
```

**Caching:**
```javascript
// Cache library data for 5 minutes
const LIBRARY_CACHE_DURATION = 5 * 60 * 1000;
let libraryCacheTimestamp = 0;

async function loadCaptureLibrary(forceRefresh = false) {
  const now = Date.now();

  if (!forceRefresh && now - libraryCacheTimestamp < LIBRARY_CACHE_DURATION) {
    // Use cached data
    applyLibraryFilters();
    return;
  }

  // Fetch fresh data
  // ... (existing fetch code)

  libraryCacheTimestamp = now;
}
```

**Lazy Loading:**
```javascript
// Only fetch tab data when tab is activated
function showMainTab(tabName) {
  observeState.ui.activeMainTab = tabName;

  // Update tab UI
  document.querySelectorAll('.main-tab').forEach(tab => {
    tab.classList.remove('active');
  });
  document.getElementById(tabName + '-tab').classList.add('active');

  // Load tab-specific data
  switch (tabName) {
    case 'library':
      loadCaptureLibrary();
      break;
    case 'telemetry':
      startTelemetryPolling();
      break;
    case 'live':
      // Live view iframe loads automatically
      break;
  }
}
```

**Virtual Scrolling:**
```javascript
// For file lists > 100 items
function renderVirtualFileList(files, containerHeight) {
  const itemHeight = 60; // px
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const scrollTop = fileListContainer.scrollTop;
  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.min(startIndex + visibleCount + 2, files.length);

  // Only render visible items
  const visibleFiles = files.slice(startIndex, endIndex);

  fileListContainer.innerHTML = `
    <div style="height: ${files.length * itemHeight}px; position: relative;">
      <div style="position: absolute; top: ${startIndex * itemHeight}px;">
        ${visibleFiles.map(renderFileItem).join('')}
      </div>
    </div>
  `;
}
```

---

## 7. Visual Design & Styling

### Color Scheme

```css
:root {
  /* Primary Colors */
  --primary-blue: #667eea;
  --primary-purple: #764ba2;
  --success-green: #10b981;
  --warning-yellow: #f59e0b;
  --danger-red: #ef4444;
  --info-blue: #3b82f6;

  /* Status Colors */
  --status-complete: #10b981;    /* 🟢 */
  --status-partial: #f59e0b;     /* 🟡 */
  --status-new: #6b7280;         /* ⚫ */
  --status-executing: #3b82f6;   /* 🔵 */

  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-panel: #ffffff;
  --bg-hover: #f3f4f6;
  --bg-drawer: #f9fafb;

  /* Borders */
  --border-color: #e5e7eb;
  --border-radius: 8px;
  --border-radius-small: 4px;

  /* Shadows */
  --shadow-small: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-medium: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-large: 0 10px 25px rgba(0,0,0,0.15);

  /* Text */
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --text-tertiary: #9ca3af;

  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
}
```

### Typography

```css
/* Headings */
h1 { font-size: 2.5em; font-weight: 700; }
h2 { font-size: 1.8em; font-weight: 600; }
h3 { font-size: 1.2em; font-weight: 600; }
h4 { font-size: 1em; font-weight: 600; }

/* Body */
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 0.95em;
  line-height: 1.6;
  color: var(--text-primary);
}

/* Utility Classes */
.text-sm { font-size: 0.85em; }
.text-xs { font-size: 0.75em; }
.text-secondary { color: var(--text-secondary); }
.text-tertiary { color: var(--text-tertiary); }
```

### Component Styles

**Buttons:**
```css
.btn {
  padding: 10px 16px;
  border-radius: var(--border-radius-small);
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease;
  border: none;
  font-size: 0.95em;
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary-blue), var(--primary-purple));
  color: white;
  box-shadow: var(--shadow-small);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-medium);
  filter: brightness(110%);
}

.btn-primary:active {
  transform: translateY(0);
  filter: brightness(95%);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: transparent;
  border: 2px solid var(--border-color);
  color: var(--text-primary);
}

.btn-danger {
  background: var(--danger-red);
  color: white;
}

.btn-success {
  background: var(--success-green);
  color: white;
}

.btn-icon {
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

**Panels:**
```css
.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  transition: box-shadow 200ms ease;
}

.panel:hover {
  box-shadow: var(--shadow-small);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.panel-collapsible .panel-header {
  cursor: pointer;
  user-select: none;
}

.panel-collapsible .panel-header:hover {
  background: var(--bg-hover);
  margin: calc(-1 * var(--spacing-sm));
  padding: var(--spacing-sm);
  border-radius: var(--border-radius-small);
}
```

**Status Indicators:**
```css
.status-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}

.status-connected {
  background: var(--success-green);
  box-shadow: 0 0 8px var(--success-green);
  animation: pulse 2s ease-in-out infinite;
}

.status-connecting {
  background: var(--warning-yellow);
  box-shadow: 0 0 8px var(--warning-yellow);
  animation: pulse 1s ease-in-out infinite;
}

.status-disconnected {
  background: var(--text-tertiary);
}

.status-error {
  background: var(--danger-red);
  box-shadow: 0 0 8px var(--danger-red);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

**Input Fields:**
```css
input[type="text"],
input[type="number"],
select {
  padding: 8px 12px;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-small);
  font-size: 0.95em;
  transition: border-color 200ms ease;
  background: var(--bg-primary);
  color: var(--text-primary);
}

input:focus,
select:focus {
  outline: none;
  border-color: var(--primary-blue);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

input:disabled {
  background: var(--bg-secondary);
  color: var(--text-tertiary);
  cursor: not-allowed;
}
```

**Sliders:**
```css
input[type="range"] {
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: var(--border-color);
  outline: none;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-blue);
  cursor: pointer;
  box-shadow: var(--shadow-small);
  transition: all 150ms ease;
}

input[type="range"]::-webkit-slider-thumb:hover {
  background: var(--primary-purple);
  transform: scale(1.1);
  box-shadow: var(--shadow-medium);
}

input[type="range"]::-webkit-slider-thumb:active {
  transform: scale(0.95);
}
```

**Progress Bars:**
```css
.progress-container {
  width: 100%;
  height: 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-blue), var(--primary-purple));
  transition: width 500ms linear;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 0.85em;
}

.progress-bar-striped {
  background-image: linear-gradient(
    45deg,
    rgba(255,255,255,0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255,255,255,0.15) 50%,
    rgba(255,255,255,0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 40px 40px;
  animation: progress-stripes 1s linear infinite;
}

@keyframes progress-stripes {
  0% { background-position: 40px 0; }
  100% { background-position: 0 0; }
}
```

**Tabs:**
```css
.tab-container {
  display: flex;
  gap: var(--spacing-sm);
  border-bottom: 2px solid var(--border-color);
  margin-bottom: var(--spacing-lg);
}

.tab {
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  color: var(--text-secondary);
  font-weight: 500;
  transition: all 200ms ease;
  user-select: none;
}

.tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tab.active {
  color: var(--primary-blue);
  border-bottom-color: var(--primary-blue);
}
```

### Responsive Breakpoints

```css
/* Desktop (default) */
.observe-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--spacing-lg);
}

/* Tablet */
@media (max-width: 1200px) {
  .observe-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: fixed;
    left: -320px;
    top: 0;
    bottom: 0;
    width: 320px;
    background: var(--bg-primary);
    box-shadow: var(--shadow-large);
    transition: left 300ms ease;
    z-index: 1000;
  }

  .sidebar.open {
    left: 0;
  }

  .hamburger-btn {
    display: block;
  }
}

/* Mobile */
@media (max-width: 768px) {
  .tab-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .tab {
    white-space: nowrap;
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .panel {
    padding: var(--spacing-md);
  }

  .btn {
    width: 100%;
    margin-bottom: var(--spacing-sm);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  /* Bottom drawer becomes modal */
  .drawer {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    max-height: 80vh;
    border-radius: var(--border-radius) var(--border-radius) 0 0;
  }

  /* Touch targets */
  .btn,
  input,
  select {
    min-height: 44px;
  }
}
```

### Animations

```css
/* Smooth transitions */
* {
  transition-property: background-color, border-color, color, box-shadow, transform;
  transition-duration: 150ms;
  transition-timing-function: ease;
}

/* Panel expand/collapse */
.panel-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 300ms ease-in-out;
}

.panel-body.expanded {
  max-height: 1000px;
}

/* Drawer slide */
.drawer {
  transform: translateY(100%);
  transition: transform 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer.open {
  transform: translateY(0);
}

/* Fade in */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 200ms ease;
}

/* Slide in from right */
@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.slide-in-right {
  animation: slideInRight 300ms ease;
}

/* Loading skeleton */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 25%,
    var(--bg-hover) 50%,
    var(--bg-secondary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Spinner */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-color);
  border-top-color: var(--primary-blue);
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### Accessibility

```css
/* Focus indicators */
*:focus {
  outline: 2px solid var(--primary-blue);
  outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :root {
    --border-color: #000000;
    --text-secondary: #000000;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Screen reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

---

## 8. Implementation Strategy

### Phase 1: Foundation (Week 1)
1. Create new HTML structure for three-zone layout
2. Implement global state management object
3. Set up API wrapper functions for all telescope commands
4. Create CSS framework with variables and base styles
5. Build sidebar with collapsible sections (static, no functionality)

### Phase 2: Core Functionality (Week 2)
1. Implement connection management (connect/disconnect/status)
2. Build execution view with progress monitoring
3. Add polling mechanism for real-time updates
4. Integrate existing plan execution logic
5. Create error handling framework

### Phase 3: Capture History Integration (Week 3)
1. Build Library tab with target grid
2. Implement file transfer UI and progress
3. Integrate capture history into Execution tab
4. Add search/filter/sort to library
5. Create target detail views

### Phase 4: Advanced Controls (Week 4)
1. Build bottom drawer with tabbed interface
2. Implement all imaging controls
3. Add telescope control functions (goto, focus, etc.)
4. Build hardware controls (dew heater, DC outputs)
5. Implement system management features

### Phase 5: Telemetry & Polish (Week 5)
1. Build Telemetry tab with live data
2. Implement plate solve and annotations display
3. Add Live View tab integration
4. Polish animations and transitions
5. Responsive design optimization

### Phase 6: Testing & Refinement (Week 6)
1. Cross-browser testing
2. Mobile device testing
3. Accessibility audit and fixes
4. Performance optimization
5. User testing and feedback incorporation

---

## 9. Success Criteria

**Functional:**
- ✅ Can connect/disconnect from telescope successfully
- ✅ Can execute plans and monitor progress in real-time
- ✅ Capture history displays correctly and updates
- ✅ File transfers work reliably
- ✅ All 60+ telescope commands are accessible and functional
- ✅ Telemetry updates in real-time (< 2s latency)
- ✅ Error handling gracefully handles all failure modes

**Usability:**
- ✅ Interface is intuitive for first-time users
- ✅ Common tasks require ≤ 3 clicks
- ✅ Keyboard navigation works throughout
- ✅ Mobile layout is fully functional
- ✅ No UI freezing or lag during operations

**Performance:**
- ✅ Initial page load < 2s
- ✅ Tab switching < 500ms
- ✅ Polling overhead < 5% CPU
- ✅ Library with 100+ targets loads < 1s
- ✅ Smooth 60fps animations

**Reliability:**
- ✅ Handles network interruptions gracefully
- ✅ Auto-reconnects after temporary disconnection
- ✅ No data loss during crashes
- ✅ Polling continues reliably for 12+ hour sessions
- ✅ State persists across page refreshes

---

## 10. Future Enhancements

**Post-MVP Features:**
- WebSocket support for real-time updates (reduce polling overhead)
- Offline mode with service workers
- Multi-telescope support (control multiple Seestars)
- Image preview thumbnails in library
- Advanced analytics dashboard (best targets, weather correlation, etc.)
- Plan templates and scheduler
- Mobile app wrapper (Cordova/Capacitor)
- Voice control integration
- Automated target selection based on conditions
- Integration with weather forecasts for planning

---

## Appendix: File Structure

```
frontend/
├── index.html                 # Main entry point (updated Observe tab)
├── css/
│   ├── observe.css           # Observe view styles
│   ├── components.css        # Reusable components
│   └── responsive.css        # Breakpoints
├── js/
│   ├── observe-state.js      # State management
│   ├── observe-connection.js # Connection handling
│   ├── observe-execution.js  # Execution monitoring
│   ├── observe-library.js    # Capture library
│   ├── observe-telemetry.js  # Telemetry display
│   ├── observe-controls.js   # Telescope controls
│   ├── observe-drawer.js     # Bottom drawer
│   └── observe-ui.js         # UI updates
└── assets/
    └── icons/                # UI icons
