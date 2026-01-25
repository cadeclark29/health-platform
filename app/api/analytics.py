from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import date, datetime, timedelta
import math

from app.db import get_db
from app.models import User, HealthData, SupplementLog, SupplementStart, LifeEvent


# --- Statistical Helper Functions ---

def calculate_std_dev(values: List[float]) -> float:
    """Calculate standard deviation of a list of values."""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def calculate_t_statistic(before_values: List[float], after_values: List[float]) -> dict:
    """
    Calculate t-statistic and confidence level for before/after comparison.
    Uses Welch's t-test (unequal variances assumed).
    Returns confidence level: 'high' (p<0.05), 'medium' (p<0.1), 'low' (p>=0.1)
    """
    if len(before_values) < 3 or len(after_values) < 3:
        return {"confidence": "insufficient_data", "t_stat": None, "p_estimate": None}

    n1, n2 = len(before_values), len(after_values)
    mean1, mean2 = sum(before_values) / n1, sum(after_values) / n2
    std1, std2 = calculate_std_dev(before_values), calculate_std_dev(after_values)

    # Avoid division by zero
    if std1 == 0 and std2 == 0:
        return {"confidence": "no_variance", "t_stat": None, "p_estimate": None}

    # Welch's t-test
    se = math.sqrt((std1**2 / n1) + (std2**2 / n2)) if (std1**2 / n1 + std2**2 / n2) > 0 else 0.001
    t_stat = (mean2 - mean1) / se if se > 0 else 0

    # Approximate degrees of freedom (Welch-Satterthwaite)
    if std1 > 0 or std2 > 0:
        numerator = ((std1**2 / n1) + (std2**2 / n2))**2
        denom1 = (std1**4 / (n1**2 * (n1 - 1))) if std1 > 0 else 0
        denom2 = (std2**4 / (n2**2 * (n2 - 1))) if std2 > 0 else 0
        df = numerator / (denom1 + denom2) if (denom1 + denom2) > 0 else min(n1, n2) - 1
    else:
        df = min(n1, n2) - 1

    # Rough p-value estimation using t-distribution approximations
    # For df >= 30, t approaches normal distribution
    abs_t = abs(t_stat)

    # Conservative confidence estimates based on t-statistic thresholds
    if df >= 30:
        # Use normal approximation
        if abs_t >= 2.576:  # ~99% confidence
            confidence = "very_high"
            p_estimate = 0.01
        elif abs_t >= 1.96:  # ~95% confidence
            confidence = "high"
            p_estimate = 0.05
        elif abs_t >= 1.645:  # ~90% confidence
            confidence = "medium"
            p_estimate = 0.10
        else:
            confidence = "low"
            p_estimate = 0.20 if abs_t >= 1.28 else 0.50
    else:
        # More conservative for small samples
        if abs_t >= 3.0:
            confidence = "high"
            p_estimate = 0.05
        elif abs_t >= 2.0:
            confidence = "medium"
            p_estimate = 0.10
        else:
            confidence = "low"
            p_estimate = 0.30

    return {
        "confidence": confidence,
        "t_stat": round(t_stat, 2),
        "p_estimate": p_estimate,
        "sample_sizes": {"before": n1, "after": n2}
    }


def detect_trend(values: List[float], dates: List[date]) -> dict:
    """
    Detect trend direction using linear regression.
    Returns: improving, declining, stable, or insufficient_data
    """
    if len(values) < 5:
        return {"direction": "insufficient_data", "slope": None, "strength": None}

    # Convert dates to numeric (days from first date)
    first_date = min(dates)
    x_values = [(d - first_date).days for d in dates]

    n = len(values)
    sum_x = sum(x_values)
    sum_y = sum(values)
    sum_xy = sum(x * y for x, y in zip(x_values, values))
    sum_x2 = sum(x**2 for x in x_values)

    # Calculate slope
    denominator = n * sum_x2 - sum_x**2
    if denominator == 0:
        return {"direction": "stable", "slope": 0, "strength": "weak"}

    slope = (n * sum_xy - sum_x * sum_y) / denominator

    # Calculate R-squared for trend strength
    mean_y = sum_y / n
    ss_tot = sum((y - mean_y)**2 for y in values)
    intercept = (sum_y - slope * sum_x) / n
    predictions = [slope * x + intercept for x in x_values]
    ss_res = sum((y - pred)**2 for y, pred in zip(values, predictions))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Determine direction and strength
    # Slope threshold: consider ~1 point per week significant
    weekly_change = slope * 7

    if abs(weekly_change) < 0.5:
        direction = "stable"
    elif weekly_change > 0:
        direction = "improving"
    else:
        direction = "declining"

    if r_squared >= 0.5:
        strength = "strong"
    elif r_squared >= 0.2:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "direction": direction,
        "slope": round(slope, 3),
        "weekly_change": round(weekly_change, 1),
        "r_squared": round(r_squared, 2),
        "strength": strength
    }

