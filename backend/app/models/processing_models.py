"""SQLAlchemy models for direct file processing (no sessions)."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ProcessingFile(Base):
    """Individual FITS file for processing."""

    __tablename__ = "processing_files"

    id = Column(Integer, primary_key=True, index=True)
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
    file_id = Column(Integer, ForeignKey("processing_files.id"), nullable=False)
    pipeline_id = Column(Integer, ForeignKey("processing_pipelines.id"), nullable=False)
    container_id = Column(String(64), nullable=True)  # Docker container ID
    status = Column(String(20), default="queued")  # queued, starting, running, complete, failed, cancelled
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
    pipeline = relationship("ProcessingPipeline", back_populates="jobs")
