# Astro Planner - Quick Start Guide

Get up and running with Astro Planner in minutes! Choose the path that best fits your needs.

---

## Choose Your Path

### 🐳 [Docker Quick Start](#docker-quick-start-recommended) (Recommended)
**Best for:** Most users, production use, testing
**Time:** 5 minutes
**Requirements:** Docker, Docker Compose

### 💻 [Native Development](#native-development)
**Best for:** Contributors, advanced customization
**Time:** 15-20 minutes
**Requirements:** Python 3.11+, PostgreSQL, Redis

### 🔭 [Seestar Integration Only](#seestar-integration-only)
**Best for:** Seestar S50 users who want to export plans
**Time:** 2 minutes
**Requirements:** Running Astro Planner instance

---

## Docker Quick Start (Recommended)

### TL;DR

```bash
# 1. Stop any native services
./scripts/docker-clean.sh

# 2. Start Docker services
./scripts/docker-start.sh

# 3. Access the application
open http://localhost:9247
```

### Detailed Setup

#### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- (Optional) NVIDIA Docker Runtime for GPU-accelerated processing

#### Step 1: Environment Configuration

Create a `.env` file in the project root:

```bash
# Required
OPENWEATHERMAP_API_KEY=your_api_key_here

# Optional - Location defaults
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver

# Optional - FITS directory (for Seestar image processing)
FITS_DIR=/path/to/your/fits/files
```

**Get API Key:**
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Generate a free API key
3. Add to `.env` file

#### Step 2: Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

#### Step 3: Verify Installation

1. **API Health Check**: http://localhost:9247/api/health
2. **Main Application**: http://localhost:9247
3. **Generate a Plan**:
   - Set your location
   - Choose an observing date
   - Click "Generate Observing Plan"

### What's Running?

After starting with Docker, you'll have:

| Service | Port | Purpose |
|---------|------|---------|
| **astronomus** | 9247 | Main API and web interface |
| **redis** | 6379 | Message broker (internal) |
| **postgres** | 5432 | Database (internal) |
| **celery-worker** | - | Background task processor |
| **celery-beat** | - | Periodic task scheduler |

### Common Docker Commands

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f astronomus
docker-compose logs -f celery-worker

# Restart a service
docker-compose restart astronomus

# Stop everything
./scripts/docker-stop.sh
# OR
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Monitoring (Optional)

Start Flower for Celery monitoring:

```bash
docker-compose --profile monitoring up -d flower
# Access at http://localhost:5555
```

### Troubleshooting Docker

#### Port Already in Use

```bash
# Check what's using port 9247
lsof -i :9247

# Stop native services
./scripts/docker-clean.sh
```

#### Database Issues

```bash
# Restart database service
docker-compose restart postgres

# View database logs
docker-compose logs postgres

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

#### GPU Not Working

```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Check worker GPU access
docker exec astronomus-worker nvidia-smi
```

For comprehensive Docker documentation, see [Docker Setup Guide](docs/development/DOCKER_SETUP.md)

---

## Native Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Git
- (Optional) CUDA 12.8+ for GPU processing

### Quick Setup

```bash
# 1. Clone repository (if not already done)
git clone https://github.com/irjudson/astronomus.git
cd astronomus

# 2. Install backend dependencies
cd backend
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your configuration

# 4. Initialize database
alembic upgrade head

# 5. Start services
# Terminal 1: Redis
redis-server

# Terminal 2: PostgreSQL (if not running as service)
# Terminal 3: API server
uvicorn app.main:app --host 0.0.0.0 --port 9247 --reload

# Terminal 4: Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 5: Celery beat (for daily plans)
celery -A app.tasks.celery_app beat --loglevel=info

# 6. Access application
open http://localhost:9247
```

### Environment Variables (Native)

Required variables for native installation:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/astro_planner
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/test_astro_planner

# Redis
REDIS_URL=redis://localhost:6379/1

# Weather
OPENWEATHERMAP_API_KEY=your_key_here

# Location defaults
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
CELERY_TIMEZONE=America/Denver

# Files
FITS_DIR=/path/to/fits/files
```

### Development Tips

**Hot Reload:**
The `--reload` flag for uvicorn automatically restarts when code changes.

**Testing:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_planner_service.py
```

**Code Quality:**
```bash
# Format code
black backend/app backend/tests
isort backend/app backend/tests

# Lint
ruff check backend/app

