# Astro Planner: Scan and Catalog Functionality Analysis

## Overview
The Astro Planner is a Python FastAPI-based astrophotography session planner for the Seestar S50 smart telescope. The system includes catalog management and execution monitoring, but does NOT have traditional "scan" functionality. Instead, it uses a catalog-based planning and execution model.

---

## 1. CATALOG FUNCTIONALITY

### 1.1 Catalog Service (`backend/app/services/catalog_service.py`)

**Location:** `/home/irjudson/Projects/astronomus/backend/app/services/catalog_service.py`

**Purpose:** Manages deep sky object (DSO) catalog stored in SQLite database.

**Database:** 
- Path: `backend/data/catalogs.db` (local) or `/app/data/catalogs.db` (Docker)
- Auto-creates if missing by running import script

**Key Methods:**
```python
- get_all_targets(limit, offset)           # Get all catalog targets with pagination
- get_target_by_id(catalog_id)             # Get specific target (M31, NGC224, IC434)
- filter_targets(object_types, min_mag, max_mag, constellation, limit, offset)
```

**Data Models Returned:**
```python
class DSOTarget:
    name: str                    # "Andromeda Galaxy"
    catalog_id: str             # "M31", "NGC224", "IC434"
    object_type: str            # "galaxy", "nebula", "cluster", "planetary_nebula"
    ra_hours: float             # Right ascension in hours
    dec_degrees: float          # Declination in degrees
    magnitude: float            # Visual magnitude
    size_arcmin: float          # Size in arcminutes
    description: str            # Generated description with constellation, magnitude
```

**Filtering Capabilities:**
- Object type (galaxy, nebula, cluster, planetary_nebula)
- Magnitude range (brightness)
- Constellation (3-letter abbreviation)
- Pagination (limit/offset)

---

### 1.2 Catalog Import Script (`backend/scripts/import_catalog.py`)

**Location:** `/home/irjudson/Projects/astronomus/backend/scripts/import_catalog.py`

**Purpose:** Import NGC and IC catalog objects from pyongc library into SQLite database

**Parameters/Arguments:**
```
--database PATH          Path to SQLite database (default: backend/data/catalogs.db)
--limit N               Limit number of objects to import (for testing)
--rebuild               Drop existing tables and rebuild from scratch
```

**What It Does:**
1. Creates database schema with indexes
2. Populates constellation names lookup table (88 constellations)
3. Imports NGC catalog (NGC 1-7840)
4. Imports IC catalog (IC 1-5386)
5. Prints statistics

**Schema:**
```sql
CREATE TABLE dso_catalog (
    id INTEGER PRIMARY KEY,
    catalog_name VARCHAR(20),       -- 'NGC', 'IC', 'Messier'
    catalog_number VARCHAR(20),     -- '31', '224', etc.
    common_name VARCHAR(100),       -- Common name if available
    ra_hours FLOAT NOT NULL,        -- RA in hours (0-24)
    dec_degrees FLOAT NOT NULL,     -- Dec in degrees (-90 to 90)
    object_type VARCHAR(50),        -- galaxy, nebula, cluster, etc.
    magnitude FLOAT,                -- Visual magnitude
    surface_brightness FLOAT,       -- mag/arcsec^2
    size_major_arcmin FLOAT,        -- Major axis in arcminutes
    size_minor_arcmin FLOAT,        -- Minor axis in arcminutes
    constellation VARCHAR(20),      -- 3-letter constellation abbreviation
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(catalog_name, catalog_number)
)
```

**Indexes Created:**
- `idx_object_type` - For filtering by type
- `idx_magnitude` - For filtering by magnitude
- `idx_coords` - For coordinate lookups
- `idx_constellation` - For constellation filtering
- `idx_catalog_lookup` - For catalog ID lookups

**Object Type Mapping:**
- galaxy → galaxy
- open cluster → cluster
- globular cluster → cluster
- planetary nebula → planetary_nebula
- nebula, emission nebula, reflection nebula, supernova remnant, h ii region → nebula
- star, double star → star
- nonexistent, duplicate → skipped

**Data Source:** pyongc library (OpenNGC catalog)

**Example Usage:**
```bash
python backend/scripts/import_catalog.py --database backend/data/catalogs.db --rebuild
```

---

