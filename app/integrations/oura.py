from typing import Optional, List
import httpx
from datetime import datetime, timedelta
import time

from app.config import get_settings
from .base import WearableIntegration, NormalizedHealthData


class OuraIntegration(WearableIntegration):
    """Oura Ring API integration with full OAuth2 support."""

    BASE_URL = "https://api.ouraring.com/v2"
    AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
    TOKEN_URL = "https://api.ouraring.com/oauth/token"

    def __init__(self):
        self.settings = get_settings()

    def get_auth_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Oura OAuth authorization URL."""
        # Scopes must match what's registered in Oura developer portal
        scopes = "email+personal+daily+heartrate+tag+workout+session+spo2+ring_configuration+stress+heart_health"
        url = (
            f"{self.AUTH_URL}"
            f"?client_id={self.settings.oura_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scopes}"
        )
        if state:
            url += f"&state={state}"
        return url

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
            token_data = response.json()

            # Add expiry timestamp for easier checking
            if "expires_in" in token_data:
                token_data["expires_at"] = int(time.time()) + token_data["expires_in"]

            return token_data

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.settings.oura_client_id,
                    "client_secret": self.settings.oura_client_secret,
                }
            )
            response.raise_for_status()
            token_data = response.json()

            if "expires_in" in token_data:
                token_data["expires_at"] = int(time.time()) + token_data["expires_in"]

            return token_data

    def is_token_expired(self, token_data: dict) -> bool:
        """Check if the access token is expired or about to expire."""
        expires_at = token_data.get("expires_at", 0)
        # Consider expired if less than 5 minutes remaining
        return time.time() > (expires_at - 300)

    async def get_valid_token(self, token_data: dict) -> dict:
        """Get a valid token, refreshing if necessary."""
        if self.is_token_expired(token_data):
            refresh_token = token_data.get("refresh_token")
            if refresh_token:
                return await self.refresh_token(refresh_token)
            raise Exception("Token expired and no refresh token available")
        return token_data

    async def fetch_latest_data(self, access_token: dict) -> NormalizedHealthData:
        """Fetch and normalize the latest health data from Oura."""
        token = access_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        async with httpx.AsyncClient() as client:
            # Fetch daily sleep summary
            sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_sleep",
                headers=headers,
                params={"start_date": str(yesterday), "end_date": str(today)}
            )
            sleep_data = sleep_response.json().get("data", [])

            # Fetch detailed sleep data (contains actual HRV)
            detailed_sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/sleep",
                headers=headers,
                params={"start_date": str(yesterday), "end_date": str(today)}
            )
            detailed_sleep_data = detailed_sleep_response.json().get("data", [])

            # Fetch readiness data
            readiness_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_readiness",
                headers=headers,
                params={"start_date": str(yesterday), "end_date": str(today)}
            )
            readiness_data = readiness_response.json().get("data", [])

        # Extract latest values
        latest_sleep = sleep_data[-1] if sleep_data else {}
        latest_detailed_sleep = detailed_sleep_data[-1] if detailed_sleep_data else {}
        latest_readiness = readiness_data[-1] if readiness_data else {}

        # Get HRV - try average_hrv from detailed sleep first, then hrv_balance from readiness
        actual_hrv = latest_detailed_sleep.get("average_hrv")
        if actual_hrv is None:
            # Fallback to hrv_balance contributor from readiness (0-100 score)
            actual_hrv = latest_readiness.get("contributors", {}).get("hrv_balance")

        # Normalize to our schema
        return NormalizedHealthData(
            sleep_score=latest_sleep.get("score"),
            hrv_score=actual_hrv,  # HRV in ms or hrv_balance score
            recovery_score=latest_readiness.get("score"),
            strain_score=self._calculate_strain_from_activity(latest_readiness),
            resting_hr=latest_readiness.get("contributors", {}).get("resting_heart_rate"),
            sleep_duration_hrs=self._seconds_to_hours(latest_detailed_sleep.get("total_sleep_duration")),
            deep_sleep_pct=latest_sleep.get("contributors", {}).get("deep_sleep"),
            rem_sleep_pct=latest_sleep.get("contributors", {}).get("rem_sleep"),
            source="oura",
            timestamp=datetime.utcnow()
        )

    async def fetch_historical_data(self, access_token: dict, days: int = 7) -> List[dict]:
        """Fetch historical health data for the past N days."""
        token = access_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days)

        async with httpx.AsyncClient() as client:
            # Fetch daily sleep summary
            sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_sleep",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            sleep_data = {d.get("day"): d for d in sleep_response.json().get("data", [])}

            # Fetch detailed sleep data (contains actual HRV)
            detailed_sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/sleep",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            # Index by day (sleep sessions have a "day" field)
            detailed_sleep_data = {}
            for d in detailed_sleep_response.json().get("data", []):
                day = d.get("day")
                if day:
                    # Keep the latest sleep session for each day
                    detailed_sleep_data[day] = d

            # Fetch readiness data
            readiness_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_readiness",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            readiness_data = {d.get("day"): d for d in readiness_response.json().get("data", [])}

            # Fetch activity data
            activity_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_activity",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            activity_data = {d.get("day"): d for d in activity_response.json().get("data", [])}

        # Combine data by date
        historical = []
        current = start_date
        while current <= today:
            date_str = str(current)
            sleep = sleep_data.get(date_str, {})
            detailed_sleep = detailed_sleep_data.get(date_str, {})
            readiness = readiness_data.get(date_str, {})
            activity = activity_data.get(date_str, {})

            # Get HRV - try average_hrv from detailed sleep first, then hrv_balance from readiness
            actual_hrv = detailed_sleep.get("average_hrv")
            if actual_hrv is None:
                # Fallback to hrv_balance contributor from readiness (0-100 score)
                actual_hrv = readiness.get("contributors", {}).get("hrv_balance")

            historical.append({
                "date": date_str,
                "sleep_score": sleep.get("score"),
                "hrv_score": actual_hrv,  # HRV in ms or hrv_balance score
                "recovery_score": readiness.get("score"),
                "strain_score": self._calculate_strain_from_activity(readiness),
                "resting_hr": readiness.get("contributors", {}).get("resting_heart_rate"),
                "sleep_duration_hrs": self._seconds_to_hours(detailed_sleep.get("total_sleep_duration")),
                "deep_sleep_pct": sleep.get("contributors", {}).get("deep_sleep"),
                "rem_sleep_pct": sleep.get("contributors", {}).get("rem_sleep"),
                "steps": activity.get("steps"),
                "active_calories": activity.get("active_calories"),
            })
            current += timedelta(days=1)

        return historical

    async def verify_connection(self, access_token: dict) -> dict:
        """Verify the Oura connection is valid and get user info."""
        token = access_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/usercollection/personal_info",
                headers=headers
            )
            if response.status_code == 200:
                return {"connected": True, "info": response.json()}
            elif response.status_code == 401:
                return {"connected": False, "error": "Token expired"}
            else:
                return {"connected": False, "error": f"API error: {response.status_code}"}

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
