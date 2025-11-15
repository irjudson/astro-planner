# Development Guide

This guide explains how to develop Astro Planner locally, with or without Docker.

---

## Native Development (Recommended)

Running natively gives you:
- ✅ Instant code reloading (no container rebuilds)
- ✅ Direct debugging with breakpoints
- ✅ Faster iteration cycles
- ✅ Full access to logs
- ✅ No bytecode caching issues

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv redis-server

# macOS
brew install python redis
brew services start redis
```

### Quick Start

**Option 1: Background mode (recommended for development)**

```bash
# First time setup
chmod +x dev-simple.sh dev-stop.sh
./dev-simple.sh

# View logs
tail -f logs/api.log
tail -f logs/celery.log

# Stop services
./dev-stop.sh
```

**Option 2: Multiple terminals (better for debugging)**

Terminal 1 - Celery Worker:
```bash
source venv/bin/activate
cd backend
export REDIS_URL="redis://localhost:6379/1"
celery -A app.tasks.celery_app worker --loglevel=info
```

Terminal 2 - FastAPI Server:
```bash
source venv/bin/activate
cd backend
export REDIS_URL="redis://localhost:6379/1"
uvicorn app.main:app --host 127.0.0.1 --port 9247 --reload
```

Terminal 3 - Optional: Flower (monitoring):
```bash
source venv/bin/activate
cd backend
export REDIS_URL="redis://localhost:6379/1"
celery -A app.tasks.celery_app flower --port=5555
```

### Environment Configuration

Create `backend/.env`:
```bash
OPENWEATHERMAP_API_KEY=your_key_here
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME=Your Location
FITS_DIR=./fits
```

### Testing

```bash
# Run tests
cd backend
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Run integration test
cd ..
python3 test_processing.py
```

### Debugging

**With breakpoints:**
```python
# In your code
import pdb; pdb.set_trace()
```

Run the service in foreground to see the debugger.

**With VS Code:**

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "127.0.0.1",
        "--port", "9247"
      ],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "REDIS_URL": "redis://localhost:6379/1"
      }
    },
    {
      "name": "Celery Worker",
      "type": "python",
      "request": "launch",
      "module": "celery",
      "args": [
        "-A", "app.tasks.celery_app",
        "worker",
        "--loglevel=info"
      ],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "REDIS_URL": "redis://localhost:6379/1"
      }
    }
  ]
}
```

---

## Docker Development

Use Docker when you need:
- Exact production environment replication
- Complex system dependencies
- Deployment testing

### Quick Start

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Restart after code changes
docker-compose restart astro-planner

# Stop everything
docker-compose down
```

### Limitations

- ⚠️ Code changes require container restart
- ⚠️ Python bytecode caching can cause stale code
- ⚠️ Slower iteration cycles
- ⚠️ Harder to debug with breakpoints

### Force Clean Rebuild

If you see stale code or weird behavior:

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## Switching Between Native and Docker

**Stop Docker services:**
```bash
docker-compose down
```

**Stop native services:**
```bash
./dev-stop.sh
# or
pkill -f 'celery.*app.tasks'
pkill -f 'uvicorn.*app.main'
```

**Important:** Both use the same database (`data/astro_planner.db`) and FITS directory (`./fits`), so your data is preserved when switching.

---

## Redis Database Isolation

This project uses Redis database `/1` to avoid conflicts with other projects.

If you need to clear the queue:
```bash
redis-cli -n 1 FLUSHDB
```

View queue contents:
```bash
# Check queue length
redis-cli -n 1 LLEN celery

# View all keys
redis-cli -n 1 KEYS '*'
```

---

## File Structure

```
astro-planner/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI endpoints
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   ├── tasks/        # Celery tasks
│   │   └── main.py       # FastAPI app
│   ├── tests/            # Test suite
│   └── requirements.txt
├── frontend/
│   └── index.html        # Web UI
├── data/                 # SQLite database
├── fits/                 # FITS files
├── logs/                 # Native dev logs
├── venv/                 # Python virtual env (native dev)
├── dev-simple.sh         # Start native dev (background)
├── dev-stop.sh           # Stop native dev
├── docker-compose.yml    # Docker setup
└── test_processing.py    # Integration test
```

---

## Common Tasks

### Add a new API endpoint

1. Edit `backend/app/api/routes.py` or relevant router
2. If using native dev: Code reloads automatically
3. If using Docker: `docker-compose restart astro-planner`
4. Test at http://localhost:9247/docs

### Add a new Celery task

1. Edit `backend/app/tasks/processing_tasks.py`
2. Add `@celery_app.task` decorator
3. Restart Celery worker:
   - Native: Ctrl+C and restart
   - Docker: `docker-compose restart celery-worker`

### Change database schema

1. Edit models in `backend/app/models/`
2. Native dev:
   ```bash
   cd backend
   python3 -c "from app.database import engine; from app.models.processing_models import Base; Base.metadata.create_all(bind=engine)"
   ```
3. Docker: Restart containers

### View Celery tasks

Start Flower:
```bash
# Native
cd backend
celery -A app.tasks.celery_app flower --port=5555

# Docker
docker-compose --profile monitoring up -d flower
```

Visit: http://localhost:5555

---

## Troubleshooting

### "Address already in use" (port 9247)

```bash
# Find process
lsof -i :9247

# Kill it
kill -9 <PID>
```

### Celery tasks not running

```bash
# Check Redis connection
redis-cli -n 1 ping

# Check worker is running
ps aux | grep celery

# Check queue
redis-cli -n 1 LLEN celery
```

### Database locked

```bash
# Stop all services first
./dev-stop.sh
docker-compose down

# Then restart one or the other
```

### Import errors

```bash
# Reinstall dependencies
source venv/bin/activate
cd backend
pip install -r requirements.txt -r requirements-processing.txt
```

---

## Performance

**Native development:**
- API startup: ~2 seconds
- Code reload: <1 second
- Test suite: ~5 seconds

**Docker development:**
- Container startup: ~10 seconds
- Code reload: Need restart (~5 seconds)
- Test suite: ~8 seconds

---

## Recommended Workflow

For **feature development**: Use native mode
```bash
./dev-simple.sh
# Make changes
# Test at http://localhost:9247
./dev-stop.sh
```

For **deployment testing**: Use Docker
```bash
docker-compose up -d
# Test production-like environment
docker-compose down
```

For **integration testing**: Either works
```bash
python3 test_processing.py
```

---

## Next Steps

- Read [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing strategies
- Read [PROCESSING_DESIGN.md](PROCESSING_DESIGN.md) for processing pipeline
- Read [MOSAIC_AND_STACKING_PLAN.md](MOSAIC_AND_STACKING_PLAN.md) for future features

---

**Last Updated:** 2025-11-07