# Type checking
mypy backend/app
```

For comprehensive development documentation, see [Development Guide](docs/development/DEVELOPMENT.md)

---

## Seestar Integration Only

### 5-Minute Workflow for Seestar S50 Users

If you just want to export observing plans for your Seestar S50 telescope:

#### Step 1: Generate Your Plan

1. Access Astro Planner: http://localhost:9247
2. Set your location
3. Select **Seestar S50** from telescope dropdown
4. Choose exposure time (10s recommended)
5. Set observing date
6. Click **"Generate Observing Plan"**

#### Step 2: Export for seestar_alp

1. Scroll to **"Export Plan"** section
2. Choose export method:
   - **📱 Share QR Code** - Scan with phone/tablet
   - **🚀 seestar_alp CSV** - Download CSV file
3. Save file as: `observing_plan_YYYY-MM-DD.csv`

#### Step 3: Import into seestar_alp

1. Open seestar_alp web interface (http://raspberrypi.local:5000)
2. Go to **"Scheduler"** tab
3. Click **"Import CSV"**
4. Select your downloaded CSV file
5. Verify targets loaded correctly

#### Step 4: Execute Your Session

1. Ensure Seestar S50 is connected and powered on
2. In seestar_alp, click **"Start Schedule"**
3. Monitor progress in seestar_alp interface
4. seestar_alp will automatically:
   - Slew to each target
   - Auto-focus
   - Image for specified duration
   - Advance to next target

### Complete Seestar Integration Guide

For detailed setup, optimal settings, and troubleshooting, see:
- **[Seestar Integration Guide](docs/seestar/SEESTAR_INTEGRATION.md)**

---

## Next Steps

### After Installation

1. **Configure Your Location**
   - Set accurate latitude, longitude, and elevation
   - Choose your IANA timezone

2. **Get Weather API Key**
   - Sign up at OpenWeatherMap (free tier is fine)
   - Add to configuration

3. **Generate Your First Plan**
   - Choose tonight's date
   - Select "Balanced" planning mode
   - Include galaxies, nebulae, and clusters

4. **Explore Features**
   - Try different planning modes
   - Adjust altitude constraints
   - Export to different formats

### Learn More

- **[User Guide](docs/user-guides/USAGE.md)** - Complete usage documentation
- **[API Documentation](docs/user-guides/API_USAGE.md)** - API endpoints and examples
- **[Configuration Reference](docs/CONFIGURATION.md)** - All environment variables
- **[Architecture](docs/architecture/ARCHITECTURE.md)** - System design
- **[Complete Documentation Index](docs/INDEX.md)** - All documentation

---

## Common Questions

### How do I update Astro Planner?

**Docker:**
```bash
git pull
docker-compose build
docker-compose up -d
```

**Native:**
```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
# Restart services
```

### How do I backup my data?

**Docker:**
```bash
# Backup database
docker exec astronomus-postgres pg_dump -U pg astro_planner > backup.sql

# Backup saved plans
docker exec astronomus cp -r /app/data ./backup-data
```

**Native:**
```bash
# Backup PostgreSQL database
pg_dump astro_planner > backup.sql

# Backup data directory
cp -r backend/data backup-data
```

### How do I change my location?

**Method 1: UI** (Recommended)
- Set location in the planning interface
- Astro Planner remembers your last used location

**Method 2: Environment Variables** (for default location)
```bash
# Edit .env file
DEFAULT_LAT=34.0522
DEFAULT_LON=-118.2437
DEFAULT_ELEVATION=71
DEFAULT_TIMEZONE=America/Los_Angeles
```

### How do I enable GPU acceleration?

**Requirements:**
- NVIDIA GPU with CUDA support
- NVIDIA Docker Runtime (Docker installations)
- CUDA 12.8+ drivers

**Docker:**
Already configured! Just ensure `runtime: nvidia` is in docker-compose.yml

**Native:**
```bash
# Install CuPy
pip install cupy-cuda12x

# Verify
python -c "import cupy; print(cupy.cuda.is_available())"
```

### How do I set up automatic daily planning?

**Included by default!** Astro Planner automatically generates a plan every day at noon.

Configure via environment variables:
```bash
DEFAULT_LAT=your_latitude
DEFAULT_LON=your_longitude
CELERY_TIMEZONE=America/Denver  # Your timezone
WEBHOOK_URL=https://your-webhook.com/api  # Optional notifications
```

See [Daily Planning Guide](DAILY_PLANNING.md) for details.

---

## Getting Help

### Documentation
- **[Complete Documentation Index](docs/INDEX.md)**
- **[Troubleshooting Guide](docs/development/TESTING_GUIDE.md)**

### Support
- **GitHub Issues**: https://github.com/irjudson/astronomus/issues
- **Discussions**: GitHub Discussions (for questions)

### Community
- Share your imaging results!
- Report bugs and feature requests
- Contribute improvements

---

**Ready to start planning your observations!** 🌌
