#!/bin/bash
set -e

# Ensure the data directory exists and is writable
mkdir -p /app/data

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "Database migrations complete."

# Execute the main command (start the server)
exec "$@"
