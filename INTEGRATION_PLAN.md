# Data Source Integration Plan
## Astro Planner Multi-Source Integration Strategy

**Created**: 2025-10-30
**Status**: Planning Phase
**Goal**: Integrate multiple astronomy data sources for comprehensive observing planning

---

## Executive Summary

This document outlines the integration plan for expanding Astro Planner's data sources across three key domains:

1. **Weather & Seeing Conditions** - Multiple forecast sources for accuracy
2. **Comet & Asteroid Ephemeris** - Real-time solar system object tracking
3. **DSO Catalogs** - Expanded from 28 to 10,000+ deep sky objects

---

## 🌦️ WEATHER & SEEING INTEGRATION

### Current State
- ✅ OpenWeatherMap API (basic weather: clouds, humidity, wind)
- ❌ No seeing/transparency forecasts
- ❌ No astronomy-specific metrics

### Proposed Sources

#### **Source 1: 7Timer! (FREE) - Primary Astronomy Weather**
**Priority**: HIGH | **Effort**: LOW | **Status**: Not Started

**Why This First**: Free, astronomy-specific, includes seeing and transparency

**Capabilities**:
- Astronomical seeing index (arcseconds)
- Atmospheric transparency (magnitude limit)
- 3-layer cloud cover (0-4km, 4-8km, 8-15km)
- 72-hour forecasts
- Based on NOAA GFS model

**API Details**:
- **Endpoint**: `http://www.7timer.info/bin/astro.php`
- **Authentication**: None required (completely free)
- **Format**: JSON
- **Rate Limits**: Reasonable usage (no hard limits published)

**Example Request**:
```python
import requests

def get_7timer_forecast(lat, lon):
    url = f"http://www.7timer.info/bin/astro.php?lat={lat}&lon={lon}&output=json"
    response = requests.get(url)
    return response.json()

# Returns:
# {
#   "dataseries": [
#     {
#       "timepoint": 3,  # hours from init
#       "cloudcover": 2,  # 1-9 scale
#       "seeing": 3,      # 1-8 scale (1=worst, 8=best <0.5")
#       "transparency": 5, # 1-8 scale (1=worst, 8=best >6.5mag)
#       "lifted_index": -4,
#       "rh2m": 60,       # humidity
#       "wind10m": {"direction": "SE", "speed": 2},
#       "temp2m": 15,
#       "prec_type": "none"
#     },
#     ...
#   ]
# }
```

**Integration Steps**:
1. Create `app/services/weather_service_7timer.py`
2. Parse 7Timer JSON format
3. Convert seeing scale (1-8) to arcseconds
4. Convert transparency scale (1-8) to magnitude limit
5. Add to composite weather scoring
6. Fallback to OpenWeatherMap if unavailable

**Score Calculation**:
```python
def calculate_astronomy_score(forecast):
    # Seeing: 1=worst (>2"), 8=best (<0.5")
    seeing_score = forecast['seeing'] / 8.0

    # Transparency: 1=worst (<3mag), 8=best (>6.5mag)
    transparency_score = forecast['transparency'] / 8.0

    # Cloud cover: 1=clear, 9=overcast
    cloud_score = 1.0 - (forecast['cloudcover'] / 9.0)

    # Composite score
    return (seeing_score * 0.3 + transparency_score * 0.3 + cloud_score * 0.4)
```

---

#### **Source 2: Meteoblue Astronomy (PAID) - Premium Seeing**
**Priority**: MEDIUM | **Effort**: MEDIUM | **Status**: Not Started

**Why**: Most accurate seeing predictions, professional-grade

**Capabilities**:
- High-resolution seeing index (1-5 scale)
- Bad layer identification (turbulence zones)
- Jet stream analysis
- 3-layer cloud cover with altitudes
- Temperature inversions

**API Details**:
- **Endpoint**: `https://my.meteoblue.com/packages/`
- **Authentication**: API key required (paid service)
- **Pricing**: ~€200-500/year depending on call volume
- **Format**: JSON

**Integration Timeline**: Q3 2026 (after user base established)

---

