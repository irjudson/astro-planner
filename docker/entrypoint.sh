#!/bin/bash
set -e

# Ensure the data directory exists and is writable
mkdir -p /app/data

# Initialize database if it doesn't exist
if [ ! -f /app/data/astro_planner.db ]; then
    echo "Database not found. Running Alembic migrations..."
    alembic upgrade head
    echo "Database migrations applied successfully."

    echo "Importing catalog data..."
    python -m scripts.import_catalog --database /app/data/astro_planner.db
    echo "Catalog data imported successfully."
else
    echo "Database already exists at /app/data/astro_planner.db"
fi

# Execute the main command (start the server)
exec "$@"