### 1.3 API Endpoints for Catalog

**Base URL:** `/api`

#### GET /targets
**Query Parameters:**
```
object_types=galaxy&object_types=nebula    # Can specify multiple
min_magnitude=5.0                          # Minimum magnitude (brighter)
max_magnitude=12.0                         # Maximum magnitude (fainter)
constellation=Ori                          # 3-letter constellation code
limit=100                                  # Max results (default: 100, max: 1000)
offset=0                                   # Pagination offset
```

**Response:**
```json
[
  {
    "name": "Andromeda Galaxy",
    "catalog_id": "M31",
    "object_type": "galaxy",
    "ra_hours": 0.7145,
    "dec_degrees": 41.2688,
    "magnitude": 3.4,
    "size_arcmin": 189.0,
    "description": "Galaxy in Andromeda (mag 3.4), 189.0' across"
  },
  ...
]
```

#### GET /targets/{catalog_id}
**Path Parameters:**
```
catalog_id: M31, NGC224, IC434
```

**Response:** Single DSOTarget object

#### GET /catalog/stats
**Response:**
```json
{
  "total_objects": 12543,
  "by_type": {
    "galaxy": 5234,
    "nebula": 2341,
    "cluster": 4156,
    "planetary_nebula": 812
  },
  "by_catalog": {
    "NGC": 7840,
    "IC": 5386,
    "Messier": 110
  },
  "by_magnitude": {
    "<=5.0 (Very Bright)": 234,
    "5.0-10.0 (Bright)": 1234,
    "10.0-15.0 (Moderate)": 5234,
    ">15.0 (Faint)": 5841
  },
  "database_path": "/app/data/catalogs.db"
}
```

---

## 2. EXECUTION AND MONITORING (NOT TRADITIONAL SCANNING)

### 2.1 Observation Plan Execution

**Workflow:**
1. User generates observing plan via `/api/plan` POST endpoint
2. Plan contains list of scheduled targets (DSOTarget + timing + scoring)
3. User connects to telescope via `/api/telescope/connect`
4. User executes plan via `/api/telescope/execute` POST
5. Execution runs asynchronously in background
6. Frontend polls `/api/telescope/progress` every 2 seconds for monitoring

### 2.2 Execution Endpoints

#### POST /telescope/connect
**Request:**
```json
{
  "host": "seestar.local",
  "port": 4700
}
```

#### POST /telescope/execute
**Request:**
```json
{
  "scheduled_targets": [
    {
      "target": {
        "name": "M31",
        "catalog_id": "M31",
        "object_type": "galaxy",
        "ra_hours": 0.7145,
        "dec_degrees": 41.2688,
        ...
      },
      "start_time": "2024-11-06T02:15:00-07:00",
      "end_time": "2024-11-06T02:35:00-07:00",
      "duration_minutes": 20,
      ...
    }
  ],
  "park_when_done": true
}
```

**Response:**
```json
{
  "execution_id": "a1b2c3d4",
  "status": "started",
  "total_targets": 5,
  "message": "Execution started. Use /telescope/progress to monitor."
}
```

#### GET /telescope/progress
**Response:**
```json
{
  "execution_id": "a1b2c3d4",
  "state": "running",              # idle, starting, running, paused, stopping, completed, aborted, error
  "total_targets": 5,
  "current_target_index": 1,
  "targets_completed": 1,
  "targets_failed": 0,
  "current_target_name": "M31",
  "current_phase": "Imaging",      # Slewing, Auto focusing, Imaging, Parking
  "progress_percent": 35.2,
  "elapsed_time": "0:45:30",
  "estimated_remaining": "1:20:00",
  "estimated_end_time": "2024-11-06T05:30:00-07:00",
  "errors": [
    {
      "timestamp": "2024-11-06T04:15:00-07:00",
      "target": "NGC7000",
      "phase": "focus",
      "message": "Auto focus failed after 3 retries",
      "retries": 3
    }
  ]
}
```

### 2.3 Telescope Service (`backend/app/services/telescope_service.py`)

**Location:** `/home/irjudson/Projects/astronomus/backend/app/services/telescope_service.py`

**Execution Phases for Each Target:**
1. **Goto** - Slew to target coordinates (timeout: 180s, retries: 3)
2. **Focus** - Auto focus (timeout: 120s, retries: 3)
3. **Imaging** - Capture for specified duration (retries: 3)

