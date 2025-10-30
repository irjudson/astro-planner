"""DSO catalog management service."""

import sqlite3
from pathlib import Path
from typing import List, Optional
from app.models import DSOTarget


class CatalogService:
    """Service for managing deep sky object catalog."""

    def __init__(self, db_path: str = None):
        """Initialize catalog service with SQLite database."""
        # Auto-detect database path
        if db_path is None:
            # Try Docker path first, then local dev path
            docker_path = Path("/app/data/catalogs.db")
            local_path = Path("backend/data/catalogs.db")
            if docker_path.exists():
                db_path = str(docker_path)
            else:
                db_path = str(local_path)

        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Ensure database file exists, create with default catalog if not."""
        db_file = Path(self.db_path)
        if not db_file.exists():
            # Database doesn't exist - try to create it
            db_file.parent.mkdir(parents=True, exist_ok=True)
            # Run import script to create database
            import subprocess
            import sys

            # Determine the correct path to the import script
            # In Docker, we're in /app, so scripts/ is directly accessible
            # Outside Docker, we might be in backend/ or root
            script_paths = [
                "scripts/import_catalog.py",  # Docker path
                "backend/scripts/import_catalog.py",  # Local dev path
            ]

            script_path = None
            for path in script_paths:
                if Path(path).exists():
                    script_path = path
                    break

            if not script_path:
                # Can't find import script, just create empty database
                print(f"Warning: Import script not found. Creating empty database at {self.db_path}")
                return

            try:
                subprocess.run([
                    sys.executable, script_path,
                    "--database", str(self.db_path)
                ], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to import catalog: {e}")
                print(f"Please run manually: python {script_path} --database {self.db_path}")

    def _db_row_to_target(self, row: tuple) -> DSOTarget:
        """Convert database row to DSOTarget model."""
        (id, catalog_name, catalog_number, common_name, ra_hours, dec_degrees,
         object_type, magnitude, surface_brightness, size_major_arcmin,
         size_minor_arcmin, constellation, created_at, updated_at) = row

        # Generate catalog ID (e.g., "M31", "NGC224", "IC434")
        # For Messier objects (stored with common_name like "M031"), use that as catalog_id
        if common_name and common_name.startswith('M') and common_name[1:].isdigit():
            # Convert M031 -> M31 by removing leading zeros
            messier_num = int(common_name[1:])
            catalog_id = f"M{messier_num}"
            name = catalog_id  # Use M31 as both catalog_id and name
        else:
            catalog_id = f"{catalog_name}{catalog_number}"
            # Use common name if available, otherwise generate from catalog
            name = common_name if common_name else catalog_id

        # Use major axis for size, default to 1.0 if None
        size_arcmin = size_major_arcmin if size_major_arcmin else 1.0

        # Generate description
        type_name = object_type.replace('_', ' ').title()
        description = f"{type_name}"
        if constellation:
            description += f" in {constellation}"

        # Default magnitude if None
        mag = magnitude if magnitude else 99.0

        return DSOTarget(
            name=name,
            catalog_id=catalog_id,
            object_type=object_type,
            ra_hours=ra_hours,
            dec_degrees=dec_degrees,
            magnitude=mag,
            size_arcmin=size_arcmin,
            description=description
        )

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        return conn

    def get_all_targets(self, limit: Optional[int] = None, offset: int = 0) -> List[DSOTarget]:
        """
        Get all targets in catalog.

        Args:
            limit: Maximum number of targets to return (None = all)
            offset: Number of targets to skip (for pagination)

        Returns:
            List of DSOTarget objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM dso_catalog ORDER BY magnitude ASC"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [self._db_row_to_target(row) for row in rows]

    def get_target_by_id(self, catalog_id: str) -> Optional[DSOTarget]:
        """
        Get a specific target by catalog ID.

        Args:
            catalog_id: Catalog identifier (e.g., "M31", "NGC224", "IC434")

        Returns:
            DSOTarget object or None if not found
        """
        # Parse catalog ID to extract catalog name and number
        # Handle formats: M31, NGC224, IC434
        catalog_id_upper = catalog_id.upper()

        conn = self._get_connection()
        cursor = conn.cursor()

        # For Messier objects, search by common_name (stored as M042, M031, etc.)
        if catalog_id_upper.startswith('M') and len(catalog_id_upper) > 1 and catalog_id_upper[1:].isdigit():
            # Pad the Messier number to 3 digits (M42 -> M042)
            messier_padded = f"M{int(catalog_id_upper[1:]):03d}"
            cursor.execute("""
                SELECT * FROM dso_catalog
                WHERE common_name = ?
            """, (messier_padded,))
        elif catalog_id_upper.startswith('NGC'):
            catalog_number = catalog_id_upper[3:]
            cursor.execute("""
                SELECT * FROM dso_catalog
                WHERE catalog_name = 'NGC' AND catalog_number = ?
            """, (catalog_number,))
        elif catalog_id_upper.startswith('IC'):
            catalog_number = catalog_id_upper[2:]
            cursor.execute("""
                SELECT * FROM dso_catalog
                WHERE catalog_name = 'IC' AND catalog_number = ?
            """, (catalog_number,))
        else:
            conn.close()
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._db_row_to_target(row)
        return None

    def filter_targets(
        self,
        object_types: Optional[List[str]] = None,
        min_magnitude: Optional[float] = None,
        max_magnitude: Optional[float] = None,
        constellation: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[DSOTarget]:
        """
        Filter targets by various criteria.

        Args:
            object_types: List of object types to include (None = all)
            min_magnitude: Minimum magnitude (brighter)
            max_magnitude: Maximum magnitude (fainter)
            constellation: Constellation name filter
            limit: Maximum number of results
            offset: Number of results to skip (for pagination)

        Returns:
            Filtered list of targets
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM dso_catalog WHERE 1=1"
        params = []

        if object_types and len(object_types) > 0:
            placeholders = ','.join('?' * len(object_types))
            query += f" AND object_type IN ({placeholders})"
            params.extend(object_types)

        if min_magnitude is not None:
            query += " AND magnitude >= ?"
            params.append(min_magnitude)

        if max_magnitude is not None:
            query += " AND magnitude <= ?"
            params.append(max_magnitude)

        if constellation:
            query += " AND constellation = ?"
            params.append(constellation)

        # Order by magnitude (brightest first)
        query += " ORDER BY magnitude ASC"

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._db_row_to_target(row) for row in rows]
