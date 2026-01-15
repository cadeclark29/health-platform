from sqlalchemy import Column, String, DateTime, Integer, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid

from app.db.database import Base


class DailyCheckIn(Base):
    """Daily user-reported symptoms and feelings."""
    __tablename__ = "daily_checkins"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    check_in_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Subjective ratings (1-5 scale)
    energy_level = Column(Integer, nullable=True)  # 1=exhausted, 5=energized
    stress_level = Column(Integer, nullable=True)  # 1=calm, 5=very stressed
    sleep_quality = Column(Integer, nullable=True)  # 1=terrible, 5=excellent
    mood = Column(Integer, nullable=True)  # 1=low, 5=great
    focus = Column(Integer, nullable=True)  # 1=scattered, 5=sharp

    # Optional notes
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="check_ins")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": str(self.check_in_date),
            "energy_level": self.energy_level,
            "stress_level": self.stress_level,
            "sleep_quality": self.sleep_quality,
            "mood": self.mood,
            "focus": self.focus,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