**Configuration:**
```python
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds
FOCUS_TIMEOUT = 120.0  # 2 minutes
GOTO_TIMEOUT = 180.0  # 3 minutes
SETTLE_TIME = 2.0  # seconds to settle after operations
```

**Progress Tracking:**
- Total targets and current index
- Targets completed/failed counts
- Current target name
- Current phase (Slewing, Auto focusing, Imaging, Parking, Configuring)
- Progress percentage
- Elapsed time and estimated remaining
- Error list with timestamps and retry counts

---

## 3. WEB INTERFACE STRUCTURE

### 3.1 Frontend Files

**Location:** `/home/irjudson/Projects/astronomus/frontend/`

**Files:**
- `index.html` - Main application interface (planning + execution + catalog browser)
- `catalog.html` - Dedicated catalog browser interface
- `plan.html` - Shared plan viewer
- `tron-theme.css` - Styling

**Technologies:**
- Vanilla JavaScript (no build step required)
- Responsive HTML5/CSS3
- Direct API calls via Fetch API
- QR code generation for plan sharing

### 3.2 Frontend Application Structure

**Main Tabs:**
1. **Plan Tab** - Generate observing plans
2. **Observe Tab** - Connect telescope and execute plans
3. **Catalog Tab** - Browse DSO catalog

### 3.3 Plan Generation UI

**Input Fields:**
```javascript
// Location
location-name: String
latitude: Float (-90 to 90)
longitude: Float (-180 to 180)
elevation: Float (in feet, converted to meters)
timezone: String (IANA format)

// Observing Session
observing-date: Date (YYYY-MM-DD)

// Constraints
min-altitude: Float (default: 30°)
max-altitude: Float (default: 90°)
setup-time: Integer (minutes)
planning-mode: Select (balanced, quality, quantity)
daytime-planning: Checkbox

// Object Types (checkboxes)
type-galaxy: Boolean
type-nebula: Boolean
type-cluster: Boolean
type-planetary_nebula: Boolean
type-comet: Boolean
```

**Output Display:**
- Session summary (twilight times, imaging window, total targets)
- Weather forecast (cloud cover, humidity, seeing, transparency)
- Target list with:
  - Name and catalog ID
  - Scoring breakdown
  - Timing and altitude/azimuth
  - Field rotation rate
  - Recommended exposures
  - 🔭 Preview button for field preview

### 3.4 Execution Control UI

**Connection Panel:**
```
Status Indicator: (Disconnected/Connected)
Connect Button
Disconnect Button
```

**Execution Panel:**
```
Execute Button (disabled until plan generated)
Abort Button
Park Telescope Button
Park When Done Checkbox
```

**Progress Panel (shown during execution):**
```
Current Target: [target name]
Current Phase: [Slewing/Focusing/Imaging/Parking]
Targets Completed: [count] / [total]
Elapsed Time: [HH:MM:SS]
Progress Bar: [percentage visual]
Error Log: [if errors occurred]
```

**Progress Monitoring:**
- Frontend polls `/api/telescope/progress` every 2 seconds
- Updates progress bar, current target, phase
- Displays errors with timestamps and retry counts
- Auto-stops monitoring when execution finishes

### 3.5 Catalog Browser UI

**Filter Controls:**
```
Catalog Type Tabs: Messier | NGC | IC | All

Filter Section:
- Object Type: Select (galaxies, nebulae, clusters, planetary nebulae)
- Magnitude Range: Min/Max sliders
- Search: Catalog ID search (M31, NGC224)
```

**Results:**
- Grid layout with catalog cards
- Each card shows:
  - Name and catalog ID
  - Object type
  - Magnitude
  - Size (arcminutes)
  - Description with constellation
  - Coordinates (RA/Dec)
  - Add to Plan button

---

## 4. JOB MANAGEMENT AND MONITORING

### 4.1 Execution State Machine

**States:**
```
IDLE
  ↓
STARTING (configure telescope)
  ↓
RUNNING (execute each target)
  ├→ PAUSED (not implemented)
  ├→ STOPPING (user abort)
  ├→ ERROR (unrecoverable)
COMPLETED
ABORTED
```

