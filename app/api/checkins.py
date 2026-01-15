from typing import List, Optional
from datetime import datetime, date, timedelta
import statistics

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.db import get_db
from app.models import User, DailyCheckIn, UserBaseline, HealthData

router = APIRouter()


class CheckInCreate(BaseModel):
    energy_level: Optional[int] = None  # 1-5
    stress_level: Optional[int] = None  # 1-5
    sleep_quality: Optional[int] = None  # 1-5
    mood: Optional[int] = None  # 1-5
    focus: Optional[int] = None  # 1-5
    notes: Optional[str] = None


class CheckInResponse(BaseModel):
    id: str
    date: str
    energy_level: Optional[int]
    stress_level: Optional[int]
    sleep_quality: Optional[int]
    mood: Optional[int]
    focus: Optional[int]
    notes: Optional[str]


class BaselineResponse(BaseModel):
    user_id: str
    data_points: int
    calculated_at: Optional[str]
    metrics: dict


@router.post("/{user_id}/checkin", response_model=CheckInResponse)
def create_checkin(
    user_id: str,
    checkin_data: CheckInCreate,
    db: Session = Depends(get_db)
):
    """
    Record a daily check-in with subjective health ratings.

    Ratings are on a 1-5 scale:
    - energy_level: 1=exhausted, 5=energized
    - stress_level: 1=calm, 5=very stressed
    - sleep_quality: 1=terrible, 5=excellent
    - mood: 1=low, 5=great
    - focus: 1=scattered, 5=sharp
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate ratings are 1-5
    for field in ['energy_level', 'stress_level', 'sleep_quality', 'mood', 'focus']:
        value = getattr(checkin_data, field)
        if value is not None and (value < 1 or value > 5):
            raise HTTPException(status_code=400, detail=f"{field} must be between 1 and 5")

    # Check if already checked in today - update instead of create
    today = date.today()
    existing = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date == today
    ).first()

    if existing:
        # Update existing check-in
        if checkin_data.energy_level is not None:
            existing.energy_level = checkin_data.energy_level
        if checkin_data.stress_level is not None:
            existing.stress_level = checkin_data.stress_level
        if checkin_data.sleep_quality is not None:
            existing.sleep_quality = checkin_data.sleep_quality
        if checkin_data.mood is not None:
            existing.mood = checkin_data.mood
        if checkin_data.focus is not None:
            existing.focus = checkin_data.focus
        if checkin_data.notes is not None:
            existing.notes = checkin_data.notes
        db.commit()
        checkin = existing
    else:
        # Create new check-in
        checkin = DailyCheckIn(
            user_id=user_id,
            check_in_date=today,
            energy_level=checkin_data.energy_level,
            stress_level=checkin_data.stress_level,
            sleep_quality=checkin_data.sleep_quality,
            mood=checkin_data.mood,
            focus=checkin_data.focus,
            notes=checkin_data.notes
        )
        db.add(checkin)
        db.commit()
        db.refresh(checkin)

    return CheckInResponse(
        id=checkin.id,
        date=str(checkin.check_in_date),
        energy_level=checkin.energy_level,
        stress_level=checkin.stress_level,
        sleep_quality=checkin.sleep_quality,
        mood=checkin.mood,
        focus=checkin.focus,
        notes=checkin.notes
    )


@router.get("/{user_id}/checkins")
def get_checkins(
    user_id: str,
    days: int = 14,
    db: Session = Depends(get_db)
):
    """Get check-in history for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = date.today() - timedelta(days=days)

    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= start_date
    ).order_by(DailyCheckIn.check_in_date.desc()).all()

    return {
        "user_id": user_id,
        "days": days,
        "checkins": [c.to_dict() for c in checkins]
    }


