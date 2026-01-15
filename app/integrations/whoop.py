from typing import Optional
import httpx
from datetime import datetime, timedelta

from app.config import get_settings
from .base import WearableIntegration, NormalizedHealthData


class WhoopIntegration(WearableIntegration):
    """Whoop Band API integration."""

    BASE_URL = "https://api.prod.whoop.com/developer/v1"
    AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
    TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

    def __init__(self):
        self.settings = get_settings()

    def get_auth_url(self, redirect_uri: str) -> str:
        """Get Whoop OAuth authorization URL."""
        return (
            f"{self.AUTH_URL}"
            f"?client_id={self.settings.whoop_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=read:recovery+read:sleep+read:workout"
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
                    "client_id": self.settings.whoop_client_id,
                    "client_secret": self.settings.whoop_client_secret,
                }
            )
            response.raise_for_status()
            return response.json()

    async def fetch_latest_data(self, access_token: dict) -> NormalizedHealthData:
        """Fetch and normalize the latest health data from Whoop."""
        token = access_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            # Fetch recovery data
            recovery_response = await client.get(
                f"{self.BASE_URL}/recovery",
                headers=headers,
                params={"limit": 1}
            )
            recovery_data = recovery_response.json().get("records", [])

            # Fetch sleep data
            sleep_response = await client.get(
                f"{self.BASE_URL}/activity/sleep",
                headers=headers,
                params={"limit": 1}
            )
            sleep_data = sleep_response.json().get("records", [])

            # Fetch cycle/strain data
            cycle_response = await client.get(
                f"{self.BASE_URL}/cycle",
                headers=headers,
                params={"limit": 1}
            )
            cycle_data = cycle_response.json().get("records", [])

        # Extract latest values
        latest_recovery = recovery_data[0] if recovery_data else {}
        latest_sleep = sleep_data[0] if sleep_data else {}
        latest_cycle = cycle_data[0] if cycle_data else {}

        # Normalize to our schema
        return NormalizedHealthData(
            sleep_score=self._calculate_sleep_score(latest_sleep),
            hrv_score=self._normalize_hrv(latest_recovery.get("score", {}).get("hrv_rmssd_milli")),
            recovery_score=latest_recovery.get("score", {}).get("recovery_score"),
            strain_score=self._normalize_strain(latest_cycle.get("score", {}).get("strain")),
            resting_hr=latest_recovery.get("score", {}).get("resting_heart_rate"),
            sleep_duration_hrs=self._millis_to_hours(latest_sleep.get("score", {}).get("total_in_bed_time_milli")),
            deep_sleep_pct=self._calculate_sleep_stage_pct(
                latest_sleep.get("score", {}).get("stage_summary", {}).get("total_slow_wave_sleep_time_milli"),
                latest_sleep.get("score", {}).get("total_in_bed_time_milli")
            ),
            rem_sleep_pct=self._calculate_sleep_stage_pct(
                latest_sleep.get("score", {}).get("stage_summary", {}).get("total_rem_sleep_time_milli"),
                latest_sleep.get("score", {}).get("total_in_bed_time_milli")
            ),
            source="whoop",
            timestamp=datetime.utcnow()
        )

    def _calculate_sleep_score(self, sleep: dict) -> Optional[float]:
        """Calculate sleep score from Whoop sleep metrics."""
        performance = sleep.get("score", {}).get("sleep_performance_percentage")
        if performance is None:
            return None
        return float(performance)

    def _normalize_hrv(self, hrv_rmssd: Optional[float]) -> Optional[float]:
        """Convert Whoop's HRV RMSSD to 0-100 scale."""
        if hrv_rmssd is None:
            return None
        # Typical HRV RMSSD ranges from 20-100ms, normalize to 0-100
        normalized = min(100, max(0, (hrv_rmssd - 20) * 1.25))
        return round(normalized, 1)

    def _normalize_strain(self, strain: Optional[float]) -> Optional[float]:
        """Convert Whoop's strain (0-21) to 0-100 scale."""
        if strain is None:
            return None
        # Whoop strain is 0-21, normalize to 0-100
        return round((strain / 21) * 100, 1)

    def _millis_to_hours(self, millis: Optional[int]) -> Optional[float]:
        """Convert milliseconds to hours."""
        if millis is None:
            return None
        return round(millis / 3600000, 1)

    def _calculate_sleep_stage_pct(self, stage_millis: Optional[int], total_millis: Optional[int]) -> Optional[float]:
        """Calculate sleep stage percentage."""
        if stage_millis is None or total_millis is None or total_millis == 0:
            return None
        return round((stage_millis / total_millis) * 100, 1)
