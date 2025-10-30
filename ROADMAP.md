# Astro Planner Roadmap

This document outlines the planned features and improvements for the Astro Planner application.

## 🎯 Priority 1: Seamless Telescope Integration (Seestar S50)

**Goal**: Make it stupid simple to load plans onto the Seestar S50 telescope

### Current State
- ✅ Export to Seestar Plan Mode JSON format
- ✅ Export to Seestar ALP format
- ❌ User must manually transfer file to telescope
- ❌ No direct integration with Seestar app/device

### Planned Features

#### 1.1 One-Click Plan Transfer
**Status**: Not Started
**Priority**: High
**Effort**: Medium

**Features**:
- Direct upload to Seestar S50 via WiFi/network
- QR code generation for mobile app import
- Auto-detect Seestar on local network
- Clipboard copy for quick paste into Seestar app

**Technical Approach**:
```
Option A: Direct API Integration
- Research Seestar S50 API/network protocol
- Implement direct device communication
- Auto-discovery via mDNS/Bonjour

Option B: Mobile-First Approach
- Generate QR code with plan data
- Mobile app scans and imports
- Share button for native mobile sharing

Option C: File-Based with Auto-Upload
- Monitor for Seestar mount point (USB/network drive)
- Auto-copy plan file when detected
- Desktop app for easier workflow
```

**User Story**:
> "As an astronomer, I click 'Send to Seestar' and my plan is immediately loaded on my telescope - no file transfers, no manual steps."

#### 1.2 Seestar App Integration
**Status**: Not Started
**Priority**: High
**Effort**: High

**Features**:
- Native Seestar app plugin/extension
- In-app plan browser
- One-tap plan activation
- Real-time plan updates during session

**Dependencies**:
- Seestar SDK/API access
- Partnership with Seestar team

#### 1.3 Live Session Tracking
**Status**: Not Started
**Priority**: Medium
**Effort**: Medium

**Features**:
- Track which target is currently imaging
- Show remaining time per target
- Auto-advance to next target notification
- Weather updates during session
- Re-plan on the fly if targets become unavailable

**Technical Approach**:
- WebSocket connection to Seestar
- Real-time status updates
- Mobile-responsive session view

---

## 📚 Priority 2: Expanded Object Catalogs

**Goal**: Provide access to thousands of DSO targets beyond the current 27

### Current State
- ✅ 27 hand-picked popular targets (Messier, NGC, IC)
- ❌ Fixed catalog (requires code changes to add objects)
- ❌ No user-added targets
- ❌ Limited to brightest/largest objects

### Planned Features

#### 2.1 Comprehensive DSO Catalogs
**Status**: Not Started
**Priority**: High
**Effort**: Medium

**Catalogs to Add**:
- **Messier Catalog**: Complete 110 objects (currently ~15)
- **NGC Catalog**: ~7,840 objects (New General Catalogue)
- **IC Catalog**: ~5,386 objects (Index Catalogue)
- **Caldwell Catalog**: 109 objects for amateur astronomy
- **Arp Catalog**: 338 peculiar galaxies
- **Sharpless Catalog**: 313 HII regions (emission nebulae)
- **Abell Catalog**: Planetary nebulae and galaxy clusters

**Database Schema**:
```sql
CREATE TABLE dso_catalog (
    id INTEGER PRIMARY KEY,
    catalog_name VARCHAR(20),  -- 'Messier', 'NGC', 'IC', etc.
    catalog_number VARCHAR(20),
    common_name VARCHAR(100),
    object_type VARCHAR(50),
    ra_hours FLOAT,
    dec_degrees FLOAT,
    magnitude FLOAT,
    size_arcmin FLOAT,
    surface_brightness FLOAT,
    constellation VARCHAR(20),
    description TEXT,
    imaging_difficulty VARCHAR(20),  -- 'Easy', 'Medium', 'Hard'
    recommended_focal_length INT,
    recommended_exposure INT,
    best_months VARCHAR(50)
);
```

**Implementation**:
- Migrate from Python dict to SQLite database
- Import catalogs from astronomical databases (SIMBAD, Vizier)
- Add catalog selection UI
- Filter by catalog, brightness, size, difficulty