#### **Source 3: OpenWeatherMap (CURRENT) - Baseline Weather**
**Priority**: HIGH | **Effort**: COMPLETE | **Status**: ✅ Implemented

**Keep Using For**:
- Basic cloud cover
- Precipitation probability
- Wind speed
- Temperature
- Moon phase data (via One Call API)

**Enhancement Needed**:
- Extract moon rise/set times
- Add moon illumination percentage to scoring

---

#### **Source 4: Clear Dark Sky / Astrospheric (WEB SCRAPING) - Community**
**Priority**: LOW | **Effort**: HIGH | **Status**: Not Started

**Note**: No public APIs available, would require web scraping
**Recommendation**: Skip due to maintenance burden and legal concerns

---

### Weather Integration Architecture

```
┌─────────────────────────────────────────────────┐
│         Weather Service Orchestrator            │
│  app/services/weather_service_composite.py      │
└────────────┬────────────────────────────────────┘
             │
             ├──► 7Timer (Primary Astronomy)
             │    ├─ Seeing
             │    ├─ Transparency
             │    └─ 3-layer clouds
             │
             ├──► OpenWeatherMap (Baseline)
             │    ├─ Precipitation
             │    ├─ Wind/Temp
             │    └─ Moon data
             │
             └──► Meteoblue (Future Premium)
                  └─ Enhanced seeing

Final Score = Weighted average with confidence intervals
```

**Composite Scoring Logic**:
```python
class CompositeWeatherService:
    def get_composite_forecast(self, location, time_range):
        forecasts = {
            '7timer': self._fetch_7timer(location, time_range),
            'openweather': self._fetch_openweather(location, time_range),
        }

        return self._merge_forecasts(forecasts)

    def _merge_forecasts(self, forecasts):
        # Weight by source reliability
        weights = {
            '7timer': 0.6,  # Best for astronomy
            'openweather': 0.4,  # Good baseline
        }

        composite = []
        for hour in time_range:
            scores = []
            for source, weight in weights.items():
                if source in forecasts:
                    scores.append(forecasts[source][hour] * weight)

            composite.append({
                'hour': hour,
                'score': sum(scores),
                'confidence': len(scores) / len(weights),  # How many sources responded
            })

        return composite
```

---

## ☄️ COMET & ASTEROID INTEGRATION

### Current State
- ✅ UI checkboxes for comets/asteroids
- ❌ No comet/asteroid data in catalog
- ❌ No ephemeris calculations
- ❌ No orbital elements

### Proposed Sources

#### **Source 1: JPL Horizons (FREE) - Primary Ephemeris**
**Priority**: HIGH | **Effort**: MEDIUM | **Status**: Not Started

**Why This First**: Official NASA data, comprehensive, well-documented Python library

**Capabilities**:
- 1.4+ million asteroids
- 4,034 comets
- Real-time position calculations
- Magnitude predictions
- Orbital elements
- Rise/set times

**API Details**:
- **Library**: `astroquery.jplhorizons` (official Python client)
- **Authentication**: None required (free)
- **Coverage**: All known solar system objects
- **Rate Limits**: Reasonable (avoid spam)

**Example Code**:
```python
from astroquery.jplhorizons import Horizons
from datetime import datetime
import pytz

def get_comet_ephemeris(comet_designation, location, start_time, end_time):
    """
    Get comet ephemeris from JPL Horizons

    Args:
        comet_designation: str (e.g., "C/2023 A3" or "1P" for periodic)
        location: Location object with lat/lon/elevation
        start_time: datetime
        end_time: datetime

    Returns:
        Ephemeris table with RA, Dec, altitude, magnitude
    """
    # Create observer location (negative longitude for West)
    site = {
        'lon': location.longitude,
        'lat': location.latitude,
        'elevation': location.elevation / 1000.0  # Convert to km
    }

    # Query Horizons
    obj = Horizons(
        id=comet_designation,
        location=site,
        epochs={
            'start': start_time.strftime('%Y-%m-%d'),
            'stop': end_time.strftime('%Y-%m-%d'),
            'step': '1h'  # Hourly resolution
        }
    )

    # Get ephemeris
    eph = obj.ephemerides()

    # Returns astropy Table with columns:
    # datetime_str, RA, DEC, AZ, EL (altitude), V (magnitude),
    # r (sun distance), delta (earth distance), elongation, etc.

    return eph

# Example: Get Comet C/2023 A3 (Tsuchinshan-ATLAS) position
location = Location(
    name="Three Forks, MT",
    latitude=45.9183,
    longitude=-111.5433,
    elevation=1234.0,
    timezone="America/Denver"
)

eph = get_comet_ephemeris(
    "C/2023 A3",
    location,
    datetime.now(pytz.UTC),
    datetime.now(pytz.UTC) + timedelta(hours=8)
)

print(eph['datetime_str', 'RA', 'DEC', 'EL', 'V'])
```

