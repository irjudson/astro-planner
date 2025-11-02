# Astro Planner Roadmap

This document outlines the planned features and improvements for the Astro Planner application.

**📋 NEW: Detailed technical integration plan now available!**
See [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) for comprehensive research on weather APIs, comet/asteroid data sources, and catalog expansion with code examples and implementation steps.

**Last Updated**: 2025-10-30

## 🎯 Priority 1: Seamless Telescope Integration (Seestar S50)

**Goal**: Make it stupid simple to load plans onto the Seestar S50 telescope

### Current State
- ✅ Export to Seestar Plan Mode JSON format
- ✅ Export to Seestar ALP CSV format
- ✅ QR code sharing for mobile workflow
- ❌ Direct WiFi upload to Seestar S50
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

## 📚 Priority 2: Expanded Object Catalogs ✅ COMPLETED!

**Goal**: Provide access to thousands of DSO targets beyond the current 27

### Current State (Updated 2025-10-30)
- ✅ **12,394 objects** from OpenNGC catalog (459x increase!)
- ✅ SQLite database with optimized indexes
- ✅ Advanced filtering API (type, magnitude, constellation, pagination)
- ✅ Messier (M), NGC, and IC catalog support
- ✅ Smart catalog ID resolution
- ✅ Statistics endpoint for catalog metrics
- ⏳ Frontend UI updates (pending)
- ⏳ User-added targets (future enhancement)

### Completed Features

#### 2.1 Comprehensive DSO Catalogs ✅ COMPLETED
**Status**: Implemented and Deployed
**Completed**: 2025-10-30
**Actual Effort**: 1 day (faster than estimated!)

**Primary Catalog Source (FREE)**:
- **OpenNGC** ✅: Open-source NGC/IC database with CC-BY-SA-4.0 license (commercial-friendly!)
  - Python library: `pyongc`
  - **13,226 objects total**: 7,840 NGC + 5,386 IC
  - Includes Messier cross-references and common names
  - One-time import to SQLite database
  - **Recommended as primary catalog**

**Catalogs Included in OpenNGC**:
- **Messier Catalog**: Complete 110 objects (currently ~15)
- **NGC Catalog**: Complete 7,840 objects (New General Catalogue)
- **IC Catalog**: Complete 5,386 objects (Index Catalogue)
- All with RA/Dec, magnitude, size, object type, constellation

**Future Catalogs (via VizieR/SIMBAD)**:
- **Caldwell Catalog**: 109 objects for amateur astronomy
- **Arp Catalog**: 338 peculiar galaxies
- **Sharpless Catalog**: 313 HII regions (emission nebulae)

**See INTEGRATION_PLAN.md Section "DSO Catalog Expansion" for database schema and import code**

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

#### 2.2 Catalog Enrichment (Future Phase)
**Status**: Ideas for Future Implementation
**Priority**: Medium
**Effort**: Medium

**Ideas for Enhancement**:
1. **Traditional Common Names**
   - Add "Andromeda Galaxy" for M31
   - "Orion Nebula" for M42
   - Import from SIMBAD or manual curation
   - Display both catalog ID and common name in UI

2. **Additional Catalogs**
   - Caldwell Catalog (109 objects for amateur astronomy)
   - Arp Catalog (338 peculiar galaxies)
   - Sharpless Catalog (313 HII regions)
   - Barnard Dark Nebulae
   - Collinder Open Clusters

3. **Imaging Metadata**
   - Difficulty rating (Easy/Medium/Hard)
   - Recommended focal length
   - Recommended exposure time
   - Best months for imaging
   - Popular filters (Ha, OIII, SII)
   - Sample images/thumbnails

4. **Search Enhancements**
   - Full-text search by name
   - Search by coordinate range
   - "Objects near M31" (angular distance search)
   - Search by season/month
   - Search by equipment compatibility

5. **Data Quality Improvements**
   - Replace magnitude=99.0 defaults with NULL
   - Add more accurate size data
   - Cross-reference with SIMBAD for enrichment
   - Periodic catalog updates (quarterly sync)