router = APIRouter()


# --- Request/Response Models ---

class SupplementLogCreate(BaseModel):
    supplement_id: str
    log_date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    taken: bool = True
    dose_mg: Optional[float] = None
    time_taken: Optional[str] = None  # "morning", "afternoon", "evening"


class SupplementLogResponse(BaseModel):
    id: str
    supplement_id: str
    date: str
    taken: bool
    dose_mg: Optional[float]
    time_taken: Optional[str]


class SupplementStartCreate(BaseModel):
    supplement_id: str
    start_date: str  # YYYY-MM-DD
    notes: Optional[str] = None
    # Manual supplement fields
    supplement_name: Optional[str] = None  # Display name for custom supplements
    is_manual: bool = False
    dosage: Optional[str] = None  # e.g., "500mg", "2000 IU"
    frequency: Optional[str] = None  # "daily", "twice_daily", "as_needed"
    reason: Optional[str] = None  # "sleep", "energy", "recovery", "general_health"


class SupplementStartUpdate(BaseModel):
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None
    notes: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    reason: Optional[str] = None


class SupplementStartResponse(BaseModel):
    id: str
    supplement_id: str
    supplement_name: Optional[str]
    start_date: str
    end_date: Optional[str]
    notes: Optional[str]
    is_manual: bool
    dosage: Optional[str]
    frequency: Optional[str]
    reason: Optional[str]


class LifeEventCreate(BaseModel):
    event_date: str  # YYYY-MM-DD
    event_type: str
    description: Optional[str] = None
    impact: Optional[str] = None  # "positive", "negative", "neutral"


class LifeEventResponse(BaseModel):
    id: str
    date: str
    event_type: str
    description: Optional[str]
    impact: Optional[str]


class DailyCheckInRequest(BaseModel):
    """Batch check-in for multiple supplements at once."""
    date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    supplements: List[dict]  # [{"supplement_id": "magnesium", "taken": true, "time_taken": "evening"}]


class AnalyticsDataPoint(BaseModel):
    date: str
    sleep_score: Optional[float]
    hrv_score: Optional[float]
    recovery_score: Optional[float]
    resting_hr: Optional[int]
    sleep_duration_hrs: Optional[float]


class AnalyticsResponse(BaseModel):
    health_data: List[dict]
    supplement_starts: List[dict]
    life_events: List[dict]
    supplement_logs: List[dict]


# --- Supplement Log Endpoints ---

@router.post("/{user_id}/supplement-logs", response_model=SupplementLogResponse)
def log_supplement(
    user_id: str,
    log: SupplementLogCreate,
    db: Session = Depends(get_db)
):
    """Log that a user took (or skipped) a supplement."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log_date = date.fromisoformat(log.log_date) if log.log_date else date.today()

    # Check if already logged for this date/supplement
    existing = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.supplement_id == log.supplement_id,
        SupplementLog.log_date == log_date
    ).first()

    if existing:
        # Update existing log
        existing.taken = log.taken
        existing.dose_mg = log.dose_mg
        existing.time_taken = log.time_taken
        db.commit()
        return existing.to_dict()

    # Create new log
    supplement_log = SupplementLog(
        user_id=user_id,
        supplement_id=log.supplement_id,
        log_date=log_date,
        taken=log.taken,
        dose_mg=log.dose_mg,
        time_taken=log.time_taken
    )
    db.add(supplement_log)
    db.commit()

    return supplement_log.to_dict()


@router.post("/{user_id}/daily-checkin")
def daily_checkin(
    user_id: str,
    checkin: DailyCheckInRequest,
    db: Session = Depends(get_db)
):
    """
    Batch check-in for all supplements the user took today.
    Replaces the dispense simulation with real behavior tracking.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    log_date = date.fromisoformat(checkin.date) if checkin.date else date.today()
    results = []

    for supp in checkin.supplements:
        supplement_id = supp.get("supplement_id")
        taken = supp.get("taken", True)
        time_taken = supp.get("time_taken")
        dose_mg = supp.get("dose_mg")

        # Check if already logged
        existing = db.query(SupplementLog).filter(
            SupplementLog.user_id == user_id,
            SupplementLog.supplement_id == supplement_id,
            SupplementLog.log_date == log_date
        ).first()

        if existing:
            existing.taken = taken
            existing.time_taken = time_taken
            existing.dose_mg = dose_mg
            results.append(existing.to_dict())
        else:
            new_log = SupplementLog(
                user_id=user_id,
                supplement_id=supplement_id,
                log_date=log_date,
                taken=taken,
                time_taken=time_taken,
                dose_mg=dose_mg
            )
            db.add(new_log)
            results.append({
                "supplement_id": supplement_id,
                "date": str(log_date),
                "taken": taken,
                "time_taken": time_taken
            })

    db.commit()

    return {
        "status": "success",
        "date": str(log_date),
        "logged": len(results),
        "supplements": results
    }