**Integration Steps**:
1. Install `astroquery` package: `pip install astroquery`
2. Create `app/models/solar_system.py`:
   ```python
   class Comet(BaseModel):
       name: str
       designation: str  # Official MPC designation
       object_type: Literal["comet"]
       perihelion_date: datetime
       magnitude_formula: dict  # H and G parameters
       is_periodic: bool
       period_years: Optional[float]

   class Asteroid(BaseModel):
       name: str
       number: Optional[int]  # Numbered asteroids only
       designation: str
       object_type: Literal["asteroid"]
       magnitude: float
       diameter_km: Optional[float]
       is_neo: bool  # Near Earth Object
       is_pha: bool  # Potentially Hazardous Asteroid
   ```

3. Create `app/services/ephemeris_service_horizons.py`:
   ```python
   class HorizonsEphemerisService:
       def calculate_position(self, obj, location, time):
           """Calculate position for comet or asteroid"""
           pass

       def is_observable(self, obj, location, time, constraints):
           """Check if comet/asteroid meets observing constraints"""
           pass

       def get_brightness(self, obj, time):
           """Predict magnitude at given time"""
           pass
   ```

4. Extend scheduler to handle moving objects:
   ```python
   def schedule_solar_system_object(self, obj, session, constraints):
       # Sample positions throughout night at 30min intervals
       positions = []
       for time in session.hourly_times:
           pos = self.ephemeris.calculate_position(obj, session.location, time)
           positions.append(pos)

       # Find optimal window when altitude and brightness are good
       best_window = self._find_optimal_window(positions, constraints)

       # Create observing block
       return ObservingBlock(
           target=obj,
           start_time=best_window.start,
           duration=best_window.duration,
           estimated_magnitude=best_window.avg_magnitude
       )
   ```

---

#### **Source 2: Minor Planet Center (FREE) - Comet Discovery**
**Priority**: MEDIUM | **Effort**: LOW | **Status**: Not Started

**Why**: Official source for newly discovered comets

**Capabilities**:
- Latest comet discoveries
- Orbital elements (updated frequently)
- Observation circumstances
- Names and designations

**API Details**:
- **Library**: `astroquery.mpc` (Python client)
- **Authentication**: None required
- **Format**: Astropy Table

**Use Case**: Auto-update comet list weekly

**Example Code**:
```python
from astroquery.mpc import MPC

def get_bright_comets(magnitude_limit=12.0):
    """
    Get list of currently bright comets from MPC

    Returns comets predicted brighter than magnitude_limit
    """
    # Query MPC for comet list
    comets = MPC.query_objects('comet', get_query_payload=False)

    # Filter by predicted magnitude
    bright_comets = comets[comets['magnitude'] < magnitude_limit]

    return bright_comets

# Auto-refresh comet catalog weekly
def update_comet_catalog():
    comets = get_bright_comets(magnitude_limit=12.0)

    for comet in comets:
        catalog.add_or_update(
            Comet(
                name=comet['Name'],
                designation=comet['Designation'],
                perihelion_date=comet['Perihelion_date'],
                magnitude_formula={
                    'H': comet['H'],
                    'G': comet['G']
                }
            )
        )
```

**Integration**:
- Run weekly via cron job or background task
- Update `app/data/comet_catalog.json` automatically

---

#### **Source 3: COBS (FREE) - Real Brightness Observations**
**Priority**: LOW | **Effort**: MEDIUM | **Status**: Not Started

