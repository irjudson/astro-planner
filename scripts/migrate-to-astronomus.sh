#!/bin/bash
# Migration script to rename astronomus databases to astronomus

set -e

echo "🔭 Migrating databases to Astronomus..."

# Stop all astronomus containers
echo "Stopping containers..."
docker-compose down

# Connect to PostgreSQL and rename databases
echo "Renaming databases..."
docker exec -i postgres psql -U pg << 'EOF'
-- Terminate existing connections
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname IN ('astronomus', 'test_astro_planner')
  AND pid <> pg_backend_pid();

-- Rename databases
ALTER DATABASE "astronomus" RENAME TO "astronomus";
ALTER DATABASE "test_astro_planner" RENAME TO "test_astronomus";

\l
EOF

echo "✅ Database migration complete!"
echo ""
echo "Next steps:"
echo "1. Update docker-compose.yml (automated)"
echo "2. Update alembic.ini (automated)"
echo "3. Restart containers with new configuration"
