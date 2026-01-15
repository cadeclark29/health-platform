from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class UserBaseline(Base):
    """
    Personal baseline metrics calculated from user's historical data.

    Instead of using fixed thresholds (e.g., HRV < 65 = stressed),
    we compare against each user's personal baseline.
    """
    __tablename__ = "user_baselines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # Calculated baseline values (rolling 30-day averages)
    hrv_mean = Column(Float, nullable=True)
    hrv_std = Column(Float, nullable=True)  # Standard deviation for detecting anomalies

    sleep_score_mean = Column(Float, nullable=True)
    sleep_score_std = Column(Float, nullable=True)

    recovery_score_mean = Column(Float, nullable=True)
    recovery_score_std = Column(Float, nullable=True)

    strain_score_mean = Column(Float, nullable=True)
    strain_score_std = Column(Float, nullable=True)

    resting_hr_mean = Column(Float, nullable=True)
    resting_hr_std = Column(Float, nullable=True)

    sleep_duration_mean = Column(Float, nullable=True)
    sleep_duration_std = Column(Float, nullable=True)

    # Subjective baseline (from check-ins)
    energy_mean = Column(Float, nullable=True)
    stress_mean = Column(Float, nullable=True)
    mood_mean = Column(Float, nullable=True)

    # Metadata
    data_points = Column(Integer, default=0)  # Number of days used in calculation
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="baseline")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "hrv": {"mean": self.hrv_mean, "std": self.hrv_std},
            "sleep_score": {"mean": self.sleep_score_mean, "std": self.sleep_score_std},
            "recovery_score": {"mean": self.recovery_score_mean, "std": self.recovery_score_std},
            "strain_score": {"mean": self.strain_score_mean, "std": self.strain_score_std},
            "resting_hr": {"mean": self.resting_hr_mean, "std": self.resting_hr_std},
            "sleep_duration": {"mean": self.sleep_duration_mean, "std": self.sleep_duration_std},
            "subjective": {
                "energy_mean": self.energy_mean,
                "stress_mean": self.stress_mean,
                "mood_mean": self.mood_mean
            },
            "data_points": self.data_points,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None
        }

    def get_deviation(self, metric: str, current_value: float) -> dict:
        """
        Calculate how far current value deviates from baseline.

        Returns:
            dict with 'deviation_pct', 'z_score', and 'status'
        """
        mean_attr = f"{metric}_mean"
        std_attr = f"{metric}_std"

        mean = getattr(self, mean_attr, None)
        std = getattr(self, std_attr, None)

        if mean is None or current_value is None:
            return {"deviation_pct": None, "z_score": None, "status": "unknown"}

        deviation_pct = ((current_value - mean) / mean) * 100 if mean != 0 else 0
        z_score = (current_value - mean) / std if std and std != 0 else 0

        # Determine status based on z-score
        if abs(z_score) < 1:
            status = "normal"
        elif abs(z_score) < 2:
            status = "moderate_deviation"
        else:
            status = "significant_deviation"

        return {
            "deviation_pct": round(deviation_pct, 1),
            "z_score": round(z_score, 2),
            "status": status,
            "baseline_mean": round(mean, 1) if mean else None
        }