### 4.2 Progress Tracking

**Data Structures:**
```python
class ExecutionProgress:
    execution_id: str
    state: ExecutionState
    total_targets: int
    current_target_index: int
    targets_completed: int
    targets_failed: int
    current_target_name: Optional[str]
    current_phase: Optional[str]
    progress_percent: float           # 0-100
    start_time: Optional[datetime]
    estimated_end_time: Optional[datetime]
    elapsed_time: Optional[timedelta]
    estimated_remaining: Optional[timedelta]
    errors: List[ExecutionError]      # With timestamps and retry info
    target_progress: List[TargetProgress]

class ExecutionError:
    timestamp: datetime
    target_index: int
    target_name: str
    phase: str                        # "goto", "focus", "imaging", etc.
    error_message: str
    retry_count: int
```

### 4.3 Session Information

**SessionInfo Model:**
```python
class SessionInfo:
    observing_date: str               # YYYY-MM-DD
    sunset: datetime
    civil_twilight_end: datetime
    nautical_twilight_end: datetime
    astronomical_twilight_end: datetime    # Imaging starts here
    astronomical_twilight_start: datetime  # Imaging ends here
    nautical_twilight_start: datetime
    civil_twilight_start: datetime
    sunrise: datetime
    imaging_start: datetime
    imaging_end: datetime
    total_imaging_minutes: int
```

---

## 5. API SUMMARY

### Core Planning API
```
POST   /api/plan                      # Generate observation plan
GET    /api/targets                   # List catalog targets with filters
GET    /api/targets/{catalog_id}      # Get specific target
GET    /api/catalog/stats             # Get catalog statistics
POST   /api/twilight                  # Calculate twilight times
POST   /api/export                    # Export plan (JSON, CSV, text)
POST   /api/share                     # Create shareable plan link
GET    /api/plans/{plan_id}           # Retrieve shared plan
```

### Telescope Control API
```
POST   /api/telescope/connect         # Connect to telescope
POST   /api/telescope/disconnect      # Disconnect
GET    /api/telescope/status          # Get current telescope status
POST   /api/telescope/execute         # Start plan execution
GET    /api/telescope/progress        # Get execution progress
POST   /api/telescope/abort           # Abort execution
POST   /api/telescope/park            # Park telescope
GET    /api/health                    # Health check
```

### Specialized APIs (Comets, Asteroids, Planets)
```
GET    /api/comets                    # List visible comets
GET    /api/comets/{designation}      # Get comet details
GET    /api/asteroids                 # List asteroids
GET    /api/planets                   # Get planetary positions
```

---

## 6. CONFIGURATION

### Environment Variables (backend/.env)
```
HOST=0.0.0.0
PORT=9247
RELOAD=True

OPENWEATHERMAP_API_KEY=your_api_key_here

DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME=Three Forks, MT

SEESTAR_FOCAL_LENGTH=50
SEESTAR_APERTURE=50
SEESTAR_FOCAL_RATIO=5.0
SEESTAR_FOV_WIDTH=1.27
SEESTAR_FOV_HEIGHT=0.71
SEESTAR_MAX_EXPOSURE=10

MIN_ALTITUDE=30
MAX_ALTITUDE=90
OPTIMAL_MIN_ALTITUDE=45
OPTIMAL_MAX_ALTITUDE=65
SLEW_TIME_SECONDS=60
SETUP_TIME_MINUTES=30

LOOKAHEAD_MINUTES=30
MIN_TARGET_DURATION_MINUTES=20
```

### Runtime Configuration (app/core/config.py)
```python
class Settings:
    host: str = "0.0.0.0"
    port: int = 9247
    reload: bool = True
    openweathermap_api_key: str = ""
    default_lat: float = 45.9183
    default_lon: float = -111.5433
    default_elevation: float = 1234.0
    default_timezone: str = "America/Denver"
    default_location_name: str = "Three Forks, MT"
    seestar_focal_length: float = 50.0
    seestar_aperture: float = 50.0
    seestar_focal_ratio: float = 5.0
    seestar_fov_width: float = 1.27
    seestar_fov_height: float = 0.71
    seestar_max_exposure: int = 10
    min_altitude: float = 30.0
    max_altitude: float = 90.0
    optimal_min_altitude: float = 45.0
    optimal_max_altitude: float = 65.0
    slew_time_seconds: int = 60
    setup_time_minutes: int = 30
    lookahead_minutes: int = 30
    min_target_duration_minutes: int = 20
```

