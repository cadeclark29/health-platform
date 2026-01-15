from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class Recommendation(Base):
    """Represents a supplement recommendation from the engine."""
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # The recommended supplements
    supplements = Column(JSON, nullable=False)  # List of {name, dose, unit, reason}

    # Context used to generate recommendation
    time_of_day = Column(String, nullable=False)  # morning, afternoon, evening
    health_snapshot = Column(JSON, nullable=True)  # Health data at time of recommendation

    # LLM reasoning
    reasoning = Column(String, nullable=True)


class DispenseLog(Base):
    """Tracks what was actually dispensed."""
    __tablename__ = "dispense_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    dispensed_at = Column(DateTime, default=datetime.utcnow)

    # What was dispensed
    supplement_name = Column(String, nullable=False)
    dose = Column(Float, nullable=False)
    unit = Column(String, nullable=False)

    # Relationship
    user = relationship("User", back_populates="dispense_logs")