**Why**: Ground truth for actual comet brightness (predictions often wrong)

**Capabilities**:
- Real observer magnitude estimates
- Coma diameter measurements
- Updated daily by amateur observers worldwide

**API Details**:
- **Endpoint**: `https://cobs.si/api/`
- **Authentication**: None required
- **Format**: JSON

**Use Case**: Override JPL predictions with recent observations

**Example**:
```python
import requests

def get_comet_observed_magnitude(comet_designation):
    """Get recent brightness observations from COBS"""
    url = f"https://cobs.si/api/observations/{comet_designation}"
    response = requests.get(url)

    observations = response.json()

    # Average recent observations (last 4 days)
    recent = [obs for obs in observations if days_ago(obs['date']) < 4]

    if recent:
        avg_magnitude = sum(obs['magnitude'] for obs in recent) / len(recent)
        return avg_magnitude
    else:
        return None  # Fall back to JPL prediction

# In planning:
predicted_mag = horizons.get_magnitude(comet, time)
observed_mag = cobs.get_observed_magnitude(comet.designation)

# Use observed if available (more accurate)
actual_magnitude = observed_mag if observed_mag else predicted_mag
```

---

### Comet/Asteroid Data Flow

```
┌────────────────────────────────────────────────────┐
│     Solar System Object Manager                    │
│     app/services/solar_system_service.py           │
└─────────────┬──────────────────────────────────────┘
              │
              ├──► MPC (Weekly Update)
              │    └─ New comet discoveries
              │
              ├──► JPL Horizons (Real-time)
              │    ├─ Current position (RA/Dec/Alt)
              │    ├─ Predicted magnitude
              │    └─ Rise/set times
              │
              └──► COBS (Daily Update)
                   └─ Actual observed magnitude (overrides prediction)

Database: SQLite table for comets/asteroids
Cache: Redis for ephemeris (1 hour TTL)
```

**Comet Catalog Database Schema**:
```sql
CREATE TABLE comets (
    id INTEGER PRIMARY KEY,
    designation VARCHAR(20) UNIQUE,  -- C/2023 A3
    name VARCHAR(100),               -- Tsuchinshan-ATLAS
    perihelion_date DATE,
    magnitude_H FLOAT,
    magnitude_G FLOAT,
    last_observed_magnitude FLOAT,
    last_observation_date DATE,
    is_currently_visible BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE asteroids (
    id INTEGER PRIMARY KEY,
    number INTEGER UNIQUE,           -- 1, 2, 3, etc.
    name VARCHAR(100),               -- Ceres, Pallas, etc.
    designation VARCHAR(20),         -- 2023 AB1
    magnitude FLOAT,
    diameter_km FLOAT,
    is_neo BOOLEAN,
    is_pha BOOLEAN,
    created_at TIMESTAMP
);
```

**UI Enhancement - "Currently Visible Comets" Widget**:
```javascript
// frontend/index.html addition
<div class="visible-comets-widget">
    <h3>🔭 Currently Visible Comets</h3>
    <ul id="comet-list">
        <!-- Auto-populated from API -->
    </ul>
</div>

// API endpoint: GET /api/comets/visible
// Returns: List of comets with magnitude < 12 and altitude > 20°
```

---

## 📚 DSO CATALOG EXPANSION

### Current State
- ✅ 28 hand-picked DSO targets
- ❌ Hard-coded in Python dict
- ❌ No user additions
- ❌ Limited to brightest objects

### Target: 10,000+ DSO Database

#### **Source 1: OpenNGC (FREE, LICENSE FRIENDLY) - Primary Catalog**
**Priority**: HIGH | **Effort**: MEDIUM | **Status**: Not Started

**Why This First**: Open license (CC-BY-SA-4.0), comprehensive, maintained

**Capabilities**:
- Complete NGC catalog: 7,840 objects
- Complete IC catalog: 5,386 objects
- Messier cross-references
- Common names included
- Object types, sizes, magnitudes

**Data Format**:
- CSV download available
- Python library: `pyongc`