---

## 7. DATABASE STORAGE

### Location
```
Local Development: backend/data/catalogs.db
Docker Container: /app/data/catalogs.db
```

### Tables
1. **dso_catalog** - NGC and IC objects (12,000+ objects)
2. **constellation_names** - 88 constellation abbreviations to full names

### Size Considerations
- Initial import ~30MB database file
- Indexed for fast queries
- Auto-created on first run if missing

---

## 8. KEY PARAMETERS AND CONSTRAINTS

### Planning Parameters
```python
# Magnitude filtering
target_magnitude_max = 12.0  # Seestar S50 practical limit

# Target selection
max_candidates = 200  # Balance variety with performance
lookahead_window = 30 minutes  # For urgency-based scheduling

# Exposure settings
min_target_duration = 15-45 min  # Depends on planning mode
max_target_duration = 45-180 min # Depends on planning mode
exposure_time = 10 seconds  # Per frame (Seestar S50)

# Scoring thresholds
min_score_threshold = 0.5-0.7  # Depends on planning mode
```

### Altitude Constraints
```python
min_altitude = 30° (default, configurable)
max_altitude = 90° (overhead)
optimal_range = 45-65° (best for Seestar S50)
```

### Execution Retry Logic
```python
MAX_RETRIES = 3 per phase
RETRY_DELAY = 2 seconds between retries
FOCUS_TIMEOUT = 120 seconds
GOTO_TIMEOUT = 180 seconds
SETTLE_TIME = 2 seconds between operations
```

---

## 9. NOTABLE FEATURES

### Dynamic Adjustment
- Weather scoring affects target selection
- Altitude and visibility calculated for each target at each time
- Field rotation rate computed for optimal dithering

### Scheduling Algorithm
- Greedy algorithm with urgency lookahead
- Targets setting soon get priority
- Balances breadth vs. depth based on planning mode

### No Traditional Scanning
- System is **catalog-based**, not scan-based
- Pre-selected targets from DSO catalog
- Optional scan features could be added to expand functionality

---

## 10. FILE LOCATIONS SUMMARY

```
Backend:
  /home/irjudson/Projects/astronomus/backend/
  ├── app/
  │   ├── main.py                      # FastAPI app entry point
  │   ├── api/
  │   │   ├── routes.py                # Main API routes
  │   │   ├── comets.py                # Comet endpoints
  │   │   ├── asteroids.py             # Asteroid endpoints
  │   │   └── planets.py               # Planet endpoints
  │   ├── services/
  │   │   ├── catalog_service.py       # Catalog management
  │   │   ├── telescope_service.py     # Execution orchestration
  │   │   ├── planner_service.py       # Main planning logic
  │   │   ├── scheduler_service.py     # Target scheduling
  │   │   ├── ephemeris_service.py     # Astronomy calculations
  │   │   ├── weather_service.py       # Weather forecasting
  │   │   └── export_service.py        # Plan export formats
  │   ├── models/
  │   │   └── models.py                # All data models
  │   ├── clients/
  │   │   └── seestar_client.py        # Telescope communication
  │   └── core/
  │       └── config.py                # Configuration management
  ├── scripts/
  │   ├── import_catalog.py            # Catalog import (NGC/IC)
  │   ├── init_test_db.py              # Test database setup
  │   ├── add_asteroid_tables.py       # Asteroid table creation
  │   └── add_comet_tables.py          # Comet table creation
  ├── data/
  │   └── catalogs.db                  # SQLite database (generated)
  ├── requirements.txt
  ├── pytest.ini
  └── .env.example

Frontend:
  /home/irjudson/Projects/astronomus/frontend/
  ├── index.html                       # Main application UI
  ├── catalog.html                     # Catalog browser UI
  ├── plan.html                        # Plan viewer UI
  └── tron-theme.css                   # Styling

Configuration:
  /home/irjudson/Projects/astronomus/
  ├── docker-compose.yml               # Docker setup
  ├── docker/
  │   └── Dockerfile
  └── backend/.env                     # Runtime configuration
```