@router.get("/{user_id}/supplement-logs")
def get_supplement_logs(
    user_id: str,
    days: int = 30,
    supplement_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get supplement logs for the past N days."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = date.today() - timedelta(days=days)

    query = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.log_date >= start_date
    )

    if supplement_id:
        query = query.filter(SupplementLog.supplement_id == supplement_id)

    logs = query.order_by(SupplementLog.log_date.desc()).all()

    return [log.to_dict() for log in logs]


# --- Supplement Start Endpoints ---

@router.post("/{user_id}/supplement-starts", response_model=SupplementStartResponse)
def start_supplement(
    user_id: str,
    start: SupplementStartCreate,
    db: Session = Depends(get_db)
):
    """Record when a user started taking a supplement."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if there's already an active start for this supplement
    existing = db.query(SupplementStart).filter(
        SupplementStart.user_id == user_id,
        SupplementStart.supplement_id == start.supplement_id,
        SupplementStart.end_date == None
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Already tracking {start.supplement_id} since {existing.start_date}. End it first to start a new period."
        )

    supplement_start = SupplementStart(
        user_id=user_id,
        supplement_id=start.supplement_id,
        supplement_name=start.supplement_name,
        start_date=date.fromisoformat(start.start_date),
        notes=start.notes,
        is_manual=start.is_manual,
        dosage=start.dosage,
        frequency=start.frequency,
        reason=start.reason
    )
    db.add(supplement_start)
    db.commit()

    return supplement_start.to_dict()


@router.get("/{user_id}/supplement-starts")
def get_supplement_starts(
    user_id: str,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all supplement start records for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(SupplementStart).filter(SupplementStart.user_id == user_id)

    if active_only:
        query = query.filter(SupplementStart.end_date == None)

    starts = query.order_by(SupplementStart.start_date.desc()).all()

    return [start.to_dict() for start in starts]


@router.patch("/{user_id}/supplement-starts/{start_id}")
def update_supplement_start(
    user_id: str,
    start_id: str,
    update: SupplementStartUpdate,
    db: Session = Depends(get_db)
):
    """Update a supplement start record (e.g., to set end date)."""
    start = db.query(SupplementStart).filter(
        SupplementStart.id == start_id,
        SupplementStart.user_id == user_id
    ).first()

    if not start:
        raise HTTPException(status_code=404, detail="Supplement start record not found")

    if update.start_date:
        start.start_date = date.fromisoformat(update.start_date)
    if update.end_date:
        start.end_date = date.fromisoformat(update.end_date)
    if update.notes is not None:
        start.notes = update.notes
    if update.dosage is not None:
        start.dosage = update.dosage
    if update.frequency is not None:
        start.frequency = update.frequency
    if update.reason is not None:
        start.reason = update.reason

    db.commit()

    return start.to_dict()


@router.delete("/{user_id}/supplement-starts/{start_id}")
def delete_supplement_start(
    user_id: str,
    start_id: str,
    db: Session = Depends(get_db)
):
    """Delete a supplement start record."""
    start = db.query(SupplementStart).filter(
        SupplementStart.id == start_id,
        SupplementStart.user_id == user_id
    ).first()

    if not start:
        raise HTTPException(status_code=404, detail="Supplement start record not found")

    db.delete(start)
    db.commit()

    return {"status": "deleted", "id": start_id}


@router.get("/supplement-library")
def get_supplement_library():
    """Get the list of common supplements for manual entry."""
    return {
        "supplements": [
            {"id": s[0], "name": s[1], "typical_dose": s[2], "unit": s[3]}
            for s in SupplementStart.SUPPLEMENT_LIBRARY
        ],
        "frequencies": [
            {"id": f[0], "name": f[1]}
            for f in SupplementStart.FREQUENCIES
        ],
        "reasons": [
            {"id": r[0], "name": r[1]}
            for r in SupplementStart.REASONS
        ]
    }


# --- Life Event Endpoints ---

@router.post("/{user_id}/life-events", response_model=LifeEventResponse)
def log_life_event(
    user_id: str,
    event: LifeEventCreate,
    db: Session = Depends(get_db)
):
    """Log a life event that might affect health metrics."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    life_event = LifeEvent(
        user_id=user_id,
        event_date=date.fromisoformat(event.event_date),
        event_type=event.event_type,
        description=event.description,
        impact=event.impact
    )
    db.add(life_event)
    db.commit()

    return life_event.to_dict()


