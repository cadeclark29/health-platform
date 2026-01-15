from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.models import User
from app.engine import RecommendationEngine

router = APIRouter()
engine = RecommendationEngine()


class TriggerExplanation(BaseModel):
    trigger: str
    description: str
    metric: str
    actual_value: Optional[float]
    threshold: Optional[float]
    comparison: Optional[str]


class SupplementExplanation(BaseModel):
    matched_triggers: List[TriggerExplanation] = []
    evidence: str = ""
    standard_dose: float
    max_daily_dose: float
    time_windows: List[str] = []


class SupplementRecommendation(BaseModel):
    supplement_id: str
    name: str
    dose: float
    unit: str
    reason: str
    explanation: Optional[SupplementExplanation] = None


class DispenseResponse(BaseModel):
    user_id: str
    time_of_day: str
    recommendations: List[SupplementRecommendation]
    reasoning: str
    active_triggers: List[str]


class DispenseConfirm(BaseModel):
    supplement_id: str
    dose: float


class DispenseConfirmResponse(BaseModel):
    status: str
    supplement_id: str
    dose: float
    unit: str


@router.get("/{user_id}", response_model=DispenseResponse)
async def get_dispense_recommendation(
    user_id: str,
    time_override: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get current supplement recommendation for the hardware dispenser.

    This is the main endpoint the dispenser hardware will poll.

    Args:
        user_id: The user's ID
        time_override: Optional hour (0-23) to simulate a different time of day

    Returns:
        List of supplements to dispense with dosages and reasoning
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await engine.get_recommendation(user, db, time_override)

    return DispenseResponse(
        user_id=user_id,
        time_of_day=result["time_of_day"],
        recommendations=[
            SupplementRecommendation(**rec) for rec in result["recommendations"]
        ],
        reasoning=result.get("reasoning", ""),
        active_triggers=result.get("active_triggers", [])
    )


@router.post("/{user_id}/confirm", response_model=DispenseConfirmResponse)
async def confirm_dispense(
    user_id: str,
    confirm: DispenseConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm that a supplement was dispensed.

    The hardware should call this after successfully dispensing a supplement
    to track daily usage limits.

    Args:
        user_id: The user's ID
        confirm: The supplement and dose that was dispensed

    Returns:
        Confirmation of the logged dispense
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        log = engine.record_dispense(
            user_id=user_id,
            supplement_id=confirm.supplement_id,
            dose=confirm.dose,
            db=db
        )
        return DispenseConfirmResponse(
            status="confirmed",
            supplement_id=confirm.supplement_id,
            dose=confirm.dose,
            unit=log.unit
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}/detailed")
async def get_detailed_recommendation(
    user_id: str,
    time_override: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get detailed recommendation with full health context.

    This endpoint provides more information than the dispenser endpoint,
    suitable for display in a mobile app or dashboard.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await engine.get_recommendation(user, db, time_override)

    return {
        "user_id": user_id,
        "user_name": user.name,
        "time_of_day": result["time_of_day"],
        "recommendations": result["recommendations"],
        "reasoning": result.get("reasoning", ""),
        "active_triggers": result.get("active_triggers", []),
        "health_snapshot": result.get("health_snapshot", {})
    }
