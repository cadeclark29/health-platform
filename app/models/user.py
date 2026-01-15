from sqlalchemy import Column, String, DateTime, JSON, Integer, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Profile information for dosing (imperial units)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)  # "male", "female", "other"
    height_feet = Column(Integer, nullable=True)
    height_inches = Column(Integer, nullable=True)
    weight_lbs = Column(Float, nullable=True)

    @property
    def weight_kg(self) -> float:
        """Convert weight to kg for internal calculations."""
        if self.weight_lbs:
            return self.weight_lbs * 0.453592
        return None

    @property
    def height_cm(self) -> float:
        """Convert height to cm for internal calculations."""
        if self.height_feet is not None and self.height_inches is not None:
            total_inches = (self.height_feet * 12) + self.height_inches
            return total_inches * 2.54
        return None

    # User preferences and constraints
    allergies = Column(JSON, default=list)  # List of allergens
    medications = Column(JSON, default=list)  # Current medications
    goals = Column(JSON, default=list)  # Health goals

    # OAuth tokens for wearables
    oura_token = Column(JSON, nullable=True)
    whoop_token = Column(JSON, nullable=True)

    # Relationships
    health_data = relationship("HealthData", back_populates="user", cascade="all, delete-orphan")
    dispense_logs = relationship("DispenseLog", back_populates="user", cascade="all, delete-orphan")
    check_ins = relationship("DailyCheckIn", back_populates="user", cascade="all, delete-orphan")
    baseline = relationship("UserBaseline", back_populates="user", uselist=False, cascade="all, delete-orphan")
