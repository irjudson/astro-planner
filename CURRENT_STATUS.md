# Current Status - Astro Planner

## Project Overview
A production-ready astrophotography session planner web application optimized for the Seestar S50 smart telescope (but adaptable to other equipment).

**Live URL**: http://localhost:9247

## ✅ Implemented Features

### Core Functionality
- **Astronomical Calculations**: Precise twilight times (civil, nautical, astronomical), altitude/azimuth positions, field rotation rates for alt-az mounts
- **Smart Scheduling**: Greedy algorithm with urgency-based lookahead to maximize night coverage
- **Weather Integration**: OpenWeatherMap API support (optional, falls back to optimistic defaults)
- **12,394 DSO Targets** (NEW!): Comprehensive catalog from OpenNGC with Messier, NGC, and IC objects
  - Advanced filtering (magnitude, type, constellation)
  - Statistics API endpoint
  - Pagination support (up to 1000 per request)

### Planning Modes (NEW!)
- **Balanced Mode** (default): 20min minimum, 90min maximum per target, 0.6 score threshold, up to 15 targets
- **Best Quality Mode**: 45min minimum, 180min maximum per target, 0.7 score threshold, up to 8 targets (longer exposures, fewer targets)
- **More Objects Mode**: 15min minimum, 45min maximum per target, 0.5 score threshold, up to 20 targets (more variety)

### Object Types Supported
- Galaxies
- Nebulae
- Star Clusters
- Planetary Nebulae
- Comets (UI support - requires custom catalog entries)
- Asteroids (UI support - requires custom catalog entries)

### User Interface Improvements
- **Elevation in feet** (converts to meters for calculations) - default: 4049 ft
- **Setup time**: Default 30 minutes
- **Maximum altitude**: 90° (full zenith) allowed
- **Planning mode dropdown**: Easy selection of optimization strategy
- **Object type checkboxes**: Filter by preferred object types
- **Port**: Non-conflicting 9247 (changed from 8000)

### Export Formats
- Seestar Plan Mode JSON (direct import to Seestar S50)
- Seestar_alp format (compatible with various tools)
- Human-readable text (detailed session summary)
- CSV (for spreadsheet analysis)
- JSON (complete data export)

### Technical Stack
- **Backend**: Python 3.11+, FastAPI, Skyfield, Astropy
- **Frontend**: HTML5/CSS3/JavaScript (no build step)
- **Deployment**: Docker with docker-compose
- **API**: RESTful endpoints with full OpenAPI documentation

## 🔧 Configuration

### Default Location
Three Forks, Montana (45.9183°N, 111.5433°W, 4049 ft elevation, America/Denver timezone)

### Seestar S50 Specifications (Built-in)
- Focal length: 50mm
- Aperture: 50mm (f/5)
- FOV: 1.27° × 0.71°
- Max exposure: 10 seconds
- Mount type: Alt-az (field rotation compensated)

### Observing Constraints
- Default min altitude: 30°
- Default max altitude: 90°
- Optimal altitude range: 45-65° (preferred by scorer)
- Slew time: 60 seconds between targets
- Lookahead window: 30 minutes (for urgency-based scheduling)

## 📁 Project Structure

```
astro-planner/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # REST API endpoints
│   │   ├── core/config.py         # Configuration
│   │   ├── models/models.py       # Pydantic data models
│   │   └── services/              # 6 core services:
│   │       ├── ephemeris_service.py    # Twilight, positions, field rotation
│   │       ├── catalog_service.py      # 27 DSO targets
│   │       ├── weather_service.py      # OpenWeatherMap integration
│   │       ├── scheduler_service.py    # Planning algorithm
│   │       ├── export_service.py       # Multi-format export
│   │       └── planner_service.py      # Main orchestration
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html                 # Single-page web app
├── docker/
│   ├── Dockerfile
│   └── .dockerignore
├── docker-compose.yml
├── setup.sh                       # Automated setup
├── test_api.py                    # API test suite
└── docs/
    ├── README.md                  # Project overview
    ├── QUICKSTART.md              # 5-minute setup
    ├── USAGE.md                   # Detailed guide
    ├── ARCHITECTURE.md            # Technical details
    └── CURRENT_STATUS.md          # This file
```

## 🐛 Known Issues / Limitations

### Date Handling
- Civil/Nautical twilight times sometimes show next day's date (astronomy crosses midnight)
- Recommendation: Focus on astronomical twilight times for imaging window

### Weather API
- Requires free OpenWeatherMap API key
- Without key, uses optimistic defaults (20% clouds, clear conditions)
- API has rate limits on free tier

### Catalog Limitations
- Fixed catalog of 27 objects (requires code changes to add more)
- Comets/asteroids require custom ephemeris data (not auto-calculated)
- No support for moving objects yet

### Alt-Az Field Rotation
- Calculated but not currently used to filter targets
- Very high rotation rates (>2°/min) near zenith included if within altitude constraints
- Recommendation: Keep max altitude at 80° for better tracking

## 🧪 Testing

**Run test suite**:
```bash
# Start server first
docker-compose up -d

# Wait for startup, then run tests
python test_api.py
```

**Test in browser**:
1. Open http://localhost:9247
2. Default location should work out of the box
3. Click "Generate Observing Plan"
4. See scheduled targets with times, altitudes, scores

**Test different planning modes**:
- Balanced: Good mix of targets and quality
- Best Quality: Fewer targets, longer exposures (great for deep imaging)
- More Objects: Many targets, shorter exposures (survey mode)

## 📊 Recent Improvements

### Session 1 (Initial Development)
- Complete full-stack application
- Core astronomical calculations
- Basic scheduling algorithm
- Export formats
- Docker deployment

### Session 2 (Bug Fixes & Enhancements)
- Fixed Skyfield vector addition errors
- Fixed twilight calculation logic
- Fixed weather service hour overflow
- Added planning modes (Balanced, Quality, Quantity)
- Added comet and asteroid object types to UI
- Changed elevation to feet for US users
- Increased setup time default to 30 minutes
- Allowed 90° maximum altitude
- Changed port to 9247 to avoid conflicts
- Added duration caps per planning mode
- Updated page title to be more generic

## 🎯 Next Steps

See [FUTURE_ENHANCEMENTS.md](FUTURE_ENHANCEMENTS.md) for planned features and nice-to-haves.

## 📝 Git History Summary

```
63d993a Update page title to be more generic
b96c5e0 Add max duration caps per planning mode
9ea4342 Add planning modes and new object types (comets, asteroids)
5060ab6 Fix weather service hour overflow bug
9d29612 Fix twilight times to use first occurrence only
d241255 Fix twilight calculation to use Skyfield's built-in dark_twilight_day
60600a5 Fix UI tweaks and Skyfield vector addition error
8a5cf52 Fix frontend path resolution in main.py
725554a Fix Dockerfile: correct FROM casing and add curl for health checks
e1fabeb Change default port from 8000 to 9247 to avoid conflicts
cf08f49 Initial commit: Complete Astro Planner application
```

**Total Commits**: 11
**Development Time**: 2 sessions
**Status**: Production-ready, fully functional

---

*Last Updated*: 2025-10-29
*Version*: 1.0.0
*Port*: 9247