**Example Code**:
```python
from pyongc import ongc
import sqlite3

def import_ngc_catalog():
    """Import entire NGC/IC catalog into SQLite"""
    db = sqlite3.connect('data/catalogs.db')

    # Get all NGC objects
    for ngc_num in range(1, 7841):
        try:
            obj = ongc.get(f"NGC{ngc_num}")

            db.execute("""
                INSERT INTO dso_catalog (
                    catalog_name, catalog_number, common_name,
                    object_type, ra_hours, dec_degrees,
                    magnitude, size_arcmin, constellation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'NGC', ngc_num, obj.getCommonName(),
                obj.getType(), obj.getRA(), obj.getDec(),
                obj.getMagnitude(), obj.getDimensions()[0],
                obj.getConstellation()
            ))
        except Exception:
            continue  # Some numbers aren't valid

    # Get all IC objects
    for ic_num in range(1, 5387):
        try:
            obj = ongc.get(f"IC{ic_num}")
            # Similar insert...
        except Exception:
            continue

    db.commit()

# One-time import to populate database
import_ngc_catalog()
```

**Integration Steps**:
1. Install `pyongc`: `pip install pyongc`
2. Create database schema (see below)
3. Import all NGC/IC objects (one-time)
4. Add API endpoints for catalog search
5. Update UI with advanced filtering

---

#### **Source 2: SIMBAD (FREE) - Enhanced Metadata**
**Priority**: MEDIUM | **Effort**: MEDIUM | **Status**: Not Started

**Why**: 25,839+ catalogs, cross-references, research data

**Capabilities**:
- Cross-match object IDs (NGC, M, IC, common names)
- Spectral types
- Distance estimates
- Bibliography (research papers)
- Alternative names

**API Details**:
- **Library**: `astroquery.simbad`
- **Authentication**: None required
- **Rate Limits**: ~5-10 queries/sec max

**Use Case**: Enrich catalog entries on-demand

**Example**:
```python
from astroquery.simbad import Simbad

def enrich_object_data(catalog_id):
    """Get additional data from SIMBAD"""
    result = Simbad.query_object(catalog_id)

    if result:
        return {
            'main_id': result['MAIN_ID'][0],
            'ra': result['RA'][0],
            'dec': result['DEC'][0],
            'object_type': result['OTYPE'][0],
            'magnitude_V': result['FLUX_V'][0],
        }
    return None

# When user views object details:
basic_info = catalog.get('M31')
enhanced_info = simbad.enrich_object_data('M31')
combined = {**basic_info, **enhanced_info}
```

---

#### **Source 3: VizieR (FREE) - Specialized Catalogs**
**Priority**: LOW | **Effort**: HIGH | **Status**: Future

**Why**: Access to specialized catalogs (Arp, Caldwell, Sharpless, etc.)

**Capabilities**:
- 25,839 astronomical catalogs
- Query by coordinates, object type, magnitude
- Cross-match with multiple catalogs

**Use Case**: Import specialized object lists for advanced users

---

### DSO Database Schema

```sql
-- Main catalog table
CREATE TABLE dso_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_name VARCHAR(20),        -- 'NGC', 'IC', 'Messier', etc.
    catalog_number VARCHAR(20),      -- '31', '224', 'A'
    common_name VARCHAR(100),        -- 'Andromeda Galaxy'

    -- Coordinates
    ra_hours FLOAT NOT NULL,
    dec_degrees FLOAT NOT NULL,

    -- Physical properties
    object_type VARCHAR(50),         -- galaxy, nebula, cluster, etc.
    magnitude FLOAT,
    magnitude_B FLOAT,               -- Blue magnitude
    surface_brightness FLOAT,        -- mag/arcsec^2
    size_major_arcmin FLOAT,
    size_minor_arcmin FLOAT,

    -- Observing info
    constellation VARCHAR(20),
    imaging_difficulty VARCHAR(20),  -- Easy, Medium, Hard, Extreme
    recommended_focal_length INT,    -- mm
    recommended_min_exposure INT,    -- seconds
    best_months VARCHAR(50),         -- 'Oct,Nov,Dec,Jan,Feb'

    -- Metadata
    simbad_enriched BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for fast queries
    UNIQUE(catalog_name, catalog_number)
);

CREATE INDEX idx_object_type ON dso_catalog(object_type);
CREATE INDEX idx_magnitude ON dso_catalog(magnitude);
CREATE INDEX idx_coords ON dso_catalog(ra_hours, dec_degrees);
CREATE INDEX idx_constellation ON dso_catalog(constellation);

-- User custom targets
CREATE TABLE user_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,  -- Future: multi-user support
    name VARCHAR(100) NOT NULL,
    ra_hours FLOAT NOT NULL,
    dec_degrees FLOAT NOT NULL,
    object_type VARCHAR(50),
    magnitude FLOAT,
    size_arcmin FLOAT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Observing history (future feature)
CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER,
    catalog_name VARCHAR(20),
    observed_date DATE,
    location_name VARCHAR(100),
    exposure_seconds INT,
    num_frames INT,
    notes TEXT,
    image_url VARCHAR(500),
    FOREIGN KEY (target_id) REFERENCES dso_catalog(id)
);
```

