import csv
import io
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.models import User, HealthData

router = APIRouter()


class CSVUploadResponse(BaseModel):
    status: str
    records_imported: int
    latest_data: dict


@router.post("/{user_id}/oura-csv", response_model=CSVUploadResponse)
async def upload_oura_csv(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload Oura Ring CSV export and import health data.

    To export from Oura:
    1. Go to Oura Web (cloud.ouraring.com)
    2. Click your profile → Download My Data
    3. Upload the sleep or readiness CSV here
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    text = content.decode('utf-8')

    reader = csv.DictReader(io.StringIO(text))
    records_imported = 0
    latest_health_data = None

    for row in reader:
        health_data = parse_oura_row(row, user_id)
        if health_data:
            db.add(health_data)
            records_imported += 1
            latest_health_data = health_data

    db.commit()

    if latest_health_data is None:
        raise HTTPException(
            status_code=400,
            detail="No valid health data found in CSV. Make sure it's an Oura export."
        )

    return CSVUploadResponse(
        status="success",
        records_imported=records_imported,
        latest_data=latest_health_data.to_dict()
    )


def parse_oura_row(row: dict, user_id: str) -> Optional[HealthData]:
    """Parse a row from Oura CSV export into HealthData."""

    # Oura exports different CSV formats for different data types
    # Try to detect and parse the format

    try:
        # Try sleep data format
        if 'Sleep Score' in row or 'sleep_score' in row or 'Score' in row:
            return parse_oura_sleep(row, user_id)

        # Try readiness data format
        if 'Readiness Score' in row or 'readiness_score' in row:
            return parse_oura_readiness(row, user_id)

        # Try daily summary format (newer exports)
        if 'date' in row and ('score' in row or 'total' in row):
            return parse_oura_daily(row, user_id)

    except Exception as e:
        print(f"Error parsing row: {e}")
        return None

    return None


def parse_oura_sleep(row: dict, user_id: str) -> Optional[HealthData]:
    """Parse Oura sleep CSV format."""

    # Map various column name formats
    sleep_score = get_value(row, ['Sleep Score', 'sleep_score', 'Score', 'score'])
    total_sleep = get_value(row, ['Total Sleep Duration', 'total_sleep_duration', 'Total Sleep', 'duration'])
    deep_sleep = get_value(row, ['Deep Sleep Duration', 'deep_sleep_duration', 'Deep Sleep', 'deep'])
    rem_sleep = get_value(row, ['REM Sleep Duration', 'rem_sleep_duration', 'REM Sleep', 'rem'])
    resting_hr = get_value(row, ['Average Resting Heart Rate', 'avg_resting_hr', 'Resting HR', 'hr_average'])
    hrv = get_value(row, ['Average HRV', 'avg_hrv', 'HRV', 'rmssd'])
    date_str = get_value(row, ['date', 'Date', 'summary_date', 'day'])

    if sleep_score is None:
        return None

    # Calculate percentages if we have total sleep
    deep_pct = None
    rem_pct = None
    sleep_hours = None

    if total_sleep:
        total_seconds = parse_duration(total_sleep)
        if total_seconds:
            sleep_hours = round(total_seconds / 3600, 1)
            if deep_sleep:
                deep_seconds = parse_duration(deep_sleep)
                if deep_seconds:
                    deep_pct = round((deep_seconds / total_seconds) * 100, 1)
            if rem_sleep:
                rem_seconds = parse_duration(rem_sleep)
                if rem_seconds:
                    rem_pct = round((rem_seconds / total_seconds) * 100, 1)

    # Parse HRV to score (normalize if needed)
    hrv_score = None
    if hrv:
        hrv_val = float(hrv)
        # If HRV is in ms (typical range 20-100), normalize to 0-100 score
        if hrv_val < 150:
            hrv_score = min(100, max(0, (hrv_val - 20) * 1.25))
        else:
            hrv_score = hrv_val  # Already a score

    return HealthData(
        user_id=user_id,
        source="oura_csv",
        sleep_score=float(sleep_score) if sleep_score else None,
        hrv_score=hrv_score,
        recovery_score=None,  # Not in sleep data
        strain_score=None,
        resting_hr=int(float(resting_hr)) if resting_hr else None,
        sleep_duration_hrs=sleep_hours,
        deep_sleep_pct=deep_pct,
        rem_sleep_pct=rem_pct,
        timestamp=parse_date(date_str) if date_str else datetime.utcnow()
    )


def parse_oura_readiness(row: dict, user_id: str) -> Optional[HealthData]:
    """Parse Oura readiness CSV format."""

    readiness_score = get_value(row, ['Readiness Score', 'readiness_score', 'Score', 'score'])
    hrv = get_value(row, ['HRV Balance', 'hrv_balance', 'HRV', 'rmssd'])
    resting_hr = get_value(row, ['Resting Heart Rate', 'resting_hr', 'Resting HR'])
    date_str = get_value(row, ['date', 'Date', 'summary_date', 'day'])

    if readiness_score is None:
        return None

    hrv_score = float(hrv) if hrv else None

    return HealthData(
        user_id=user_id,
        source="oura_csv",
        sleep_score=None,
        hrv_score=hrv_score,
        recovery_score=float(readiness_score),
        strain_score=None,
        resting_hr=int(float(resting_hr)) if resting_hr else None,
        sleep_duration_hrs=None,
        deep_sleep_pct=None,
        rem_sleep_pct=None,
        timestamp=parse_date(date_str) if date_str else datetime.utcnow()
    )


def parse_oura_daily(row: dict, user_id: str) -> Optional[HealthData]:
    """Parse Oura daily summary format."""

    # This handles the newer export format
    score = get_value(row, ['score', 'Score'])
    date_str = get_value(row, ['date', 'Date'])

    if score is None:
        return None

    return HealthData(
        user_id=user_id,
        source="oura_csv",
        sleep_score=float(score),
        hrv_score=None,
        recovery_score=None,
        strain_score=None,
        resting_hr=None,
        sleep_duration_hrs=None,
        deep_sleep_pct=None,
        rem_sleep_pct=None,
        timestamp=parse_date(date_str) if date_str else datetime.utcnow()
    )


def get_value(row: dict, keys: List[str]) -> Optional[str]:
    """Get value from row using multiple possible key names."""
    for key in keys:
        if key in row and row[key] and row[key].strip():
            return row[key].strip()
    return None


def parse_duration(duration_str: str) -> Optional[float]:
    """Parse duration string to seconds. Handles various formats."""
    if not duration_str:
        return None

    try:
        # If it's already a number (seconds or minutes)
        val = float(duration_str)
        # If small number, assume hours
        if val < 24:
            return val * 3600
        # If medium, assume minutes
        elif val < 1440:
            return val * 60
        # Otherwise assume seconds
        return val
    except ValueError:
        pass

    # Try HH:MM:SS format
    try:
        parts = duration_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except:
        pass

    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str:
        return None

    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None
