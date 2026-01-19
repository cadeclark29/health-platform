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


class DoseAdjustmentInfo(BaseModel):
    adjusted_dose: float
    standard_dose: float
    adjustments_applied: List[dict] = []
    reasoning: str = ""


class SupplementExplanation(BaseModel):
    matched_triggers: List[TriggerExplanation] = []
    evidence: str = ""
    standard_dose: float
    max_daily_dose: float
    time_windows: List[str] = []
    dose_adjustment: Optional[DoseAdjustmentInfo] = None


class SupplementRecommendation(BaseModel):
    supplement_id: str
    name: str
    dose: float
    unit: str
    reason: str
    explanation: Optional[SupplementExplanation] = None


class InteractionWarning(BaseModel):
    supplements: List[str]
    severity: str
    type: str
    description: str
    recommendation: str


class CycleWarning(BaseModel):
    supplement_id: str
    status: str
    message: str
    needs_cycling: bool
    off_weeks: Optional[int] = None
    days_until_cycle: Optional[int] = None
    reason: Optional[str] = None


class HeldSupplement(BaseModel):
    id: str
    name: str
    reason: str
    trigger: Optional[str] = None


class DynamicIntelligence(BaseModel):
    overall_status: str
    active_conditions: List[dict] = []
    compound_conditions: List[str] = []
    held_supplements: List[HeldSupplement] = []
    alerts: List[str] = []


class DispenseResponse(BaseModel):
    user_id: str
    time_of_day: str
    recommendations: List[SupplementRecommendation]
    reasoning: str
    active_triggers: List[str]
    using_baseline: Optional[bool] = False
    has_checkin: Optional[bool] = False
    interaction_warnings: List[InteractionWarning] = []
    cycle_warnings: List[CycleWarning] = []
    dynamic_intelligence: Optional[DynamicIntelligence] = None


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

    # Build dynamic intelligence info if available
    dynamic_intel = result.get("dynamic_intelligence")
    dynamic_response = None
    if dynamic_intel:
        dynamic_response = DynamicIntelligence(
            overall_status=dynamic_intel.get("overall_status", "optimal"),
            active_conditions=dynamic_intel.get("active_conditions", []),
            compound_conditions=dynamic_intel.get("compound_conditions", []),
            held_supplements=[
                HeldSupplement(**h) for h in dynamic_intel.get("held_supplements", [])
            ],
            alerts=dynamic_intel.get("alerts", [])
        )

    return DispenseResponse(
        user_id=user_id,
        time_of_day=result["time_of_day"],
        recommendations=[
            SupplementRecommendation(**rec) for rec in result["recommendations"]
        ],
        reasoning=result.get("reasoning", ""),
        active_triggers=result.get("active_triggers", []),
        using_baseline=result.get("using_baseline", False),
        has_checkin=result.get("has_checkin", False),
        interaction_warnings=[
            InteractionWarning(**w) for w in result.get("interaction_warnings", [])
        ],
        cycle_warnings=[
            CycleWarning(**w) for w in result.get("cycle_warnings", [])
        ],
        dynamic_intelligence=dynamic_response
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
        "health_snapshot": result.get("health_snapshot", {}),
        "interaction_warnings": result.get("interaction_warnings", []),
        "cycle_warnings": result.get("cycle_warnings", []),
        "dynamic_intelligence": result.get("dynamic_intelligence")
    }
