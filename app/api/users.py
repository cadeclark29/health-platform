from typing import List, Optional, Dict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr

from app.db import get_db
from app.models import User, HealthData, DispenseLog

router = APIRouter()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    # Required profile fields for personalized dosing (imperial units)
    age: int
    sex: str  # "male", "female", "other"
    height_feet: int
    height_inches: int
    weight_lbs: float
    # Lifestyle quiz fields
    region: Optional[str] = None  # northern, central, southern, gulf
    activity_level: Optional[str] = None  # sedentary, light, moderate, active, athlete
    work_environment: Optional[str] = None  # office, outdoor, shift, remote
    diet_type: Optional[str] = None  # omnivore, vegetarian, vegan
    bedtime: Optional[str] = None  # "22:30" format
    wake_time: Optional[str] = None  # "06:30" format
    chronotype: Optional[str] = None  # early_bird, night_owl, neutral
    # Optional fields
    allergies: List[str] = []
    medications: List[str] = []
    goals: List[str] = []


class UserUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    height_feet: Optional[int] = None
    height_inches: Optional[int] = None
    weight_lbs: Optional[float] = None
    region: Optional[str] = None
    activity_level: Optional[str] = None
    work_environment: Optional[str] = None
    diet_type: Optional[str] = None
    bedtime: Optional[str] = None
    wake_time: Optional[str] = None
    chronotype: Optional[str] = None
    allergies: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    health_goal: Optional[str] = None  # sleep, recovery, energy, wellness
    onboarding_complete: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: Optional[int]
    sex: Optional[str]
    height_feet: Optional[int]
    height_inches: Optional[int]
    weight_lbs: Optional[float]
    region: Optional[str]
    activity_level: Optional[str]
    work_environment: Optional[str]
    diet_type: Optional[str]
    bedtime: Optional[str]
    wake_time: Optional[str]
    chronotype: Optional[str]
    allergies: List[str]
    medications: List[str]
    goals: List[str]
    health_goal: Optional[str]
    onboarding_complete: Optional[str]
    has_oura: bool
    has_whoop: bool
    has_baseline: bool

    class Config:
        from_attributes = True


class UserSignIn(BaseModel):
    email: EmailStr


@router.post("", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=user_data.name,
        email=user_data.email,
        age=user_data.age,
        sex=user_data.sex,
        height_feet=user_data.height_feet,
        height_inches=user_data.height_inches,
        weight_lbs=user_data.weight_lbs,
        region=user_data.region,
        activity_level=user_data.activity_level,
        work_environment=user_data.work_environment,
        diet_type=user_data.diet_type,
        bedtime=user_data.bedtime,
        wake_time=user_data.wake_time,
        chronotype=user_data.chronotype,
        allergies=user_data.allergies,
        medications=user_data.medications,
        goals=user_data.goals
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _user_to_response(user)


@router.post("/signin", response_model=UserResponse)
def sign_in(signin_data: UserSignIn, db: Session = Depends(get_db)):
    """Sign in with an existing email."""
    user = db.query(User).filter(User.email == signin_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email")

    return _user_to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_data: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.name is not None:
        user.name = user_data.name
    if user_data.age is not None:
        user.age = user_data.age
    if user_data.sex is not None:
        user.sex = user_data.sex
    if user_data.height_feet is not None:
        user.height_feet = user_data.height_feet
    if user_data.height_inches is not None:
        user.height_inches = user_data.height_inches
    if user_data.weight_lbs is not None:
        user.weight_lbs = user_data.weight_lbs
    if user_data.region is not None:
        user.region = user_data.region
    if user_data.activity_level is not None:
        user.activity_level = user_data.activity_level
    if user_data.work_environment is not None:
        user.work_environment = user_data.work_environment
    if user_data.diet_type is not None:
        user.diet_type = user_data.diet_type
    if user_data.bedtime is not None:
        user.bedtime = user_data.bedtime
    if user_data.wake_time is not None:
        user.wake_time = user_data.wake_time
    if user_data.chronotype is not None:
        user.chronotype = user_data.chronotype
    if user_data.allergies is not None:
        user.allergies = user_data.allergies
    if user_data.medications is not None:
        user.medications = user_data.medications
    if user_data.goals is not None:
        user.goals = user_data.goals
    if user_data.health_goal is not None:
        user.health_goal = user_data.health_goal
    if user_data.onboarding_complete is not None:
        user.onboarding_complete = user_data.onboarding_complete

    db.commit()
    db.refresh(user)

    return _user_to_response(user)


@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"status": "deleted"}


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        age=user.age,
        sex=user.sex,
        height_feet=user.height_feet,
        height_inches=user.height_inches,
        weight_lbs=user.weight_lbs,
        region=user.region,
        activity_level=user.activity_level,
        work_environment=user.work_environment,
        diet_type=user.diet_type,
        bedtime=user.bedtime,
        wake_time=user.wake_time,
        chronotype=user.chronotype,
        allergies=user.allergies or [],
        medications=user.medications or [],
        goals=user.goals or [],
        health_goal=user.health_goal,
        onboarding_complete=user.onboarding_complete,
        has_oura=user.oura_token is not None,
        has_whoop=user.whoop_token is not None,
        has_baseline=user.baseline is not None
    )


