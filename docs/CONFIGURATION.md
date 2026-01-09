# Configuration Reference

**Last Updated:** 2025-12-25

This document consolidates all configuration options for Astro Planner, including environment variables, configuration files, and deployment settings.

## Table of Contents

- [Environment Variables](#environment-variables)
  - [Required Variables](#required-variables)
  - [Database Configuration](#database-configuration)
  - [Location Defaults](#location-defaults)
  - [Weather Services](#weather-services)
  - [Daily Planning](#daily-planning)
  - [GPU Processing](#gpu-processing)
  - [Network Configuration](#network-configuration)
- [Configuration Files](#configuration-files)
- [Docker Configuration](#docker-configuration)

---

## Environment Variables

### Required Variables

These variables are required for the application to function:

| Variable | Description | Example | Used By |
|----------|-------------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/dbname` | API, Worker, Beat |
| `REDIS_URL` | Redis connection string | `redis://:password@host:6379/1` | API, Worker, Beat, Flower |
| `OPENWEATHERMAP_API_KEY` | OpenWeatherMap API key for weather forecasts | `abc123def456...` | API server |

**Note:** For Docker deployments, these are pre-configured in `docker-compose.yml`. For native installations, set them in `.env` or export them.

---

### Database Configuration

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | (required) | API, Worker, Beat |
| `TEST_DATABASE_URL` | PostgreSQL connection for tests | (required for tests) | Test suite |

**Examples:**
```bash
# Docker deployment
DATABASE_URL=postgresql://pg:buffalo-jump@postgres:5432/astronomus
TEST_DATABASE_URL=postgresql://pg:buffalo-jump@postgres:5432/test_astro_planner

# Native deployment
DATABASE_URL=postgresql://localhost:5432/astro_planner
TEST_DATABASE_URL=postgresql://localhost:5432/test_astro_planner
```

---

### Location Defaults

These variables set the default observer location for automated planning:

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `DEFAULT_LAT` | Observer latitude (degrees, -90 to 90) | `45.9183` | API, Worker, Beat |
| `DEFAULT_LON` | Observer longitude (degrees, -180 to 180) | `-111.5433` | API, Worker, Beat |
| `DEFAULT_ELEVATION` | Observer elevation (meters) | `1234` | API, Worker, Beat |
| `DEFAULT_TIMEZONE` | IANA timezone identifier | `America/Denver` | Worker, Beat |
| `DEFAULT_LOCATION_NAME` | Friendly location name | (generated from coords) | Worker, Beat |

**Example:**
```bash
# Three Forks, Montana (default)
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME="Three Forks, MT"

# Los Angeles, California
DEFAULT_LAT=34.0522
DEFAULT_LON=-118.2437
DEFAULT_ELEVATION=71
DEFAULT_TIMEZONE=America/Los_Angeles
DEFAULT_LOCATION_NAME="Los Angeles, CA"
```

---

### Weather Services

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `OPENWEATHERMAP_API_KEY` | API key for OpenWeatherMap | (required) | API server |

**Getting an API key:**
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Generate a free API key
3. Add to `.env` file

The application also uses 7Timer (no API key required) for astronomical seeing forecasts.

---

### Daily Planning

Configuration for automatic daily plan generation (runs at noon):

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `CELERY_TIMEZONE` | Timezone for task scheduling | `America/Denver` | Beat scheduler |
| `WEBHOOK_URL` | HTTP endpoint for plan notifications | (none) | Worker |

**Schedule:** Daily at 12:00 noon in the configured `CELERY_TIMEZONE`

**Webhook Payload Example:**
```json
{
  "event": "plan_created",
  "timestamp": "2024-12-25T12:00:00Z",
  "plan": {
    "id": 123,
    "name": "2024-12-25-plan",
    "observing_date": "2024-12-25",
    "target_count": 5,
    "targets": ["M31", "M42", "M81", "NGC 2244", "NGC 7000"]
  }
}
```

**Example:**
```bash
CELERY_TIMEZONE=America/Los_Angeles
WEBHOOK_URL=https://your-server.com/api/webhooks/astro-plans
```

---

### GPU Processing

Configuration for GPU-accelerated image processing with NVIDIA CUDA:

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `NVIDIA_VISIBLE_DEVICES` | Which GPUs to expose to container | `all` | Worker (Docker only) |
| `NVIDIA_DRIVER_CAPABILITIES` | NVIDIA driver capabilities | `compute,utility` | Worker (Docker only) |
| `CUDA_MPS_PIPE_DIRECTORY` | MPS control socket directory | `/tmp/nvidia-mps` | Worker (Docker only) |
| `CUDA_MPS_LOG_DIRECTORY` | MPS logging directory | `/tmp/nvidia-mps` | Worker (Docker only) |

**Requirements:**
- NVIDIA GPU with CUDA support (Compute Capability 5.0+)
- NVIDIA Driver 450.80.02+ (Linux), 452.39+ (Windows)
- NVIDIA Container Toolkit (for Docker)
- CUDA 12.8.0
- CuPy (installed automatically)

**MPS (Multi-Process Service):**
- Allows multiple Celery workers to share GPU
- Must be running on host system (Docker deployments)
- Improves GPU utilization for parallel processing

**Verification:**
```bash
# Check GPU access in container
docker exec astronomus-worker nvidia-smi

# Check CuPy installation
docker exec astronomus-worker python3 -c "import cupy; print(cupy.__version__)"
```

**Fallback:** If GPU is unavailable, processing automatically falls back to CPU (NumPy).

---

### Network Configuration

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `HOST` | API server bind address | `0.0.0.0` | API server |
| `PORT` | API server port | `9247` | API server |
| `RELOAD` | Enable auto-reload (development) | `False` | API server |

**Production:**
```bash
HOST=0.0.0.0
PORT=9247
RELOAD=False
```

**Development:**
```bash
HOST=127.0.0.1
PORT=9247
RELOAD=True
```

---

### FITS Directory

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `FITS_DIR` | Path to FITS files directory | `/fits` (Docker)<br>`./fits` (native) | API, Worker |

**Docker:**
```yaml
# docker-compose.yml
volumes:
  - /mnt/seestar-s50:/fits:rw  # Mount Seestar network share
```

**Native:**
```bash
export FITS_DIR=/path/to/your/fits/files
```

---

## Configuration Files

### alembic.ini

Database migration configuration.

**Key settings:**
```ini
[alembic]
sqlalchemy.url = postgresql://user:pass@host:5432/dbname

# Set this from environment variable instead:
# sqlalchemy.url =
```

**Usage:**
```bash
# Use DATABASE_URL environment variable
alembic upgrade head

# Or specify explicitly
alembic -c alembic.ini upgrade head
```

---

### pytest.ini

Test suite configuration.

**Key settings:**
```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

---

### docker-compose.yml

Docker services configuration. See [Docker Configuration](#docker-configuration) section below.

---

## Docker Configuration

### Services

The application runs as multiple Docker services:

| Service | Port | Purpose |
|---------|------|---------|
| `astronomus` | 9247 | Main API server |
| `celery-worker` | - | Background task processor |
| `celery-beat` | - | Periodic task scheduler |
| `flower` | 5555 | Celery monitoring UI (optional) |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis message broker |

---

### Service Configuration

**astronomus (API server):**
```yaml
ports:
  - "9247:9247"
environment:
  - DATABASE_URL=postgresql://pg:buffalo-jump@postgres:5432/astronomus
  - REDIS_URL=redis://:buffalo-jump@redis:6379/1
  - OPENWEATHERMAP_API_KEY=${OPENWEATHERMAP_API_KEY}
  - DEFAULT_LAT=${DEFAULT_LAT:-45.9183}
  - DEFAULT_LON=${DEFAULT_LON:--111.5433}
  - FITS_DIR=/fits
volumes:
  - /mnt/seestar-s50:/fits:ro
```

**celery-worker (Background processor with GPU):**
```yaml
runtime: nvidia  # Enables GPU access
environment:
  - REDIS_URL=redis://:buffalo-jump@redis:6379/1
  - DATABASE_URL=postgresql://pg:buffalo-jump@postgres:5432/astronomus
  - FITS_DIR=/fits
  - NVIDIA_VISIBLE_DEVICES=all
  - CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
  - DEFAULT_LAT=${DEFAULT_LAT:-45.9183}
  - DEFAULT_LON=${DEFAULT_LON:--111.5433}
  - CELERY_TIMEZONE=${CELERY_TIMEZONE:-America/Denver}
  - WEBHOOK_URL=${WEBHOOK_URL:-}
volumes:
  - /mnt/seestar-s50:/fits:rw
  - /tmp/nvidia-mps:/tmp/nvidia-mps  # MPS socket for GPU sharing
```

**celery-beat (Scheduler for daily plans):**
```yaml
environment:
  - REDIS_URL=redis://:buffalo-jump@redis:6379/1
  - DATABASE_URL=postgresql://pg:buffalo-jump@postgres:5432/astronomus
  - CELERY_TIMEZONE=${CELERY_TIMEZONE:-America/Denver}
  - WEBHOOK_URL=${WEBHOOK_URL:-}
```

---

### Resource Limits (Production)

Add resource limits in production:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

---

### Networks

```yaml
networks:
  shared-infra:
    external: true
    name: shared-infra
```

All services communicate via the `shared-infra` Docker network.

---

## Configuration Examples

### Minimal Setup (Docker)

**.env file:**
```bash
OPENWEATHERMAP_API_KEY=your_api_key_here
```

**Run:**
```bash
docker-compose up -d
```

---

### Custom Location (Docker)

**.env file:**
```bash
OPENWEATHERMAP_API_KEY=your_api_key_here
DEFAULT_LAT=34.0522
DEFAULT_LON=-118.2437
DEFAULT_ELEVATION=71
DEFAULT_TIMEZONE=America/Los_Angeles
DEFAULT_LOCATION_NAME="Los Angeles, CA"
CELERY_TIMEZONE=America/Los_Angeles
```

---

### With Webhook Notifications

**.env file:**
```bash
OPENWEATHERMAP_API_KEY=your_api_key_here
WEBHOOK_URL=https://your-server.com/api/webhooks/astro-plans
```

---

### Native Installation

**Shell exports:**
```bash
export DATABASE_URL="postgresql://localhost:5432/astro_planner"
export REDIS_URL="redis://localhost:6379/1"
export OPENWEATHERMAP_API_KEY="your_api_key_here"
export DEFAULT_LAT="45.9183"
export DEFAULT_LON="-111.5433"
export DEFAULT_ELEVATION="1234"
export DEFAULT_TIMEZONE="America/Denver"
export CELERY_TIMEZONE="America/Denver"
export FITS_DIR="/path/to/fits/files"
```

---

## Troubleshooting

### Missing Required Variables

**Symptom:** Application fails to start with "Environment variable not set"

**Solution:** Check `.env` file or export required variables:
```bash
# Check what's set
env | grep -E "(DATABASE_URL|REDIS_URL|OPENWEATHERMAP_API_KEY)"
```

---

### Wrong Timezone

**Symptom:** Daily plans generated at wrong time

**Solution:** Set `CELERY_TIMEZONE` to your local timezone:
```bash
CELERY_TIMEZONE=America/Los_Angeles  # Pacific Time
CELERY_TIMEZONE=America/New_York     # Eastern Time
CELERY_TIMEZONE=Europe/London        # GMT/BST
```

**Verify:**
```bash
docker exec astronomus-beat python3 -c "
from app.tasks.celery_app import celery_app
print('Configured timezone:', celery_app.conf.timezone)
"
```

---

### GPU Not Available

**Symptom:** Processing fails with "CUDA not available" or falls back to CPU

**Check:**
```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Check worker GPU access
docker exec astronomus-worker nvidia-smi

# Verify CuPy
docker exec astronomus-worker python3 -c "import cupy; print(cupy.cuda.is_available())"
```

---

### Database Connection Refused

**Symptom:** "Connection refused" or "could not connect to server"

**Check:**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Test connection
docker exec astronomus psql $DATABASE_URL -c "SELECT 1;"
```

---

## Related Documentation

- [Docker Setup Guide](development/DOCKER_SETUP.md) - Docker deployment details
- [Development Guide](development/DEVELOPMENT.md) - Native installation
- [Daily Planning Guide](../DAILY_PLANNING.md) - Automatic plan generation
- [GPU Configuration](../GPU_MPS_CONFIG.md) - GPU acceleration setup
- [User Guide](user-guides/USAGE.md) - Using the application

---

## Environment Variable Summary

Quick reference of all variables:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://:pass@host:6379/1
OPENWEATHERMAP_API_KEY=your_key_here

# Location (optional, defaults shown)
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME="Three Forks, MT"

# Scheduling (optional, defaults shown)
CELERY_TIMEZONE=America/Denver
WEBHOOK_URL=

# Network (optional, defaults shown)
HOST=0.0.0.0
PORT=9247
RELOAD=False

# Files (optional, defaults shown)
FITS_DIR=/fits

# GPU (Docker only, defaults shown)
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps
CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps

# Testing (optional)
TEST_DATABASE_URL=postgresql://user:pass@host:5432/test_dbname
```
