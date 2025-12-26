# Automatic Daily Plan Generation

## Overview

The system automatically generates an observing plan every day at noon (local time) with the top 5 objects for that evening. Plans are saved with the naming convention `YYYY-MM-DD-plan`.

## How It Works

### Scheduling
- **Trigger Time**: Daily at 12:00 (noon) in configured timezone
- **Scheduler**: Celery Beat periodic task scheduler
- **Execution**: Background Celery worker processes the task

### Plan Generation Process

1. **Location**: Uses default location from environment variables
   - `DEFAULT_LAT`: Observer latitude
   - `DEFAULT_LON`: Observer longitude
   - `DEFAULT_ELEVATION`: Observer elevation in meters
   - `DEFAULT_TIMEZONE` / `CELERY_TIMEZONE`: Local timezone

2. **Observing Date**: Today's evening (the night following the current day)

3. **Planning Mode**: Quality mode constraints
   - Min altitude: 30°, Max altitude: 90°
   - Duration per target: 45-180 minutes
   - Minimum score threshold: 0.7
   - Object types: Galaxies, nebulae, clusters, planetary nebulae, supernovae remnants, comets

4. **Target Selection**:
   - Generates full plan using PlannerService
   - Ranks targets by composite score (visibility, weather, object quality)
   - Selects top 5 highest-scoring targets

5. **Plan Naming**:
   - Base name: `YYYY-MM-DD-plan`
   - If plan already exists, adds suffix: `-2`, `-3`, etc.
   - Example: `2024-12-25-plan`, `2024-12-25-plan-2`

6. **Storage**: Plan saved to database (SavedPlan model)

7. **Notifications**:
   - Logs plan creation to application logs
   - Optional webhook notification if `WEBHOOK_URL` configured

## Configuration

### Environment Variables

**Required:**
- `DEFAULT_LAT` - Observer latitude (default: 45.9183)
- `DEFAULT_LON` - Observer longitude (default: -111.5433)
- `DEFAULT_ELEVATION` - Observer elevation in meters (default: 1234)
- `CELERY_TIMEZONE` - Timezone for scheduling (default: America/Denver)

**Optional:**
- `WEBHOOK_URL` - HTTP endpoint for plan creation notifications
- `DEFAULT_LOCATION_NAME` - Friendly name for location (default: generated from coordinates)

### Docker Services

The feature requires two Docker services:

1. **celery-worker** - Executes tasks
   - Processes plan generation when triggered
   - Also handles image processing tasks

2. **celery-beat** - Schedules periodic tasks
   - Triggers daily plan generation at noon
   - Lightweight scheduler service

Both services are defined in `docker-compose.yml`.

## Deployment

### Start Services

```bash
# Build and start beat scheduler
docker-compose build celery-beat
docker-compose up -d celery-beat

# Verify beat scheduler is running
docker logs astro-planner-beat

# Verify worker is ready to process tasks
docker logs astro-planner-worker
```

### Verify Configuration

```bash
# Check beat scheduler configuration
docker exec astro-planner-beat python3 -c "
from app.tasks.celery_app import celery_app
print('Timezone:', celery_app.conf.timezone)
print('Schedule:', celery_app.conf.beat_schedule)
"

# Check registered tasks
docker exec astro-planner-worker python3 -c "
from app.tasks.celery_app import celery_app
tasks = [t for t in celery_app.tasks.keys() if not t.startswith('celery.')]
print('Registered tasks:', tasks)
"
```

## Manual Trigger

You can manually trigger plan generation for testing:

```bash
# Using Celery CLI
docker exec astro-planner-worker celery -A app.tasks.celery_app call generate_daily_plan

# Using Python
docker exec astro-planner-worker python3 -c "
from app.tasks.planning_tasks import generate_daily_plan_task
result = generate_daily_plan_task.delay()
print('Task ID:', result.id)
"
```

## Webhook Notifications

When `WEBHOOK_URL` is configured, the system sends HTTP POST notifications when plans are created.

### Webhook Payload

```json
{
  "event": "plan_created",
  "timestamp": "2024-12-25T12:00:00Z",
  "plan": {
    "id": 123,
    "name": "2024-12-25-plan",
    "observing_date": "2024-12-25",
    "target_count": 5,
    "targets": ["M31", "M42", "M81", "NGC 2244", "NGC 7000"],
    "session_start": "2024-12-25T18:30:00-07:00",
    "session_end": "2024-12-26T06:15:00-07:00"
  }
}
```

