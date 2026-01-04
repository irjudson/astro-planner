# Docker Setup Guide

This guide explains how to run Astro Planner entirely in Docker containers, keeping your native system clean.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Docker Runtime (optional, for GPU-accelerated processing)

## Quick Start

### 1. Environment Configuration

Create a `.env` file in the project root (or use `backend/.env`):

```bash
# Required
OPENWEATHERMAP_API_KEY=your_api_key_here

# Optional location defaults
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME=Three Forks, MT

# FITS directory (absolute path on host)
FITS_DIR=/path/to/your/fits/files
```

### 2. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f astronomus
```

### 3. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Services

### Main Services

1. **astronomus** - Main API server
   - Port: 9247
   - Health check: http://localhost:9247/api/health
   - Access UI: http://localhost:9247

2. **redis** - Message broker for Celery
   - Port: 6379 (exposed for debugging)
   - Persistent storage via volume

3. **celery-worker** - Background task processor
   - Processes FITS files and long-running tasks
   - Connects to Docker socket for spawning processing containers

### Optional Services

4. **flower** - Celery monitoring UI
   - Port: 5555
   - Access: http://localhost:5555
   - Enable with: `docker-compose --profile monitoring up -d`

## Volume Management

### Data Persistence

The following data is persisted in Docker volumes:

- `/app/data` - SQLite databases and application data
- `redis-data` - Redis persistence data

### FITS Files

FITS files are mounted from your host system:

```yaml
volumes:
  - ${FITS_DIR:-./fits}:/fits:rw
```

Set `FITS_DIR` in your `.env` file to point to your FITS directory.

## Common Operations

### Rebuild After Code Changes

```bash
docker-compose build
docker-compose up -d
```

### View Service Status

```bash
docker-compose ps
```

### Execute Commands in Containers

```bash
# Run tests
docker-compose exec astronomus pytest

# Access Python shell
docker-compose exec astronomus python

# Check database
docker-compose exec astronomus sqlite3 /app/data/astro_planner.db
```

### Check Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f astronomus
docker-compose logs -f celery-worker

# Last N lines
docker-compose logs --tail=100 astronomus
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart astronomus
```

## Clean Native System

If you have services running natively on your system, stop them before using Docker:

### Stop Native Processes

```bash
# Find and kill native processes
pkill -f "uvicorn app.main:app"
pkill -f "celery.*app.tasks"

# Stop native Redis (if running)
sudo systemctl stop redis-server
# or
redis-cli shutdown
```

### Check for Conflicts

```bash
# Check if ports are in use
netstat -tulpn | grep 9247  # Main app
netstat -tulpn | grep 6379  # Redis
netstat -tulpn | grep 5555  # Flower
```

## Troubleshooting

### Port Conflicts

If ports are already in use, either:
1. Stop native services (see above)
2. Change ports in `docker-compose.yml`:

```yaml
ports:
  - "9248:9247"  # Host:Container
```

### Database Issues

If database initialization fails:

```bash
# Remove existing database
rm -rf data/*.db

# Restart services
docker-compose restart astronomus
```

### View Container Logs

```bash
# Detailed logs
docker logs astronomus
docker logs astronomus-celery
docker logs astronomus-redis
```

### Access Container Shell

```bash
docker-compose exec astronomus /bin/bash
```

### Network Issues

Ensure containers can communicate:

```bash
# Check network
docker network inspect astronomus_astronomus-network

# Test connectivity
docker-compose exec astronomus ping redis
```

### GPU Support for Processing

For GPU-accelerated processing, ensure NVIDIA Docker runtime is installed:

```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

## Development Mode

For development with hot-reload:

1. Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  astronomus:
    volumes:
      - ./backend:/app:rw  # Mount source code
    environment:
      - RELOAD=True
    command: python -m uvicorn app.main:app --host 0.0.0.0 --port 9247 --reload
```

2. Start services:

```bash
docker-compose up -d
```

## Production Deployment

For production:

1. Remove debug features:
   - Set `RELOAD=False`
   - Remove volume mounts for source code
   - Use specific image tags instead of `latest`

2. Add SSL/TLS termination (nginx, Traefik, etc.)

3. Use secrets management:
   - Docker secrets
   - External secrets manager (Vault, AWS Secrets Manager)

4. Configure resource limits in `docker-compose.yml`:

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

## Monitoring

### Health Checks

Services include health checks:

```bash
# Check health status
docker-compose ps
```

### Celery Monitoring with Flower

```bash
# Start Flower
docker-compose --profile monitoring up -d flower

# Access at http://localhost:5555
```

### Logs

```bash
# Follow logs
docker-compose logs -f

# Export logs
docker-compose logs > astronomus.log
```

## Backup and Restore

### Backup Data

```bash
# Backup volumes
docker run --rm -v astronomus_redis-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup.tar.gz -C /data .

# Backup database
docker-compose exec astronomus sqlite3 /app/data/astro_planner.db .dump > backup.sql
```

### Restore Data

```bash
# Restore volumes
docker run --rm -v astronomus_redis-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/redis-backup.tar.gz -C /data

# Restore database
cat backup.sql | docker-compose exec -T astronomus \
  sqlite3 /app/data/astro_planner.db
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
