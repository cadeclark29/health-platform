from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class HealthData(Base):
    __tablename__ = "health_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String, nullable=False)  # oura, whoop, apple, eight_sleep, mock

    # Normalized health metrics (0-100 scale where applicable)
    sleep_score = Column(Float, nullable=True)
    hrv_score = Column(Float, nullable=True)
    recovery_score = Column(Float, nullable=True)
    strain_score = Column(Float, nullable=True)
    resting_hr = Column(Integer, nullable=True)
    sleep_duration_hrs = Column(Float, nullable=True)
    deep_sleep_pct = Column(Float, nullable=True)
    rem_sleep_pct = Column(Float, nullable=True)

    # Relationship
    user = relationship("User", back_populates="health_data")

    def to_dict(self) -> dict:
        return {
            "sleep_score": self.sleep_score,
            "hrv_score": self.hrv_score,
            "recovery_score": self.recovery_score,
            "strain_score": self.strain_score,
            "resting_hr": self.resting_hr,
            "sleep_duration_hrs": self.sleep_duration_hrs,
            "deep_sleep_pct": self.deep_sleep_pct,
            "rem_sleep_pct": self.rem_sleep_pct,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
