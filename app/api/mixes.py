from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.models import User, HealthData, DispenseLog
from app.engine.mixes import mix_engine, SUPPLEMENT_MIXES
from app.engine.rules import RulesEngine

router = APIRouter()
rules = RulesEngine()


class MixSupplement(BaseModel):
    supplement_id: str
    name: str
    dose: float
    unit: str
    standard_dose: float
    adjusted_from: Optional[float] = None
    adjustments: Optional[List[dict]] = None


class MixWarning(BaseModel):
    supplement_id: str
    name: str
    message: str


class MixSkipped(BaseModel):
    supplement_id: str
    name: Optional[str] = None
    reason: str


class InteractionWarning(BaseModel):
    supplements: List[str]
    severity: str
    type: str
    description: str
    recommendation: str


class MixResponse(BaseModel):
    mix_id: str
    mix_name: str
    mix_icon: str
    mix_description: str
    supplements: List[MixSupplement]
    warnings: List[MixWarning] = []
    skipped: List[MixSkipped] = []
    interaction_warnings: List[InteractionWarning] = []
    total_supplements: int


class MixInfo(BaseModel):
    id: str
    name: str
    icon: str
    description: str
    category: str
    color: str
    time_windows: List[str]
    component_count: int


class SmartRecommendation(BaseModel):
    recommended_mix_id: Optional[str]
    recommended_mix_name: Optional[str]
    reason: str
    health_summary: dict


@router.get("/available")
async def get_available_mixes(
    time_override: Optional[int] = None
) -> List[MixInfo]:
    """
    Get all mixes available for the current time of day.

    Args:
        time_override: Optional hour (0-23) to simulate different time

    Returns:
        List of available mixes with their info
    """
    time_of_day = rules.get_time_of_day(time_override)
    available = mix_engine.get_available_mixes(time_of_day)

    return [
        MixInfo(
            id=mix.id,
            name=mix.name,
            icon=mix.icon,
            description=mix.description,
            category=mix.category,
            color=mix.color,
            time_windows=mix.time_windows,
            component_count=len(mix.components)
        )
        for mix in available
    ]


@router.get("/all")
async def get_all_mixes() -> List[MixInfo]:
    """Get all mixes regardless of time."""
    return [
        MixInfo(
            id=mix.id,
            name=mix.name,
            icon=mix.icon,
            description=mix.description,
            category=mix.category,
            color=mix.color,
            time_windows=mix.time_windows,
            component_count=len(mix.components)
        )
        for mix in SUPPLEMENT_MIXES.values()
    ]


@router.get("/{user_id}/smart")
async def get_smart_recommendation(
    user_id: str,
    time_override: Optional[int] = None,
    db: Session = Depends(get_db)
) -> SmartRecommendation:
    """
    Get a smart mix recommendation based on health data.

    Uses wearable data to suggest the most appropriate mix.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get time of day
    time_of_day = rules.get_time_of_day(time_override)

    # Get latest health data
    health_data = db.query(HealthData).filter(
        HealthData.user_id == user_id
    ).order_by(HealthData.timestamp.desc()).first()

    if not health_data:
        # No health data - recommend based on time only
        if time_of_day == "morning":
            return SmartRecommendation(
                recommended_mix_id="daily_foundation",
                recommended_mix_name="Daily Foundation",
                reason="No health data available. Recommending essential daily nutrients.",
                health_summary={}
            )
        elif time_of_day == "evening":
            return SmartRecommendation(
                recommended_mix_id="night_drink",
                recommended_mix_name="Night Drink",
                reason="No health data available. Recommending sleep support for evening.",
                health_summary={}
            )
        else:
            return SmartRecommendation(
                recommended_mix_id="focus_mode",
                recommended_mix_name="Focus Mode",
                reason="No health data available. Recommending focus support for afternoon.",
                health_summary={}
            )

    health_dict = health_data.to_dict()
    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex
    }

    # Get smart recommendation
    mix_id = mix_engine.get_smart_recommendation(
        health_dict,
        time_of_day,
        user_profile
    )

    mix = mix_engine.get_mix_by_id(mix_id)
    reason = _generate_reason(health_dict, mix_id, time_of_day)

    return SmartRecommendation(
        recommended_mix_id=mix_id,
        recommended_mix_name=mix.name if mix else None,
        reason=reason,
        health_summary={
            "sleep_score": health_dict.get("sleep_score"),
            "hrv_score": health_dict.get("hrv_score"),
            "recovery_score": health_dict.get("recovery_score"),
            "strain_score": health_dict.get("strain_score"),
        }
    )


def _generate_reason(health_data: dict, mix_id: str, time_of_day: str) -> str:
    """Generate a human-readable reason for the recommendation."""
    sleep = health_data.get("sleep_score")
    hrv = health_data.get("hrv_score")
    recovery = health_data.get("recovery_score")
    strain = health_data.get("strain_score")

    reasons = {
        "wake_me_up": f"Your sleep score was {sleep}. Wake Me Up will help boost your energy.",
        "night_drink": "Night Drink will help you wind down and optimize sleep quality.",
        "stressed": f"Your HRV is {hrv}, indicating elevated stress. This blend will help you relax.",
        "recovery_day": f"High strain ({strain}) detected. Recovery Day will help your body repair.",
        "daily_foundation": "Starting your day with essential nutrients for overall health.",
        "focus_mode": "Focus Mode will help you maintain mental clarity this afternoon.",
        "low_energy": f"Low sleep score ({sleep}) suggests fatigue. This blend provides gentle energy.",
        "post_workout": f"High strain day ({strain}). Post-Workout will accelerate recovery.",
    }

    return reasons.get(mix_id, f"Recommended based on your health data and current time ({time_of_day}).")


@router.get("/{user_id}/history")
async def get_mix_history(
    user_id: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get user's recent dispense history.

    Shows what mixes/supplements have been dispensed recently.
    """
    from datetime import timedelta

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    start_date = datetime.combine(
        date.today() - timedelta(days=days),
        datetime.min.time()
    )

    logs = db.query(DispenseLog).filter(
        DispenseLog.user_id == user_id,
        DispenseLog.dispensed_at >= start_date
    ).order_by(DispenseLog.dispensed_at.desc()).all()

    # Group by day
    by_day = {}
    for log in logs:
        day = log.dispensed_at.date().isoformat()
        if day not in by_day:
            by_day[day] = []
        by_day[day].append({
            "supplement_id": log.supplement_name,
            "dose": log.dose,
            "unit": log.unit,
            "time": log.dispensed_at.strftime("%H:%M")
        })

    return {
        "user_id": user_id,
        "days": days,
        "history": by_day
    }


