# Astro Planner

A complete web-based astrophotography session planner specifically designed for the **Seestar S50 smart telescope**. This application intelligently schedules deep sky objects (DSOs) throughout the night, accounting for visibility, weather conditions, and the unique characteristics of alt-az mounts.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)

## Features

### Intelligent Planning
- **Astronomical Calculations**: Precise twilight times, altitude/azimuth positions, and field rotation rates
- **Smart Scheduling**: Greedy algorithm with urgency-based lookahead to maximize night coverage
- **Seestar S50 Optimized**: Accounts for 50mm f/5 optics, 1.27°×0.71° FOV, and alt-az mount limitations
- **Weather Integration**: Real-time forecasts from OpenWeatherMap API to optimize target selection

### Rich Target Catalog
- **27+ Pre-loaded Targets**: Popular Messier, NGC, and IC objects
- **Object Types**: Galaxies, nebulae, star clusters, and planetary nebulae
- **Detailed Information**: Coordinates, magnitude, size, and descriptions

### Flexible Configuration
- **Location-Based**: Customize for any observing site (lat/lon/elevation/timezone)
- **Date Selection**: Plan for any night, defaults to tonight's session
- **Constraints**: Set altitude limits, setup time, and object type preferences
- **Field Rotation Aware**: Avoids zenith and optimizes for alt-az mount imaging

### Multiple Export Formats
- **Seestar Plan Mode JSON**: Direct import into Seestar S50
- **Seestar_alp Format**: Compatible with various astronomy tools
- **Human-Readable Text**: Detailed session summary
- **CSV**: For spreadsheet analysis
- **JSON**: Complete data export

## Quick Start

### Option 1: Native Development (Recommended for Development)

```bash
# One-time setup
cd astro-planner
python3 -m venv venv
source venv/bin/activate
cd backend
pip install -r requirements.txt -r requirements-processing.txt
cd ..

# Start services (background mode)
./dev-simple.sh

# Stop services when done
./dev-stop.sh
```

Open http://localhost:9247 in your browser.

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed native development guide.

### Option 2: Docker (Production-like)

```bash
cd astro-planner
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Open http://localhost:9247 in your browser.

## Requirements

- **Python**: 3.11 or higher
- **OS**: Linux, macOS, or Windows (with WSL)
- **API Key**: OpenWeatherMap (optional, free tier available)

## Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Native vs Docker development setup
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing strategies and troubleshooting
- [PROCESSING_DESIGN.md](PROCESSING_DESIGN.md) - Image processing pipeline architecture
- [MOSAIC_AND_STACKING_PLAN.md](MOSAIC_AND_STACKING_PLAN.md) - Future roadmap
- [CAPABILITIES_STATUS.md](CAPABILITIES_STATUS.md) - Current feature status

## Project Structure

```
astro-planner/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Configuration
│   │   ├── models/      # Data models
│   │   └── services/    # Business logic
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Web interface
│   └── index.html
├── docker/              # Docker configuration
│   └── Dockerfile
├── data/                # Runtime data
├── setup.sh             # Setup script
├── test_api.py          # API test suite
└── docker-compose.yml
```

## Default Location

The application defaults to **Three Forks, Montana** (45.9183°N, 111.5433°W, 1234m elevation, America/Denver timezone). You can customize this in the web interface or via the API.

## Key Algorithms

### Field Rotation Calculation
For alt-az mounts: `rate = 15 × cos(lat) / cos(alt) × |sin(az)|`

The scheduler avoids high rotation rates by:
- Preferring 45-65° altitude range
- Avoiding zenith during meridian passage
- Scoring targets based on rotation rate

### Target Scoring
Composite score (0-1) based on:
- **Visibility (40%)**: Altitude, duration, field rotation
- **Weather (30%)**: Cloud cover, humidity, wind
- **Object (30%)**: Brightness, size match to FOV

### Urgency-Based Scheduling
Targets setting within the lookahead window (default 30 minutes) receive a priority bonus, ensuring time-sensitive objects aren't missed.

## API Endpoints

- `POST /api/plan` - Generate complete observing plan
- `GET /api/targets` - List all DSO targets
- `GET /api/targets/{id}` - Get specific target details
- `POST /api/twilight` - Calculate twilight times
- `POST /api/export` - Export plan in various formats
- `GET /api/health` - Health check

Full API documentation available at http://localhost:9247/api/docs

## Testing

```bash
# Start the server first
python -m uvicorn app.main:app --reload

# In another terminal
python test_api.py
```

## Weather API Setup

1. Sign up for a free API key at https://openweathermap.org/api
2. Edit `backend/.env` and set `OPENWEATHERMAP_API_KEY=your_key_here`
3. Restart the application

Without an API key, the system uses optimistic default weather forecasts.

## Contributing

This is a production-ready application designed for astrophotography enthusiasts using the Seestar S50. Contributions welcome:

- Additional DSO targets
- Enhanced scheduling algorithms
- New export formats
- UI improvements

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Astronomical calculations using [Skyfield](https://rhodesmill.org/skyfield/)
- Weather data from [OpenWeatherMap](https://openweathermap.org/)

## Support

For issues or questions, please check the documentation or create an issue in the project repository.

---

**Made for stargazers, by stargazers** 🔭✨