#### 2.3 User-Added Targets
**Status**: Future Enhancement
**Priority**: Medium
**Effort**: Low

**Features**:
- Add custom targets via UI
- Import from Stellarium, SkySafari formats
- Share custom target lists with community
- Personal observing history tracking
- "Targets I've imaged" collection

**UI Mockup**:
```
[Add Custom Target]
Name: _______________
Catalog ID (optional): ___
RA: ___h ___m ___s
Dec: ___° ___' ___"
Object Type: [Dropdown]
Magnitude: ___
Size: ___ arcmin
Notes: _________________
[Save] [Cancel]
```

#### 2.4 Frontend Catalog Browser
**Status**: Next Priority
**Priority**: High
**Effort**: Medium (2-3 weeks)

**Features**:
1. **Catalog Browser UI**
   - Grid/list view of objects
   - Advanced filter sidebar
   - Sort by magnitude, size, type
   - Pagination with infinite scroll
   - Quick filters (bright objects, tonight's targets)

2. **Object Detail Page**
   - Full object information
   - Visibility chart for current location
   - Rise/set times
   - Altitude graph over night
   - "Add to plan" button
   - Similar objects nearby

3. **Search Interface**
   - Search by name or catalog ID
   - Autocomplete suggestions
   - Recent searches
   - Popular objects shortcut

4. **Statistics Dashboard**
   - Visual charts of catalog composition
   - Magnitude distribution histogram
   - Object type pie chart
   - Constellation distribution map

5. **Mobile Optimization**
   - Touch-friendly catalog browsing
   - Swipe gestures for filtering
   - Offline caching of favorites
   - Dark mode for field use

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

#### 3.1 Multiple Weather Sources ✅ RESEARCHED
**Status**: Research Complete, Ready for Implementation
**Priority**: High
**Effort**: Medium (4-6 weeks)

**Primary Source (FREE)**:
- **7Timer** ✅: Astronomy-specific, includes seeing (arcseconds) and transparency (magnitude limit), 3-layer cloud cover, completely free NOAA GFS-based forecasts
  - API: `http://www.7timer.info/bin/astro.php`
  - No authentication required
  - Returns JSON with 72-hour forecasts
  - **Recommended as Phase 1 implementation**

**Secondary Sources**:
- **OpenWeatherMap** (CURRENT): Keep for baseline weather, precipitation, moon phase
- **Meteoblue** (PAID ~€200-500/year): Premium seeing predictions, consider for Phase 4
- **Clear Outside**: No public API available (web scraping not recommended)

**Composite Score Architecture**:
- Weight 7Timer at 60% (best for astronomy)
- Weight OpenWeatherMap at 40% (good baseline)
- Show confidence level based on source availability
- Automatic fallback if primary unavailable

**See INTEGRATION_PLAN.md Section "Weather & Seeing Integration" for detailed implementation**

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

#### 4.1 Comet Database & Ephemeris ✅ RESEARCHED
**Status**: Research Complete, Ready for Implementation
**Priority**: High
**Effort**: Medium (6-8 weeks)

**Primary Data Source (FREE)**:
- **JPL Horizons via astroquery** ✅: Official NASA ephemeris for 4,034 comets, 1.4M+ asteroids
  - Python library: `from astroquery.jplhorizons import Horizons`
  - No authentication required
  - Real-time position calculation (RA/Dec/Alt/Az)
  - Magnitude predictions
  - Rise/set times
  - **Recommended as primary ephemeris engine**

**Supporting Sources (FREE)**:
- **MPC (Minor Planet Center)**: Weekly comet discovery updates via `astroquery.mpc`
- **COBS (Comet Observation Database)**: Real observed brightness (more accurate than predictions)
  - API: `https://cobs.si/api/`
  - Override JPL predictions with recent observations (last 4 days)

**Implementation Highlights**:
- Database table for comets with orbital elements
- Auto-update catalog weekly from MPC
- Cache ephemeris calculations (Redis, 1 hour TTL)
- "Currently Visible Comets" UI widget

**See INTEGRATION_PLAN.md Section "Comet & Asteroid Integration" for code examples**

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

### ✅ COMPLETED: Catalog Expansion (October 2025)
- ✅ Research complete (2025-10-30)
- ✅ OpenNGC import (12,394 NGC/IC objects)
- ✅ Database migration (dict → SQLite)
- ✅ Advanced filtering & search API
- ✅ Messier/NGC/IC catalog support
- ✅ Statistics endpoint
- ✅ API documentation
**Completed**: 1 day | **All sources FREE** | **Branch**: `feature/catalog-expansion`

### 🎯 NEXT: Frontend Catalog Browser (November 2025)
**Priority**: HIGH
- 🎯 Catalog browser UI component
- 🎯 Advanced filtering interface
- 🎯 Object detail pages
- 🎯 Statistics dashboard with charts
- 🎯 Mobile-optimized browsing
**Estimated**: 2-3 weeks | **Depends on**: Catalog expansion (done!)

### Q1 2026: Weather Enhancement
**Priority**: HIGH
- ✅ Research complete (2025-10-30)
- 🎯 7Timer API integration (seeing & transparency)
- 🎯 Composite weather scoring (multi-source)
- 🎯 Moon phase/illumination from OpenWeatherMap
- 🎯 UI updates with astronomy-specific metrics
**Estimated**: 4-6 weeks | **All sources FREE**

### Q2 2026: Comet & Asteroid Support
**Priority**: HIGH
- ✅ Research complete (2025-10-30)
- 🎯 JPL Horizons via astroquery (ephemeris engine)
- 🎯 MPC integration (comet discoveries)
- 🎯 COBS integration (real brightness data)
- 🎯 Database schema for solar system objects
- 🎯 "Currently Visible Comets" UI
- 🎯 Scheduler support for moving objects
**Estimated**: 6-8 weeks | **All sources FREE**

### Q3 2026: Catalog Enrichment & Additional Features
**Priority**: MEDIUM
- 🎯 Traditional common names (SIMBAD integration)
- 🎯 Additional catalogs (Caldwell, Arp, Sharpless)
- 🎯 Imaging metadata (difficulty, recommendations)
- 🎯 User custom targets
- 🎯 Observing history tracking
**Estimated**: 4-6 weeks | **All sources FREE**

### Q4 2026: Telescope Integration & Premium Features
**Priority**: MEDIUM
- 🎯 Seestar WiFi auto-discovery
- 🎯 One-click plan transfer
- 🎯 Live session tracking
- 🎯 Meteoblue premium seeing (PAID option)
- 🎯 Multi-telescope support
**Estimated**: 6-8 weeks

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

## 💰 Cost Summary (2025-10-30 Research)

### Free Tier (Phases 1-3)
All core features can be implemented with **$0 monthly cost**:
- ✅ 7Timer (weather/seeing/transparency): FREE
- ✅ JPL Horizons (comet/asteroid ephemeris): FREE
- ✅ MPC (comet discoveries): FREE
- ✅ COBS (brightness observations): FREE
- ✅ OpenNGC (13K+ DSO catalog): FREE
- ✅ SIMBAD/VizieR (catalog enrichment): FREE
- ✅ OpenWeatherMap (1000 calls/day): FREE

### Optional Premium Tier (Phase 4)
- Meteoblue API: ~$17-42/month
- Redis hosting: ~$15/month
- PostgreSQL hosting: ~$25/month
**Total**: ~$67-92/month (for production scaling)

---

## 📊 Success Metrics

- **User Adoption**: 1000+ active users
- **Plan Transfers**: 10,000+ plans loaded to telescopes
- **Catalog Size**: 10,000+ targets available
- **Weather Accuracy**: 85%+ forecast accuracy (composite scoring)
- **Comet Coverage**: 20+ visible comets tracked automatically
- **User Satisfaction**: 4.5/5 star rating

---

*Last Updated*: 2025-10-30 (Research complete)
*Version*: 1.0.0
*Status*: Active Development - Ready for Phase 1 implementation
*Next Step*: Review [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) and begin weather integration