### Webhook Configuration

```yaml
# docker-compose.yml
environment:
  - WEBHOOK_URL=https://your-server.com/api/webhooks/astro-plans
```

The webhook service includes:
- 5-second timeout
- 2 retries with exponential backoff
- Error logging (doesn't fail task if webhook fails)

## Monitoring

### Check Logs

```bash
# Beat scheduler logs (scheduling events)
docker logs -f astro-planner-beat

# Worker logs (task execution)
docker logs -f astro-planner-worker

# Filter for daily plan events
docker logs astro-planner-worker 2>&1 | grep "Daily plan"
```

### Example Log Output

```
INFO: Daily plan generation started for location: Three Forks, MT (45.92, -111.54)
INFO: Generating plan for observing date: 2024-12-25
INFO: Plan name: 2024-12-25-plan
INFO: Calling PlannerService to generate plan...
INFO: Plan generated with 8 targets
INFO: Limited to top 5 targets by score
INFO: Selected targets: M31, M42, M81, NGC 2244, NGC 7000
INFO: Saved plan ID 123 to database
INFO: Daily plan generation complete: '2024-12-25-plan' with 5 targets: M31, M42, M81, NGC 2244, NGC 7000
```

## Accessing Generated Plans

Plans are accessible through the API:

```bash
# List all saved plans
curl http://localhost:9247/api/plans/

# Get specific plan
curl http://localhost:9247/api/plans/{plan_id}

# Get plan by name (requires filtering in application)
curl http://localhost:9247/api/plans/ | jq '.[] | select(.name == "2024-12-25-plan")'
```

## Schedule Details

The Celery Beat schedule is configured in `backend/app/tasks/celery_app.py`:

```python
celery_app.conf.beat_schedule = {
    "generate-daily-plan": {
        "task": "generate_daily_plan",
        "schedule": crontab(hour=12, minute=0),  # Daily at noon
        "args": (),
    },
}
```

The schedule runs in the configured timezone (`CELERY_TIMEZONE`), not UTC.

## Troubleshooting

### Beat Scheduler Not Starting

```bash
# Check logs for errors
docker logs astro-planner-beat

# Verify Redis connection
docker exec astro-planner-beat python3 -c "
from app.tasks.celery_app import celery_app
print(celery_app.connection().as_uri())
"
```

### Tasks Not Executing

```bash
# Check worker is connected to beat
docker exec astro-planner-worker celery -A app.tasks.celery_app inspect active

# Check for task in queue
docker exec astro-planner-beat python3 -c "
from celery import Celery
app = Celery(broker='redis://:buffalo-jump@redis:6379/1')
print('Queued tasks:', app.control.inspect().scheduled())
"
```

### Wrong Timezone

```bash
# Check configured timezone
docker exec astro-planner-beat python3 -c "
from app.tasks.celery_app import celery_app
print('Configured timezone:', celery_app.conf.timezone)
"

# Update in docker-compose.yml
environment:
  - CELERY_TIMEZONE=Your/Timezone  # e.g., America/Los_Angeles
```

### Plan Not Created

Check logs for errors:

```bash
docker logs astro-planner-worker 2>&1 | grep -A 20 "Daily plan generation failed"
```

Common issues:
- Database connection errors
- Invalid location coordinates
- No targets visible at the observing date
- Weather service unavailable

### Webhook Failing

Webhook failures don't prevent plan creation, but check logs:

```bash
docker logs astro-planner-worker 2>&1 | grep webhook
```

Common issues:
- Invalid webhook URL
- Webhook endpoint timeout (>5 seconds)
- Network connectivity issues

## Files Modified/Created

### New Files
- `backend/app/tasks/planning_tasks.py` - Daily plan generation task
- `backend/app/services/webhook_service.py` - Webhook notifications
- `DAILY_PLANNING.md` - This documentation

### Modified Files
- `backend/app/tasks/celery_app.py` - Added beat schedule configuration
- `backend/app/tasks/__init__.py` - Registered planning tasks
- `docker-compose.yml` - Added celery-beat service and worker environment variables

## Integration with Telescope

Future enhancement: The generated plans can be automatically loaded and executed by the telescope control system.

## Related Documentation

- [SEESTAR_PROCESSING.md](SEESTAR_PROCESSING.md) - Image post-processing pipeline
- [GPU_MPS_CONFIG.md](GPU_MPS_CONFIG.md) - GPU configuration for processing
- API documentation for plan management endpoints
