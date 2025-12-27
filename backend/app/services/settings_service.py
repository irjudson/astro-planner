"""Settings service for retrieving configuration."""

from typing import Optional

from sqlalchemy.orm import Session

from app.models import Location
from app.models.settings_models import ObservingLocation


class SettingsService:
    """Service for managing application settings."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def get_location(self) -> Optional[Location]:
        """
        Get configured location from settings.

        Returns:
            Location object or None if not configured
        """
        # Query for default observing location
        db_location = (
            self.db.query(ObservingLocation)
            .filter(ObservingLocation.is_default == True)
            .filter(ObservingLocation.is_active == True)
            .first()
        )

        if not db_location:
            return None

        # Convert SQLAlchemy model to Pydantic Location model
        return Location(
            name=db_location.name,
            latitude=db_location.latitude,
            longitude=db_location.longitude,
            elevation=db_location.elevation,
            timezone=db_location.timezone,
        )
