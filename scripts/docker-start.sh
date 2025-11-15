#!/bin/bash
# Start Astro Planner Docker services

set -e

echo "Starting Astro Planner services..."

# Check if .env file exists
if [ ! -f "backend/.env" ] && [ ! -f ".env" ]; then
    echo "WARNING: No .env file found. Creating a template..."
    cat > .env << 'EOF'
# OpenWeatherMap API Key (required for weather data)
OPENWEATHERMAP_API_KEY=your_api_key_here

# Location defaults
DEFAULT_LAT=45.9183
DEFAULT_LON=-111.5433
DEFAULT_ELEVATION=1234
DEFAULT_TIMEZONE=America/Denver
DEFAULT_LOCATION_NAME=Three Forks, MT

# FITS directory (absolute path on host)
FITS_DIR=/path/to/your/fits/files
EOF
    echo "Created .env template. Please edit it with your settings."
    exit 1
fi

# Stop any native services that might conflict
echo "Checking for conflicting native services..."
if lsof -Pi :9247 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "WARNING: Port 9247 is in use. Please stop the conflicting service."
    lsof -Pi :9247 -sTCP:LISTEN
    exit 1
fi

if lsof -Pi :6379 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "WARNING: Port 6379 (Redis) is in use by another process."
    echo "This might be okay if it's just the Docker container."
fi

# Build and start services
echo "Building Docker images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

echo ""
echo "Services started successfully!"
echo ""
echo "Main API:    http://localhost:9247"
echo "Health:      http://localhost:9247/api/health"
echo ""
echo "View logs:   docker-compose logs -f"
echo "Stop:        docker-compose down"
echo ""
