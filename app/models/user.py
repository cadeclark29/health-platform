from sqlalchemy import Column, String, DateTime, JSON
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
