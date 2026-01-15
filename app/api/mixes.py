from typing import List, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.models import User, HealthData, DispenseLog, CustomBlend
from app.engine.mixes import mix_engine, SUPPLEMENT_MIXES
from app.engine.rules import RulesEngine
from app.engine.interactions import interaction_checker
from app.engine.llm import llm_personalizer

router = APIRouter()
blends_router = APIRouter()  # Separate router for custom blends (needs to be registered first)
rules = RulesEngine()


class MixSupplement(BaseModel):
    supplement_id: str
    name: str
    dose: float
    unit: str
    standard_dose: float
    adjusted_from: Optional[float] = None
    adjustments: Optional[List[dict]] = None
    intelligence_notes: Optional[List[str]] = None


class IntelligenceInsight(BaseModel):
    supplement: str
    insight: str
    type: str  # seasonal_adjustment, tolerance_cycle, timing_optimization, etc.


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
    intelligence_insights: List[IntelligenceInsight] = []
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
    time_override: Optional[int] = None,
    date_override: Optional[str] = None,
    db: Session = Depends(get_db)
) -> MixResponse:
    """
    Get personalized mix details for a user.

    Calculates doses based on user profile and checks daily limits.
    Includes caffeine timing warnings based on time and sleep data.

    Args:
        time_override: Hour (0-23) to simulate different time of day
        date_override: Date (YYYY-MM-DD) to check limits against a specific day
    """
    # Reserved paths - don't treat as mix_id
    if mix_id in ("custom", "tracking", "smart", "history"):
        raise HTTPException(status_code=404, detail="Mix not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mix = mix_engine.get_mix_by_id(mix_id)
    if not mix:
        raise HTTPException(status_code=404, detail="Mix not found")

    # Parse date override
    target_date = date.today()
    if date_override:
        try:
            target_date = datetime.strptime(date_override, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Get current hour
    current_hour = time_override if time_override is not None else datetime.now().hour

    # Get user's latest health data for intelligence
    latest_health = db.query(HealthData).filter(
        HealthData.user_id == user_id
    ).order_by(HealthData.timestamp.desc()).first()
    sleep_score = latest_health.sleep_score if latest_health else None

    # Build health_data dict for intelligence module
    health_data = {}
    if latest_health:
        health_data = {
            "sleep_score": latest_health.sleep_score,
            "recovery_score": latest_health.recovery_score,
            "hrv_score": latest_health.hrv_score,
            "strain_score": latest_health.strain_score,
            "resting_hr": latest_health.resting_hr
        }

    # Get user profile with lifestyle factors
    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex,
        "region": user.region,
        "activity_level": user.activity_level,
        "work_environment": user.work_environment,
        "diet_type": user.diet_type,
        "bedtime": user.bedtime,
        "wake_time": user.wake_time,
        "chronotype": user.chronotype,
    }

    # Get usage history for tolerance detection
    usage_history = _get_usage_history(user_id, db, days=30)

    # Get what's been dispensed on the target date
    dispensed_on_date = _get_dispensed_for_date(user_id, target_date, db)

    # Get latitude from user's region
    user_latitude = user.latitude if hasattr(user, 'latitude') else None

    # Calculate mix doses with intelligence
    result = mix_engine.calculate_mix_doses(
        mix, user_profile, dispensed_on_date,
        current_hour=current_hour,
        sleep_score=sleep_score,
        health_data=health_data,
        usage_history=usage_history,
        user_latitude=user_latitude
    )

    return MixResponse(**result)


@router.post("/{user_id}/{mix_id}/dispense")
async def dispense_mix(
    user_id: str,
    mix_id: str,
    time_override: Optional[int] = None,
    date_override: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Dispense a complete mix for a user.

    Records all supplements in the mix as dispensed.

    Args:
        time_override: Hour (0-23) to simulate different time of day
        date_override: Date (YYYY-MM-DD) to simulate dispensing on a different day
    """
    # Reserved paths - don't treat as mix_id
    if mix_id in ("custom", "tracking", "smart", "history"):
        raise HTTPException(status_code=404, detail="Mix not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mix = mix_engine.get_mix_by_id(mix_id)
    if not mix:
        raise HTTPException(status_code=404, detail="Mix not found")

    # Parse date override
    target_date = date.today()
    if date_override:
        try:
            target_date = datetime.strptime(date_override, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Check time window
    time_of_day = rules.get_time_of_day(time_override)
    if time_of_day not in mix.time_windows:
        raise HTTPException(
            status_code=400,
            detail=f"{mix.name} is not available during {time_of_day}. Available: {', '.join(mix.time_windows)}"
        )

    # Get current hour
    current_hour = time_override if time_override is not None else datetime.now().hour

    # Get user's latest health data for intelligence
    latest_health = db.query(HealthData).filter(
        HealthData.user_id == user_id
    ).order_by(HealthData.timestamp.desc()).first()
    sleep_score = latest_health.sleep_score if latest_health else None

    # Build health_data dict for intelligence module
    health_data = {}
    if latest_health:
        health_data = {
            "sleep_score": latest_health.sleep_score,
            "recovery_score": latest_health.recovery_score,
            "hrv_score": latest_health.hrv_score,
            "strain_score": latest_health.strain_score,
            "resting_hr": latest_health.resting_hr
        }

    # Get user profile with lifestyle factors
    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex,
        "region": user.region,
        "activity_level": user.activity_level,
        "work_environment": user.work_environment,
        "diet_type": user.diet_type,
        "bedtime": user.bedtime,
        "wake_time": user.wake_time,
        "chronotype": user.chronotype,
    }

    # Get usage history for tolerance detection
    usage_history = _get_usage_history(user_id, db, days=30)

    # Get what's been dispensed on the target date
    dispensed_on_date = _get_dispensed_for_date(user_id, target_date, db)

    # Get latitude from user's region
    user_latitude = user.latitude if hasattr(user, 'latitude') else None

    # Calculate mix doses with intelligence
    result = mix_engine.calculate_mix_doses(
        mix, user_profile, dispensed_on_date,
        current_hour=current_hour,
        sleep_score=sleep_score,
        health_data=health_data,
        usage_history=usage_history,
        user_latitude=user_latitude
    )

    # Create timestamp for the target date with the override time
    hour = time_override if time_override is not None else 12
    dispense_timestamp = datetime.combine(target_date, datetime.min.time().replace(hour=hour))

    # Record each supplement
    dispensed = []
    for supp in result["supplements"]:
        config = rules.supplements.get(supp["supplement_id"])
        if config:
            log = DispenseLog(
                user_id=user_id,
                supplement_name=supp["supplement_id"],
                dose=supp["dose"],
                unit=config.unit,
                dispensed_at=dispense_timestamp
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
        "date": target_date.isoformat(),
        "supplements_dispensed": dispensed,
        "total_dispensed": len(dispensed),
        "warnings": result.get("warnings", []),
        "skipped": result.get("skipped", []),
        "intelligence_insights": result.get("intelligence_insights", [])
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


def _get_dispensed_for_date(user_id: str, target_date: date, db: Session) -> dict:
    """Get total dispensed amounts for a specific date."""
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    logs = db.query(DispenseLog).filter(
        DispenseLog.user_id == user_id,
        DispenseLog.dispensed_at >= day_start,
        DispenseLog.dispensed_at < day_end
    ).all()

    dispensed = {}
    for log in logs:
        if log.supplement_name not in dispensed:
            dispensed[log.supplement_name] = 0
        dispensed[log.supplement_name] += log.dose

    return dispensed


def _get_usage_history(user_id: str, db: Session, days: int = 30) -> dict:
    """Get supplement usage history for intelligence analysis."""
    start_date = datetime.combine(date.today() - timedelta(days=days), datetime.min.time())

    logs = db.query(DispenseLog).filter(
        DispenseLog.user_id == user_id,
        DispenseLog.dispensed_at >= start_date
    ).order_by(DispenseLog.dispensed_at.desc()).all()

    usage = {}
    for log in logs:
        supp_id = log.supplement_name
        if supp_id not in usage:
            usage[supp_id] = {
                "last_taken": None,
                "days_used_last_14": 0,
                "total_doses": 0,
                "dates": []
            }

        log_date = log.dispensed_at.date()
        if usage[supp_id]["last_taken"] is None:
            usage[supp_id]["last_taken"] = log_date.isoformat()

        if log_date not in usage[supp_id]["dates"]:
            usage[supp_id]["dates"].append(log_date)
            if (date.today() - log_date).days <= 14:
                usage[supp_id]["days_used_last_14"] += 1

        usage[supp_id]["total_doses"] += 1

    return usage


@router.get("/{user_id}/tracking/daily")
async def get_daily_tracking(
    user_id: str,
    date_str: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get daily supplement intake vs daily limits.

    Args:
        date_str: Optional date in YYYY-MM-DD format. Defaults to today.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    target_date = date.today()
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    dispensed = _get_dispensed_for_date(user_id, target_date, db)

    # Build tracking data with limits
    tracking = []
    for supp_id, config in rules.supplements.items():
        taken = dispensed.get(supp_id, 0)
        if taken > 0 or config.max_daily_dose > 0:
            tracking.append({
                "supplement_id": supp_id,
                "name": config.name,
                "taken": taken,
                "max_daily": config.max_daily_dose,
                "unit": config.unit,
                "percentage": min(100, round((taken / config.max_daily_dose) * 100)) if config.max_daily_dose > 0 else 0
            })

    # Sort by percentage taken (highest first)
    tracking.sort(key=lambda x: x["percentage"], reverse=True)

    # Filter to only show supplements with intake
    active_tracking = [t for t in tracking if t["taken"] > 0]

    return {
        "user_id": user_id,
        "date": target_date.isoformat(),
        "supplements": active_tracking
    }


@router.get("/{user_id}/tracking/weekly")
async def get_weekly_tracking(
    user_id: str,
    end_date_str: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get weekly supplement totals (last 7 days).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    end_date = date.today()
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    start_date = end_date - timedelta(days=6)

    # Get all logs for the week
    week_start = datetime.combine(start_date, datetime.min.time())
    week_end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

    logs = db.query(DispenseLog).filter(
        DispenseLog.user_id == user_id,
        DispenseLog.dispensed_at >= week_start,
        DispenseLog.dispensed_at < week_end
    ).all()

    # Aggregate by supplement
    weekly_totals = {}
    daily_breakdown = {}

    for log in logs:
        supp = log.supplement_name
        day = log.dispensed_at.date().isoformat()

        if supp not in weekly_totals:
            weekly_totals[supp] = 0
            daily_breakdown[supp] = {}

        weekly_totals[supp] += log.dose

        if day not in daily_breakdown[supp]:
            daily_breakdown[supp][day] = 0
        daily_breakdown[supp][day] += log.dose

    # Build response with supplement info
    supplements = []
    for supp_id, total in weekly_totals.items():
        config = rules.supplements.get(supp_id)
        if config:
            supplements.append({
                "supplement_id": supp_id,
                "name": config.name,
                "weekly_total": total,
                "weekly_max": config.max_daily_dose * 7,
                "unit": config.unit,
                "daily_breakdown": daily_breakdown.get(supp_id, {}),
                "days_taken": len(daily_breakdown.get(supp_id, {}))
            })

    supplements.sort(key=lambda x: x["weekly_total"], reverse=True)

    return {
        "user_id": user_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "supplements": supplements
    }


# PubMed study links for each supplement
PUBMED_LINKS = {
    "vitamin_d3": [
        {"title": "Vitamin D and Health Outcomes", "pmid": "32690727", "url": "https://pubmed.ncbi.nlm.nih.gov/32690727/"},
        {"title": "Vitamin D Supplementation Guidelines", "pmid": "33146667", "url": "https://pubmed.ncbi.nlm.nih.gov/33146667/"},
    ],
    "magnesium_glycinate": [
        {"title": "Magnesium and Sleep Quality", "pmid": "34883514", "url": "https://pubmed.ncbi.nlm.nih.gov/34883514/"},
        {"title": "Magnesium in Stress and Anxiety", "pmid": "28445426", "url": "https://pubmed.ncbi.nlm.nih.gov/28445426/"},
    ],
    "vitamin_b12": [
        {"title": "B12 and Cognitive Function", "pmid": "27654807", "url": "https://pubmed.ncbi.nlm.nih.gov/27654807/"},
        {"title": "B12 Supplementation Review", "pmid": "29077210", "url": "https://pubmed.ncbi.nlm.nih.gov/29077210/"},
    ],
    "omega_3": [
        {"title": "Omega-3 and Cardiovascular Health", "pmid": "31567003", "url": "https://pubmed.ncbi.nlm.nih.gov/31567003/"},
        {"title": "EPA/DHA and Inflammation", "pmid": "28900017", "url": "https://pubmed.ncbi.nlm.nih.gov/28900017/"},
    ],
    "creatine": [
        {"title": "Creatine Supplementation and Exercise", "pmid": "28615996", "url": "https://pubmed.ncbi.nlm.nih.gov/28615996/"},
        {"title": "Creatine Safety and Efficacy", "pmid": "32359762", "url": "https://pubmed.ncbi.nlm.nih.gov/32359762/"},
        {"title": "Creatine and Cognitive Function", "pmid": "29704637", "url": "https://pubmed.ncbi.nlm.nih.gov/29704637/"},
    ],
    "l_theanine": [
        {"title": "L-Theanine and Stress Reduction", "pmid": "31758301", "url": "https://pubmed.ncbi.nlm.nih.gov/31758301/"},
        {"title": "L-Theanine and Sleep Quality", "pmid": "31623400", "url": "https://pubmed.ncbi.nlm.nih.gov/31623400/"},
    ],
    "caffeine": [
        {"title": "Caffeine and Cognitive Performance", "pmid": "26677204", "url": "https://pubmed.ncbi.nlm.nih.gov/26677204/"},
        {"title": "Caffeine and Exercise Performance", "pmid": "31876380", "url": "https://pubmed.ncbi.nlm.nih.gov/31876380/"},
    ],
    "ashwagandha": [
        {"title": "Ashwagandha and Stress/Anxiety", "pmid": "32021735", "url": "https://pubmed.ncbi.nlm.nih.gov/32021735/"},
        {"title": "Ashwagandha and Cortisol", "pmid": "23439798", "url": "https://pubmed.ncbi.nlm.nih.gov/23439798/"},
    ],
    "melatonin": [
        {"title": "Melatonin and Sleep Disorders", "pmid": "28648359", "url": "https://pubmed.ncbi.nlm.nih.gov/28648359/"},
        {"title": "Low-dose Melatonin Efficacy", "pmid": "15649745", "url": "https://pubmed.ncbi.nlm.nih.gov/15649745/"},
    ],
    "glycine": [
        {"title": "Glycine and Sleep Quality", "pmid": "22529837", "url": "https://pubmed.ncbi.nlm.nih.gov/22529837/"},
        {"title": "Glycine Effects on Sleep", "pmid": "17296677", "url": "https://pubmed.ncbi.nlm.nih.gov/17296677/"},
    ],
    "vitamin_c": [
        {"title": "Vitamin C and Immune Function", "pmid": "29099763", "url": "https://pubmed.ncbi.nlm.nih.gov/29099763/"},
        {"title": "Vitamin C and Physical Activity", "pmid": "28353648", "url": "https://pubmed.ncbi.nlm.nih.gov/28353648/"},
    ],
    "zinc": [
        {"title": "Zinc and Immune Response", "pmid": "27193603", "url": "https://pubmed.ncbi.nlm.nih.gov/27193603/"},
        {"title": "Zinc Supplementation Review", "pmid": "28515951", "url": "https://pubmed.ncbi.nlm.nih.gov/28515951/"},
    ],
    "coq10": [
        {"title": "CoQ10 and Energy Metabolism", "pmid": "29587774", "url": "https://pubmed.ncbi.nlm.nih.gov/29587774/"},
        {"title": "Ubiquinol vs Ubiquinone", "pmid": "31141234", "url": "https://pubmed.ncbi.nlm.nih.gov/31141234/"},
    ],
    "lions_mane": [
        {"title": "Lion's Mane and Cognitive Function", "pmid": "31413233", "url": "https://pubmed.ncbi.nlm.nih.gov/31413233/"},
        {"title": "Lion's Mane Neuroprotection", "pmid": "24266378", "url": "https://pubmed.ncbi.nlm.nih.gov/24266378/"},
    ],
    "nac": [
        {"title": "NAC and Oxidative Stress", "pmid": "28753185", "url": "https://pubmed.ncbi.nlm.nih.gov/28753185/"},
        {"title": "NAC Clinical Applications", "pmid": "25925875", "url": "https://pubmed.ncbi.nlm.nih.gov/25925875/"},
    ],
    "vitamin_k2": [
        {"title": "Vitamin K2 and Bone Health", "pmid": "30621299", "url": "https://pubmed.ncbi.nlm.nih.gov/30621299/"},
        {"title": "K2 and Calcium Metabolism", "pmid": "25636220", "url": "https://pubmed.ncbi.nlm.nih.gov/25636220/"},
    ],
    "l_citrulline": [
        {"title": "Citrulline and Exercise Performance", "pmid": "28944645", "url": "https://pubmed.ncbi.nlm.nih.gov/28944645/"},
        {"title": "Citrulline and Blood Flow", "pmid": "27749691", "url": "https://pubmed.ncbi.nlm.nih.gov/27749691/"},
    ],
    "electrolytes": [
        {"title": "Electrolyte Balance in Exercise", "pmid": "17277604", "url": "https://pubmed.ncbi.nlm.nih.gov/17277604/"},
    ],
    "blackseed_oil": [
        {"title": "Nigella Sativa Health Benefits", "pmid": "27630008", "url": "https://pubmed.ncbi.nlm.nih.gov/27630008/"},
        {"title": "Black Seed and Immune Function", "pmid": "28068557", "url": "https://pubmed.ncbi.nlm.nih.gov/28068557/"},
    ],
    "apigenin": [
        {"title": "Apigenin Health Effects", "pmid": "26339191", "url": "https://pubmed.ncbi.nlm.nih.gov/26339191/"},
    ],
    "magnesium_l_threonate": [
        {"title": "Mg-L-Threonate and Brain Magnesium", "pmid": "20152124", "url": "https://pubmed.ncbi.nlm.nih.gov/20152124/"},
        {"title": "Magnesium and Cognitive Aging", "pmid": "26519439", "url": "https://pubmed.ncbi.nlm.nih.gov/26519439/"},
    ],
}


@router.get("/catalog")
async def get_supplement_catalog():
    """
    Get full supplement catalog with info, dosing, and PubMed study links.

    Returns all available supplements with their details for building custom blends.
    """
    catalog = []
    for supp_id, config in rules.supplements.items():
        catalog.append({
            "id": supp_id,
            "name": config.name,
            "unit": config.unit,
            "standard_dose": config.standard_dose,
            "max_daily_dose": config.max_daily_dose,
            "time_windows": config.time_windows,
            "description": _get_supplement_description(supp_id),
            "benefits": _get_supplement_benefits(supp_id),
            "pubmed_studies": PUBMED_LINKS.get(supp_id, []),
            "category": _get_supplement_category(supp_id)
        })

    # Sort by category then name
    catalog.sort(key=lambda x: (x["category"], x["name"]))
    return {"supplements": catalog}


class BlendSuggestionRequest(BaseModel):
    user_request: str
    user_id: Optional[str] = None


@router.post("/suggest-blend")
async def suggest_blend(
    request: BlendSuggestionRequest,
    db: Session = Depends(get_db)
):
    """
    Use AI to suggest a custom blend based on user's goals.

    Provide a natural language description of what you want (e.g., "better sleep",
    "more energy without jitters", "help with stress and focus") and get
    supplement suggestions with doses.
    """
    # Build supplement catalog for AI
    catalog = []
    for supp_id, config in rules.supplements.items():
        catalog.append({
            "id": supp_id,
            "name": config.name,
            "unit": config.unit,
            "standard_dose": config.standard_dose,
            "max_daily_dose": config.max_daily_dose,
            "time_windows": config.time_windows,
            "description": _get_supplement_description(supp_id),
            "benefits": _get_supplement_benefits(supp_id),
        })

    # Get user profile if provided
    user_profile = None
    if request.user_id:
        user = db.query(User).filter(User.id == request.user_id).first()
        if user:
            user_profile = {
                "age": user.age,
                "sex": user.sex,
                "weight_kg": user.weight_kg
            }

    # Get AI suggestion
    suggestion = await llm_personalizer.suggest_blend(
        request.user_request,
        catalog,
        user_profile
    )

    return suggestion


def _get_supplement_description(supp_id: str) -> str:
    """Get a brief description of the supplement."""
    descriptions = {
        "vitamin_d3": "The sunshine vitamin - essential for bone health, immune function, and mood regulation.",
        "magnesium_glycinate": "Highly absorbable magnesium bound to glycine - great for sleep, stress, and muscle recovery.",
        "vitamin_b12": "Essential for energy production, nerve function, and red blood cell formation.",
        "omega_3": "EPA and DHA fatty acids - supports heart, brain, and reduces inflammation.",
        "creatine": "Most researched sports supplement - enhances strength, power, and cognitive function.",
        "l_theanine": "Amino acid from tea - promotes calm focus without drowsiness.",
        "caffeine": "Natural stimulant - improves alertness, focus, and exercise performance.",
        "ashwagandha": "Adaptogenic herb - helps body manage stress and supports hormonal balance.",
        "melatonin": "Sleep hormone - helps regulate circadian rhythm and improve sleep onset.",
        "glycine": "Amino acid - improves sleep quality and supports collagen production.",
        "vitamin_c": "Powerful antioxidant - supports immune function and collagen synthesis.",
        "zinc": "Essential mineral - crucial for immune function, wound healing, and protein synthesis.",
        "coq10": "Cellular energy producer - supports heart health and energy metabolism.",
        "lions_mane": "Medicinal mushroom - supports cognitive function and nerve growth factor.",
        "nac": "Precursor to glutathione - powerful antioxidant and liver support.",
        "vitamin_k2": "Directs calcium to bones - works synergistically with Vitamin D3.",
        "l_citrulline": "Amino acid - boosts nitric oxide for improved blood flow and performance.",
        "electrolytes": "Essential minerals - maintain hydration and support muscle function.",
        "blackseed_oil": "Traditional remedy - supports immune function with thymoquinone.",
        "apigenin": "Flavonoid from chamomile - promotes relaxation and sleep.",
        "magnesium_l_threonate": "Brain-penetrating magnesium - supports cognitive function and memory.",
    }
    return descriptions.get(supp_id, "A dietary supplement for health optimization.")


def _get_supplement_benefits(supp_id: str) -> List[str]:
    """Get key benefits of the supplement."""
    benefits = {
        "vitamin_d3": ["Immune support", "Bone health", "Mood regulation", "Energy"],
        "magnesium_glycinate": ["Better sleep", "Stress relief", "Muscle relaxation", "Recovery"],
        "vitamin_b12": ["Energy production", "Nerve health", "Mental clarity"],
        "omega_3": ["Heart health", "Brain function", "Anti-inflammatory", "Joint support"],
        "creatine": ["Strength", "Power output", "Cognitive function", "Muscle recovery"],
        "l_theanine": ["Calm focus", "Stress relief", "Sleep quality", "Anxiety reduction"],
        "caffeine": ["Alertness", "Focus", "Physical performance", "Metabolism"],
        "ashwagandha": ["Stress adaptation", "Cortisol balance", "Energy", "Sleep"],
        "melatonin": ["Sleep onset", "Circadian rhythm", "Jet lag recovery"],
        "glycine": ["Deep sleep", "Recovery", "Collagen support"],
        "vitamin_c": ["Immune boost", "Antioxidant", "Skin health", "Iron absorption"],
        "zinc": ["Immune function", "Wound healing", "Testosterone support"],
        "coq10": ["Cellular energy", "Heart health", "Antioxidant"],
        "lions_mane": ["Cognitive function", "Nerve growth", "Focus", "Memory"],
        "nac": ["Liver support", "Antioxidant", "Respiratory health"],
        "vitamin_k2": ["Calcium direction", "Bone strength", "Arterial health"],
        "l_citrulline": ["Blood flow", "Pump", "Endurance", "Recovery"],
        "electrolytes": ["Hydration", "Muscle function", "Energy"],
        "blackseed_oil": ["Immune support", "Anti-inflammatory", "Antioxidant"],
        "apigenin": ["Relaxation", "Sleep", "Anti-anxiety"],
        "magnesium_l_threonate": ["Brain health", "Memory", "Cognitive function", "Sleep"],
    }
    return benefits.get(supp_id, ["General wellness"])


def _get_supplement_category(supp_id: str) -> str:
    """Categorize supplements."""
    categories = {
        "vitamin_d3": "vitamins",
        "vitamin_b12": "vitamins",
        "vitamin_c": "vitamins",
        "vitamin_k2": "vitamins",
        "magnesium_glycinate": "minerals",
        "magnesium_l_threonate": "minerals",
        "zinc": "minerals",
        "electrolytes": "minerals",
        "omega_3": "fatty_acids",
        "creatine": "performance",
        "l_citrulline": "performance",
        "caffeine": "performance",
        "l_theanine": "amino_acids",
        "glycine": "amino_acids",
        "nac": "amino_acids",
        "ashwagandha": "adaptogens",
        "lions_mane": "nootropics",
        "coq10": "antioxidants",
        "melatonin": "sleep",
        "apigenin": "sleep",
        "blackseed_oil": "herbals",
    }
    return categories.get(supp_id, "other")


# Custom Blend endpoints
class CustomBlendCreate(BaseModel):
    name: str
    icon: str = "🧪"
    description: str = ""
    components: List[dict]  # [{supplement_id, dose_multiplier}]


class CustomBlendResponse(BaseModel):
    id: str
    user_id: str
    name: str
    icon: str
    description: str
    components: List[dict]
    created_at: Optional[str]


@blends_router.get("/{user_id}")
async def get_user_custom_blends(
    user_id: str,
    db: Session = Depends(get_db)
) -> List[CustomBlendResponse]:
    """Get all custom blends created by a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    blends = db.query(CustomBlend).filter(CustomBlend.user_id == user_id).all()

    return [
        CustomBlendResponse(
            id=b.id,
            user_id=b.user_id,
            name=b.name,
            icon=b.icon,
            description=b.description,
            components=b.components,
            created_at=b.created_at.isoformat() if b.created_at else None
        )
        for b in blends
    ]


@blends_router.post("/{user_id}")
async def create_custom_blend(
    user_id: str,
    blend_data: CustomBlendCreate,
    db: Session = Depends(get_db)
) -> CustomBlendResponse:
    """Create a new custom blend for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate components
    for comp in blend_data.components:
        if "supplement_id" not in comp:
            raise HTTPException(status_code=400, detail="Each component must have supplement_id")
        if comp["supplement_id"] not in rules.supplements:
            raise HTTPException(status_code=400, detail=f"Unknown supplement: {comp['supplement_id']}")

    blend = CustomBlend(
        user_id=user_id,
        name=blend_data.name,
        icon=blend_data.icon,
        description=blend_data.description,
        components=blend_data.components
    )
    db.add(blend)
    db.commit()
    db.refresh(blend)

    return CustomBlendResponse(
        id=blend.id,
        user_id=blend.user_id,
        name=blend.name,
        icon=blend.icon,
        description=blend.description,
        components=blend.components,
        created_at=blend.created_at.isoformat() if blend.created_at else None
    )


@blends_router.delete("/{user_id}/{blend_id}")
async def delete_custom_blend(
    user_id: str,
    blend_id: str,
    db: Session = Depends(get_db)
):
    """Delete a custom blend."""
    blend = db.query(CustomBlend).filter(
        CustomBlend.id == blend_id,
        CustomBlend.user_id == user_id
    ).first()

    if not blend:
        raise HTTPException(status_code=404, detail="Custom blend not found")

    db.delete(blend)
    db.commit()

    return {"status": "deleted", "blend_id": blend_id}


@blends_router.get("/{user_id}/{blend_id}/preview")
async def preview_custom_blend(
    user_id: str,
    blend_id: str,
    date_override: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Preview a custom blend with personalized doses.

    Shows what supplements and doses will be dispensed.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    blend = db.query(CustomBlend).filter(
        CustomBlend.id == blend_id,
        CustomBlend.user_id == user_id
    ).first()

    if not blend:
        raise HTTPException(status_code=404, detail="Custom blend not found")

    # Parse date
    target_date = date.today()
    if date_override:
        try:
            target_date = datetime.strptime(date_override, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex
    }

    dispensed_on_date = _get_dispensed_for_date(user_id, target_date, db)

    # Calculate doses for each component
    supplements = []
    skipped = []
    warnings = []

    for comp in blend.components:
        supp_id = comp["supplement_id"]
        # Support both new 'dose' field and legacy 'dose_multiplier'
        if "dose" in comp:
            requested_dose = comp["dose"]
        else:
            dose_mult = comp.get("dose_multiplier", 1.0)
            requested_dose = config.standard_dose * dose_mult if config else 0

        config = rules.supplements.get(supp_id)
        if not config:
            skipped.append({"supplement_id": supp_id, "reason": "Unknown supplement"})
            continue

        # Use the requested dose directly (already specified by user)
        dose = requested_dose

        # Check daily limit
        already = dispensed_on_date.get(supp_id, 0)
        remaining = config.max_daily_dose - already

        if remaining <= 0:
            skipped.append({
                "supplement_id": supp_id,
                "name": config.name,
                "reason": "Daily limit reached"
            })
            continue

        final_dose = min(dose, remaining)
        if final_dose < dose * 0.5:
            warnings.append({
                "supplement_id": supp_id,
                "name": config.name,
                "message": f"Reduced to {final_dose}{config.unit} (daily limit)"
            })

        supplements.append({
            "supplement_id": supp_id,
            "name": config.name,
            "dose": round(final_dose, 1),
            "unit": config.unit,
            "standard_dose": config.standard_dose
        })

    # Check interactions
    supp_ids = [s["supplement_id"] for s in supplements]
    interactions = interaction_checker.check_interactions(supp_ids)
    interaction_warnings = [
        {
            "supplements": [i.supplement_a, i.supplement_b],
            "severity": i.severity,
            "type": i.interaction_type,
            "description": i.description
        }
        for i in interactions if i.interaction_type != "synergy"
    ]

    return {
        "blend_id": blend_id,
        "blend_name": blend.name,
        "blend_icon": blend.icon,
        "supplements": supplements,
        "skipped": skipped,
        "warnings": warnings,
        "interaction_warnings": interaction_warnings,
        "total_supplements": len(supplements)
    }


@blends_router.post("/{user_id}/{blend_id}/dispense")
async def dispense_custom_blend(
    user_id: str,
    blend_id: str,
    time_override: Optional[int] = None,
    date_override: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Dispense a custom blend."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    blend = db.query(CustomBlend).filter(
        CustomBlend.id == blend_id,
        CustomBlend.user_id == user_id
    ).first()

    if not blend:
        raise HTTPException(status_code=404, detail="Custom blend not found")

    # Parse date
    target_date = date.today()
    if date_override:
        try:
            target_date = datetime.strptime(date_override, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    user_profile = {
        "weight_kg": user.weight_kg,
        "age": user.age,
        "sex": user.sex
    }

    dispensed_on_date = _get_dispensed_for_date(user_id, target_date, db)

    # Calculate and dispense
    hour = time_override if time_override is not None else 12
    dispense_timestamp = datetime.combine(target_date, datetime.min.time().replace(hour=hour))

    dispensed = []
    for comp in blend.components:
        supp_id = comp["supplement_id"]

        config = rules.supplements.get(supp_id)
        if not config:
            continue

        # Support both new 'dose' field and legacy 'dose_multiplier'
        if "dose" in comp:
            dose = comp["dose"]
        else:
            dose_mult = comp.get("dose_multiplier", 1.0)
            dose = config.standard_dose * dose_mult

        already = dispensed_on_date.get(supp_id, 0)
        remaining = config.max_daily_dose - already

        if remaining <= 0:
            continue

        final_dose = min(dose, remaining)

        log = DispenseLog(
            user_id=user_id,
            supplement_name=supp_id,
            dose=final_dose,
            unit=config.unit,
            dispensed_at=dispense_timestamp
        )
        db.add(log)
        dispensed.append({
            "supplement_id": supp_id,
            "name": config.name,
            "dose": round(final_dose, 1),
            "unit": config.unit
        })

        # Update dispensed_on_date for subsequent calcs
        dispensed_on_date[supp_id] = already + final_dose

    db.commit()

    return {
        "status": "dispensed",
        "blend_id": blend_id,
        "blend_name": blend.name,
        "date": target_date.isoformat(),
        "supplements_dispensed": dispensed,
        "total_dispensed": len(dispensed)
    }


# Saturation supplements config
SATURATION_SUPPLEMENTS = {
    "creatine": {
        "name": "Creatine",
        "saturation_days": 28,  # Days to reach full saturation
        "maintenance_dose": 5.0,  # g per day for maintenance
        "loading_dose": 20.0,  # g per day during loading (optional)
        "decay_days": 30,  # Days without taking before losing saturation
        "unit": "g"
    }
}


@router.get("/{user_id}/tracking/saturation")
async def get_saturation_status(
    user_id: str,
    as_of_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get saturation status for supplements that require loading (like creatine).

    Saturation is calculated based on consistent daily intake over time.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    check_date = date.today()
    if as_of_date:
        try:
            check_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    saturation_status = []

    for supp_id, config in SATURATION_SUPPLEMENTS.items():
        # Look back over saturation period + decay period
        lookback_days = config["saturation_days"] + config["decay_days"]
        start_date = check_date - timedelta(days=lookback_days)

        # Get all logs for this supplement
        logs = db.query(DispenseLog).filter(
            DispenseLog.user_id == user_id,
            DispenseLog.supplement_name == supp_id,
            DispenseLog.dispensed_at >= datetime.combine(start_date, datetime.min.time()),
            DispenseLog.dispensed_at < datetime.combine(check_date + timedelta(days=1), datetime.min.time())
        ).order_by(DispenseLog.dispensed_at).all()

        # Calculate days with sufficient intake
        daily_intake = {}
        for log in logs:
            day = log.dispensed_at.date()
            if day not in daily_intake:
                daily_intake[day] = 0
            daily_intake[day] += log.dose

        # Count consecutive days with maintenance dose (working backward from today)
        consecutive_days = 0
        last_intake_date = None

        current = check_date
        while current >= start_date:
            intake = daily_intake.get(current, 0)
            if intake >= config["maintenance_dose"] * 0.4:  # Allow 40% threshold (2g for 5g maintenance)
                consecutive_days += 1
                if last_intake_date is None:
                    last_intake_date = current
            else:
                # Check if we've had a gap that breaks the chain
                if last_intake_date and (last_intake_date - current).days > config["decay_days"]:
                    break
            current -= timedelta(days=1)

        # Calculate saturation percentage
        saturation_pct = min(100, round((consecutive_days / config["saturation_days"]) * 100))

        # Calculate days since last intake
        days_since_last = None
        if last_intake_date:
            days_since_last = (check_date - last_intake_date).days

        # Determine status
        if saturation_pct >= 100:
            status = "saturated"
        elif saturation_pct >= 50:
            status = "building"
        elif saturation_pct > 0:
            status = "starting"
        else:
            status = "not_started"

        # Check for decay
        if days_since_last and days_since_last > 3:
            decay_pct = min(100, round((days_since_last / config["decay_days"]) * 100))
            if decay_pct > 0:
                saturation_pct = max(0, saturation_pct - decay_pct)
                if saturation_pct < 50:
                    status = "decaying"

        saturation_status.append({
            "supplement_id": supp_id,
            "name": config["name"],
            "saturation_percentage": saturation_pct,
            "status": status,
            "consecutive_days": consecutive_days,
            "days_to_saturate": config["saturation_days"],
            "days_since_last_intake": days_since_last,
            "maintenance_dose": config["maintenance_dose"],
            "unit": config["unit"]
        })

    return {
        "user_id": user_id,
        "as_of_date": check_date.isoformat(),
        "supplements": saturation_status
    }