@router.get("/{user_id}/progress")
def get_progress_data(
    user_id: str,
    days: int = 14,
    db: Session = Depends(get_db)
):
    """
    Get progress data for a user including health metrics and dispense logs.

    Returns historical health data and supplement dispense events for charting.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get health data for the period
    health_records = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= start_date
    ).order_by(HealthData.timestamp.asc()).all()

    # Get dispense logs for the period
    dispense_logs = db.query(DispenseLog).filter(
        DispenseLog.user_id == user_id,
        DispenseLog.dispensed_at >= start_date
    ).order_by(DispenseLog.dispensed_at.asc()).all()

    # Format health data by date
    health_by_date = {}
    for record in health_records:
        date_str = record.timestamp.strftime("%Y-%m-%d")
        if date_str not in health_by_date:
            health_by_date[date_str] = record.to_dict()
        else:
            # Keep the most recent record for each day
            health_by_date[date_str] = record.to_dict()

    # Format dispense logs by date
    dispenses_by_date: Dict[str, List[dict]] = {}
    for log in dispense_logs:
        date_str = log.dispensed_at.strftime("%Y-%m-%d")
        if date_str not in dispenses_by_date:
            dispenses_by_date[date_str] = []
        dispenses_by_date[date_str].append({
            "supplement": log.supplement_name,
            "dose": log.dose,
            "unit": log.unit,
            "time": log.dispensed_at.strftime("%H:%M")
        })

    # Build timeline data
    timeline = []
    current = start_date.date()
    end = end_date.date()

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        health = health_by_date.get(date_str, {})
        dispenses = dispenses_by_date.get(date_str, [])

        timeline.append({
            "date": date_str,
            "sleep_score": health.get("sleep_score"),
            "hrv_score": health.get("hrv_score"),
            "recovery_score": health.get("recovery_score"),
            "strain_score": health.get("strain_score"),
            "sleep_duration_hrs": health.get("sleep_duration_hrs"),
            "resting_hr": health.get("resting_hr"),
            "supplements_taken": dispenses
        })
        current += timedelta(days=1)

    # Calculate correlations
    correlations = _calculate_correlations(timeline)

    return {
        "user_id": user_id,
        "days": days,
        "timeline": timeline,
        "correlations": correlations
    }


def _calculate_correlations(timeline: List[dict]) -> List[dict]:
    """
    Calculate simple correlations between supplement intake and next-day metrics.

    This is a simplified correlation analysis that compares metrics the day
    after taking a supplement vs days without taking it.
    """
    # Track supplement -> next day metrics
    supplement_effects: Dict[str, Dict[str, List[float]]] = {}

    for i, day in enumerate(timeline[:-1]):  # Skip last day (no next day)
        next_day = timeline[i + 1]

        for supp_info in day.get("supplements_taken", []):
            supp_name = supp_info["supplement"]

            if supp_name not in supplement_effects:
                supplement_effects[supp_name] = {
                    "sleep_with": [],
                    "recovery_with": [],
                    "hrv_with": []
                }

            # Record next day metrics
            if next_day.get("sleep_score") is not None:
                supplement_effects[supp_name]["sleep_with"].append(next_day["sleep_score"])
            if next_day.get("recovery_score") is not None:
                supplement_effects[supp_name]["recovery_with"].append(next_day["recovery_score"])
            if next_day.get("hrv_score") is not None:
                supplement_effects[supp_name]["hrv_with"].append(next_day["hrv_score"])

    # Calculate baseline (days without each supplement)
    all_sleep = [d["sleep_score"] for d in timeline if d.get("sleep_score") is not None]
    all_recovery = [d["recovery_score"] for d in timeline if d.get("recovery_score") is not None]
    all_hrv = [d["hrv_score"] for d in timeline if d.get("hrv_score") is not None]

    baseline_sleep = sum(all_sleep) / len(all_sleep) if all_sleep else 0
    baseline_recovery = sum(all_recovery) / len(all_recovery) if all_recovery else 0
    baseline_hrv = sum(all_hrv) / len(all_hrv) if all_hrv else 0

    # Build correlation results
    correlations = []
    for supp_name, effects in supplement_effects.items():
        days_taken = len(effects["sleep_with"])
        if days_taken < 2:  # Need at least 2 data points
            continue

        avg_sleep_with = sum(effects["sleep_with"]) / len(effects["sleep_with"]) if effects["sleep_with"] else baseline_sleep
        avg_recovery_with = sum(effects["recovery_with"]) / len(effects["recovery_with"]) if effects["recovery_with"] else baseline_recovery
        avg_hrv_with = sum(effects["hrv_with"]) / len(effects["hrv_with"]) if effects["hrv_with"] else baseline_hrv

        # Calculate deltas
        sleep_delta = round(avg_sleep_with - baseline_sleep, 1)
        recovery_delta = round(avg_recovery_with - baseline_recovery, 1)
        hrv_delta = round(avg_hrv_with - baseline_hrv, 1)

        # Overall score (simple average of deltas)
        overall_score = round((sleep_delta + recovery_delta + hrv_delta) / 3, 1)

        correlations.append({
            "supplement": supp_name,
            "days_taken": days_taken,
            "overall_score": overall_score,
            "sleep_delta": sleep_delta,
            "recovery_delta": recovery_delta,
            "hrv_delta": hrv_delta,
            "avg_sleep_after": round(avg_sleep_with, 1),
            "avg_recovery_after": round(avg_recovery_with, 1),
            "avg_hrv_after": round(avg_hrv_with, 1)
        })

    # Sort by overall score descending
    correlations.sort(key=lambda x: x["overall_score"], reverse=True)

    return correlations
