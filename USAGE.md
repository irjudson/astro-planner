# Usage Guide

Comprehensive guide to using Astro Planner for planning astrophotography sessions with your Seestar S50.

## Table of Contents
- [Web Interface](#web-interface)
- [API Usage](#api-usage)
- [Python Client Examples](#python-client-examples)
- [Configuration](#configuration)
- [Customization](#customization)

## Web Interface

### Basic Workflow

1. **Set Your Location**
   ```
   Location Name: Your Observatory
   Latitude: 45.9183 (decimal degrees, positive = North)
   Longitude: -111.5433 (decimal degrees, negative = West)
   Elevation: 1234 (meters above sea level)
   Timezone: America/Denver (IANA timezone)
   ```

2. **Choose Observing Date**
   - The date picker defaults to TODAY
   - This represents the astronomical night containing this date
   - If it's afternoon, plan for tonight
   - If it's morning, you might want tomorrow's date for tomorrow night

3. **Set Constraints**
   - **Setup Time**: Minutes needed to set up equipment (default: 15)
   - **Min Altitude**: Lowest altitude to image (default: 30°)
   - **Max Altitude**: Highest altitude to image (default: 80°)
   - **Object Types**: Check which types to include

4. **Generate Plan**
   - Click "Generate Observing Plan"
   - Wait for calculations (5-10 seconds)
   - Review the schedule

5. **Export**
   - Choose your preferred format
   - Download the file
   - Import to Seestar S50 or use as reference

### Understanding the Results

#### Session Summary
- **Observing Date**: The date you selected
- **Astronomical Twilight**: When it's dark enough for imaging
- **Imaging Window**: After setup time through twilight start
- **Total Imaging Time**: Available dark time (minutes)
- **Total Targets**: Number of objects scheduled
- **Night Coverage**: Percentage of night with scheduled targets

#### Target Cards
Each scheduled target shows:
- **Name and Catalog ID**: e.g., "Andromeda Galaxy (M31)"
- **Type**: Galaxy, nebula, cluster, or planetary nebula
- **Time**: Start and end times in local timezone
- **Altitude**: Starting and ending altitude (aim for 45-65°)
- **Azimuth**: Compass direction (0° = North, 90° = East)
- **Field Rotation**: Rate in degrees/minute (lower is better)
- **Exposure Settings**: Recommended exposure time and frame count
- **Score**: Quality score (0-1, higher is better)

### Interpreting Field Rotation

The Seestar S50 uses an **alt-az mount**, which causes field rotation:

- **< 0.5°/min**: Excellent - minimal rotation
- **0.5-1.0°/min**: Good - acceptable for most targets
- **1.0-2.0°/min**: Fair - noticeable rotation in long sessions
- **> 2.0°/min**: Poor - avoid if possible

The scheduler automatically prefers targets with lower rotation rates.

## API Usage

### Endpoints

#### 1. Generate Plan

```bash
POST /api/plan
Content-Type: application/json

{
  "location": {
    "name": "Three Forks, MT",
    "latitude": 45.9183,
    "longitude": -111.5433,
    "elevation": 1234.0,
    "timezone": "America/Denver"
  },
  "observing_date": "2025-10-29",
  "constraints": {
    "min_altitude": 30.0,
    "max_altitude": 80.0,
    "setup_time_minutes": 15,
    "object_types": ["galaxy", "nebula", "cluster", "planetary_nebula"]
  }
}
```

Response: Complete `ObservingPlan` object with session info, scheduled targets, and weather forecast.

#### 2. List Targets

```bash
GET /api/targets
GET /api/targets?object_type=galaxy
```

Response: Array of `DSOTarget` objects.

#### 3. Get Target Details

```bash
GET /api/targets/M31
```

Response: Single `DSOTarget` object.

#### 4. Calculate Twilight

```bash
POST /api/twilight?date=2025-10-29
Content-Type: application/json

{
  "name": "Three Forks, MT",
  "latitude": 45.9183,
  "longitude": -111.5433,
  "elevation": 1234.0,
  "timezone": "America/Denver"
}
```

Response: Dictionary of twilight times (ISO format).

#### 5. Export Plan

```bash
POST /api/export?format=seestar_plan
Content-Type: application/json

{...ObservingPlan object...}
```

Formats: `json`, `seestar_plan`, `seestar_alp`, `text`, `csv`

Response: `ExportFormat` object with exported data.

## Python Client Examples

### Example 1: Generate Plan for Tonight

```python
import requests
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000/api"

# Create request
request = {
    "location": {
        "name": "My Backyard",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "elevation": 10.0,
        "timezone": "America/New_York"
    },
    "observing_date": datetime.now().strftime("%Y-%m-%d"),
    "constraints": {
        "min_altitude": 35.0,
        "max_altitude": 75.0,
        "setup_time_minutes": 20,
        "object_types": ["galaxy", "nebula"]
    }
}

# Generate plan
response = requests.post(f"{BASE_URL}/plan", json=request)
plan = response.json()

# Print summary
print(f"Scheduled {plan['total_targets']} targets")
print(f"Night coverage: {plan['coverage_percent']:.1f}%")

# Print targets
for target in plan['scheduled_targets']:
    print(f"{target['target']['name']}: {target['start_time']} - {target['end_time']}")
```

### Example 2: Find All Nebulae

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Get nebulae
response = requests.get(f"{BASE_URL}/targets", params={"object_type": "nebula"})
nebulae = response.json()

# Sort by magnitude (brightest first)
nebulae.sort(key=lambda t: t['magnitude'])

# Print top 5
print("Brightest nebulae:")
for i, nebula in enumerate(nebulae[:5], 1):
    print(f"{i}. {nebula['name']} ({nebula['catalog_id']}) - Mag {nebula['magnitude']}")
```

### Example 3: Calculate Tonight's Dark Time

```python
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

location = {
    "name": "Observatory",
    "latitude": 35.0,
    "longitude": -110.0,
    "elevation": 2000.0,
    "timezone": "America/Phoenix"
}

# Get twilight times
response = requests.post(
    f"{BASE_URL}/twilight",
    params={"date": datetime.now().strftime("%Y-%m-%d")},
    json=location
)
times = response.json()

# Calculate dark time
from datetime import datetime as dt
start = dt.fromisoformat(times['astronomical_twilight_end'])
end = dt.fromisoformat(times['astronomical_twilight_start'])
dark_hours = (end - start).total_seconds() / 3600

print(f"Tonight's dark time: {dark_hours:.1f} hours")
print(f"Astronomical twilight: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
```

### Example 4: Export to Seestar Format

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Generate plan (from previous example)
plan = {...}  # Your plan object

# Export in Seestar Plan Mode format
response = requests.post(
    f"{BASE_URL}/export",
    params={"format": "seestar_plan"},
    json=plan
)
export_data = response.json()

# Save to file
with open("tonight_plan.json", "w") as f:
    f.write(export_data['data'])

print("Plan exported to tonight_plan.json")
```

## Configuration

### Environment Variables

Edit `backend/.env`:

```bash
# API Keys
OPENWEATHERMAP_API_KEY=your_key_here

# Default Location
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME=Three Forks, MT

# Observing Constraints
MIN_ALTITUDE=30
MAX_ALTITUDE=80
OPTIMAL_MIN_ALTITUDE=45
OPTIMAL_MAX_ALTITUDE=65

# Scheduling
LOOKAHEAD_MINUTES=30
MIN_TARGET_DURATION_MINUTES=20
SLEW_TIME_SECONDS=60
SETUP_TIME_MINUTES=15
```

### Seestar S50 Specifications

These are configured in `.env` (don't change unless you know what you're doing):

```bash
SEESTAR_FOCAL_LENGTH=50
SEESTAR_APERTURE=50
SEESTAR_FOCAL_RATIO=5.0
SEESTAR_FOV_WIDTH=1.27
SEESTAR_FOV_HEIGHT=0.71
SEESTAR_MAX_EXPOSURE=10
```

## Customization

### Adding Custom Targets

Edit `backend/app/services/catalog_service.py`:

```python
DSOTarget(
    name="Your Object Name",
    catalog_id="M999",
    object_type="galaxy",  # or nebula, cluster, planetary_nebula
    ra_hours=12.5,  # Right ascension in hours (0-24)
    dec_degrees=45.0,  # Declination in degrees (-90 to 90)
    magnitude=8.0,  # Visual magnitude
    size_arcmin=20.0,  # Size in arcminutes
    description="Optional description"
)
```

### Adjusting Scoring Weights

Edit `backend/app/services/scheduler_service.py` in the `_score_target` method:

```python
# Current weights (total = 100%)
visibility_score * 0.4 +  # 40% for visibility
weather_score * 0.3 +     # 30% for weather
object_score * 0.3        # 30% for object quality
```

### Changing Optimal Altitude Range

The scheduler prefers 45-65° altitude. To change this, edit `backend/.env`:

```bash
OPTIMAL_MIN_ALTITUDE=40
OPTIMAL_MAX_ALTITUDE=70
```

## Tips for Best Results

1. **Location Accuracy**: Use precise coordinates for accurate rise/set times
2. **Timezone**: Always use IANA timezone (e.g., "America/New_York", not "EST")
3. **Date Selection**: Plan 1-2 days ahead to check weather trends
4. **Altitude Constraints**:
   - Too low (< 30°): Atmospheric distortion
   - Too high (> 80°): High field rotation near zenith
5. **Setup Time**: Be realistic - include time for polar alignment (if needed), cooling, focusing
6. **Object Types**: Start with bright nebulae (M42, M8) before faint galaxies
7. **Field Rotation**: For long integrations (> 1 hour), prefer targets with < 0.5°/min rotation

---

Need more help? Check the API docs at http://localhost:8000/api/docs
