#!/bin/bash
# Clean up native system processes for Astro Planner

set -e

echo "Cleaning up native Astro Planner processes..."

# Find and kill uvicorn processes for astro-planner
echo "Stopping native API server..."
pkill -f "uvicorn app.main:app" || echo "No native API server running"

# Find and kill celery processes for astro-planner
echo "Stopping native Celery workers..."
pkill -f "celery.*app.tasks.celery_app" || echo "No native Celery workers running"

# Note: We don't stop Redis as it might be used by other services
echo ""
echo "Native processes cleaned up!"
echo ""
echo "Note: Native Redis was not stopped as it may be used by other services."
echo "If you want to stop it: sudo systemctl stop redis-server"
echo ""
echo "Now you can start Docker services with: ./scripts/docker-start.sh"
echo ""