### Catalog API Enhancements

**New Endpoints**:
```python
# GET /api/catalog/search?q=andromeda
# Returns: Matches from name, catalog ID, common name

# GET /api/catalog/filter?object_type=galaxy&magnitude_max=10&constellation=And
# Returns: Filtered list

# GET /api/catalog/visible?location_id=1&date=2025-10-30
# Returns: Objects observable tonight from location

# POST /api/catalog/custom
# Body: { name, ra, dec, object_type, magnitude }
# Creates user custom target

# GET /api/catalog/recommend?location_id=1&date=2025-10-30&skill_level=beginner
# Returns: Recommended targets based on difficulty, current season
```

**Advanced Filtering UI**:
```html
<div class="catalog-filters">
    <input type="text" id="search" placeholder="Search by name or catalog ID">

    <select id="catalog">
        <option value="all">All Catalogs</option>
        <option value="messier">Messier (110)</option>
        <option value="ngc">NGC (7,840)</option>
        <option value="ic">IC (5,386)</option>
        <option value="caldwell">Caldwell (109)</option>
        <option value="custom">My Custom Targets</option>
    </select>

    <select id="object-type" multiple>
        <option value="galaxy">Galaxies</option>
        <option value="nebula">Nebulae</option>
        <option value="cluster">Star Clusters</option>
        <option value="planetary_nebula">Planetary Nebulae</option>
    </select>

    <label>Magnitude: <input type="range" id="mag-max" min="0" max="15" value="12"></label>

    <select id="difficulty">
        <option value="all">All Difficulties</option>
        <option value="easy">Easy (bright, large)</option>
        <option value="medium">Medium</option>
        <option value="hard">Hard (faint, small)</option>
    </select>

    <label><input type="checkbox" id="visible-tonight"> Visible Tonight</label>
</div>
```

---

## 🛠️ TECHNICAL ARCHITECTURE

### Database Migration Strategy

**Current**: Python dict in `app/services/catalog_service.py`
**Target**: SQLite database with migration path

**Migration Steps**:

1. **Phase 1: Add Database Alongside Dict (No Breaking Changes)**
   ```python
   class CatalogService:
       def __init__(self):
           self.legacy_targets = self._load_legacy_dict()  # Keep working
           self.db = sqlite3.connect('data/catalogs.db')   # New database

       def get_all_targets(self):
           # Try database first, fall back to legacy
           try:
               return self._get_from_database()
           except:
               return self.legacy_targets
   ```

2. **Phase 2: Import All Data (One-Time)**
   ```bash
   python scripts/import_catalogs.py --source opengc --output data/catalogs.db
   ```

3. **Phase 3: Switch Primary Source (After Testing)**
   ```python
   class CatalogService:
       def get_all_targets(self, filters=None):
           # Now use database as primary
           return self._get_from_database(filters)
   ```

4. **Phase 4: Remove Legacy Dict**
   - Delete old hardcoded targets
   - Update tests
   - Update documentation

### Caching Strategy

**Problem**: Ephemeris calculations are CPU-intensive
**Solution**: Multi-layer caching