@router.post("/{user_id}/baseline/calculate")
def calculate_baseline(
    user_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Calculate personal baseline from historical data.

    This creates personalized thresholds based on the user's own patterns,
    rather than using population averages.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = datetime.utcnow() - timedelta(days=days)

    # Get health data
    health_records = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= start_date
    ).all()

    # Get check-in data
    checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= start_date.date()
    ).all()

    if len(health_records) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough data to calculate baseline. Need at least 3 data points, have {len(health_records)}."
        )

    # Calculate stats for each metric
    def calc_stats(values):
        values = [v for v in values if v is not None]
        if len(values) < 2:
            return None, None
        return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0

    hrv_values = [r.hrv_score for r in health_records]
    sleep_values = [r.sleep_score for r in health_records]
    recovery_values = [r.recovery_score for r in health_records]
    strain_values = [r.strain_score for r in health_records]
    rhr_values = [r.resting_hr for r in health_records]
    sleep_dur_values = [r.sleep_duration_hrs for r in health_records]

    energy_values = [c.energy_level for c in checkins]
    stress_values = [c.stress_level for c in checkins]
    mood_values = [c.mood for c in checkins]

    # Create or update baseline
    baseline = user.baseline
    if not baseline:
        baseline = UserBaseline(user_id=user_id)
        db.add(baseline)

    baseline.hrv_mean, baseline.hrv_std = calc_stats(hrv_values)
    baseline.sleep_score_mean, baseline.sleep_score_std = calc_stats(sleep_values)
    baseline.recovery_score_mean, baseline.recovery_score_std = calc_stats(recovery_values)
    baseline.strain_score_mean, baseline.strain_score_std = calc_stats(strain_values)
    baseline.resting_hr_mean, baseline.resting_hr_std = calc_stats(rhr_values)
    baseline.sleep_duration_mean, baseline.sleep_duration_std = calc_stats(sleep_dur_values)

    # Subjective baselines
    energy_clean = [v for v in energy_values if v is not None]
    stress_clean = [v for v in stress_values if v is not None]
    mood_clean = [v for v in mood_values if v is not None]

    baseline.energy_mean = statistics.mean(energy_clean) if energy_clean else None
    baseline.stress_mean = statistics.mean(stress_clean) if stress_clean else None
    baseline.mood_mean = statistics.mean(mood_clean) if mood_clean else None

    baseline.data_points = len(health_records)
    baseline.calculated_at = datetime.utcnow()

    db.commit()
    db.refresh(baseline)

    return {
        "status": "calculated",
        "user_id": user_id,
        "data_points": baseline.data_points,
        "baseline": baseline.to_dict()
    }


@router.get("/{user_id}/baseline")
def get_baseline(user_id: str, db: Session = Depends(get_db)):
    """Get a user's personal baseline metrics."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.baseline:
        raise HTTPException(
            status_code=404,
            detail="No baseline calculated yet. Add health data and call POST /baseline/calculate"
        )

    return user.baseline.to_dict()


@router.get("/{user_id}/deviations")
def get_current_deviations(user_id: str, db: Session = Depends(get_db)):
    """
    Compare current health metrics against personal baseline.

    Returns how much each metric deviates from the user's normal range.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.baseline:
        raise HTTPException(
            status_code=404,
            detail="No baseline calculated yet"
        )

    # Get latest health data
    latest_health = db.query(HealthData).filter(
        HealthData.user_id == user_id
    ).order_by(HealthData.timestamp.desc()).first()

    # Get today's check-in
    today_checkin = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date == date.today()
    ).first()

    baseline = user.baseline
    deviations = {}

    if latest_health:
        if latest_health.hrv_score is not None:
            deviations["hrv"] = baseline.get_deviation("hrv", latest_health.hrv_score)
        if latest_health.sleep_score is not None:
            deviations["sleep_score"] = baseline.get_deviation("sleep_score", latest_health.sleep_score)
        if latest_health.recovery_score is not None:
            deviations["recovery_score"] = baseline.get_deviation("recovery_score", latest_health.recovery_score)
        if latest_health.strain_score is not None:
            deviations["strain_score"] = baseline.get_deviation("strain_score", latest_health.strain_score)

    # Add subjective deviations if check-in exists
    if today_checkin:
        if today_checkin.stress_level is not None and baseline.stress_mean:
            stress_dev = ((today_checkin.stress_level - baseline.stress_mean) / baseline.stress_mean) * 100
            deviations["stress_reported"] = {
                "current": today_checkin.stress_level,
                "baseline_mean": round(baseline.stress_mean, 1),
                "deviation_pct": round(stress_dev, 1),
                "elevated": today_checkin.stress_level > baseline.stress_mean
            }

    return {
        "user_id": user_id,
        "deviations": deviations,
        "latest_health_timestamp": latest_health.timestamp.isoformat() if latest_health else None,
        "has_todays_checkin": today_checkin is not None
    }
