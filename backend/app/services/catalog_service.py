"""DSO catalog management service."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import DSOTarget
from app.models.catalog_models import ConstellationName, DSOCatalog


class CatalogService:
    """Service for managing deep sky object catalog."""

    def __init__(self, db: Session):
        """Initialize catalog service with database session."""
        self.db = db

    def _db_row_to_target(self, dso: DSOCatalog) -> DSOTarget:
        """Convert database model to DSOTarget."""
        # Generate catalog ID (e.g., "M31", "NGC224", "IC434", "C80")
        # For Messier objects (stored with common_name like "M031"), use that as catalog_id
        if dso.common_name and dso.common_name.startswith("M") and dso.common_name[1:].isdigit():
            # Convert M031 -> M31 by removing leading zeros
            messier_num = int(dso.common_name[1:])
            catalog_id = f"M{messier_num}"
            name = catalog_id  # Use M31 as both catalog_id and name
        elif dso.caldwell_number:
            # Prefer Caldwell designation if available
            catalog_id = f"C{dso.caldwell_number}"
            # Use common name if available, otherwise use Caldwell designation
            name = dso.common_name if dso.common_name else catalog_id
        else:
            catalog_id = f"{dso.catalog_name}{dso.catalog_number}"
            # Use common name if available, otherwise generate from catalog
            name = dso.common_name if dso.common_name else catalog_id

        # Use major axis for size, default to 1.0 if None
        size_arcmin = dso.size_major_arcmin if dso.size_major_arcmin else 1.0

        # Default magnitude if None
        mag = dso.magnitude if dso.magnitude else 99.0

        # Generate description
        type_name = dso.object_type.replace("_", " ").title()
        # Look up full constellation name
        full_constellation = self._get_constellation_full_name(dso.constellation) if dso.constellation else None
        description = f"{type_name} in {full_constellation}" if full_constellation else type_name

        # Add common name if available and different from Messier/catalog designation
        if dso.common_name and not (dso.common_name.startswith("M") and dso.common_name[1:].isdigit()):
            description += f" - {dso.common_name}"

        # Add additional info for better descriptions
        if mag and mag < 99:
            description += f" (mag {mag:.1f})"
        if size_arcmin and size_arcmin > 1:
            description += f", {size_arcmin:.1f}' across"

        return DSOTarget(
            name=name,
            catalog_id=catalog_id,
            object_type=dso.object_type,
            ra_hours=dso.ra_hours,
            dec_degrees=dso.dec_degrees,
            magnitude=mag,
            size_arcmin=size_arcmin,
            description=description,
        )

    def _get_constellation_full_name(self, abbreviation: str) -> str:
        """Look up full constellation name from abbreviation."""
        if not abbreviation:
            return None

        constellation = self.db.query(ConstellationName).filter(ConstellationName.abbreviation == abbreviation).first()

        return constellation.full_name if constellation else abbreviation

    def get_all_targets(self, limit: Optional[int] = None, offset: int = 0) -> List[DSOTarget]:
        """
        Get all targets in catalog.

        Args:
            limit: Maximum number of targets to return (None = all)
            offset: Number of targets to skip (for pagination)

        Returns:
            List of DSOTarget objects
        """
        query = self.db.query(DSOCatalog).order_by(DSOCatalog.magnitude.asc())

        if limit:
            query = query.limit(limit).offset(offset)

        dso_objects = query.all()
        return [self._db_row_to_target(dso) for dso in dso_objects]

    def get_target_by_id(self, catalog_id: str) -> Optional[DSOTarget]:
        """
        Get a specific target by catalog ID.

        Args:
            catalog_id: Catalog identifier (e.g., "M31", "NGC224", "IC434", "C80")

        Returns:
            DSOTarget object or None if not found
        """
        # Parse catalog ID to extract catalog name and number
        # Handle formats: M31, NGC224, IC434, C80
        catalog_id_upper = catalog_id.upper()

        # For Messier objects, search by common_name (stored as M042, M031, etc.)
        if catalog_id_upper.startswith("M") and len(catalog_id_upper) > 1 and catalog_id_upper[1:].isdigit():
            # Pad the Messier number to 3 digits (M42 -> M042)
            messier_padded = f"M{int(catalog_id_upper[1:]):03d}"
            dso = self.db.query(DSOCatalog).filter(DSOCatalog.common_name == messier_padded).first()
        elif catalog_id_upper.startswith("C") and len(catalog_id_upper) > 1 and catalog_id_upper[1:].isdigit():
            # Caldwell objects (C1-C109)
            caldwell_number = int(catalog_id_upper[1:])
            dso = self.db.query(DSOCatalog).filter(DSOCatalog.caldwell_number == caldwell_number).first()
        elif catalog_id_upper.startswith("NGC"):
            catalog_number = int(catalog_id_upper[3:])
            dso = (
                self.db.query(DSOCatalog)
                .filter(DSOCatalog.catalog_name == "NGC", DSOCatalog.catalog_number == catalog_number)
                .first()
            )
        elif catalog_id_upper.startswith("IC"):
            catalog_number = int(catalog_id_upper[2:])
            dso = (
                self.db.query(DSOCatalog)
                .filter(DSOCatalog.catalog_name == "IC", DSOCatalog.catalog_number == catalog_number)
                .first()
            )
        else:
            return None

        if dso:
            return self._db_row_to_target(dso)
        return None

    def filter_targets(
        self,
        object_types: Optional[List[str]] = None,
        min_magnitude: Optional[float] = None,
        max_magnitude: Optional[float] = None,
        constellation: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
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
        query = self.db.query(DSOCatalog)

        if object_types and len(object_types) > 0:
            query = query.filter(DSOCatalog.object_type.in_(object_types))

        if min_magnitude is not None:
            query = query.filter(DSOCatalog.magnitude >= min_magnitude)

        if max_magnitude is not None:
            query = query.filter(DSOCatalog.magnitude <= max_magnitude)

        if constellation:
            query = query.filter(DSOCatalog.constellation == constellation)

        # Order by magnitude (brightest first)
        query = query.order_by(DSOCatalog.magnitude.asc())

        if limit:
            query = query.limit(limit).offset(offset)

        dso_objects = query.all()
        return [self._db_row_to_target(dso) for dso in dso_objects]

    def get_caldwell_targets(self, limit: Optional[int] = None, offset: int = 0) -> List[DSOTarget]:
        """
        Get all Caldwell catalog targets.

        Args:
            limit: Maximum number of targets to return (None = all)
            offset: Number of targets to skip (for pagination)

        Returns:
            List of Caldwell DSOTarget objects ordered by Caldwell number
        """
        query = (
            self.db.query(DSOCatalog)
            .filter(DSOCatalog.caldwell_number.isnot(None))
            .order_by(DSOCatalog.caldwell_number.asc())
        )

        if limit:
            query = query.limit(limit).offset(offset)

        dso_objects = query.all()
        return [self._db_row_to_target(dso) for dso in dso_objects]
