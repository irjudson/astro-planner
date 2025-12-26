# Astro Planner

> Intelligent observing session planner for astrophotography with Seestar S50 integration

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)

---

## What is Astro Planner?

Astro Planner is a comprehensive observing session planning tool that helps astrophotographers maximize their imaging time by intelligently scheduling deep sky objects throughout the night. The application accounts for astronomical phenomena, weather conditions, and equipment limitations to create optimal observation plans.

**Perfect for:**
- 🔭 Seestar S50 telescope users
- 🌌 Astrophotography enthusiasts
- 📊 Data-driven session planning
- 🌐 Any location worldwide

---

## Key Features

### ✅ Implemented

**Smart Scheduling**
- Greedy algorithm with urgency-based lookahead optimizes target selection
- Field rotation calculation for alt-az mounts
- Automated daily plan generation at noon

**Comprehensive Catalog**
- **12,400+ objects** from OpenNGC catalog
- Messier, NGC, and IC catalogs
- Advanced filtering by type, magnitude, constellation
- Search by catalog ID or common name

**Weather Integration**
- 7Timer astronomical seeing and transparency forecasts
- OpenWeatherMap cloud cover and conditions
- Composite weather scoring for target selection

**Seestar S50 Integration**
- Direct export to seestar_alp CSV format
- QR code sharing for mobile workflow
- Optimized for 50mm f/5 optics (1.27° × 0.71° FOV)
- Alt-az mount field rotation compensation

**GPU Processing**
- CUDA-accelerated image stacking with CuPy
- Sigma-clipped mean stacking for outlier rejection
- Auto-stretch matching Seestar native output
- NVIDIA MPS for efficient GPU sharing

**Automatic Planning**
- Daily plan generation at configurable time
- Celery Beat scheduler for periodic tasks
- Webhook notifications for plan creation
- Database-backed configuration

**Multiple Export Formats**
- seestar_alp CSV (recommended)
- Seestar Plan Mode JSON
- Human-readable text
- CSV for analysis
- Complete JSON export

### 🚧 In Progress

**Frontend Catalog Browser**
- Interactive catalog exploration UI
- Advanced search and filtering
- Target preview and details

**Live Session Tracking**
- Real-time execution monitoring
- Progress updates during imaging
- Weather-based re-planning

### 📋 Planned (2026)

**Comet/Asteroid Ephemeris**
- Automated position calculations
- Integration with MPC and JPL databases
- Moving object tracking

**Mosaic Planning**
- Multi-panel session planning
- FOV overlap calculation
- Automatic stitching support

**Multi-Telescope Support**
- Equipment profiles
- Simultaneous telescope control
- Cloud observation coordination

[See full roadmap →](docs/planning/ROADMAP.md)

---

## Quick Start

### Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Access the application
open http://localhost:9247
```

**That's it!** The default configuration works out of the box for testing.

[Full quick start guide →](QUICK_START.md)

### Native Development

```bash
# Setup
git clone https://github.com/irjudson/astro-planner.git
cd astro-planner/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 9247 --reload
```

[Development guide →](docs/development/DEVELOPMENT.md)

---

## Documentation

### For Users

- **[Quick Start](QUICK_START.md)** - Get started in 5 minutes
- **[User Guide](docs/user-guides/USAGE.md)** - How to use the planner
- **[API Documentation](docs/user-guides/API_USAGE.md)** - API endpoints and examples
- **[Seestar Integration](docs/seestar/SEESTAR_INTEGRATION.md)** - Using with Seestar S50
- **[Daily Planning](docs/planning/DAILY_PLANNING.md)** - Automatic plan generation

### For Developers

- **[Architecture](docs/architecture/ARCHITECTURE.md)** - System design and components
- **[Development Setup](docs/development/DEVELOPMENT.md)** - Native installation guide
- **[Testing Guide](docs/development/TESTING_GUIDE.md)** - Running and writing tests
- **[Processing Design](docs/architecture/PROCESSING_DESIGN.md)** - Image processing pipeline

### For Operators

- **[Docker Deployment](docs/development/DOCKER_SETUP.md)** - Production deployment
- **[Configuration Reference](docs/CONFIGURATION.md)** - All environment variables
- **[GPU Configuration](docs/planning/GPU_MPS_CONFIG.md)** - NVIDIA MPS setup

[Complete documentation index →](docs/INDEX.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Vue.js)                      │
│         http://localhost:9247                       │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/REST API
┌──────────────────▼──────────────────────────────────┐
│           FastAPI Backend (Python 3.11)             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │  Planner   │  │  Catalog   │  │   Weather    │  │
│  │  Service   │  │  Service   │  │   Service    │  │
│  └────────────┘  └────────────┘  └──────────────┘  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ Processing │  │ Telescope  │  │   Export     │  │
│  │  Service   │  │  Service   │  │   Service    │  │
│  └────────────┘  └────────────┘  └──────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
┌────▼────┐  ┌────▼─────┐  ┌───▼──────┐
│PostgreSQL│  │  Redis   │  │  Celery  │
│ Database │  │  Broker  │  │  Workers │
└──────────┘  └──────────┘  └──────────┘
```

[Detailed architecture →](docs/architecture/ARCHITECTURE.md)

---

## Tech Stack

**Backend**
- Python 3.11+
- FastAPI for REST API
- SQLAlchemy for ORM
- Alembic for migrations
- Celery for background tasks

**Database**
- PostgreSQL for data persistence
- Redis for message broker

**Processing**
- CuPy for GPU acceleration (CUDA 12.8+)
- NumPy for CPU fallback
- Astropy for FITS file handling
- Skyfield for astronomical calculations

