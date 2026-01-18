"""
Notifications API - Phone verification and SMS preferences management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime, timedelta
import random
import re

from app.db import get_db
from app.models import User
from app.services.sms_service import sms_service
from app.services.scheduler import get_reminder_time

router = APIRouter()


# Pydantic Models
class PhoneVerifyRequest(BaseModel):
    phone_number: str

    @validator("phone_number")
    def validate_phone(cls, v):
        # Basic E.164 validation for US numbers
        pattern = r"^\+1\d{10}$"
        if not re.match(pattern, v):
            raise ValueError("Phone number must be in format +1XXXXXXXXXX")
        return v


class VerifyCodeRequest(BaseModel):
    code: str

    @validator("code")
    def validate_code(cls, v):
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("Code must be 6 digits")
        return v


class NotificationPreferencesUpdate(BaseModel):
    sms_enabled: Optional[bool] = None
    morning_reminder: Optional[bool] = None
    evening_reminder: Optional[bool] = None
    custom_morning_time: Optional[str] = None
    custom_evening_time: Optional[str] = None

    @validator("custom_morning_time", "custom_evening_time")
    def validate_time(cls, v):
        if v is not None and v != "":
            pattern = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
            if not re.match(pattern, v):
                raise ValueError("Time must be in HH:MM format")
        return v if v != "" else None


class TimezoneUpdate(BaseModel):
    timezone: str


class NotificationPreferencesResponse(BaseModel):
    phone_number: Optional[str]
    phone_verified: bool
    timezone: str
    sms_enabled: bool
    morning_reminder: bool
    evening_reminder: bool
    custom_morning_time: Optional[str]
    custom_evening_time: Optional[str]
    effective_morning_time: str
    effective_evening_time: str


# Helper functions
def _mask_phone(phone: str) -> str:
    """Mask phone number for display."""
    if phone and len(phone) > 6:
        return phone[:3] + "***" + phone[-4:]
    return None


def _generate_code() -> str:
    """Generate 6-digit verification code."""
    return "".join([str(random.randint(0, 9)) for _ in range(6)])


# Endpoints
@router.post("/{user_id}/phone/request-verification")
def request_phone_verification(
    user_id: str,
    request: PhoneVerifyRequest,
    db: Session = Depends(get_db)
):
    """Send a verification code to the phone number."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not sms_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="SMS service not configured"
        )

    # Generate 6-digit code
    code = _generate_code()

    # Store code with expiration
    user.phone_number = request.phone_number
    user.phone_verified = False
    user.phone_verification_code = code
    user.phone_verification_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    # Send SMS
    result = sms_service.send_verification_code(request.phone_number, code)

    if result["success"]:
        return {
            "message": "Verification code sent",
            "expires_in_minutes": 10,
            "phone_masked": _mask_phone(request.phone_number)
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send verification code: {result.get('error', 'Unknown error')}"
        )


@router.post("/{user_id}/phone/verify")
def verify_phone(
    user_id: str,
    request: VerifyCodeRequest,
    db: Session = Depends(get_db)
):
    """Verify phone number with code."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.phone_verification_code:
        raise HTTPException(status_code=400, detail="No verification pending")

    if user.phone_verification_expires and datetime.utcnow() > user.phone_verification_expires:
        user.phone_verification_code = None
        user.phone_verification_expires = None
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code expired")

    if request.code != user.phone_verification_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    # Mark as verified
    user.phone_verified = True
    user.phone_verification_code = None
    user.phone_verification_expires = None

    # Enable SMS by default on verification
    prefs = user.notification_preferences or {}
    prefs["sms_enabled"] = True
    user.notification_preferences = prefs

    db.commit()

    return {
        "message": "Phone verified successfully",
        "sms_enabled": True,
        "phone_masked": _mask_phone(user.phone_number)
    }


@router.post("/{user_id}/phone/resend")
def resend_verification_code(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Resend verification code to existing phone number."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.phone_number:
        raise HTTPException(status_code=400, detail="No phone number on file")

    if user.phone_verified:
        raise HTTPException(status_code=400, detail="Phone already verified")

    if not sms_service.is_configured():
        raise HTTPException(status_code=503, detail="SMS service not configured")

    # Generate new code
    code = _generate_code()
    user.phone_verification_code = code
    user.phone_verification_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    # Send SMS
    result = sms_service.send_verification_code(user.phone_number, code)

    if result["success"]:
        return {
            "message": "Verification code resent",
            "expires_in_minutes": 10
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to send verification code")


@router.get("/{user_id}/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user's notification preferences."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.notification_preferences or {}

    return NotificationPreferencesResponse(
        phone_number=_mask_phone(user.phone_number) if user.phone_number else None,
        phone_verified=user.phone_verified or False,
        timezone=user.timezone or "America/New_York",
        sms_enabled=prefs.get("sms_enabled", False),
        morning_reminder=prefs.get("morning_reminder", True),
        evening_reminder=prefs.get("evening_reminder", True),
        custom_morning_time=prefs.get("custom_morning_time"),
        custom_evening_time=prefs.get("custom_evening_time"),
        effective_morning_time=get_reminder_time(user, "morning"),
        effective_evening_time=get_reminder_time(user, "evening")
    )


@router.patch("/{user_id}/preferences")
def update_notification_preferences(
    user_id: str,
    update: NotificationPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """Update user's notification preferences."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cannot enable SMS without verified phone
    if update.sms_enabled and not user.phone_verified:
        raise HTTPException(
            status_code=400,
            detail="Please verify your phone number before enabling SMS"
        )

    prefs = user.notification_preferences or {}

    if update.sms_enabled is not None:
        prefs["sms_enabled"] = update.sms_enabled
    if update.morning_reminder is not None:
        prefs["morning_reminder"] = update.morning_reminder
    if update.evening_reminder is not None:
        prefs["evening_reminder"] = update.evening_reminder
    if update.custom_morning_time is not None:
        prefs["custom_morning_time"] = update.custom_morning_time or None
    if update.custom_evening_time is not None:
        prefs["custom_evening_time"] = update.custom_evening_time or None

    user.notification_preferences = prefs
    db.commit()

    return {
        "message": "Preferences updated",
        "preferences": prefs,
        "effective_morning_time": get_reminder_time(user, "morning"),
        "effective_evening_time": get_reminder_time(user, "evening")
    }


@router.patch("/{user_id}/timezone")
def update_timezone(
    user_id: str,
    update: TimezoneUpdate,
    db: Session = Depends(get_db)
):
    """Update user's timezone."""
    import pytz

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate timezone
    try:
        pytz.timezone(update.timezone)
    except:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    user.timezone = update.timezone
    db.commit()

    return {"message": "Timezone updated", "timezone": update.timezone}


@router.delete("/{user_id}/phone")
def remove_phone_number(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Remove phone number and disable SMS notifications."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.phone_number = None
    user.phone_verified = False
    user.phone_verification_code = None
    user.phone_verification_expires = None

    # Disable SMS
    prefs = user.notification_preferences or {}
    prefs["sms_enabled"] = False
    user.notification_preferences = prefs

    db.commit()

    return {"message": "Phone number removed and SMS disabled"}