@router.get("/{user_id}/life-events")
def get_life_events(
    user_id: str,
    days: int = 90,
    db: Session = Depends(get_db)
):
    """Get life events for the past N days."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = date.today() - timedelta(days=days)

    events = db.query(LifeEvent).filter(
        LifeEvent.user_id == user_id,
        LifeEvent.event_date >= start_date
    ).order_by(LifeEvent.event_date.desc()).all()

    return [event.to_dict() for event in events]


@router.get("/{user_id}/life-events/types")
def get_life_event_types():
    """Get available life event types."""
    return LifeEvent.EVENT_TYPES


@router.delete("/{user_id}/life-events/{event_id}")
def delete_life_event(
    user_id: str,
    event_id: str,
    db: Session = Depends(get_db)
):
    """Delete a life event."""
    event = db.query(LifeEvent).filter(
        LifeEvent.id == event_id,
        LifeEvent.user_id == user_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Life event not found")

    db.delete(event)
    db.commit()

    return {"status": "deleted", "id": event_id}


# --- Analytics Data Endpoint ---

@router.get("/{user_id}/analytics")
def get_analytics_data(
    user_id: str,
    days: int = 60,
    db: Session = Depends(get_db)
):
    """
    Get combined analytics data for charting.

    Returns:
    - health_data: Daily health metrics over time
    - supplement_starts: When user started each supplement (for chart markers)
    - life_events: Life events (for chart markers)
    - supplement_logs: Daily adherence data
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = date.today() - timedelta(days=days)

    # Get health data
    health_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(start_date, datetime.min.time())
    ).order_by(HealthData.timestamp).all()

    # Aggregate health data by date (take the latest per day)
    daily_health = {}
    for hd in health_data:
        day_key = hd.timestamp.date().isoformat()
        daily_health[day_key] = {
            "date": day_key,
            # Core metrics
            "sleep_score": hd.sleep_score,
            "hrv_score": hd.hrv_score,
            "recovery_score": hd.recovery_score,
            "strain_score": hd.strain_score,
            # Sleep details
            "sleep_duration_hrs": hd.sleep_duration_hrs,
            "deep_sleep_duration": hd.deep_sleep_duration,
            "rem_sleep_duration": hd.rem_sleep_duration,
            "light_sleep_duration": hd.light_sleep_duration,
            "awake_duration": hd.awake_duration,
            "sleep_efficiency": hd.sleep_efficiency,
            "sleep_latency": hd.sleep_latency,
            "restfulness_score": hd.restfulness_score,
            "bedtime": hd.bedtime,
            "wake_time": hd.wake_time,
            "deep_sleep_pct": hd.deep_sleep_pct,
            "rem_sleep_pct": hd.rem_sleep_pct,
            # Heart rate
            "resting_hr": hd.resting_hr,
            "lowest_hr": hd.lowest_hr,
            "average_hr_sleep": hd.average_hr_sleep,
            # Heart health
            "vo2_max": hd.vo2_max,
            "cardiovascular_age": hd.cardiovascular_age,
            # Activity
            "activity_score": hd.activity_score,
            "steps": hd.steps,
            "active_calories": hd.active_calories,
            "total_calories": hd.total_calories,
            "sedentary_time": hd.sedentary_time,
            "active_time": hd.active_time,
            # SpO2 / Breathing
            "spo2_average": hd.spo2_average,
            "breathing_average": hd.breathing_average,
            "breathing_regularity": hd.breathing_regularity,
            # Stress
            "stress_level": hd.stress_level,
            "stress_score": hd.stress_score,
            # Workout
            "workout_type": hd.workout_type,
            "workout_duration": hd.workout_duration,
            "workout_intensity": hd.workout_intensity,
            "workout_calories": hd.workout_calories,
            "workout_source": hd.workout_source,
            # Temperature
            "temperature_deviation": hd.temperature_deviation,
            "temperature_trend": hd.temperature_trend,
            # Source
            "source": hd.source
        }

    # Get supplement starts (all time, for markers)
    supplement_starts = db.query(SupplementStart).filter(
        SupplementStart.user_id == user_id
    ).order_by(SupplementStart.start_date).all()

    # Get life events in date range
    life_events = db.query(LifeEvent).filter(
        LifeEvent.user_id == user_id,
        LifeEvent.event_date >= start_date
    ).order_by(LifeEvent.event_date).all()

    # Get supplement logs in date range
    supplement_logs = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.log_date >= start_date
    ).order_by(SupplementLog.log_date).all()

    return {
        "health_data": list(daily_health.values()),
        "supplement_starts": [s.to_dict() for s in supplement_starts],
        "life_events": [e.to_dict() for e in life_events],
        "supplement_logs": [l.to_dict() for l in supplement_logs],
        "date_range": {
            "start": str(start_date),
            "end": str(date.today())
        }
    }


# --- Outcome Analysis Endpoint ---

MIN_DATA_DAYS = 14  # Minimum days of data required for meaningful analysis

