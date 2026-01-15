from fastapi import APIRouter, Depends, HTTPException
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


class SyncResponse(BaseModel):
    status: str
    source: str
    data: dict


# --- Oura Integration ---

@router.get("/{user_id}/oura/auth", response_model=OAuthStartResponse)
def start_oura_auth(user_id: str, redirect_uri: str, db: Session = Depends(get_db)):
    """Start Oura OAuth flow."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    oura = OuraIntegration()
    auth_url = oura.get_auth_url(redirect_uri)

    return OAuthStartResponse(auth_url=auth_url)


@router.post("/{user_id}/oura/callback")
async def oura_callback(
    user_id: str,
    callback: OAuthCallback,
    db: Session = Depends(get_db)
):
    """Complete Oura OAuth flow."""
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
            data = await oura.fetch_latest_data(user.oura_token)
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
