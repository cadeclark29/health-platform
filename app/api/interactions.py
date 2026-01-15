from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.models import User, DispenseLog
from app.engine.interactions import interaction_checker

router = APIRouter()


class InteractionCheckRequest(BaseModel):
    supplement_ids: List[str]
    medications: Optional[List[str]] = None


class InteractionResponse(BaseModel):
    supplements: List[str]
    severity: str
    type: str
    description: str
    recommendation: str


class TimingConflict(BaseModel):
    supplements: List[str]
    separation_hours: float
    reason: str


class CycleWarning(BaseModel):
    supplement_id: str
    status: str
    message: str
    needs_cycling: bool
    off_weeks: Optional[int] = None
    days_until_cycle: Optional[int] = None
    reason: Optional[str] = None


class DoseAdjustment(BaseModel):
    adjusted_dose: float
    standard_dose: float
    adjustments_applied: List[dict]
    reasoning: str


class SafetyCheckResponse(BaseModel):
    interactions: List[InteractionResponse]
    timing_conflicts: List[TimingConflict]
    cycle_warnings: List[CycleWarning]
    dose_adjustments: dict


@router.post("/check", response_model=List[InteractionResponse])
async def check_interactions(request: InteractionCheckRequest):
    """
    Check for interactions between a list of supplements.

    Pass supplement IDs and optionally medications to check for conflicts.
    """
    interactions = interaction_checker.check_interactions(
        request.supplement_ids,
        request.medications
    )

    return [
        InteractionResponse(
            supplements=[i.supplement_a, i.supplement_b],
            severity=i.severity,
            type=i.interaction_type,
            description=i.description,
            recommendation=i.recommendation
        )
        for i in interactions
    ]


@router.get("/timing/{supplements}")
async def check_timing_conflicts(supplements: str):
    """
    Check for timing conflicts between supplements.

    Pass comma-separated supplement IDs, e.g., /timing/caffeine,melatonin,zinc
    """
    supplement_list = [s.strip() for s in supplements.split(",")]
    conflicts = interaction_checker.check_timing_conflicts(supplement_list)
    return conflicts


@router.get("/cycle/{supplement_id}")
async def get_cycle_protocol(supplement_id: str):
    """Get cycling protocol for a supplement."""
    protocol = interaction_checker.get_cycle_protocol(supplement_id)

    if not protocol:
        return {
            "supplement_id": supplement_id,
            "needs_cycling": False,
            "message": "No cycling protocol defined for this supplement."
        }

    return {
        "supplement_id": supplement_id,
        "needs_cycling": True,
        "on_weeks": protocol.on_weeks,
        "off_weeks": protocol.off_weeks,
        "max_continuous_days": protocol.max_continuous_days,
        "reason": protocol.reason,
        "pubmed_ids": protocol.pubmed_ids
    }


@router.get("/dose/{supplement_id}")
async def get_adjusted_dose(
    supplement_id: str,
    weight_kg: Optional[float] = None,
    age: Optional[int] = None,
    sex: Optional[str] = None
):
    """
    Get personalized dose recommendation based on user characteristics.

    Pass user profile parameters to get adjusted dosing.
    """
    from app.engine.rules import RulesEngine
    rules = RulesEngine()

    config = rules.supplements.get(supplement_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Unknown supplement: {supplement_id}")

    user_profile = {
        "weight_kg": weight_kg,
        "age": age,
        "sex": sex
    }

    result = interaction_checker.get_adjusted_dose(
        supplement_id,
        config.standard_dose,
        user_profile
    )

    return {
        "supplement_id": supplement_id,
        "supplement_name": config.name,
        "unit": config.unit,
        **result
    }


@router.get("/{user_id}/safety-check", response_model=SafetyCheckResponse)
async def comprehensive_safety_check(
    user_id: str,
    supplements: str,
    db: Session = Depends(get_db)
):
    """
    Comprehensive safety check for a user's supplement list.

    Pass comma-separated supplement IDs to check all safety concerns:
    - Interactions between supplements
    - Timing conflicts
    - Cycling requirements (based on usage history)
    - Personalized dose adjustments
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    supplement_list = [s.strip() for s in supplements.split(",")]

    # Build user profile
    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex
    }

    # Get usage history (consecutive days)
    usage_history = _calculate_usage_history(user_id, supplement_list, db)

    # Get medications from user allergies/contraindications (if stored)
    medications = user.allergies if user.allergies else []

    # Run comprehensive check
    warnings = interaction_checker.get_all_warnings(
        supplement_list,
        user_profile,
        medications,
        usage_history
    )

    # Format response
    return SafetyCheckResponse(
        interactions=[
            InteractionResponse(**i) for i in warnings["interactions"]
        ],
        timing_conflicts=[
            TimingConflict(**t) for t in warnings["timing_conflicts"]
        ],
        cycle_warnings=[
            CycleWarning(**c) for c in warnings["cycle_warnings"]
        ],
        dose_adjustments=warnings["dose_adjustments"]
    )


def _calculate_usage_history(
    user_id: str,
    supplement_ids: List[str],
    db: Session
) -> dict:
    """
    Calculate consecutive days of use for each supplement.

    Looks at dispense history to determine how many consecutive
    days each supplement has been taken.
    """
    from datetime import date, timedelta

    history = {}
    today = date.today()

    for supp_id in supplement_ids:
        consecutive_days = 0
        check_date = today

        # Look back up to 120 days
        for _ in range(120):
            # Check if dispensed on this date
            log = db.query(DispenseLog).filter(
                DispenseLog.user_id == user_id,
                DispenseLog.supplement_name == supp_id,
                DispenseLog.dispensed_at >= check_date,
                DispenseLog.dispensed_at < check_date + timedelta(days=1)
            ).first()

            if log:
                consecutive_days += 1
                check_date -= timedelta(days=1)
            else:
                break

        if consecutive_days > 0:
            history[supp_id] = consecutive_days

    return history


@router.get("/supplements")
async def list_supplement_info():
    """
    Get all supplement information including cycling and interaction data.
    """
    from app.engine.rules import RulesEngine
    rules = RulesEngine()

    supplements_info = []

    for supp_id, config in rules.supplements.items():
        cycle_protocol = interaction_checker.get_cycle_protocol(supp_id)

        info = {
            "id": supp_id,
            "name": config.name,
            "unit": config.unit,
            "standard_dose": config.standard_dose,
            "max_daily_dose": config.max_daily_dose,
            "time_windows": config.time_windows,
            "triggers": list(config.triggers.keys()),
            "contraindications": config.contraindications,
            "evidence": config.evidence,
            "has_cycle_protocol": cycle_protocol is not None,
            "cycle_protocol": {
                "on_weeks": cycle_protocol.on_weeks,
                "off_weeks": cycle_protocol.off_weeks,
                "max_continuous_days": cycle_protocol.max_continuous_days,
                "reason": cycle_protocol.reason
            } if cycle_protocol else None
        }
        supplements_info.append(info)

    return {"supplements": supplements_info}