@router.get("/{user_id}/outcome-analysis/{supplement_id}")
def get_outcome_analysis(
    user_id: str,
    supplement_id: str,
    db: Session = Depends(get_db)
):
    """
    Calculate before/after metrics for a specific supplement with statistical confidence.

    Features:
    - Statistical confidence scoring using t-tests
    - Minimum data threshold (14+ days before showing results)
    - Trend detection (improving/stable/declining)
    - Life event awareness (flags potential confounders)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the most recent start for this supplement
    supplement_start = db.query(SupplementStart).filter(
        SupplementStart.user_id == user_id,
        SupplementStart.supplement_id == supplement_id
    ).order_by(SupplementStart.start_date.desc()).first()

    if not supplement_start:
        raise HTTPException(
            status_code=404,
            detail=f"No record of starting {supplement_id}"
        )

    start_date = supplement_start.start_date
    days_on_supplement = (date.today() - start_date).days

    # Check minimum data threshold
    has_sufficient_data = days_on_supplement >= MIN_DATA_DAYS

    # Get "before" period: 14 days before start
    before_start = start_date - timedelta(days=14)
    before_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(before_start, datetime.min.time()),
        HealthData.timestamp < datetime.combine(start_date, datetime.min.time())
    ).order_by(HealthData.timestamp).all()

    # Get "after" period: all data since starting
    after_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(start_date, datetime.min.time())
    ).order_by(HealthData.timestamp).all()

    # Check for life events that might confound the analysis
    life_events = db.query(LifeEvent).filter(
        LifeEvent.user_id == user_id,
        LifeEvent.event_date >= before_start,
        LifeEvent.event_date <= date.today()
    ).all()

    confounding_events = []
    for event in life_events:
        # Events close to the supplement start are most relevant
        days_from_start = (event.event_date - start_date).days
        if abs(days_from_start) <= 7:  # Within a week of starting
            confounding_events.append({
                "event_type": event.event_type,
                "date": str(event.event_date),
                "days_from_start": days_from_start,
                "impact": event.impact
            })

    def extract_metric_values(data_list, metric_name):
        """Extract non-null values for a specific metric."""
        values = []
        dates = []
        for hd in data_list:
            val = getattr(hd, metric_name, None)
            if val is not None:
                values.append(val)
                dates.append(hd.timestamp.date())
        return values, dates

    def calculate_averages_with_stats(data_list):
        """Calculate averages and collect raw values for statistics."""
        if not data_list:
            return None, {}

        metrics = {
            "sleep_score": [],
            "hrv_score": [],
            "recovery_score": [],
            "resting_hr": [],
            "sleep_duration_hrs": []
        }

        for hd in data_list:
            if hd.sleep_score is not None:
                metrics["sleep_score"].append(hd.sleep_score)
            if hd.hrv_score is not None:
                metrics["hrv_score"].append(hd.hrv_score)
            if hd.recovery_score is not None:
                metrics["recovery_score"].append(hd.recovery_score)
            if hd.resting_hr is not None:
                metrics["resting_hr"].append(hd.resting_hr)
            if hd.sleep_duration_hrs is not None:
                metrics["sleep_duration_hrs"].append(hd.sleep_duration_hrs)

        averages = {
            key: round(sum(vals) / len(vals), 1) if vals else None
            for key, vals in metrics.items()
        }

        return averages, metrics

    before_avg, before_values = calculate_averages_with_stats(before_data)
    after_avg, after_values = calculate_averages_with_stats(after_data)

    # Calculate changes with statistical confidence
    changes = {}
    if before_avg and after_avg:
        for key in before_avg:
            if before_avg[key] is not None and after_avg[key] is not None:
                diff = after_avg[key] - before_avg[key]
                pct = (diff / before_avg[key] * 100) if before_avg[key] != 0 else 0

                # Calculate statistical confidence
                stats = calculate_t_statistic(
                    before_values.get(key, []),
                    after_values.get(key, [])
                )

                changes[key] = {
                    "before": before_avg[key],
                    "after": after_avg[key],
                    "change": round(diff, 1),
                    "change_pct": round(pct, 1),
                    "confidence": stats["confidence"],
                    "sample_sizes": stats.get("sample_sizes", {})
                }

    # Calculate trend for each metric (using after data)
    trends = {}
    for metric_name in ["sleep_score", "hrv_score", "recovery_score", "resting_hr"]:
        values, dates = extract_metric_values(after_data, metric_name)
        if values:
            trend = detect_trend(values, dates)
            # For resting_hr, declining is good
            if metric_name == "resting_hr" and trend["direction"] == "declining":
                trend["interpretation"] = "improving"
            elif metric_name == "resting_hr" and trend["direction"] == "improving":
                trend["interpretation"] = "worsening"
            else:
                trend["interpretation"] = trend["direction"]
            trends[metric_name] = trend

    # Calculate adherence rate
    logs = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.supplement_id == supplement_id,
        SupplementLog.log_date >= start_date
    ).all()

    days_tracked = len(logs)
    days_taken = sum(1 for log in logs if log.taken)
    adherence_rate = (days_taken / days_tracked * 100) if days_tracked > 0 else 0

    # Determine overall confidence level
    if not has_sufficient_data:
        overall_confidence = "needs_more_data"
    elif len(confounding_events) > 0:
        overall_confidence = "confounded"
    elif len(before_data) < 7 or len(after_data) < 7:
        overall_confidence = "low"
    else:
        # Use the average confidence across metrics
        confidences = [c.get("confidence", "low") for c in changes.values()]
        high_count = sum(1 for c in confidences if c in ["high", "very_high"])
        if high_count >= 2:
            overall_confidence = "high"
        elif high_count >= 1 or "medium" in confidences:
            overall_confidence = "medium"
        else:
            overall_confidence = "low"

    return {
        "supplement_id": supplement_id,
        "supplement_name": supplement_start.supplement_name,
        "start_date": str(start_date),
        "end_date": str(supplement_start.end_date) if supplement_start.end_date else None,
        "days_on_supplement": days_on_supplement,
        "has_sufficient_data": has_sufficient_data,
        "min_data_days": MIN_DATA_DAYS,
        "overall_confidence": overall_confidence,
        "before_period": {
            "start": str(before_start),
            "end": str(start_date),
            "data_points": len(before_data),
            "averages": before_avg
        },
        "after_period": {
            "start": str(start_date),
            "end": str(date.today()),
            "data_points": len(after_data),
            "averages": after_avg
        },
        "changes": changes,
        "trends": trends,
        "confounding_events": confounding_events,
        "adherence": {
            "days_tracked": days_tracked,
            "days_taken": days_taken,
            "rate_pct": round(adherence_rate, 1)
        }
    }


# --- Correlation Insights Endpoint ---

@router.get("/{user_id}/correlations")
def get_correlation_insights(
    user_id: str,
    days: int = 60,
    db: Session = Depends(get_db)
):
    """
    Calculate correlations between supplement intake and health metrics.

    For each supplement, calculates:
    - Days with supplement vs days without
    - Average metrics on each type of day
    - Correlation strength
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = date.today() - timedelta(days=days)

    # Get all health data
    health_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(start_date, datetime.min.time())
    ).all()

    # Build daily health metrics lookup
    daily_health = {}
    for hd in health_data:
        day = hd.timestamp.date()
        if day not in daily_health:
            daily_health[day] = hd
        # Keep the latest entry for each day

    # Get all supplement logs
    supplement_logs = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.log_date >= start_date,
        SupplementLog.taken == True
    ).all()

    # Build supplement intake by day
    supplement_days = {}
    for log in supplement_logs:
        if log.supplement_id not in supplement_days:
            supplement_days[log.supplement_id] = set()
        supplement_days[log.supplement_id].add(log.log_date)

    # Get active supplements
    active_supplements = db.query(SupplementStart).filter(
        SupplementStart.user_id == user_id,
        SupplementStart.end_date == None
    ).all()

    correlations = []

    for supplement in active_supplements:
        supp_id = supplement.supplement_id
        supp_name = supplement.supplement_name or supp_id.replace("_", " ").title()
        days_taken = supplement_days.get(supp_id, set())

        if len(days_taken) < 5:
            continue  # Not enough data

        # Separate health data into days with/without supplement
        metrics_with = {"sleep_score": [], "hrv_score": [], "recovery_score": [], "resting_hr": []}
        metrics_without = {"sleep_score": [], "hrv_score": [], "recovery_score": [], "resting_hr": []}

        for day, hd in daily_health.items():
            target = metrics_with if day in days_taken else metrics_without

            if hd.sleep_score is not None:
                target["sleep_score"].append(hd.sleep_score)
            if hd.hrv_score is not None:
                target["hrv_score"].append(hd.hrv_score)
            if hd.recovery_score is not None:
                target["recovery_score"].append(hd.recovery_score)
            if hd.resting_hr is not None:
                target["resting_hr"].append(hd.resting_hr)

        # Calculate correlations for each metric
        metric_correlations = []
        for metric_name in ["sleep_score", "hrv_score", "recovery_score", "resting_hr"]:
            with_vals = metrics_with.get(metric_name, [])
            without_vals = metrics_without.get(metric_name, [])

            if len(with_vals) < 3 or len(without_vals) < 3:
                continue

            avg_with = sum(with_vals) / len(with_vals)
            avg_without = sum(without_vals) / len(without_vals)
            diff = avg_with - avg_without

            # For resting_hr, lower is better
            is_positive = diff < 0 if metric_name == "resting_hr" else diff > 0

            # Calculate effect size (Cohen's d)
            pooled_std = math.sqrt(
                (calculate_std_dev(with_vals)**2 + calculate_std_dev(without_vals)**2) / 2
            ) if len(with_vals) > 1 and len(without_vals) > 1 else 1

            effect_size = abs(diff) / pooled_std if pooled_std > 0 else 0

            if effect_size >= 0.8:
                strength = "strong"
            elif effect_size >= 0.5:
                strength = "moderate"
            elif effect_size >= 0.2:
                strength = "weak"
            else:
                strength = "negligible"

            metric_correlations.append({
                "metric": metric_name,
                "avg_with_supplement": round(avg_with, 1),
                "avg_without_supplement": round(avg_without, 1),
                "difference": round(diff, 1),
                "is_positive": is_positive,
                "effect_size": round(effect_size, 2),
                "strength": strength,
                "days_with": len(with_vals),
                "days_without": len(without_vals)
            })

        if metric_correlations:
            # Find the strongest positive correlation
            best_metric = max(
                [m for m in metric_correlations if m["is_positive"]],
                key=lambda x: x["effect_size"],
                default=None
            )

            correlations.append({
                "supplement_id": supp_id,
                "supplement_name": supp_name,
                "days_taken": len(days_taken),
                "total_days_analyzed": len(daily_health),
                "metrics": metric_correlations,
                "best_correlation": best_metric
            })

    # Sort by strongest correlation
    correlations.sort(
        key=lambda x: x["best_correlation"]["effect_size"] if x.get("best_correlation") else 0,
        reverse=True
    )

    return {
        "correlations": correlations,
        "analysis_period": {
            "start": str(start_date),
            "end": str(date.today()),
            "days": days
        },
        "total_supplements_analyzed": len(correlations)
    }