#### 2.2 User-Added Targets
**Status**: Not Started
**Priority**: Medium
**Effort**: Low

**Features**:
- Add custom targets via UI
- Import from Stellarium, SkySafari formats
- Share custom target lists
- Community-contributed targets

**UI Mockup**:
```
[Add Custom Target]
Name: _______________
RA: ___h ___m ___s
Dec: ___° ___' ___"
Object Type: [Dropdown]
Magnitude: ___
Size: ___ arcmin
[Save] [Cancel]
```

#### 2.3 Advanced Filtering & Search
**Status**: Not Started
**Priority**: Medium
**Effort**: Low

**Features**:
- Search by name, catalog ID, coordinates
- Filter by constellation, season
- Filter by imaging difficulty
- Filter by required equipment (focal length, aperture)
- "Show only targets visible tonight"
- "Show only targets I haven't imaged"

---

## 🌦️ Priority 3: Enhanced Weather Integration

**Goal**: Provide comprehensive weather data for better observing decisions

### Current State
- ✅ OpenWeatherMap integration (optional)
- ✅ Basic metrics: cloud cover, humidity, wind
- ✅ Weather score with <0.4 warning threshold
- ❌ Limited to 5-day forecast
- ❌ No seeing/transparency predictions
- ❌ No satellite imagery
- ❌ Single weather source

### Planned Features

#### 3.1 Multiple Weather Sources
**Status**: Not Started
**Priority**: High
**Effort**: Medium

**Sources to Integrate**:
- **Clear Outside**: Astronomy-specific forecasts (cloud cover, seeing, transparency)
- **Meteoblue**: High-resolution weather models
- **7Timer**: Astronomy-focused free API
- **NOAA/NWS**: US-based official forecasts
- **Weather Underground**: Hyperlocal conditions
- **Satellite Imagery**: Real-time cloud cover (GOES, etc.)

**Composite Score**:
- Aggregate multiple sources for better accuracy
- Show confidence level based on source agreement
- Fallback if primary source unavailable

#### 3.2 Astronomy-Specific Metrics
**Status**: Not Started
**Priority**: High
**Effort**: Medium

**New Metrics**:
- **Seeing**: Atmospheric stability (arcseconds)
- **Transparency**: Sky clarity (magnitude limit)
- **Darkness**: Moon phase, light pollution
- **Jet Stream**: High-altitude winds affecting seeing
- **Dew Point**: Risk of dew on optics
- **Air Quality Index**: Impact on transparency

**UI Enhancement**:
```
Weather Score: 8.2/10 [Excellent]
├─ Cloud Cover: 5% [Excellent]
├─ Seeing: 1.2" [Very Good]
├─ Transparency: 6.5 mag [Good]
├─ Wind: 3 mph [Calm]
└─ Humidity: 45% [Good]

Moon: 🌒 23% (sets at 10:32 PM)
```

#### 3.3 Multi-Day Forecasting
**Status**: Not Started
**Priority**: Medium
**Effort**: Low

**Features**:
- 7-14 day forecasts
- Weekly observing calendar
- Best nights indicator
- Email/SMS alerts for excellent conditions
- "Plan for this week" auto-scheduling

---

## ☄️ Priority 4: Solar System Objects (Comets & Asteroids)

**Goal**: Support imaging of moving objects with dynamic ephemeris

### Current State
- ✅ UI checkboxes for comets/asteroids
- ❌ No actual comet/asteroid data
- ❌ No ephemeris calculations for moving objects
- ❌ No orbital element database

### Planned Features

#### 4.1 Comet Database & Ephemeris
**Status**: Not Started
**Priority**: High
**Effort**: High

**Features**:
- MPC (Minor Planet Center) integration
- Automatic orbital element updates
- Real-time position calculation
- Brightness predictions
- "Currently visible" comet list

**Data Sources**:
- **MPC Orbital Elements**: https://minorplanetcenter.net/
- **JPL Horizons**: NASA ephemeris service
- **Heavens-Above**: Amateur-friendly predictions
- **COBS (Comet Observation Database)**: Brightness estimates

