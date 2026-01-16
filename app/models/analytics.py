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
    Supports both app-recommended and manually-added supplements.
    """
    __tablename__ = "supplement_starts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    supplement_id = Column(String, nullable=False)
    supplement_name = Column(String, nullable=True)  # Display name for custom supplements
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null if still taking
    notes = Column(String, nullable=True)

    # Manual supplement tracking fields
    is_manual = Column(Boolean, default=False)  # True if user added manually
    dosage = Column(String, nullable=True)  # e.g., "500mg", "2000 IU"
    frequency = Column(String, nullable=True)  # "daily", "twice_daily", "as_needed"
    reason = Column(String, nullable=True)  # "sleep", "energy", "recovery", "general_health"

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="supplement_starts")

    # Common supplement library for manual entry
    SUPPLEMENT_LIBRARY = [
        ("vitamin_d3", "Vitamin D3", "2000-5000 IU"),
        ("fish_oil", "Fish Oil / Omega-3", "1000-2000mg"),
        ("magnesium", "Magnesium", "200-400mg"),
        ("magnesium_glycinate", "Magnesium Glycinate", "200-400mg"),
        ("zinc", "Zinc", "15-30mg"),
        ("b_complex", "B-Complex", "1 capsule"),
        ("vitamin_b12", "Vitamin B12", "500-1000mcg"),
        ("creatine", "Creatine", "3-5g"),
        ("protein_powder", "Protein Powder", "20-30g"),
        ("melatonin", "Melatonin", "0.5-5mg"),
        ("probiotics", "Probiotics", "1 capsule"),
        ("iron", "Iron", "18-27mg"),
        ("vitamin_c", "Vitamin C", "500-1000mg"),
        ("multivitamin", "Multivitamin", "1 tablet"),
        ("caffeine", "Caffeine", "100-200mg"),
        ("ashwagandha", "Ashwagandha", "300-600mg"),
        ("l_theanine", "L-Theanine", "100-200mg"),
        ("collagen", "Collagen", "10-15g"),
        ("coq10", "CoQ10", "100-200mg"),
        ("turmeric", "Turmeric / Curcumin", "500-1000mg"),
        ("elderberry", "Elderberry", "500mg"),
        ("lions_mane", "Lion's Mane", "500-1000mg"),
        ("rhodiola", "Rhodiola Rosea", "200-400mg"),
        ("gaba", "GABA", "250-500mg"),
        ("glycine", "Glycine", "3g"),
        ("electrolytes", "Electrolytes", "1 serving"),
    ]

    FREQUENCIES = [
        ("daily", "Once daily"),
        ("twice_daily", "Twice daily"),
        ("three_times", "Three times daily"),
        ("as_needed", "As needed"),
        ("weekly", "Weekly"),
    ]

    REASONS = [
        ("sleep", "Better Sleep"),
        ("energy", "More Energy"),
        ("recovery", "Exercise Recovery"),
        ("focus", "Focus & Cognition"),
        ("stress", "Stress & Mood"),
        ("immunity", "Immune Support"),
        ("general_health", "General Health"),
        ("deficiency", "Address Deficiency"),
    ]

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "supplement_id": self.supplement_id,
            "supplement_name": self.supplement_name or self.supplement_id.replace("_", " ").title(),
            "start_date": str(self.start_date),
            "end_date": str(self.end_date) if self.end_date else None,
            "notes": self.notes,
            "is_manual": self.is_manual or False,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "reason": self.reason,
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
