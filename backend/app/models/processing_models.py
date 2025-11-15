"""SQLAlchemy models for processing system."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class ProcessingSession(Base):
    """Processing session containing uploaded files."""
    __tablename__ = "processing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # Future: multi-user support
    session_name = Column(String(100), nullable=False)
    observation_plan_id = Column(Integer, nullable=True)  # Link to original plan
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    total_files = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)
    status = Column(String(20), default='uploading')  # uploading, ready, processing, complete, error
    session_metadata = Column(JSON, nullable=True)  # Session log, target info
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    files = relationship("ProcessingFile", back_populates="session", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="session", cascade="all, delete-orphan")


class ProcessingFile(Base):
    """Individual file in a processing session."""
    __tablename__ = "processing_files"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("processing_sessions.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # light, dark, flat, bias, stacked
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    exposure_seconds = Column(Float, nullable=True)
    filter_name = Column(String(10), nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)  # FWHM, star count, etc.
    file_metadata = Column(JSON, nullable=True)  # FITS headers
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ProcessingSession", back_populates="files")


class ProcessingPipeline(Base):
    """Processing pipeline (workflow template)."""
    __tablename__ = "processing_pipelines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    pipeline_steps = Column(JSON, nullable=False)  # Array of step configurations
    is_preset = Column(Boolean, default=False)  # True for built-in presets
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs = relationship("ProcessingJob", back_populates="pipeline")


class ProcessingJob(Base):
    """Processing job execution."""
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("processing_sessions.id"), nullable=False)
    pipeline_id = Column(Integer, ForeignKey("processing_pipelines.id"), nullable=False)
    container_id = Column(String(64), nullable=True)  # Docker container ID
    status = Column(String(20), default='queued')  # queued, starting, running, complete, failed, cancelled
    progress_percent = Column(Float, default=0.0)
    current_step = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    output_files = Column(JSON, nullable=True)  # List of generated files
    error_message = Column(Text, nullable=True)
    processing_log = Column(Text, nullable=True)
    gpu_used = Column(Boolean, default=False)  # Whether GPU was used
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ProcessingSession", back_populates="jobs")
    pipeline = relationship("ProcessingPipeline", back_populates="jobs")