@router.get("/{user_id}/{mix_id}")
async def get_mix_details(
    user_id: str,
    mix_id: str,
    db: Session = Depends(get_db)
) -> MixResponse:
    """
    Get personalized mix details for a user.

    Calculates doses based on user profile and checks daily limits.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mix = mix_engine.get_mix_by_id(mix_id)
    if not mix:
        raise HTTPException(status_code=404, detail="Mix not found")

    # Get user profile
    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex
    }

    # Get what's been dispensed today
    dispensed_today = _get_dispensed_today(user_id, db)

    # Calculate mix doses
    result = mix_engine.calculate_mix_doses(mix, user_profile, dispensed_today)

    return MixResponse(**result)


@router.post("/{user_id}/{mix_id}/dispense")
async def dispense_mix(
    user_id: str,
    mix_id: str,
    db: Session = Depends(get_db)
):
    """
    Dispense a complete mix for a user.

    Records all supplements in the mix as dispensed.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mix = mix_engine.get_mix_by_id(mix_id)
    if not mix:
        raise HTTPException(status_code=404, detail="Mix not found")

    # Check time window
    time_of_day = rules.get_time_of_day()
    if time_of_day not in mix.time_windows:
        raise HTTPException(
            status_code=400,
            detail=f"{mix.name} is not available during {time_of_day}. Available: {', '.join(mix.time_windows)}"
        )

    # Get user profile
    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex
    }

    # Get what's been dispensed today
    dispensed_today = _get_dispensed_today(user_id, db)

    # Calculate mix doses
    result = mix_engine.calculate_mix_doses(mix, user_profile, dispensed_today)

    # Record each supplement
    dispensed = []
    for supp in result["supplements"]:
        config = rules.supplements.get(supp["supplement_id"])
        if config:
            log = DispenseLog(
                user_id=user_id,
                supplement_name=supp["supplement_id"],
                dose=supp["dose"],
                unit=config.unit
            )
            db.add(log)
            dispensed.append({
                "supplement_id": supp["supplement_id"],
                "name": supp["name"],
                "dose": supp["dose"],
                "unit": supp["unit"]
            })

    db.commit()

    return {
        "status": "dispensed",
        "mix_id": mix_id,
        "mix_name": mix.name,
        "supplements_dispensed": dispensed,
        "total_dispensed": len(dispensed),
        "warnings": result.get("warnings", []),
        "skipped": result.get("skipped", [])
    }


def _get_dispensed_today(user_id: str, db: Session) -> dict:
    """Get total dispensed amounts for today."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    logs = db.query(DispenseLog).filter(
        DispenseLog.user_id == user_id,
        DispenseLog.dispensed_at >= today_start
    ).all()

    dispensed = {}
    for log in logs:
        if log.supplement_name not in dispensed:
            dispensed[log.supplement_name] = 0
        dispensed[log.supplement_name] += log.dose

    return dispensed
