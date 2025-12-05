"""SQLAlchemy models for saved observing plans."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from app.database import Base


class SavedPlan(Base):
    """Saved observing plan."""

    __tablename__ = "saved_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Plan metadata
    observing_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    location_name = Column(String(100), nullable=False)

    # Store the complete plan as JSON
    plan_data = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SavedPlan(id={self.id}, name='{self.name}', date='{self.observing_date}')>"
