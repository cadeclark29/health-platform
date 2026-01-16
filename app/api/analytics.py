from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import date, datetime, timedelta

from app.db import get_db
from app.models import User, HealthData, SupplementLog, SupplementStart, LifeEvent

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


class SupplementStartUpdate(BaseModel):
    end_date: Optional[str] = None
    notes: Optional[str] = None


class SupplementStartResponse(BaseModel):
    id: str
    supplement_id: str
    start_date: str
    end_date: Optional[str]
    notes: Optional[str]


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
        start_date=date.fromisoformat(start.start_date),
        notes=start.notes
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

    if update.end_date:
        start.end_date = date.fromisoformat(update.end_date)
    if update.notes is not None:
        start.notes = update.notes

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
            "sleep_score": hd.sleep_score,
            "hrv_score": hd.hrv_score,
            "recovery_score": hd.recovery_score,
            "resting_hr": hd.resting_hr,
            "sleep_duration_hrs": hd.sleep_duration_hrs,
            "deep_sleep_pct": hd.deep_sleep_pct,
            "rem_sleep_pct": hd.rem_sleep_pct,
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

@router.get("/{user_id}/outcome-analysis/{supplement_id}")
def get_outcome_analysis(
    user_id: str,
    supplement_id: str,
    db: Session = Depends(get_db)
):
    """
    Calculate before/after metrics for a specific supplement.

    Compares average health metrics:
    - Before: 14 days before starting the supplement
    - After: Most recent 14 days of taking it
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

    # Get "before" period: 14 days before start
    before_start = start_date - timedelta(days=14)
    before_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(before_start, datetime.min.time()),
        HealthData.timestamp < datetime.combine(start_date, datetime.min.time())
    ).all()

    # Get "after" period: most recent 14 days (if enough time has passed)
    after_start = date.today() - timedelta(days=14)
    if after_start < start_date:
        after_start = start_date

    after_data = db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.timestamp >= datetime.combine(after_start, datetime.min.time())
    ).all()

    def calculate_averages(data_list):
        if not data_list:
            return None

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

        return {
            key: round(sum(vals) / len(vals), 1) if vals else None
            for key, vals in metrics.items()
        }

    before_avg = calculate_averages(before_data)
    after_avg = calculate_averages(after_data)

    # Calculate changes
    changes = {}
    if before_avg and after_avg:
        for key in before_avg:
            if before_avg[key] is not None and after_avg[key] is not None:
                diff = after_avg[key] - before_avg[key]
                pct = (diff / before_avg[key] * 100) if before_avg[key] != 0 else 0
                changes[key] = {
                    "before": before_avg[key],
                    "after": after_avg[key],
                    "change": round(diff, 1),
                    "change_pct": round(pct, 1)
                }

    # Calculate adherence rate
    logs = db.query(SupplementLog).filter(
        SupplementLog.user_id == user_id,
        SupplementLog.supplement_id == supplement_id,
        SupplementLog.log_date >= start_date
    ).all()

    days_tracked = len(logs)
    days_taken = sum(1 for log in logs if log.taken)
    adherence_rate = (days_taken / days_tracked * 100) if days_tracked > 0 else 0

    return {
        "supplement_id": supplement_id,
        "start_date": str(start_date),
        "end_date": str(supplement_start.end_date) if supplement_start.end_date else None,
        "days_on_supplement": (date.today() - start_date).days,
        "before_period": {
            "start": str(before_start),
            "end": str(start_date),
            "data_points": len(before_data),
            "averages": before_avg
        },
        "after_period": {
            "start": str(after_start),
            "end": str(date.today()),
            "data_points": len(after_data),
            "averages": after_avg
        },
        "changes": changes,
        "adherence": {
            "days_tracked": days_tracked,
            "days_taken": days_taken,
            "rate_pct": round(adherence_rate, 1)
        }
    }
