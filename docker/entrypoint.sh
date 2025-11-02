#!/bin/bash
set -e

# Initialize database if it doesn't exist
if [ ! -f /app/data/catalogs.db ]; then
    echo "Database not found. Initializing test database..."
    python scripts/init_test_db.py
    echo "Database initialized successfully."
else
    echo "Database already exists at /app/data/catalogs.db"
fi

# Execute the main command (start the server)
exec "$@"
