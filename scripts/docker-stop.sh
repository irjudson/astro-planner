#!/bin/bash
# Stop Astro Planner Docker services

set -e

echo "Stopping Astro Planner services..."

docker-compose down

echo ""
echo "Services stopped successfully!"
echo ""
echo "To remove volumes (WARNING: deletes data): docker-compose down -v"
echo ""
