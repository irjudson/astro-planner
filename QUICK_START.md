# Astro Planner - Quick Start with Docker

## TL;DR

```bash
# 1. Stop any native services
./scripts/docker-clean.sh

# 2. Start Docker services
./scripts/docker-start.sh

# 3. Access the application
open http://localhost:9247
```

## What's Running?

After starting with Docker, you'll have:

- **Main API**: http://localhost:9247
- **Health Check**: http://localhost:9247/api/health
- **Redis**: localhost:6379 (internal to Docker network)
- **Celery Worker**: Background task processor

## Common Commands

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f astro-planner
docker-compose logs -f celery-worker

# Restart a service
docker-compose restart astro-planner

# Stop everything
./scripts/docker-stop.sh

# Or manually
docker-compose down
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 9247
lsof -i :9247

# Stop native services
./scripts/docker-clean.sh
```

### See Detailed Setup

For comprehensive documentation, see [DOCKER_SETUP.md](DOCKER_SETUP.md)

### Monitoring

Optional: Start Flower for Celery monitoring:

```bash
docker-compose --profile monitoring up -d flower
# Access at http://localhost:5555
```

## Development

To enable hot-reload for development, edit your `.env`:

```bash
RELOAD=True
```

Then restart:

```bash
docker-compose restart astro-planner
```
