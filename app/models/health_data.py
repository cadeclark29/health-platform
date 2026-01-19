from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, JSON
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

    # === Core Metrics (0-100 scale where applicable) ===
    sleep_score = Column(Float, nullable=True)
    hrv_score = Column(Float, nullable=True)  # Actual HRV in milliseconds
    recovery_score = Column(Float, nullable=True)  # Readiness score
    strain_score = Column(Float, nullable=True)

    # === Sleep Details ===
    sleep_duration_hrs = Column(Float, nullable=True)  # Total sleep in hours
    deep_sleep_duration = Column(Integer, nullable=True)  # Seconds
    rem_sleep_duration = Column(Integer, nullable=True)  # Seconds
    light_sleep_duration = Column(Integer, nullable=True)  # Seconds
    awake_duration = Column(Integer, nullable=True)  # Seconds awake during sleep
    sleep_efficiency = Column(Integer, nullable=True)  # Percentage
    sleep_latency = Column(Integer, nullable=True)  # Seconds to fall asleep
    restfulness_score = Column(Integer, nullable=True)  # Based on restless periods
    bedtime = Column(String, nullable=True)  # ISO timestamp
    wake_time = Column(String, nullable=True)  # ISO timestamp
    deep_sleep_pct = Column(Float, nullable=True)  # Contributor score
    rem_sleep_pct = Column(Float, nullable=True)  # Contributor score

    # === Heart Rate ===
    resting_hr = Column(Integer, nullable=True)
    lowest_hr = Column(Integer, nullable=True)
    average_hr_sleep = Column(Float, nullable=True)  # Average HR during sleep

    # === Heart Health ===
    vo2_max = Column(Float, nullable=True)
    cardiovascular_age = Column(Integer, nullable=True)

    # === Activity ===
    activity_score = Column(Integer, nullable=True)
    steps = Column(Integer, nullable=True)
    active_calories = Column(Integer, nullable=True)
    total_calories = Column(Integer, nullable=True)
    sedentary_time = Column(Integer, nullable=True)  # Minutes
    active_time = Column(Integer, nullable=True)  # Minutes

    # === SpO2 / Breathing ===
    spo2_average = Column(Float, nullable=True)  # Blood oxygen %
    breathing_average = Column(Float, nullable=True)  # Breaths per minute
    breathing_regularity = Column(Float, nullable=True)

    # === Stress ===
    stress_level = Column(String, nullable=True)  # low, medium, high
    stress_score = Column(Integer, nullable=True)  # 0-100 if available

    # === Last Workout (most recent for the day) ===
    workout_type = Column(String, nullable=True)  # running, strength, cycling, etc.
    workout_duration = Column(Integer, nullable=True)  # Minutes
    workout_intensity = Column(String, nullable=True)  # low, medium, high
    workout_calories = Column(Integer, nullable=True)
    workout_source = Column(String, nullable=True)  # manual, auto-detected

    # === Temperature ===
    temperature_deviation = Column(Float, nullable=True)  # Deviation from baseline
    temperature_trend = Column(Float, nullable=True)

    # Relationship
    user = relationship("User", back_populates="health_data")

    def to_dict(self) -> dict:
        return {
            # Core metrics
            "sleep_score": self.sleep_score,
            "hrv_score": self.hrv_score,
            "recovery_score": self.recovery_score,
            "strain_score": self.strain_score,
            "resting_hr": self.resting_hr,

            # Sleep details
            "sleep_duration_hrs": self.sleep_duration_hrs,
            "deep_sleep_duration": self.deep_sleep_duration,
            "rem_sleep_duration": self.rem_sleep_duration,
            "light_sleep_duration": self.light_sleep_duration,
            "awake_duration": self.awake_duration,
            "sleep_efficiency": self.sleep_efficiency,
            "sleep_latency": self.sleep_latency,
            "restfulness_score": self.restfulness_score,
            "bedtime": self.bedtime,
            "wake_time": self.wake_time,
            "deep_sleep_pct": self.deep_sleep_pct,
            "rem_sleep_pct": self.rem_sleep_pct,

            # Heart
            "lowest_hr": self.lowest_hr,
            "average_hr_sleep": self.average_hr_sleep,
            "vo2_max": self.vo2_max,
            "cardiovascular_age": self.cardiovascular_age,

            # Activity
            "activity_score": self.activity_score,
            "steps": self.steps,
            "active_calories": self.active_calories,
            "total_calories": self.total_calories,
            "sedentary_time": self.sedentary_time,
            "active_time": self.active_time,

            # SpO2 / Breathing
            "spo2_average": self.spo2_average,
            "breathing_average": self.breathing_average,
            "breathing_regularity": self.breathing_regularity,

            # Stress
            "stress_level": self.stress_level,
            "stress_score": self.stress_score,

            # Workout
            "workout_type": self.workout_type,
            "workout_duration": self.workout_duration,
            "workout_intensity": self.workout_intensity,
            "workout_calories": self.workout_calories,

            # Temperature
            "temperature_deviation": self.temperature_deviation,
            "temperature_trend": self.temperature_trend,

            # Meta
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "date": self.timestamp.strftime("%Y-%m-%d") if self.timestamp else None
        }
