# Architecture Documentation

Technical architecture and implementation details for Astro Planner.

## Table of Contents
- [System Overview](#system-overview)
- [Backend Architecture](#backend-architecture)
- [Algorithms](#algorithms)
- [Data Models](#data-models)
- [API Design](#api-design)
- [Frontend Design](#frontend-design)

## System Overview

### Technology Stack

**Backend:**
- **FastAPI**: Modern Python web framework
- **Skyfield**: High-precision astronomical calculations
- **Astropy**: Astronomy utilities and coordinate systems
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server

**Frontend:**
- **HTML5/CSS3/JavaScript**: No build step required
- **Vanilla JS**: Direct API communication
- **Responsive Design**: Works on desktop and mobile

**Infrastructure:**
- **Docker**: Containerized deployment
- **Python 3.11+**: Modern Python features and performance

### Architecture Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────┐
│      FastAPI Application            │
│  ┌────────────────────────────────┐ │
│  │     API Routes (/api)          │ │
│  └────────┬───────────────────────┘ │
│           │                          │
│  ┌────────▼───────────────────────┐ │
│  │   Planner Service              │ │
│  │   (Orchestration Layer)        │ │
│  └────────┬───────────────────────┘ │
│           │                          │
│  ┌────────┴───────────────────────┐ │
│  │                                 │ │
│  │  Core Services:                 │ │
│  │  • Ephemeris Service            │ │
│  │  • Catalog Service              │ │
│  │  • Weather Service              │ │
│  │  • Scheduler Service            │ │
│  │  • Export Service               │ │
│  │                                 │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
         │           │
         ▼           ▼
    ┌────────┐  ┌────────────┐
    │Skyfield│  │OpenWeather │
    │  Data  │  │    API     │
    └────────┘  └────────────┘
```

## Backend Architecture

### Service Layer Pattern

The backend uses a **service-oriented architecture** with clear separation of concerns:

#### 1. EphemerisService
**Responsibility**: Astronomical calculations

**Key Methods:**
- `calculate_twilight_times()`: Sunset, twilight (civil/nautical/astronomical), sunrise
- `calculate_position()`: Alt/az coordinates for target at given time
- `calculate_field_rotation_rate()`: Rotation rate for alt-az mounts
- `is_target_visible()`: Check if target meets altitude constraints

**Dependencies:**
- Skyfield for JPL ephemeris (DE421)
- Earth location from WGS84 coordinates
- Sun position calculations

**Implementation Details:**
```python
# Field rotation formula for alt-az mounts
rate = 15 × cos(latitude) / cos(altitude) × |sin(azimuth)|

# Where:
# - 15 = Earth's rotation rate (degrees/hour)
# - Accounts for observer latitude
# - Altitude and azimuth of target
```

#### 2. CatalogService
**Responsibility**: DSO target management

**Key Methods:**
- `get_all_targets()`: Return full catalog
- `get_target_by_id()`: Retrieve specific target
- `filter_targets()`: Filter by object type

**Catalog Criteria:**
- Object size: 10-180 arcmin (fits in 1.27° FOV)
- Magnitude: < 10 (bright enough for 10s exposures)
- Popular targets: Messier, NGC, IC objects
- Diversity: Galaxies, nebulae, clusters, planetary nebulae

**Data Structure:**
- 27 pre-loaded targets
- Stored in-memory (fast access)
- Extensible via code modification

#### 3. WeatherService
**Responsibility**: Weather forecasting

**Key Methods:**
- `get_forecast()`: Fetch hourly forecast for date range
- `calculate_weather_score()`: Convert conditions to 0-1 score

**Weather Scoring Algorithm:**
```python
# Cloud cover (60% weight)
cloud_score = 1.0 - (cloud_cover / 100)

# Humidity (25% weight)
if humidity < 60%: humidity_score = 1.0
elif humidity > 80%: humidity_score = 0.3
else: linear interpolation

# Wind speed (15% weight)
if wind < 5 m/s: wind_score = 1.0
elif wind > 10 m/s: wind_score = 0.5
else: linear interpolation

weather_score = (cloud_score × 0.6) + (humidity_score × 0.25) + (wind_score × 0.15)
```

**Fallback Behavior:**
- If no API key: Returns optimistic default (20% clouds, 50% humidity)
- If API fails: Same fallback
- Allows planning without weather data

#### 4. SchedulerService
**Responsibility**: Greedy scheduling algorithm

**Key Methods:**
- `schedule_session()`: Main scheduling loop
- `_find_best_target()`: Select optimal target for current time
- `_score_target()`: Calculate composite score
- `_calculate_urgency_bonus()`: Prioritize setting targets
- `_calculate_exposure_settings()`: Determine exposure/frames

**Scheduling Algorithm:**

```
1. Initialize: current_time = imaging_start
2. While current_time < imaging_end:
   a. For each unobserved target:
      - Check visibility at current_time
      - Calculate visibility duration
      - Calculate composite score
      - Apply urgency bonus if setting soon
   b. Select target with highest score
   c. Schedule target with optimal duration
   d. Add slew time (60 seconds)
   e. Advance current_time
3. Return scheduled targets
```

**Urgency Lookahead:**
- Lookahead window: 30 minutes (configurable)
- Targets setting within window: +20% score bonus
- Ensures time-critical targets aren't missed

**Scoring Components:**

*Visibility Score (40%):*
- Altitude preference: 45-65° optimal
- Field rotation: < 0.5°/min excellent
- Duration: Longer is better (up to 2 hours)

*Weather Score (30%):*
- From WeatherService
- Hourly forecast matched to observation time

*Object Score (30%):*
- Brightness: Mag < 6 excellent, > 10 poor
- Size match: 0.3-1.2× FOV diagonal optimal

#### 5. ExportService
**Responsibility**: Format conversion

**Formats:**

1. **JSON**: Full data model (Pydantic serialization)
2. **Seestar Plan Mode**: Importable to Seestar S50
   ```json
   {
     "target_name": "M31",
     "ra": 0.712,
     "dec": 41.269,
     "exposure_sec": 8,
     "frames": 300,
     ...
   }
   ```
3. **Seestar_alp**: Pipe-delimited text
   ```
   M31|0.7120|41.2690|21:30|60|8|300
   ```
4. **Text**: Human-readable with full details
5. **CSV**: Spreadsheet import

### Configuration Management

**Pydantic Settings:**
- Environment variables from `.env`
- Type validation and coercion
- Default values
- Cached singleton pattern

**Key Settings:**
- Telescope specs (FOV, exposure limits)
- Observing constraints (altitude range)
- Scheduling parameters (lookahead, min duration)
- API keys (OpenWeatherMap)

## Algorithms

### 1. Twilight Calculation

Uses Skyfield's almanac functions:

```python
# Civil twilight: Sun 6° below horizon
# Nautical twilight: Sun 12° below horizon
# Astronomical twilight: Sun 18° below horizon

# Custom angle search for nautical/astronomical
def sun_altitude_below(t, angle):
    alt = observer.at(t).observe(sun).apparent().altaz()[0]
    return alt.degrees < angle

# Find discrete events (day→night, night→day)
times, events = almanac.find_discrete(t0, t1, sun_altitude_below)
```

### 2. Position Calculation

```python
# Create celestial object from RA/Dec
star = Star(ra_hours=target.ra_hours, dec_degrees=target.dec_degrees)

# Calculate topocentric position
astrometric = observer.at(time).observe(star)
apparent = astrometric.apparent()
altitude, azimuth, distance = apparent.altaz()
```

### 3. Field Rotation Rate

For **alt-azimuth mounts**, the field rotates as the telescope tracks:

```python
# Mathematical derivation:
# Angular velocity of sky rotation: ω = 15°/hour
# Component causing field rotation: ω × cos(lat) × sin(az) / cos(alt)

rate_deg_per_hour = 15 * cos(lat_rad) / cos(alt_rad) * abs(sin(az_rad))
rate_deg_per_min = rate_deg_per_hour / 60

# Special cases:
# - Near zenith (alt > 85°): cos(alt) → 0, rate → infinity
# - On meridian (az = 0° or 180°): sin(az) = 0, rate = 0
# - Optimal: 45-65° altitude, away from meridian
```

### 4. Greedy Scheduling with Lookahead

**Base Greedy Algorithm:**
```
For each time slot:
  score_all_targets()
  select_best_target()
  schedule_target()
```

**Problem**: Greedy can miss time-critical targets

**Solution**: Urgency-based lookahead
```
For each target:
  base_score = visibility × 0.4 + weather × 0.3 + object × 0.3

  if target_sets_within_lookahead_window:
    urgency_bonus = 0.2
  else:
    urgency_bonus = 0.0

  final_score = base_score + urgency_bonus
```

This ensures targets that are "now or never" get scheduled.

### 5. Exposure Calculation

```python
# Base exposure on magnitude
if magnitude < 6:
  exposure = 5s  # Bright (e.g., M42, M8)
elif magnitude < 8:
  exposure = 8s  # Medium (e.g., M31, M51)
else:
  exposure = 10s  # Faint (e.g., M82, NGC galaxies)

# Calculate frame count
time_per_frame = exposure + 2s  # Account for readout
max_frames = duration / time_per_frame
recommended_frames = max(10, max_frames)  # Minimum 10 for stacking
```

## Data Models

### Core Models (Pydantic)

```python
class Location(BaseModel):
    name: str
    latitude: float  # -90 to 90
    longitude: float  # -180 to 180
    elevation: float  # meters
    timezone: str  # IANA timezone

class DSOTarget(BaseModel):
    name: str
    catalog_id: str  # e.g., "M31", "NGC7000"
    object_type: str  # galaxy, nebula, cluster, planetary_nebula
    ra_hours: float  # 0-24
    dec_degrees: float  # -90 to 90
    magnitude: float
    size_arcmin: float
    description: Optional[str]

class ScheduledTarget(BaseModel):
    target: DSOTarget
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    start_altitude: float
    end_altitude: float
    start_azimuth: float
    end_azimuth: float
    field_rotation_rate: float
    recommended_exposure: int
    recommended_frames: int
    score: TargetScore

class ObservingPlan(BaseModel):
    session: SessionInfo
    location: Location
    scheduled_targets: List[ScheduledTarget]
    weather_forecast: List[WeatherForecast]
    total_targets: int
    coverage_percent: float
    generated_at: datetime
```

## API Design

### RESTful Principles

- **Resource-based URLs**: `/api/targets`, `/api/plan`
- **HTTP methods**: GET (retrieve), POST (create/action)
- **JSON content**: All requests and responses
- **Status codes**: 200 (success), 400 (bad request), 404 (not found), 500 (server error)

### Error Handling

```python
try:
    result = perform_operation()
    return result
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
```

### CORS Configuration

Allows cross-origin requests for API testing and development:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Frontend Design

### Single-Page Application

- **No build step**: Pure HTML/CSS/JS
- **Progressive enhancement**: Works without JavaScript (for basic viewing)
- **Responsive design**: Mobile and desktop friendly

### API Communication

```javascript
async function generatePlan() {
  const request = buildRequestFromForm();

  const response = await fetch('/api/plan', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(request)
  });

  const plan = await response.json();
  displayPlan(plan);
}
```

### State Management

- **Single source of truth**: `currentPlan` variable
- **Reactive updates**: DOM updates when plan changes
- **No framework**: Vanilla JS for simplicity

## Performance Considerations

### Optimization Strategies

1. **In-Memory Catalog**: Fast target lookup (< 1ms)
2. **Efficient Ephemeris**: Skyfield caches calculations
3. **Async API**: Non-blocking I/O for weather requests
4. **Minimal Dependencies**: Faster startup and smaller image

### Scalability

**Current Design:**
- Single-user workload
- Compute-bound (astronomical calculations)
- Typical plan generation: 5-10 seconds

**Future Improvements:**
- Caching: Store twilight times by date/location
- Background workers: Async plan generation
- Database: Persist plans and custom catalogs

## Security Considerations

1. **No authentication**: Designed for local/personal use
2. **Input validation**: Pydantic models validate all inputs
3. **API key protection**: .env file not committed to git
4. **CORS**: Should be restricted in production

## Testing Strategy

### Test Coverage

1. **Unit Tests**: Each service independently (not included, but recommended)
2. **Integration Tests**: `test_api.py` validates end-to-end workflow
3. **Manual Testing**: Web UI testing by users

### Test API Script

Tests:
- Health check
- Target listing/retrieval
- Twilight calculation
- Plan generation
- Export in all formats

---

**Architecture Notes:**
- Designed for maintainability and extensibility
- Clear separation of concerns
- Type safety with Pydantic
- Production-ready error handling