# --- Supplement Insights Endpoint ---

# Mapping of supplements to measurable health metrics
# Only these supplements will show before/after impact analysis
MEASURABLE_SUPPLEMENTS = {
    "magnesium_glycinate": {
        "metrics": ["sleep_score", "hrv_score", "deep_sleep_pct"],
        "primary_metric": "sleep_score",
        "expected_effect": "Sleep & relaxation"
    },
    "magnesium": {
        "metrics": ["sleep_score", "hrv_score"],
        "primary_metric": "sleep_score",
        "expected_effect": "Sleep & relaxation"
    },
    "ashwagandha": {
        "metrics": ["hrv_score", "recovery_score", "resting_hr"],
        "primary_metric": "hrv_score",
        "expected_effect": "Stress & HRV"
    },
    "l_theanine": {
        "metrics": ["hrv_score", "sleep_score"],
        "primary_metric": "hrv_score",
        "expected_effect": "Calm & focus"
    },
    "glycine": {
        "metrics": ["sleep_score", "deep_sleep_pct"],
        "primary_metric": "sleep_score",
        "expected_effect": "Sleep quality"
    },
    "melatonin": {
        "metrics": ["sleep_score", "sleep_duration_hrs"],
        "primary_metric": "sleep_score",
        "expected_effect": "Sleep onset"
    },
    "rhodiola": {
        "metrics": ["recovery_score", "hrv_score"],
        "primary_metric": "recovery_score",
        "expected_effect": "Energy & recovery"
    },
    "gaba": {
        "metrics": ["sleep_score", "hrv_score"],
        "primary_metric": "sleep_score",
        "expected_effect": "Relaxation"
    },
    "apigenin": {
        "metrics": ["sleep_score"],
        "primary_metric": "sleep_score",
        "expected_effect": "Sleep quality"
    },
}

