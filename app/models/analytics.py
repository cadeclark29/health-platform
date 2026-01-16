from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid

from app.db.database import Base


class SupplementLog(Base):
    """
    Track when users actually took supplements (daily adherence).
    This replaces the dispense simulation with real human behavior tracking.
    """
    __tablename__ = "supplement_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    supplement_id = Column(String, nullable=False)  # e.g., "ashwagandha", "magnesium_glycinate"
    log_date = Column(Date, nullable=False, default=date.today)
    taken = Column(Boolean, default=True)  # Did they actually take it?
    dose_mg = Column(Float, nullable=True)  # Optional: actual dose taken
    time_taken = Column(String, nullable=True)  # "morning", "afternoon", "evening"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="supplement_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "supplement_id": self.supplement_id,
            "date": str(self.log_date),
            "taken": self.taken,
            "dose_mg": self.dose_mg,
            "time_taken": self.time_taken,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SupplementStart(Base):
    """
    Track when a user started taking a specific supplement.
    Used for before/after analysis and chart markers.
    """
    __tablename__ = "supplement_starts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    supplement_id = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null if still taking
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="supplement_starts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "supplement_id": self.supplement_id,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date) if self.end_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class LifeEvent(Base):
    """
    Track major life events that could affect health metrics.
    Used as confounding factors in supplement effectiveness analysis.
    """
    __tablename__ = "life_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    event_date = Column(Date, nullable=False)
    event_type = Column(String, nullable=False)  # e.g., "new_job", "moved", "sick", "travel"
    description = Column(String, nullable=True)  # Optional details
    impact = Column(String, nullable=True)  # "positive", "negative", "neutral"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="life_events")

    # Predefined event types
    EVENT_TYPES = [
        ("new_job", "New job/work stress"),
        ("changed_mattress", "Changed mattress"),
        ("moved", "Moved homes"),
        ("started_exercise", "Started exercising"),
        ("stopped_exercise", "Stopped exercising"),
        ("sick", "Got sick"),
        ("travel", "Travel/jet lag"),
        ("relationship", "Relationship change"),
        ("diet_change", "Major diet change"),
        ("medication", "Started/stopped medication"),
        ("stress", "Major stress event"),
        ("other", "Other")
    ]

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": str(self.event_date),
            "event_type": self.event_type,
            "description": self.description,
            "impact": self.impact,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
