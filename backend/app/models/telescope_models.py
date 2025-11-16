"""SQLAlchemy models for telescope execution tracking."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class TelescopeExecution(Base):
    """Telescope observation plan execution record."""
    __tablename__ = "telescope_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(50), unique=True, nullable=False, index=True)
    celery_task_id = Column(String(255), unique=True, nullable=False, index=True)

    # Execution state
    state = Column(String(20), nullable=False, index=True)  # starting, running, paused, completed, aborted, error

    # Plan details
    total_targets = Column(Integer, nullable=False)
    current_target_index = Column(Integer, default=-1)
    current_target_name = Column(String(100), nullable=True)
    current_phase = Column(String(50), nullable=True)  # slewing, focusing, imaging

    # Progress tracking
    targets_completed = Column(Integer, default=0)
    targets_failed = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    elapsed_seconds = Column(Integer, default=0)
    estimated_remaining_seconds = Column(Integer, nullable=True)

    # Configuration
    park_when_done = Column(Boolean, default=True)
    telescope_host = Column(String(100), nullable=True)
    telescope_port = Column(Integer, nullable=True)

    # Results and errors
    execution_result = Column(JSON, nullable=True)  # Final results summary
    error_log = Column(JSON, nullable=True)  # Array of errors encountered

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    targets = relationship("TelescopeExecutionTarget", back_populates="execution", cascade="all, delete-orphan")


class TelescopeExecutionTarget(Base):
    """Individual target within a telescope execution."""
    __tablename__ = "telescope_execution_targets"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, nullable=False, index=True)
    target_index = Column(Integer, nullable=False)

    # Target information
    target_name = Column(String(100), nullable=False)
    catalog_id = Column(String(50), nullable=True)
    ra_hours = Column(Float, nullable=False)
    dec_degrees = Column(Float, nullable=False)
    object_type = Column(String(50), nullable=True)
    magnitude = Column(Float, nullable=True)

    # Scheduling
    scheduled_start_time = Column(DateTime, nullable=False)
    scheduled_duration_minutes = Column(Integer, nullable=False)
    recommended_frames = Column(Integer, nullable=True)
    recommended_exposure_seconds = Column(Integer, nullable=True)

    # Execution tracking
    started = Column(Boolean, default=False)
    goto_completed = Column(Boolean, default=False)
    focus_completed = Column(Boolean, default=False)
    imaging_started = Column(Boolean, default=False)
    imaging_completed = Column(Boolean, default=False)
    actual_exposures = Column(Integer, default=0)

    # Timing
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Errors
    error_count = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)  # Array of error details

    # Foreign key (no SQLAlchemy ForeignKey to allow standalone usage)
    execution_id = Column(Integer, nullable=False)