**Comet-Specific Planning**:
```python
class Comet:
    name: str                    # "C/2023 A3 (Tsuchinshan-ATLAS)"
    designation: str             # "C/2023 A3"
    orbital_elements: dict       # Perihelion, eccentricity, etc.
    last_updated: datetime

    def position_at(self, time, location) -> (float, float):
        """Calculate RA/Dec at specific time using orbital mechanics."""

    def magnitude_at(self, time) -> float:
        """Predict brightness based on solar distance."""

    def is_visible(self, time, location, min_altitude, max_magnitude) -> bool:
        """Check if observable."""
```

**UI Features**:
- "Comets visible this month"
- Auto-update orbital elements weekly
- Show tail orientation
- Imaging difficulty based on brightness/motion

#### 4.2 Asteroid Database
**Status**: Not Started
**Priority**: Medium
**Effort**: High

**Features**:
- Numbered asteroids: ~1 million cataloged
- Named asteroids: ~24,000
- Potentially Hazardous Asteroids (PHA) tracking
- NEO (Near Earth Object) alerts
- Bright asteroid opportunities

**Popular Targets**:
- Main belt asteroids (Ceres, Vesta, Pallas, etc.)
- TNOs (Trans-Neptunean Objects)
- Centaurs (Chiron, etc.)

#### 4.3 Planet Imaging Support
**Status**: Not Started
**Priority**: Low
**Effort**: Medium

**Features**:
- Planetary positions
- Optimal imaging times (high altitude, good seeing)
- Opposition dates
- Satellite positions (Jupiter's moons, Saturn's moons)
- Lunar features (crater shadows, libration)

---

## 🔄 Technical Improvements

### 5.1 Backend Enhancements
- [ ] Migrate from in-memory catalog to database (SQLite/PostgreSQL)
- [ ] Add caching layer (Redis) for ephemeris calculations
- [ ] Async task queue (Celery) for long-running calculations
- [ ] RESTful API v2 with pagination
- [ ] GraphQL API for flexible queries
- [ ] WebSocket support for real-time updates

### 5.2 Frontend Enhancements
- [ ] Progressive Web App (PWA) for offline use
- [ ] Mobile app (React Native / Flutter)
- [ ] Interactive sky map (planetarium view)
- [ ] Drag-and-drop plan reordering
- [ ] Dark mode / red light mode for field use
- [ ] Multi-language support

### 5.3 DevOps & Scaling
- [ ] Kubernetes deployment
- [ ] Auto-scaling for high traffic
- [ ] CDN for static assets
- [ ] Database replication
- [ ] Monitoring & alerting (Grafana, Prometheus)
- [ ] A/B testing framework

---

## 📅 Timeline & Milestones

### Q1 2026: Telescope Integration
- ✅ Export formats (DONE)
- 🎯 QR code plan sharing
- 🎯 Seestar WiFi auto-discovery
- 🎯 One-click plan transfer

### Q2 2026: Expanded Catalogs
- 🎯 Complete Messier catalog (110 objects)
- 🎯 NGC catalog (top 1000 objects)
- 🎯 Database migration
- 🎯 Advanced filtering

### Q3 2026: Weather Enhancements
- 🎯 Clear Outside integration
- 🎯 Seeing & transparency metrics
- 🎯 Multi-day forecasts
- 🎯 Email alerts for good conditions

### Q4 2026: Solar System Objects
- 🎯 Comet ephemeris calculations
- 🎯 MPC orbital element integration
- 🎯 Bright asteroid tracking
- 🎯 Auto-updating comet list

---

## 🤝 Community & Contributions

### Ways to Contribute
1. **Testing**: Report bugs, suggest features
2. **Documentation**: Improve guides, add tutorials
3. **Code**: Submit PRs for new features
4. **Data**: Contribute target lists, imaging tips
5. **Integrations**: Add support for other telescopes

### Feature Requests
Submit feature requests via GitHub Issues:
https://github.com/irjudson/astro-planner/issues

---

## 📊 Success Metrics

- **User Adoption**: 1000+ active users
- **Plan Transfers**: 10,000+ plans loaded to telescopes
- **Catalog Size**: 10,000+ targets available
- **Weather Accuracy**: 85%+ forecast accuracy
- **User Satisfaction**: 4.5/5 star rating

---

*Last Updated*: 2025-10-29
*Version*: 1.0.0
*Status*: Active Development
