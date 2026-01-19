from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db import get_db
from app.models import User, HealthData
from app.integrations import OuraIntegration, WhoopIntegration, MockIntegration

router = APIRouter()


class OAuthStartResponse(BaseModel):
    auth_url: str


class OAuthCallback(BaseModel):
    code: str
    redirect_uri: str


class ConnectionStatus(BaseModel):
    connected: bool
    source: str
    error: Optional[str] = None


class HistoricalDataPoint(BaseModel):
    date: str
    sleep_score: Optional[float]
    hrv_score: Optional[float]
    recovery_score: Optional[float]
    strain_score: Optional[float]
    resting_hr: Optional[int]
    sleep_duration_hrs: Optional[float]


class SyncResponse(BaseModel):
    status: str
    source: str
    data: dict


# --- Oura Integration ---

@router.get("/{user_id}/oura/auth")
def start_oura_auth(
    user_id: str,
    request: Request,
    redirect_uri: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Start Oura OAuth flow.

    Returns auth URL as JSON. Client should redirect to this URL.
    """
    from app.config import get_settings
    settings = get_settings()

    # Check if Oura credentials are configured
    if not settings.oura_client_id or not settings.oura_client_secret:
        raise HTTPException(
            status_code=400,
            detail="Oura API credentials not configured. Please set OURA_CLIENT_ID and OURA_CLIENT_SECRET environment variables."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Auto-generate redirect_uri if not provided
    if not redirect_uri:
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/integrations/{user_id}/oura/callback"

    oura = OuraIntegration()
    # Include user_id in state for the callback
    auth_url = oura.get_auth_url(redirect_uri, state=user_id)

    return OAuthStartResponse(auth_url=auth_url)


@router.get("/{user_id}/oura/callback")
async def oura_callback(
    user_id: str,
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Oura OAuth callback.

    This endpoint receives the authorization code from Oura
    and exchanges it for access tokens, then redirects back to the UI.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url=f"/?oura_connected=false&error=User+not+found")

    oura = OuraIntegration()
    try:
        # Build the redirect_uri that was used in the auth request
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/integrations/{user_id}/oura/callback"

        token = await oura.exchange_code(code, redirect_uri)
        user.oura_token = token
        db.commit()

        # Redirect back to UI with success
        return RedirectResponse(url="/?oura_connected=true")
    except Exception as e:
        # Redirect back to UI with error
        error_msg = str(e).replace(' ', '+')
        return RedirectResponse(url=f"/?oura_connected=false&error={error_msg}")


@router.post("/{user_id}/oura/callback")
async def oura_callback_post(
    user_id: str,
    callback: OAuthCallback,
    db: Session = Depends(get_db)
):
    """Complete Oura OAuth flow (POST version for API calls)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    oura = OuraIntegration()
    try:
        token = await oura.exchange_code(callback.code, callback.redirect_uri)
        user.oura_token = token
        db.commit()
        return {"status": "connected", "source": "oura"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")


@router.get("/{user_id}/oura/status", response_model=ConnectionStatus)
async def check_oura_status(user_id: str, db: Session = Depends(get_db)):
    """Check if Oura is connected and token is valid."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.oura_token:
        return ConnectionStatus(connected=False, source="oura", error="Not connected")

    oura = OuraIntegration()

    # Check if token needs refresh
    if oura.is_token_expired(user.oura_token):
        try:
            new_token = await oura.get_valid_token(user.oura_token)
            user.oura_token = new_token
            db.commit()
        except Exception as e:
            return ConnectionStatus(connected=False, source="oura", error=str(e))

    # Verify connection
    result = await oura.verify_connection(user.oura_token)
    return ConnectionStatus(
        connected=result.get("connected", False),
        source="oura",
        error=result.get("error")
    )


@router.delete("/{user_id}/oura")
def disconnect_oura(user_id: str, db: Session = Depends(get_db)):
    """Disconnect Oura integration."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.oura_token = None
    db.commit()
    return {"status": "disconnected", "source": "oura"}


@router.get("/{user_id}/oura/history")
async def get_oura_history(
    user_id: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Fetch historical data from Oura for the past N days.

    Returns daily metrics including sleep score, HRV, recovery, etc.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.oura_token:
        raise HTTPException(status_code=400, detail="Oura not connected")

    oura = OuraIntegration()

    # Refresh token if needed
    try:
        valid_token = await oura.get_valid_token(user.oura_token)
        if valid_token != user.oura_token:
            user.oura_token = valid_token
            db.commit()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")

    try:
        historical = await oura.fetch_historical_data(user.oura_token, days=days)

        # Store each day's data as a separate record for analytics charting
        records_added = 0
        if historical:
            for day in historical:
                # Skip days with no meaningful data
                if day.get("sleep_score") is None and day.get("hrv_score") is None and day.get("recovery_score") is None:
                    continue

                # Parse the date and create a timestamp for that day
                from datetime import datetime as dt
                day_date = dt.strptime(day["date"], "%Y-%m-%d")

                # Check if we already have data for this date
                existing = db.query(HealthData).filter(
                    HealthData.user_id == user_id,
                    HealthData.source == "oura",
                    HealthData.timestamp >= day_date,
                    HealthData.timestamp < day_date + timedelta(days=1)
                ).first()

                if existing:
                    # Update existing record with all new fields
                    existing.sleep_score = day.get("sleep_score")
                    existing.hrv_score = day.get("hrv_score")
                    existing.recovery_score = day.get("recovery_score")
                    existing.strain_score = day.get("strain_score")
                    existing.sleep_duration_hrs = day.get("sleep_duration_hrs")
                    existing.deep_sleep_duration = day.get("deep_sleep_duration")
                    existing.rem_sleep_duration = day.get("rem_sleep_duration")
                    existing.light_sleep_duration = day.get("light_sleep_duration")
                    existing.awake_duration = day.get("awake_duration")
                    existing.sleep_efficiency = day.get("sleep_efficiency")
                    existing.sleep_latency = day.get("sleep_latency")
                    existing.restfulness_score = day.get("restfulness_score")
                    existing.bedtime = day.get("bedtime")
                    existing.wake_time = day.get("wake_time")
                    existing.deep_sleep_pct = day.get("deep_sleep_pct")
                    existing.rem_sleep_pct = day.get("rem_sleep_pct")
                    existing.resting_hr = day.get("resting_hr")
                    existing.lowest_hr = day.get("lowest_hr")
                    existing.average_hr_sleep = day.get("average_hr_sleep")
                    existing.vo2_max = day.get("vo2_max")
                    existing.activity_score = day.get("activity_score")
                    existing.steps = day.get("steps")
                    existing.active_calories = day.get("active_calories")
                    existing.total_calories = day.get("total_calories")
                    existing.sedentary_time = day.get("sedentary_time")
                    existing.active_time = day.get("active_time")
                    existing.spo2_average = day.get("spo2_average")
                    existing.breathing_average = day.get("breathing_average")
                    existing.breathing_regularity = day.get("breathing_regularity")
                    existing.stress_level = day.get("stress_level")
                    existing.stress_score = day.get("stress_score")
                    existing.workout_type = day.get("workout_type")
                    existing.workout_duration = day.get("workout_duration")
                    existing.workout_intensity = day.get("workout_intensity")
                    existing.workout_calories = day.get("workout_calories")
                    existing.workout_source = day.get("workout_source")
                    existing.temperature_deviation = day.get("temperature_deviation")
                    existing.temperature_trend = day.get("temperature_trend")
                else:
                    # Create new record for this day
                    health_data = HealthData(
                        user_id=user_id,
                        source="oura",
                        timestamp=day_date,
                        # Core metrics
                        sleep_score=day.get("sleep_score"),
                        hrv_score=day.get("hrv_score"),
                        recovery_score=day.get("recovery_score"),
                        strain_score=day.get("strain_score"),
                        # Sleep details
                        sleep_duration_hrs=day.get("sleep_duration_hrs"),
                        deep_sleep_duration=day.get("deep_sleep_duration"),
                        rem_sleep_duration=day.get("rem_sleep_duration"),
                        light_sleep_duration=day.get("light_sleep_duration"),
                        awake_duration=day.get("awake_duration"),
                        sleep_efficiency=day.get("sleep_efficiency"),
                        sleep_latency=day.get("sleep_latency"),
                        restfulness_score=day.get("restfulness_score"),
                        bedtime=day.get("bedtime"),
                        wake_time=day.get("wake_time"),
                        deep_sleep_pct=day.get("deep_sleep_pct"),
                        rem_sleep_pct=day.get("rem_sleep_pct"),
                        # Heart rate
                        resting_hr=day.get("resting_hr"),
                        lowest_hr=day.get("lowest_hr"),
                        average_hr_sleep=day.get("average_hr_sleep"),
                        # Heart health
                        vo2_max=day.get("vo2_max"),
                        # Activity
                        activity_score=day.get("activity_score"),
                        steps=day.get("steps"),
                        active_calories=day.get("active_calories"),
                        total_calories=day.get("total_calories"),
                        sedentary_time=day.get("sedentary_time"),
                        active_time=day.get("active_time"),
                        # SpO2 / Breathing
                        spo2_average=day.get("spo2_average"),
                        breathing_average=day.get("breathing_average"),
                        breathing_regularity=day.get("breathing_regularity"),
                        # Stress
                        stress_level=day.get("stress_level"),
                        stress_score=day.get("stress_score"),
                        # Workout
                        workout_type=day.get("workout_type"),
                        workout_duration=day.get("workout_duration"),
                        workout_intensity=day.get("workout_intensity"),
                        workout_calories=day.get("workout_calories"),
                        workout_source=day.get("workout_source"),
                        # Temperature
                        temperature_deviation=day.get("temperature_deviation"),
                        temperature_trend=day.get("temperature_trend"),
                    )
                    db.add(health_data)
                    records_added += 1

            db.commit()

        return {
            "status": "success",
            "days": days,
            "records_added": records_added,
            "data": historical
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Oura data: {str(e)}")


# --- Whoop Integration ---

@router.get("/{user_id}/whoop/auth", response_model=OAuthStartResponse)
def start_whoop_auth(user_id: str, redirect_uri: str, db: Session = Depends(get_db)):
    """Start Whoop OAuth flow."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    whoop = WhoopIntegration()
    auth_url = whoop.get_auth_url(redirect_uri)

    return OAuthStartResponse(auth_url=auth_url)


@router.post("/{user_id}/whoop/callback")
async def whoop_callback(
    user_id: str,
    callback: OAuthCallback,
    db: Session = Depends(get_db)
):
    """Complete Whoop OAuth flow."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    whoop = WhoopIntegration()
    try:
        token = await whoop.exchange_code(callback.code, callback.redirect_uri)
        user.whoop_token = token
        db.commit()
        return {"status": "connected", "source": "whoop"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")


# --- Sync Health Data ---

@router.post("/{user_id}/sync", response_model=SyncResponse)
async def sync_health_data(user_id: str, db: Session = Depends(get_db)):
    """
    Sync latest health data from connected wearables.

    Pulls data from all connected sources and stores normalized data.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    synced_data = None
    source = None

    # Try Oura first
    if user.oura_token:
        oura = OuraIntegration()
        try:
            # Refresh token if needed
            valid_token = await oura.get_valid_token(user.oura_token)
            if valid_token != user.oura_token:
                user.oura_token = valid_token
                db.commit()

            # Fetch historical data to get most recent non-null values
            historical = await oura.fetch_historical_data(user.oura_token, days=7)

            # Build combined data using most recent non-null values
            combined = {
                "sleep_score": None,
                "hrv_score": None,
                "recovery_score": None,
                "strain_score": None,
                "resting_hr": None,
                "sleep_duration_hrs": None,
                "deep_sleep_pct": None,
                "rem_sleep_pct": None,
            }

            # Iterate from newest to oldest
            for day in reversed(historical):
                for key in combined:
                    if combined[key] is None and day.get(key) is not None:
                        combined[key] = day[key]

            # Create normalized data object
            from app.integrations.base import NormalizedHealthData
            from datetime import datetime
            data = NormalizedHealthData(
                sleep_score=combined["sleep_score"],
                hrv_score=combined["hrv_score"],
                recovery_score=combined["recovery_score"],
                strain_score=combined["strain_score"],
                resting_hr=combined["resting_hr"],
                sleep_duration_hrs=combined["sleep_duration_hrs"],
                deep_sleep_pct=combined["deep_sleep_pct"],
                rem_sleep_pct=combined["rem_sleep_pct"],
                source="oura",
                timestamp=datetime.utcnow()
            )
            synced_data = data
            source = "oura"
        except Exception as e:
            print(f"Oura sync error: {e}")

    # Try Whoop if Oura failed or not connected
    if synced_data is None and user.whoop_token:
        whoop = WhoopIntegration()
        try:
            data = await whoop.fetch_latest_data(user.whoop_token)
            synced_data = data
            source = "whoop"
        except Exception as e:
            print(f"Whoop sync error: {e}")

    if synced_data is None:
        raise HTTPException(
            status_code=400,
            detail="No wearables connected or sync failed"
        )

    # Store normalized health data
    health_data = HealthData(
        user_id=user_id,
        source=source,
        sleep_score=synced_data.sleep_score,
        hrv_score=synced_data.hrv_score,
        recovery_score=synced_data.recovery_score,
        strain_score=synced_data.strain_score,
        resting_hr=synced_data.resting_hr,
        sleep_duration_hrs=synced_data.sleep_duration_hrs,
        deep_sleep_pct=synced_data.deep_sleep_pct,
        rem_sleep_pct=synced_data.rem_sleep_pct
    )
    db.add(health_data)
    db.commit()

    return SyncResponse(
        status="synced",
        source=source,
        data=synced_data.to_dict()
    )


# --- Mock Data for Testing ---

@router.post("/{user_id}/mock")
async def add_mock_data(
    user_id: str,
    scenario: str = "average",
    db: Session = Depends(get_db)
):
    """
    Add mock health data for testing.

    Scenarios: average, poor_sleep, high_strain, stressed, recovering, random
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mock = MockIntegration(scenario=scenario)
    data = await mock.fetch_latest_data()

    health_data = HealthData(
        user_id=user_id,
        source="mock",
        sleep_score=data.sleep_score,
        hrv_score=data.hrv_score,
        recovery_score=data.recovery_score,
        strain_score=data.strain_score,
        resting_hr=data.resting_hr,
        sleep_duration_hrs=data.sleep_duration_hrs,
        deep_sleep_pct=data.deep_sleep_pct,
        rem_sleep_pct=data.rem_sleep_pct
    )
    db.add(health_data)
    db.commit()

    return {
        "status": "mock_data_added",
        "scenario": scenario,
        "data": data.to_dict()
    }


@router.post("/{user_id}/mock-history")
async def add_mock_history(
    user_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Add historical mock health data for testing progress features.

    Creates data for the specified number of days with realistic variation.
    Earlier days have lower scores, recent days have higher scores to simulate improvement.
    """
    import random

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Clear existing mock data first
    db.query(HealthData).filter(
        HealthData.user_id == user_id,
        HealthData.source == "mock"
    ).delete()
    db.commit()

    records_added = []
    base_date = datetime.utcnow()

    for i in range(days):
        days_ago = days - i - 1
        record_date = base_date - timedelta(days=days_ago)

        # Simulate improvement over time
        # Earlier days (higher days_ago) have lower base scores
        # Recent days have higher scores
        progress_factor = i / days  # 0 to 1 as we get more recent

        # Base scores that improve over time
        base_sleep = 60 + (progress_factor * 20) + random.uniform(-5, 5)
        base_hrv = 55 + (progress_factor * 25) + random.uniform(-8, 8)
        base_recovery = 58 + (progress_factor * 22) + random.uniform(-6, 6)
        base_strain = 40 + random.uniform(-10, 20)

        # Clamp values to realistic ranges
        sleep_score = max(40, min(95, base_sleep))
        hrv_score = max(30, min(100, base_hrv))
        recovery_score = max(35, min(95, base_recovery))
        strain_score = max(20, min(90, base_strain))

        health_data = HealthData(
            user_id=user_id,
            source="mock",
            timestamp=record_date,
            sleep_score=round(sleep_score, 1),
            hrv_score=round(hrv_score, 1),
            recovery_score=round(recovery_score, 1),
            strain_score=round(strain_score, 1),
            resting_hr=random.randint(52, 65),
            sleep_duration_hrs=round(6.5 + random.uniform(0, 2), 1),
            deep_sleep_pct=random.randint(15, 25),
            rem_sleep_pct=random.randint(18, 28)
        )
        db.add(health_data)
        records_added.append({
            "date": record_date.strftime("%Y-%m-%d"),
            "sleep": round(sleep_score, 1),
            "hrv": round(hrv_score, 1),
            "recovery": round(recovery_score, 1)
        })

    db.commit()

    return {
        "status": "mock_history_added",
        "days": days,
        "records": len(records_added),
        "sample": records_added[-5:]  # Last 5 days
    }


@router.get("/{user_id}/oura/debug")
async def debug_oura_data(user_id: str, db: Session = Depends(get_db)):
    """
    Debug endpoint to see raw Oura API responses.
    Shows exactly what fields are being returned for sleep data.
    """
    import httpx

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.oura_token:
        raise HTTPException(status_code=400, detail="Oura not connected")

    oura = OuraIntegration()

    try:
        valid_token = await oura.get_valid_token(user.oura_token)
        token = valid_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        today = datetime.utcnow().date()
        start_date = today - timedelta(days=3)

        async with httpx.AsyncClient() as client:
            # Fetch detailed sleep data
            sleep_response = await client.get(
                f"https://api.ouraring.com/v2/usercollection/sleep",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            sleep_data = sleep_response.json().get("data", [])

            # Fetch daily readiness
            readiness_response = await client.get(
                f"https://api.ouraring.com/v2/usercollection/daily_readiness",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            readiness_data = readiness_response.json().get("data", [])

        # Extract just the relevant fields for debugging
        debug_sleep = []
        for s in sleep_data:
            debug_sleep.append({
                "day": s.get("day"),
                "average_hrv": s.get("average_hrv"),
                "average_heart_rate": s.get("average_heart_rate"),
                "has_hrv_field": "average_hrv" in s,
                "all_keys": list(s.keys())
            })

        debug_readiness = []
        for r in readiness_data:
            contributors = r.get("contributors", {})
            debug_readiness.append({
                "day": r.get("day"),
                "score": r.get("score"),
                "hrv_balance": contributors.get("hrv_balance"),
                "contributor_keys": list(contributors.keys())
            })

        return {
            "sleep_records": debug_sleep,
            "readiness_records": debug_readiness,
            "raw_sleep_sample": sleep_data[0] if sleep_data else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")
