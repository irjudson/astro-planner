"""Configuration management for the application."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    database_url: str = "postgresql://pg:buffalo-jump@host.docker.internal:5432/astro-planner"
    test_database_url: str = "postgresql://pg:buffalo-jump@localhost:5432/test_astro_planner"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 9247
    reload: bool = True

    # API Keys
    openweathermap_api_key: str = ""

    # Default Location (Three Forks, Montana)
    default_lat: float = 45.9183
    default_lon: float = -111.5433
    default_elevation: float = 1234.0
    default_timezone: str = "America/Denver"
    default_location_name: str = "Three Forks, MT"

    # Seestar S50 Specifications
    seestar_focal_length: float = 50.0
    seestar_aperture: float = 50.0
    seestar_focal_ratio: float = 5.0
    seestar_fov_width: float = 1.27
    seestar_fov_height: float = 0.71
    seestar_max_exposure: int = 10

    # Observing Constraints
    min_altitude: float = 30.0
    max_altitude: float = 90.0
    optimal_min_altitude: float = 45.0
    optimal_max_altitude: float = 65.0
    slew_time_seconds: int = 60
    setup_time_minutes: int = 30

    # Scheduling
    lookahead_minutes: int = 30
    min_target_duration_minutes: int = 20

    # Processing
    fits_dir: str = "./fits"  # Directory for FITS file storage
    processing_dir: str = "./data/processing"  # Directory for processing work

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