# Friendly metric names
METRIC_DISPLAY_NAMES = {
    "sleep_score": "Sleep Score",
    "hrv_score": "HRV",
    "recovery_score": "Recovery",
    "resting_hr": "Resting HR",
    "deep_sleep_pct": "Deep Sleep %",
    "sleep_duration_hrs": "Sleep Duration"
}


@router.get("/{user_id}/supplement-insights")
def get_supplement_insights(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive insights for all user supplements.

    Returns two categories:
    1. Impact Analysis - for supplements with measurable short-term effects
    2. Consistency Tracking - for long-term/preventative supplements
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all active supplement starts
    supplement_starts = db.query(SupplementStart).filter(
        SupplementStart.user_id == user_id,
        SupplementStart.end_date == None  # Active supplements only
    ).order_by(SupplementStart.start_date).all()

    if not supplement_starts:
        return {
            "impact_analysis": [],
            "consistency_tracking": [],
            "summary": {
                "total_supplements": 0,
                "measurable_count": 0,
                "consistency_count": 0
            }
        }

    # Get all health data for analysis
    earliest_start = min(s.start_date for s in supplement_starts)
    before_period_start = earliest_start - timedelta(days=14)

    health_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(before_period_start, datetime.min.time())
    ).order_by(HealthData.timestamp).all()

    # Get all supplement logs for adherence calculation
    all_logs = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.log_date >= earliest_start
    ).all()

    # Build log lookup by supplement
    logs_by_supplement = {}
    for log in all_logs:
        if log.supplement_id not in logs_by_supplement:
            logs_by_supplement[log.supplement_id] = []
        logs_by_supplement[log.supplement_id].append(log)

    impact_analysis = []
    consistency_tracking = []

    for supp_start in supplement_starts:
        supp_id = supp_start.supplement_id
        supp_name = supp_start.supplement_name or supp_id.replace("_", " ").title()
        start_date_val = supp_start.start_date
        days_on = (date.today() - start_date_val).days

        # Calculate adherence
        supp_logs = logs_by_supplement.get(supp_id, [])
        days_logged = len([l for l in supp_logs if l.log_date >= start_date_val])
        days_taken = len([l for l in supp_logs if l.log_date >= start_date_val and l.taken])
        adherence_pct = round((days_taken / days_logged * 100) if days_logged > 0 else 0, 1)

        # Calculate streak (consecutive days taken ending today or yesterday)
        streak = 0
        check_date = date.today()
        taken_dates = set(l.log_date for l in supp_logs if l.taken)

        # Allow for today not being logged yet
        if check_date not in taken_dates:
            check_date = check_date - timedelta(days=1)

        while check_date in taken_dates:
            streak += 1
            check_date = check_date - timedelta(days=1)

        # Check if this supplement is measurable
        if supp_id in MEASURABLE_SUPPLEMENTS:
            config = MEASURABLE_SUPPLEMENTS[supp_id]
            primary_metric = config["primary_metric"]

            # Get before data (14 days before start)
            before_data = [
                hd for hd in health_data
                if start_date_val - timedelta(days=14) <= hd.timestamp.date() < start_date_val
            ]

            # Get after data (from start to now)
            after_data = [
                hd for hd in health_data
                if hd.timestamp.date() >= start_date_val
            ]

            # Calculate before/after for primary metric
            def get_metric_values(data_list, metric_name):
                return [getattr(hd, metric_name) for hd in data_list if getattr(hd, metric_name, None) is not None]

            before_values = get_metric_values(before_data, primary_metric)
            after_values = get_metric_values(after_data, primary_metric)

            has_sufficient_data = len(before_values) >= 5 and len(after_values) >= 7 and days_on >= MIN_DATA_DAYS

            if before_values and after_values:
                before_avg = sum(before_values) / len(before_values)
                after_avg = sum(after_values) / len(after_values)
                change = after_avg - before_avg
                change_pct = round((change / before_avg * 100) if before_avg != 0 else 0, 1)

                # Determine if change is positive (for resting_hr, lower is better)
                is_positive = change < 0 if primary_metric == "resting_hr" else change > 0

                # Calculate confidence
                stats = calculate_t_statistic(before_values, after_values)

                impact_analysis.append({
                    "supplement_id": supp_id,
                    "supplement_name": supp_name,
                    "start_date": str(start_date_val),
                    "days_on": days_on,
                    "expected_effect": config["expected_effect"],
                    "primary_metric": primary_metric,
                    "metric_display_name": METRIC_DISPLAY_NAMES.get(primary_metric, primary_metric),
                    "before_avg": round(before_avg, 1),
                    "after_avg": round(after_avg, 1),
                    "change": round(change, 1),
                    "change_pct": change_pct,
                    "is_positive": is_positive,
                    "confidence": stats["confidence"],
                    "has_sufficient_data": has_sufficient_data,
                    "data_points": {
                        "before": len(before_values),
                        "after": len(after_values)
                    },
                    "adherence_pct": adherence_pct,
                    "streak_days": streak
                })
            else:
                # Measurable but not enough data yet
                impact_analysis.append({
                    "supplement_id": supp_id,
                    "supplement_name": supp_name,
                    "start_date": str(start_date_val),
                    "days_on": days_on,
                    "expected_effect": config["expected_effect"],
                    "primary_metric": primary_metric,
                    "metric_display_name": METRIC_DISPLAY_NAMES.get(primary_metric, primary_metric),
                    "before_avg": None,
                    "after_avg": None,
                    "change": None,
                    "change_pct": None,
                    "is_positive": None,
                    "confidence": "needs_more_data",
                    "has_sufficient_data": False,
                    "data_points": {
                        "before": len(before_values),
                        "after": len(after_values)
                    },
                    "adherence_pct": adherence_pct,
                    "streak_days": streak,
                    "message": f"Need {MIN_DATA_DAYS - days_on} more days of data" if days_on < MIN_DATA_DAYS else "Need more health data"
                })
        else:
            # Non-measurable supplement - consistency tracking only
            consistency_tracking.append({
                "supplement_id": supp_id,
                "supplement_name": supp_name,
                "start_date": str(start_date_val),
                "days_on": days_on,
                "adherence_pct": adherence_pct,
                "streak_days": streak,
                "days_taken": days_taken,
                "days_logged": days_logged,
                "dosage": supp_start.dosage,
                "frequency": supp_start.frequency,
                "reason": supp_start.reason
            })

    # Sort impact analysis by absolute change percentage (most impactful first)
    impact_analysis.sort(
        key=lambda x: abs(x["change_pct"]) if x.get("change_pct") is not None else -1,
        reverse=True
    )

    # Sort consistency by streak (longest first)
    consistency_tracking.sort(key=lambda x: x["streak_days"], reverse=True)

    return {
        "impact_analysis": impact_analysis,
        "consistency_tracking": consistency_tracking,
        "summary": {
            "total_supplements": len(supplement_starts),
            "measurable_count": len(impact_analysis),
            "consistency_count": len(consistency_tracking)
        }
    }
