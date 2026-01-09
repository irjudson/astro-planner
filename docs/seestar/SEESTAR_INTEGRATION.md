# Seestar S50 Integration Guide

**Last Updated:** 2025-12-25

This guide explains how to use your Astro Planner observing plans with the Seestar S50 smart telescope for fully automated astrophotography sessions.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Integration Methods](#integration-methods)
- [Method 1: seestar_alp CSV Export](#method-1-seestar_alp-csv-export-recommended)
- [Method 2: Direct TCP Control](#method-2-direct-tcp-control-advanced)
- [Setup Guide](#setup-guide)
- [Optimal Settings](#optimal-settings)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

---

## Quick Start

### 5-Minute Workflow

**1. Generate your plan** in Astro Planner
**2. Export as** "seestar_alp CSV (Recommended)"
**3. Import into** seestar_alp on your Raspberry Pi
**4. Start** automated imaging!

### What You'll Need

- Seestar S50 telescope
- Raspberry Pi or computer (for seestar_alp)
- Local WiFi network
- Astro Planner (this application)

---

## Integration Methods

Astro Planner offers two ways to control your Seestar S50:

### Method 1: seestar_alp CSV Export (Recommended)

**Best for:** Most users, production use, proven reliability

Export observing plans as CSV files compatible with [seestar_alp](https://github.com/smart-underworld/seestar_alp), the community-standard scheduler.

**Advantages:**
- ✅ Battle-tested by community
- ✅ Works today with no additional setup
- ✅ Full mosaic support
- ✅ Stellarium integration
- ✅ Web-based interface

### Method 2: Direct TCP Control (Advanced)

**Best for:** Developers, custom workflows, advanced automation

Direct telescope control via TCP socket connection to Seestar S50.

**Advantages:**
- ✅ Lower latency
- ✅ No middleware needed
- ✅ Access to all Seestar features
- ✅ Full API control

**Status:** Backend implementation complete, API endpoints in development

---

## Method 1: seestar_alp CSV Export (Recommended)

### Overview

The Seestar S50 is a closed ecosystem with no official API. The astrophotography community has created **[seestar_alp](https://github.com/smart-underworld/seestar_alp)**, which has become the standard for automated Seestar scheduling.

**Features:**
- CSV import for observing schedules
- WiFi connection to Seestar S50
- Automated target sequencing
- Auto-focus between targets
- Mosaic support
- Stellarium integration
- Web-based interface

---

### Setup (One-Time)

#### Prerequisites
- Seestar S50 telescope
- Raspberry Pi (recommended) or any computer
- Local WiFi network

#### Step 1: Install seestar_alp

**On Raspberry Pi:**

```bash
# Clone the repository
git clone https://github.com/smart-underworld/seestar_alp.git
cd seestar_alp

# Install dependencies
pip3 install -r requirements.txt

# Start the web interface
python3 app.py
```

The web interface will be available at: `http://raspberrypi.local:5000`

**Docker Installation (Alternative):**

```bash
docker pull smartunderworld/seestar_alp
docker run -p 5000:5000 smartunderworld/seestar_alp
```

#### Step 2: Configure Seestar S50 WiFi

**Recommended: Station Mode** (Seestar connects to your home WiFi)

1. Power on your Seestar S50
2. Open the official Seestar app
3. Go to Settings → WiFi
4. Select "Station Mode"
5. Connect to your home WiFi network
6. Note the IP address assigned to your Seestar

**Alternative: Access Point Mode** (Seestar creates its own network)

Your device must connect to Seestar's WiFi network (SSID: `S50_xxxxxx`), which means no internet access during observing.

#### Step 3: Test Connection

1. Open seestar_alp web interface: `http://raspberrypi.local:5000`
2. Enter your Seestar's IP address
3. Click "Connect"
4. Verify connection status shows "Connected"

---

### Using Astro Planner with seestar_alp

#### Step-by-Step Workflow

##### 1. Generate Your Observing Plan

In Astro Planner:

1. Set your **Location** (expand "Location & Device" if collapsed)
2. Select **Seestar S50** from telescope dropdown
3. Choose **Exposure Time** (10s, 20s, 30s, or 60s)
   - **10s recommended** - Default, good for most targets
   - **20s-60s** - For very faint targets (may have higher rejection rate)
4. Set **Observing Date**
5. Configure **Preferences**:
   - Planning Mode (Balanced recommended for Seestar)
   - Object Types to include
   - Altitude constraints (30-70° recommended for Seestar)
6. Click **"Generate Observing Plan"**

##### 2. Review the Generated Plan

Check your plan for:
- **Target coverage**: Are all desired objects included?
- **Timing**: Does the schedule fit your imaging window?
- **Weather warning**: If shown, consider trying another night
- **Target count**: Balanced mode should give 5-10 targets for a typical night

##### 3. Export for seestar_alp

1. Scroll to **"Export Plan"** section
2. Choose your preferred export method:
   - **📱 Share QR Code** - Scan with phone/tablet for instant access
   - **🚀 seestar_alp CSV (Recommended)** - Download CSV file
3. Save file as: `observing_plan_YYYY-MM-DD.csv`

**QR Code Method (Easiest for Mobile Workflow)**:
- Click "Share QR Code" button
- Scan with your phone or tablet camera
- Your device will receive the complete plan in JSON format
- Save or share the plan data for import into seestar_alp

**What's in the export?**

The CSV file contains:
- Target names and coordinates (RA/Dec in J2000)
- Start times for each target
- Exposure duration (minutes)
- Recommended exposure settings
- Detailed instructions in file header

**Example CSV:**
```csv
# Seestar S50 Observing Plan - Generated by Astro Planner
# Location: Three Forks, MT (45.9183, -111.5433)
# Date: 2025-12-25
# Imaging Window: 20:45 - 04:30
# Total Targets: 8
TARGET_NAME,RA_HOURS,DEC_DEGREES,START_TIME,DURATION_MIN,EXPOSURE_SEC,FRAMES
M31,0.7122,41.2692,20:45,90,10,540
M33,1.5642,30.6600,22:30,60,10,360
M45,3.7833,24.1167,00:15,45,10,270
```

##### 4. Import into seestar_alp

1. Open seestar_alp web interface: `http://raspberrypi.local:5000`
2. Go to **"Scheduler"** tab
3. Click **"Import CSV"** or **"Upload Schedule"**
4. Select your downloaded `observing_plan_YYYY-MM-DD.csv`
5. Verify targets loaded correctly
6. Review start times and adjust if needed

##### 5. Execute Your Session

**Before starting:**
- Ensure Seestar is powered on and connected
- Polar align your Seestar (if first use)
- Check battery level (or connect AC power)
- Verify weather conditions
- Remove lens cap!

**To start:**
1. In seestar_alp, click **"Start Schedule"**
2. seestar_alp will:
   - Slew to first target at scheduled time
   - Auto-focus
   - Begin imaging with specified settings
   - Automatically advance to next target
   - Save images to Seestar's internal storage

**During the session:**
- Monitor progress in seestar_alp web interface
- Check focus quality (auto-focus runs between targets)
- View live stacking progress
- Adjust schedule if weather degrades

**Session completion:**
- seestar_alp will park the telescope when finished
- Images saved to Seestar's 64GB internal storage
- Access images via network share: `\\Seestar\` (Windows) or `smb://seestar.local` (Mac)

---

### Alternative: Manual Entry in Seestar App

If you don't have seestar_alp set up, you can manually enter targets:

1. Generate plan in Astro Planner
2. Export as **Text Format** or **CSV** for reference
3. Open official Seestar app
4. Go to **"Plan Mode"** (requires firmware v2.3+)
5. Manually add each target:
   - Search target name in Sky Atlas
   - Set start/stop times
   - Configure exposure settings
6. Save and execute plan in app

**Downsides:**
- Time-consuming (5-10 minutes per plan)
- Error-prone (typos in coordinates/times)
- No automation between targets
- Limited to Sky Atlas objects only

---

## Method 2: Direct TCP Control (Advanced)

### Overview

Astro Planner includes a complete backend implementation for direct Seestar S50 telescope control via TCP socket communication.

**Status:** Backend complete, API endpoints in development

**What's Implemented:**

1. **Seestar Client Library** (`backend/app/clients/seestar_client.py`)
   - 561 lines of production-ready code
   - Async TCP socket communication
   - Full command interface (goto, focus, image, park)
   - Robust error handling
   - Connection management with auto-reconnect

2. **Telescope Service** (`backend/app/services/telescope_service.py`)
   - 460 lines of orchestration code
   - Execute complete observation plans automatically
   - Sequential target processing (goto → focus → image)
   - Automatic retry logic
   - Real-time progress tracking

3. **Protocol Documentation** (`docs/seestar/seestar-protocol-spec.md`)
   - Complete TCP protocol specification
   - JSON message format
   - All available commands
   - Request/response patterns

### Architecture

```
Astro Planner Frontend (Browser)
         ↓ HTTP/REST API
FastAPI Backend
         ├─ Planner Service
         ├─ Telescope Service ◄──── NEW
         └─ Seestar Client ◄──── NEW
                  ↓ TCP Socket (Port 5555)
            Seestar S50
```

### Key Features

**Async/Await Design:**
- Non-blocking operations keep UI responsive

**Automatic Retries:**
- Commands retry up to 3 times on failure
- Exponential backoff for reconnection

**Real-time Progress:**
- Current target name and coordinates
- Current phase (slewing/focusing/imaging)
- Overall progress percentage
- Time elapsed and estimated remaining
- Error tracking and reporting

**Error Recovery:**
- If a target fails after retries, execution continues with next target
- Detailed error logging for debugging

### Command Interface

The Seestar Client provides async methods for all telescope operations:

```python
# Connection
await client.connect(host="seestar.local", port=5555)
await client.disconnect()

# Telescope Control
await client.goto_target(ra_hours=12.5, dec_degrees=45.2, target_name="M31")
await client.auto_focus()
await client.park()

# Imaging
await client.start_imaging(restart=True)
await client.stop_imaging()

# Configuration
await client.set_exposure(exposure_ms=10000)
await client.configure_dither(enabled=True, pixels=50, interval=10)

# Status
status = await client.get_device_state()
```

### What Remains

To make direct control available from the UI:

1. **REST API Endpoints** (2-3 hours)
   - `POST /api/telescope/connect`
   - `POST /api/telescope/execute`
   - `GET /api/telescope/status`
   - `POST /api/telescope/abort`
   - `POST /api/telescope/park`

2. **Frontend UI** (4-6 hours)
   - Telescope connection panel
   - Execution control buttons
   - Progress monitoring display
   - Error display

3. **Integration Testing** (2-4 hours)
   - Test with real Seestar S50
   - Refine timing and retry logic
   - Validate error handling

### Example Usage

```python
from app.clients.seestar_client import SeestarClient
from app.services.telescope_service import TelescopeService

# Create client and service
client = SeestarClient()
service = TelescopeService(client)

# Connect to telescope
await client.connect("seestar.local")

# Execute observation plan
progress = await service.execute_plan(
    execution_id="plan-001",
    targets=scheduled_targets
)

# Check results
print(f"Completed: {progress.targets_completed}")
print(f"Failed: {progress.targets_failed}")

# Park and disconnect
await service.park_telescope()
await client.disconnect()
```

---

## Setup Guide

### Optimal Seestar Settings

#### Planning Mode Recommendations

**Balanced Mode** (Default - Recommended)
- Duration: 20-90 minutes per target
- 5-10 targets per night
- Good mix of quality and variety
- **Best for**: General astrophotography

**Best Quality Mode**
- Duration: 45-180 minutes per target
- 3-5 targets per night
- Longer exposures, fewer targets
- **Best for**: Deep imaging, faint objects, publication-quality images

**More Objects Mode**
- Duration: 15-45 minutes per target
- 10-15 targets per night
- Survey many objects quickly
- **Best for**: Catalog completion, testing new targets

#### Exposure Time Selection

| Exposure | Best For | Frame Rejection Rate |
|----------|----------|---------------------|
| **10s** (Default) | Most targets, general use | Low (~5-10%) |
| **20s** | Faint nebulae, galaxies | Medium (~10-20%) |
| **30s** | Very faint targets | High (~20-30%) |
| **60s** | Ultra-faint DSOs | Very High (~30-40%) |

**Recommendation**: Stick with 10s exposure for most targets. Longer exposures on Seestar's alt-az mount lead to field rotation and higher frame rejection.

#### Altitude Constraints

| Altitude Range | Quality | Notes |
|----------------|---------|-------|
| **30-45°** | Good | Lower altitude, more atmosphere |
| **45-65°** | Excellent | Optimal - least atmosphere, stable tracking |
| **65-70°** | Good | High altitude, increasing frame rejection |
| **70-90°** | Poor | Near zenith, field rotation issues, high rejection |

**Recommendation**: Set max altitude to 70° in Astro Planner preferences.

#### Setup Time

**Recommended: 30 minutes** (Default in Astro Planner)

Allows time for:
- Equipment setup
- Polar alignment check
- Initial focus
- Waiting for full darkness

---

## Troubleshooting

### seestar_alp Issues

#### "Cannot connect to Seestar"
**Solutions:**
- Verify Seestar is powered on
- Check WiFi connection (Station Mode recommended)
- Ping Seestar IP: `ping <seestar-ip>`
- Restart Seestar S50
- Restart seestar_alp

#### "Target not found"
**Solutions:**
- Check coordinates are valid (RA: 0-24h, Dec: -90 to +90°)
- Ensure target is above horizon
- Verify J2000 epoch (not JNow)
- Check for typos in CSV file

#### "High frame rejection rate"
**Causes:**
- Exposure time too long (>10s)
- Target too high (>70° altitude)
- Poor seeing conditions
- Focus issues

**Solutions:**
- Reduce exposure time to 10s
- Lower max altitude constraint
- Re-focus telescope
- Check weather conditions

#### "Plan doesn't import"
**Solutions:**
- Verify CSV format (comma-separated, not pipe-separated)
- Check file encoding (UTF-8)
- Ensure headers match expected format
- Re-export from Astro Planner

#### "seestar_alp web interface won't load"
**Solutions:**
- Check seestar_alp is running: `ps aux | grep app.py`
- Verify port 5000 is not blocked by firewall
- Try `http://localhost:5000` if on same machine
- Check seestar_alp logs for errors

### Direct Control Issues

#### Can't connect to Seestar
- Check Seestar is powered on and connected to WiFi
- Verify you're on the same network
- Try IP address instead of `seestar.local`
- Check firewall isn't blocking port 5555

#### Commands time out
- Increase `COMMAND_TIMEOUT` in client configuration
- Check network latency
- Verify Seestar firmware is up to date (2.4.27+)

#### Goto fails
- Check coordinates are valid (RA: 0-24h, Dec: -90 to +90°)
- Ensure Seestar is aligned and in EQ mode
- Verify target is above horizon

#### Focus fails
- Check there are bright stars in field
- Try manual focus first
- Increase focus timeout

#### Imaging doesn't start
- Verify exposure settings are valid
- Check Seestar isn't in another mode
- Try stopping all operations first

---

## Resources

### seestar_alp Project
- **GitHub**: https://github.com/smart-underworld/seestar_alp
- **Documentation**: Included in repository
- **Community Forum**: Seestar subreddit, CloudyNights

### Seestar S50 Community
- **Official Forum**: https://community.zwoastro.com/
- **Reddit**: r/seestar
- **Facebook Groups**: Seestar S50 Users

### Third-Party Tools
- **SeestarPi**: Alternative controller with Alpaca/ASCOM support
  - https://github.com/IZA165/SeestarPi
- **seestar_run**: Command-line tool for automation
  - https://github.com/smart-underworld/seestar_run

### Stellarium Integration

seestar_alp supports Stellarium via INDI protocol:
1. Install Stellarium
2. Enable telescope control
3. Connect to seestar_alp INDI server
4. Click objects in Stellarium to add to schedule

---

## Tips & Best Practices

1. **Test your plan during daytime** with seestar_alp in simulation mode
2. **Start observing early** - Begin at civil or nautical twilight for bright targets
3. **Monitor weather** throughout the night - pause if clouds roll in
4. **Keep firmware updated** - Latest Seestar firmware improves stability
5. **Use Station Mode WiFi** - More reliable than Access Point mode
6. **External power recommended** - Battery may not last full night
7. **Download images regularly** - 64GB fills up after ~20-30 nights
8. **Join the community** - Share tips, troubleshoot issues together

---

## Future Enhancements

Planned improvements for Astro Planner → Seestar integration:

**seestar_alp Integration:**
- Direct API integration (if ZWO releases SDK)
- QR code plan sharing for mobile workflow
- Live session tracking from Astro Planner
- Weather-based re-planning
- Seestar network auto-discovery

**Direct Control:**
- REST API endpoints completion
- Frontend UI implementation
- Real-time status monitoring via WebSocket
- Image download from telescope
- Live preview during imaging
- Multiple telescope support
- Weather integration for auto-pause

See [ROADMAP.md](../planning/ROADMAP.md) for full feature roadmap.

---

## Getting Help

**For Astro Planner issues:**
- GitHub Issues: https://github.com/irjudson/astronomus/issues
- Check [Testing Guide](../development/TESTING_GUIDE.md) for troubleshooting

**For seestar_alp issues:**
- seestar_alp GitHub Issues
- Community forums (Seestar subreddit, CloudyNights)

**For Seestar S50 issues:**
- ZWO Support: https://astronomy-imaging-camera.com/contact-us
- Official Seestar app feedback

---

**Version:** 2.0.0
**Compatible with:** Seestar S50 firmware v2.3+, seestar_alp v1.0+
**Backend:** Python 3.11+, FastAPI, asyncio