**Frontend**
- Vue.js for reactive UI
- Chart.js for visualizations
- Vanilla JavaScript (no build step)

**Deployment**
- Docker and Docker Compose
- NVIDIA Container Toolkit for GPU
- Celery Beat for scheduling

---

## Default Configuration

**Location:** Three Forks, Montana
- Latitude: 45.9183°N
- Longitude: 111.5433°W
- Elevation: 1234m (4049 ft)
- Timezone: America/Denver

**Planning:**
- Min altitude: 30°
- Max altitude: 70° (to avoid high field rotation)
- Setup time: 30 minutes
- Planning mode: Balanced

**Telescope:** Seestar S50
- Aperture: 50mm
- Focal length: 50mm (f/5)
- FOV: 1.27° × 0.71°
- Max exposure: 10 seconds

[Configuration guide →](docs/CONFIGURATION.md)

---

## Key Algorithms

### Field Rotation Calculation
For alt-az mounts, field rotation rate (degrees/minute):

```
rate = 15 × cos(latitude) / cos(altitude) × |sin(azimuth)|
```

The scheduler:
- Prefers 45-65° altitude range (optimal)
- Avoids zenith during meridian passage
- Scores targets based on rotation rate

### Target Scoring
Composite score (0-1) based on weighted components:

| Component | Weight | Factors |
|-----------|--------|---------|
| Visibility | 40% | Altitude, duration, field rotation |
| Weather | 30% | Cloud cover, humidity, wind, seeing |
| Object Quality | 30% | Brightness, size match to FOV |

### Urgency-Based Scheduling
Targets setting within the lookahead window (30 minutes) receive priority bonus to avoid missing time-sensitive objects.

---

## API Endpoints

**Planning:**
- `POST /api/plan` - Generate observing plan
- `GET /api/plans` - List saved plans
- `POST /api/plans/{id}/execute` - Execute plan on telescope

**Catalog:**
- `GET /api/targets` - List DSO targets (paginated)
- `GET /api/targets/{id}` - Get target details
- `GET /api/targets/search` - Search catalog
- `GET /api/targets/stats` - Catalog statistics

**Weather:**
- `GET /api/weather/current` - Current conditions
- `GET /api/weather/forecast` - Multi-hour forecast
- `GET /api/astronomy/weather/7timer` - Astronomical seeing

**Processing:**
- `POST /api/process/auto` - Auto-process FITS file
- `POST /api/process/stack-and-stretch` - Stack and stretch
- `GET /api/process/jobs/{id}` - Job status

**System:**
- `GET /api/health` - Health check
- `GET /api/docs` - OpenAPI documentation

[Complete API documentation →](http://localhost:9247/api/docs)

---

## Requirements

**Minimum:**
- Python 3.11+
- Docker 20.10+ and Docker Compose 2.0+ (Docker installation)
- OR PostgreSQL 14+ and Redis 6+ (Native installation)

**Optional:**
- NVIDIA GPU with CUDA 12.8+ for GPU-accelerated processing
- OpenWeatherMap API key (free tier) for weather forecasts

**OS Support:**
- Linux (tested on Ubuntu 22.04+)
- macOS (tested on 12.0+)
- Windows via WSL2

---

## Testing

```bash
# Start services
docker-compose up -d

# Run test suite
docker exec astro-planner pytest

# Run with coverage
docker exec astro-planner pytest --cov=app

# Run specific test
docker exec astro-planner pytest tests/test_planner_service.py
```

**Test Coverage:** 471 tests passing, 3 skipped

[Testing guide →](docs/development/TESTING_GUIDE.md)

---

## Contributing

Contributions are welcome! Areas of interest:

**Features:**
- Additional DSO catalogs (Caldwell, Arp, Sharpless)
- Comet/asteroid ephemeris integration
- Mosaic planning capabilities
- Advanced image processing algorithms

**Improvements:**
- Enhanced scheduling algorithms
- Additional export formats
- UI/UX enhancements
- Performance optimizations

**Documentation:**
- Additional examples and tutorials
- Translation to other languages
- Video guides

**Process:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow [development guidelines](docs/development/DEVELOPMENT.md)
4. Run tests and ensure they pass (`pytest`)
5. Submit a pull request

[Development guide →](docs/development/DEVELOPMENT.md)

---

## License

MIT License - See [LICENSE](LICENSE) for details

**Free for:**
- Personal use
- Commercial use
- Modification
- Distribution

**Requirements:**
- Include copyright notice
- Include license text

---

## Acknowledgments

**Software:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Skyfield](https://rhodesmill.org/skyfield/) - Astronomical calculations
- [Astropy](https://www.astropy.org/) - Astronomy tools for Python
- [CuPy](https://cupy.dev/) - GPU-accelerated computing

**Data Sources:**
- [OpenNGC](https://github.com/mattiaverga/OpenNGC) - Open NGC/IC catalog (CC-BY-SA-4.0)
- [OpenWeatherMap](https://openweathermap.org/) - Weather forecasts
- [7Timer](http://www.7timer.info/) - Astronomical seeing forecasts

**Community:**
- [Seestar S50 Users](https://www.reddit.com/r/seestar/) - Telescope community
- [smart-underworld/seestar_alp](https://github.com/smart-underworld/seestar_alp) - Seestar automation tools

---

## Support

**Documentation:** [docs/INDEX.md](docs/INDEX.md)

**Issues:** [GitHub Issues](https://github.com/irjudson/astro-planner/issues)

**Discussions:** [GitHub Discussions](https://github.com/irjudson/astro-planner/discussions) (for questions)

---

**Made for stargazers, by stargazers** 🔭✨
