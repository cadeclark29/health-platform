from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, Boolean
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

    # Lifestyle factors for personalized recommendations
    region = Column(String, nullable=True)  # northern, central, southern, gulf
    activity_level = Column(String, nullable=True)  # sedentary, light, moderate, active, athlete
    work_environment = Column(String, nullable=True)  # office, outdoor, shift, remote
    diet_type = Column(String, nullable=True)  # omnivore, vegetarian, vegan
    bedtime = Column(String, nullable=True)  # "22:30" format
    wake_time = Column(String, nullable=True)  # "06:30" format
    chronotype = Column(String, nullable=True)  # early_bird, night_owl, neutral

    # Primary health goal (from onboarding)
    health_goal = Column(String, nullable=True)  # sleep, recovery, energy, wellness
    onboarding_complete = Column(String, nullable=True)  # 'true' when onboarding finished

    # Region to latitude mapping for Vitamin D calculations
    REGION_LATITUDES = {
        "northern": 47.0,    # Seattle, Boston, Minneapolis, Chicago
        "central": 40.0,     # Denver, NYC, SF, Philadelphia
        "southern": 34.0,    # LA, Phoenix, Atlanta, Dallas
        "gulf": 26.0,        # Miami, Houston, New Orleans
    }

    @property
    def latitude(self) -> float:
        """Get approximate latitude based on region."""
        if self.region and self.region in self.REGION_LATITUDES:
            return self.REGION_LATITUDES[self.region]
        return 39.0  # Default to US average

    @property
    def needs_b12_boost(self) -> bool:
        """Vegetarians/vegans need more B12 supplementation."""
        return self.diet_type in ["vegetarian", "vegan"]

    @property
    def needs_omega3_boost(self) -> bool:
        """Vegans don't get EPA/DHA from diet."""
        return self.diet_type == "vegan"

    @property
    def is_shift_worker(self) -> bool:
        """Shift workers have different circadian needs."""
        return self.work_environment == "shift"

    @property
    def gets_outdoor_sun(self) -> bool:
        """Outdoor workers get more natural vitamin D."""
        return self.work_environment == "outdoor"

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

    # SMS Notification Fields
    phone_number = Column(String, nullable=True)  # E.164 format: +1234567890
    phone_verified = Column(Boolean, default=False)
    phone_verification_code = Column(String, nullable=True)
    phone_verification_expires = Column(DateTime, nullable=True)
    timezone = Column(String, default="America/New_York")  # IANA timezone
    notification_preferences = Column(JSON, default=lambda: {
        "sms_enabled": False,
        "morning_reminder": True,
        "evening_reminder": True,
        "custom_morning_time": None,
        "custom_evening_time": None,
    })

    # Relationships
    health_data = relationship("HealthData", back_populates="user", cascade="all, delete-orphan")
    dispense_logs = relationship("DispenseLog", back_populates="user", cascade="all, delete-orphan")
    check_ins = relationship("DailyCheckIn", back_populates="user", cascade="all, delete-orphan")
    baseline = relationship("UserBaseline", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Analytics relationships
    supplement_logs = relationship("SupplementLog", back_populates="user", cascade="all, delete-orphan")
    supplement_starts = relationship("SupplementStart", back_populates="user", cascade="all, delete-orphan")
    life_events = relationship("LifeEvent", back_populates="user", cascade="all, delete-orphan")
