from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

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

        # Store combined data using most recent non-null values
        if historical:
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

            # Iterate from newest to oldest to get most recent non-null values
            for day in reversed(historical):
                for key in combined:
                    if combined[key] is None and day.get(key) is not None:
                        combined[key] = day[key]

            health_data = HealthData(
                user_id=user_id,
                source="oura",
                sleep_score=combined["sleep_score"],
                hrv_score=combined["hrv_score"],
                recovery_score=combined["recovery_score"],
                strain_score=combined["strain_score"],
                resting_hr=combined["resting_hr"],
                sleep_duration_hrs=combined["sleep_duration_hrs"],
                deep_sleep_pct=combined["deep_sleep_pct"],
                rem_sleep_pct=combined["rem_sleep_pct"]
            )
            db.add(health_data)
            db.commit()

        return {
            "status": "success",
            "days": days,
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
