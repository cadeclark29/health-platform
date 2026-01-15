from typing import Optional
import httpx
from datetime import datetime, timedelta

from app.config import get_settings
from .base import WearableIntegration, NormalizedHealthData


class OuraIntegration(WearableIntegration):
    """Oura Ring API integration."""

    BASE_URL = "https://api.ouraring.com/v2"
    AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
    TOKEN_URL = "https://api.ouraring.com/oauth/token"

    def __init__(self):
        self.settings = get_settings()

    def get_auth_url(self, redirect_uri: str) -> str:
        """Get Oura OAuth authorization URL."""
        return (
            f"{self.AUTH_URL}"
            f"?client_id={self.settings.oura_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=daily+sleep+heartrate"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.settings.oura_client_id,
                    "client_secret": self.settings.oura_client_secret,
                }
            )
            response.raise_for_status()
            return response.json()

    async def fetch_latest_data(self, access_token: dict) -> NormalizedHealthData:
        """Fetch and normalize the latest health data from Oura."""
        token = access_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        async with httpx.AsyncClient() as client:
            # Fetch sleep data
            sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_sleep",
                headers=headers,
                params={"start_date": str(yesterday), "end_date": str(today)}
            )
            sleep_data = sleep_response.json().get("data", [])

            # Fetch readiness data
            readiness_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_readiness",
                headers=headers,
                params={"start_date": str(yesterday), "end_date": str(today)}
            )
            readiness_data = readiness_response.json().get("data", [])

        # Extract latest values
        latest_sleep = sleep_data[-1] if sleep_data else {}
        latest_readiness = readiness_data[-1] if readiness_data else {}

        # Normalize to our schema
        return NormalizedHealthData(
            sleep_score=latest_sleep.get("score"),
            hrv_score=self._normalize_hrv(latest_readiness.get("contributors", {}).get("hrv_balance")),
            recovery_score=latest_readiness.get("score"),
            strain_score=self._calculate_strain_from_activity(latest_readiness),
            resting_hr=latest_readiness.get("contributors", {}).get("resting_heart_rate"),
            sleep_duration_hrs=self._seconds_to_hours(latest_sleep.get("contributors", {}).get("total_sleep")),
            deep_sleep_pct=latest_sleep.get("contributors", {}).get("deep_sleep"),
            rem_sleep_pct=latest_sleep.get("contributors", {}).get("rem_sleep"),
            source="oura",
            timestamp=datetime.utcnow()
        )

    def _normalize_hrv(self, hrv_balance: Optional[int]) -> Optional[float]:
        """Convert Oura's HRV balance (contributor score) to 0-100."""
        if hrv_balance is None:
            return None
        return float(hrv_balance)

    def _calculate_strain_from_activity(self, readiness: dict) -> Optional[float]:
        """Estimate strain from readiness contributors."""
        activity_balance = readiness.get("contributors", {}).get("activity_balance")
        if activity_balance is None:
            return None
        # Higher activity balance = lower strain (inverted)
        return 100 - float(activity_balance)

    def _seconds_to_hours(self, seconds: Optional[int]) -> Optional[float]:
        """Convert seconds to hours."""
        if seconds is None:
            return None
        return round(seconds / 3600, 1)