```python
import redis
from functools import lru_cache

class CachedEphemerisService:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        self.horizons = HorizonsEphemerisService()

    def calculate_position(self, obj, location, time):
        # Check Redis cache first (1 hour TTL)
        cache_key = f"ephemeris:{obj.designation}:{location.name}:{time.isoformat()}"
        cached = self.redis.get(cache_key)

        if cached:
            return json.loads(cached)

        # Calculate if not cached
        position = self.horizons.calculate_position(obj, location, time)

        # Cache for 1 hour
        self.redis.setex(cache_key, 3600, json.dumps(position))

        return position

    @lru_cache(maxsize=1000)
    def get_twilight_times(self, location, date):
        # In-memory cache for twilight times (doesn't change often)
        return self.ephemeris.calculate_twilight_times(location, date)
```

### API Rate Limiting

**Protect External APIs**:
```python
from ratelimit import limits, sleep_and_retry

class RateLimitedService:
    @sleep_and_retry
    @limits(calls=5, period=1)  # Max 5 calls per second
    def query_simbad(self, object_id):
        return Simbad.query_object(object_id)

    @sleep_and_retry
    @limits(calls=30, period=60)  # Max 30 calls per minute
    def query_horizons(self, object_id, time):
        return Horizons(id=object_id, epochs=time).ephemerides()
```

### Background Jobs (Celery)

**Scheduled Tasks**:
```python
from celery import Celery

celery = Celery('astro_planner', broker='redis://localhost:6379/0')

@celery.task
def update_comet_catalog():
    """Run weekly on Sundays at 3 AM"""
    service = SolarSystemService()
    service.refresh_comet_list()

@celery.task
def enrich_catalog_from_simbad():
    """Run monthly: Add SIMBAD data to objects without it"""
    catalog = CatalogService()
    objects = catalog.get_objects_needing_enrichment(limit=100)

    for obj in objects:
        try:
            enriched = simbad.enrich_object_data(obj.catalog_id)
            catalog.update_object(obj.id, enriched)
            time.sleep(0.2)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to enrich {obj.catalog_id}: {e}")
```

**Celery Beat Schedule**:
```python
celery.conf.beat_schedule = {
    'update-comets-weekly': {
        'task': 'update_comet_catalog',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Sunday 3 AM
    },
    'enrich-catalog-monthly': {
        'task': 'enrich_catalog_from_simbad',
        'schedule': crontab(day_of_month=1, hour=4, minute=0),  # 1st of month
    },
}
```

---

## 📅 IMPLEMENTATION ROADMAP

### **Phase 1: Weather Enhancement (Q1 2026)**
**Timeline**: 4-6 weeks
**Priority**: HIGH

**Week 1-2**:
- ✅ Research completed (this document)
- Implement 7Timer integration
- Create composite weather scoring
- Add seeing/transparency to UI

**Week 3-4**:
- Extract moon data from OpenWeatherMap One Call API
- Add moon phase/illumination to scoring
- Update weather display UI

**Week 5-6**:
- Testing with real observing sessions
- Fine-tune composite scoring weights
- Documentation

**Deliverable**: Multi-source weather with seeing and transparency

---

### **Phase 2: Comet & Asteroid Support (Q2 2026)**
**Timeline**: 6-8 weeks
**Priority**: HIGH

**Week 1-2**:
- Install astroquery, create data models
- Implement JPL Horizons ephemeris service
- Database schema for comets/asteroids

**Week 3-4**:
- MPC integration for comet discovery
- Auto-update comet catalog (weekly job)
- COBS integration for real brightness

**Week 5-6**:
- Extend scheduler for moving objects
- UI for "Currently Visible Comets"
- Testing with C/2025 comets

**Week 7-8**:
- Bright asteroid support (Ceres, Vesta, etc.)
- NEO/PHA flagging
- Documentation and examples

**Deliverable**: Full comet and asteroid observing support

---

### **Phase 3: Catalog Expansion (Q3 2026)**
**Timeline**: 6-8 weeks
**Priority**: MEDIUM

**Week 1-2**:
- Database migration (dict → SQLite)
- Import OpenNGC (13,000+ objects)
- Update catalog service to use database

