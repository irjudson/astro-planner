"""Settings models for global application configuration."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class SeestarDevice(Base):
    """Seestar telescope device configuration.

    Stores connection and mount settings for multiple Seestar devices.
    Supports both control (API) and mount (storage) configurations.
    """

    __tablename__ = "seestar_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    # Control settings (for telescope API)
    control_host = Column(String, nullable=True)
    control_port = Column(Integer, default=4700)
    is_control_enabled = Column(Boolean, default=False)

    # Mount settings (for file storage)
    mount_path = Column(String, nullable=True)
    is_mount_enabled = Column(Boolean, default=False)

    # Device status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SeestarDevice name={self.name} control={self.control_host}:{self.control_port}>"


class ObservingLocation(Base):
    """Saved observing locations.

    Stores location configurations for planning observations.
    """

    __tablename__ = "observing_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    # Geographic coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, default=0.0)
    timezone = Column(String, default="UTC")

    # Bortle scale (light pollution)
    bortle_class = Column(Integer, nullable=True)

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ObservingLocation name={self.name} lat={self.latitude} lon={self.longitude}>"


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
    # Telescope settings
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
        "key": "telescope.default_port",
        "value": "4700",
        "value_type": "int",
        "description": "Default port for Seestar telescope control API",
        "category": "telescope",
    },
    # Processing settings
    {
        "key": "processing.working_dir",
        "value": "./data/processing",
        "value_type": "path",
        "description": "Working directory for image processing operations",
        "category": "processing",
    },
    {
        "key": "processing.output_dir",
        "value": "./data/output",
        "value_type": "path",
        "description": "Directory for final processed images",
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
        "key": "processing.default_format",
        "value": "jpeg",
        "value_type": "string",
        "description": "Default output format for processed images (jpeg, png, tiff)",
        "category": "processing",
    },
    {
        "key": "processing.default_quality",
        "value": "95",
        "value_type": "int",
        "description": "Default JPEG quality for processed images (1-100)",
        "category": "processing",
    },
    # Storage settings
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
    # UI settings
    {
        "key": "ui.theme",
        "value": "dark",
        "value_type": "string",
        "description": "UI theme (dark or light)",
        "category": "ui",
    },
    {
        "key": "ui.date_format",
        "value": "YYYY-MM-DD",
        "value_type": "string",
        "description": "Date display format",
        "category": "ui",
    },
    {
        "key": "ui.time_format",
        "value": "24h",
        "value_type": "string",
        "description": "Time display format (12h or 24h)",
        "category": "ui",
    },
]
