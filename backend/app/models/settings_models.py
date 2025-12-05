"""Settings models for global application configuration."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class AppSetting(Base):
    """Application settings stored in database.

    Uses key-value storage pattern for flexibility.
    Each setting has a key, value, and optional metadata.
    """

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)
    value_type = Column(String, nullable=False, default="string")  # string, int, bool, path
    description = Column(String, nullable=True)
    category = Column(String, nullable=True, index=True)  # telescope, processing, storage, etc.
    is_secret = Column(Boolean, default=False)  # For sensitive values like API keys
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AppSetting key={self.key} value={self.value}>"


# Default settings to be created on first startup
DEFAULT_SETTINGS = [
    {
        "key": "telescope.image_source_dir",
        "value": "/fits",
        "value_type": "path",
        "description": "Directory where telescope images are stored (mounted volume)",
        "category": "telescope",
    },
    {
        "key": "telescope.image_dest_dir",
        "value": "./data/telescope_images",
        "value_type": "path",
        "description": "Local directory to copy telescope images after observation",
        "category": "telescope",
    },
    {
        "key": "processing.working_dir",
        "value": "./data/processing",
        "value_type": "path",
        "description": "Working directory for image processing operations",
        "category": "processing",
    },
    {
        "key": "processing.auto_copy_after_plan",
        "value": "true",
        "value_type": "bool",
        "description": "Automatically copy images from telescope after plan completion",
        "category": "processing",
    },
    {
        "key": "storage.max_job_history",
        "value": "100",
        "value_type": "int",
        "description": "Maximum number of processing jobs to keep in history",
        "category": "storage",
    },
    {
        "key": "storage.auto_cleanup_days",
        "value": "30",
        "value_type": "int",
        "description": "Automatically cleanup processing files older than this many days (0=disabled)",
        "category": "storage",
    },
]