**Week 3-4**:
- Advanced filtering API
- Search by name/coordinates
- UI enhancements (pagination, filters)

**Week 5-6**:
- SIMBAD enrichment (background job)
- User custom target support
- Import/export target lists

**Week 7-8**:
- "Recommend targets" AI feature
- Difficulty scoring algorithm
- Testing with large catalog

**Deliverable**: 10,000+ object catalog with advanced search

---

### **Phase 4: Premium Features (Q4 2026)**
**Timeline**: 4-6 weeks
**Priority**: LOW

**Optional Enhancements**:
- Meteoblue seeing API (paid)
- Planetary positions
- Satellite tracking (ISS, Starlink)
- Multi-night planning
- Observation history tracking

---

## 💰 COST ANALYSIS

### Free Tier (Recommended for MVP)
- 7Timer: **FREE** ✅
- JPL Horizons: **FREE** ✅
- MPC: **FREE** ✅
- COBS: **FREE** ✅
- OpenNGC: **FREE** ✅
- SIMBAD: **FREE** ✅
- VizieR: **FREE** ✅
- OpenWeatherMap: **FREE** (1000 calls/day) ✅

**Total Monthly Cost**: $0

### Premium Tier (Future)
- Meteoblue API: ~€200-500/year ($17-42/month)
- Redis hosting: ~$15/month
- PostgreSQL hosting: ~$25/month
- Celery worker: ~$10/month

**Total Monthly Cost**: ~$67-92/month (for production hosting)

---

## 🎯 SUCCESS METRICS

### Phase 1 (Weather)
- [ ] 7Timer integration working
- [ ] Seeing and transparency displayed in UI
- [ ] Composite score accuracy >80% vs. actual conditions
- [ ] User feedback: "Weather forecasts are accurate"

### Phase 2 (Comets/Asteroids)
- [ ] 20+ comets in catalog
- [ ] Real-time ephemeris for all comets
- [ ] Brightness predictions within 1 magnitude
- [ ] User creates observing plan with comet

### Phase 3 (Catalog)
- [ ] 10,000+ objects in database
- [ ] Search response time <100ms
- [ ] Advanced filters working
- [ ] User adds custom target successfully

---

## 🚀 NEXT STEPS

### Immediate Actions (This Week)
1. ✅ Complete research (DONE)
2. Update ROADMAP.md with findings
3. Get user approval on integration plan
4. Create GitHub issues for Phase 1 tasks
5. Set up development branch: `feature/weather-integration`

### Before Starting Development
- [ ] Install required Python packages (`astroquery`, `pyongc`)
- [ ] Set up Redis for caching (Docker container)
- [ ] Design database schema (final review)
- [ ] Write integration tests for new services

### Questions for User Review
1. **Priority Order**: Weather → Comets → Catalog expansion? Or different order?
2. **Database Choice**: SQLite (simple) or PostgreSQL (scalable)?
3. **Caching**: Redis (extra service) or in-memory (simpler)?
4. **UI Preference**: Show all sources or just composite score?
5. **Timeline**: Aggressive (3 months) or conservative (6 months)?

---

## 📖 REFERENCES

### Official Documentation
- 7Timer API: http://www.7timer.info/doc.php
- JPL Horizons: https://ssd.jpl.nasa.gov/horizons/manual.html
- Astroquery: https://astroquery.readthedocs.io/
- MPC API: https://minorplanetcenter.net/web_service/
- SIMBAD: http://simbad.u-strasbg.fr/Pages/guide/sim-q.htx
- OpenNGC: https://github.com/mattiaverga/OpenNGC

### Python Libraries
- `astroquery`: Astronomy data queries
- `pyongc`: OpenNGC catalog interface
- `redis`: Caching layer
- `celery`: Background tasks
- `sqlalchemy`: Database ORM

### Research Papers
- "Astroplan: An Open Source Observation Planning Package in Python" (2018)
- "The COBS comet database: Structure and content" (2018)

---

**Document Status**: Ready for Review
**Last Updated**: 2025-10-30
**Author**: Claude Code with User
**Next Review**: After user approval
