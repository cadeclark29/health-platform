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
        latest_readiness = readiness_data[-1] if readiness_data else {}

        # Find the best sleep session - prefer "long_sleep" (main sleep) over naps
        latest_detailed_sleep = {}
        for d in detailed_sleep_data:
            if not latest_detailed_sleep:
                latest_detailed_sleep = d
            elif d.get("type") == "long_sleep" and latest_detailed_sleep.get("type") != "long_sleep":
                latest_detailed_sleep = d
            elif d.get("type") == latest_detailed_sleep.get("type"):
                # Same type - prefer longer duration
                if (d.get("total_sleep_duration") or 0) > (latest_detailed_sleep.get("total_sleep_duration") or 0):
                    latest_detailed_sleep = d

        # Get actual HRV in milliseconds from detailed sleep data
        actual_hrv = latest_detailed_sleep.get("average_hrv")

        # Normalize to our schema
        return NormalizedHealthData(
            sleep_score=latest_sleep.get("score"),
            hrv_score=actual_hrv,  # Actual HRV in milliseconds
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
        """Fetch comprehensive historical health data for the past N days."""
        token = access_token.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # === SLEEP DATA ===
            # Daily sleep summary (scores)
            sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_sleep",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            sleep_data = {d.get("day"): d for d in sleep_response.json().get("data", [])}

            # Detailed sleep sessions (HRV, duration breakdown, bedtime/wake)
            detailed_sleep_response = await client.get(
                f"{self.BASE_URL}/usercollection/sleep",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            # Index by day - prefer "long_sleep" (main sleep) over naps
            detailed_sleep_data = {}
            for d in detailed_sleep_response.json().get("data", []):
                day = d.get("day")
                if day:
                    existing = detailed_sleep_data.get(day)
                    if not existing:
                        detailed_sleep_data[day] = d
                    elif d.get("type") == "long_sleep" and existing.get("type") != "long_sleep":
                        detailed_sleep_data[day] = d
                    elif d.get("type") == existing.get("type"):
                        if (d.get("total_sleep_duration") or 0) > (existing.get("total_sleep_duration") or 0):
                            detailed_sleep_data[day] = d

            # === READINESS DATA ===
            readiness_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_readiness",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            readiness_data = {d.get("day"): d for d in readiness_response.json().get("data", [])}

            # === ACTIVITY DATA ===
            activity_response = await client.get(
                f"{self.BASE_URL}/usercollection/daily_activity",
                headers=headers,
                params={"start_date": str(start_date), "end_date": str(today)}
            )
            activity_data = {d.get("day"): d for d in activity_response.json().get("data", [])}

            # === SPO2 DATA ===
            spo2_data = {}
            try:
                spo2_response = await client.get(
                    f"{self.BASE_URL}/usercollection/daily_spo2",
                    headers=headers,
                    params={"start_date": str(start_date), "end_date": str(today)}
                )
                if spo2_response.status_code == 200:
                    spo2_data = {d.get("day"): d for d in spo2_response.json().get("data", [])}
            except Exception:
                pass  # SpO2 may not be available for all users

            # === STRESS DATA ===
            stress_data = {}
            try:
                stress_response = await client.get(
                    f"{self.BASE_URL}/usercollection/daily_stress",
                    headers=headers,
                    params={"start_date": str(start_date), "end_date": str(today)}
                )
                if stress_response.status_code == 200:
                    stress_data = {d.get("day"): d for d in stress_response.json().get("data", [])}
            except Exception:
                pass  # Stress may not be available

            # === WORKOUT DATA ===
            workout_data = {}
            try:
                workout_response = await client.get(
                    f"{self.BASE_URL}/usercollection/workout",
                    headers=headers,
                    params={"start_date": str(start_date), "end_date": str(today)}
                )
                if workout_response.status_code == 200:
                    # Group workouts by day, keep most recent per day
                    for w in workout_response.json().get("data", []):
                        day = w.get("day")
                        if day:
                            workout_data[day] = w
            except Exception:
                pass

            # === VO2 MAX / HEART HEALTH ===
            vo2_data = {}
            try:
                vo2_response = await client.get(
                    f"{self.BASE_URL}/usercollection/vO2_max",
                    headers=headers,
                    params={"start_date": str(start_date), "end_date": str(today)}
                )
                if vo2_response.status_code == 200:
                    vo2_data = {d.get("day"): d for d in vo2_response.json().get("data", [])}
            except Exception:
                pass

        # Combine all data by date
        historical = []
        current = start_date
        while current <= today:
            date_str = str(current)
            sleep = sleep_data.get(date_str, {})
            detailed_sleep = detailed_sleep_data.get(date_str, {})
            readiness = readiness_data.get(date_str, {})
            activity = activity_data.get(date_str, {})
            spo2 = spo2_data.get(date_str, {})
            stress = stress_data.get(date_str, {})
            workout = workout_data.get(date_str, {})
            vo2 = vo2_data.get(date_str, {})

            # Extract readiness contributors
            readiness_contributors = readiness.get("contributors", {})

            # Calculate restfulness from restless periods (lower = more restful)
            restless_periods = detailed_sleep.get("restless_periods")
            restfulness_score = None
            if restless_periods is not None:
                # Typical range 0-500, normalize to 0-100 (inverted)
                restfulness_score = max(0, min(100, 100 - int(restless_periods / 5)))

            # Stress level categorization
            stress_score = stress.get("stress_high")
            stress_level = None
            if stress_score is not None:
                if stress_score < 30:
                    stress_level = "low"
                elif stress_score < 60:
                    stress_level = "medium"
                else:
                    stress_level = "high"

            historical.append({
                "date": date_str,

                # === Core Metrics ===
                "sleep_score": sleep.get("score"),
                "hrv_score": detailed_sleep.get("average_hrv"),
                "recovery_score": readiness.get("score"),
                "strain_score": self._calculate_strain_from_activity(readiness),

                # === Sleep Details ===
                "sleep_duration_hrs": self._seconds_to_hours(detailed_sleep.get("total_sleep_duration")),
                "deep_sleep_duration": detailed_sleep.get("deep_sleep_duration"),
                "rem_sleep_duration": detailed_sleep.get("rem_sleep_duration"),
                "light_sleep_duration": detailed_sleep.get("light_sleep_duration"),
                "awake_duration": detailed_sleep.get("awake_time"),
                "sleep_efficiency": detailed_sleep.get("efficiency"),
                "sleep_latency": detailed_sleep.get("latency"),
                "restfulness_score": restfulness_score,
                "bedtime": detailed_sleep.get("bedtime_start"),
                "wake_time": detailed_sleep.get("bedtime_end"),
                "deep_sleep_pct": sleep.get("contributors", {}).get("deep_sleep"),
                "rem_sleep_pct": sleep.get("contributors", {}).get("rem_sleep"),

                # === Heart Rate ===
                "resting_hr": readiness_contributors.get("resting_heart_rate"),
                "lowest_hr": detailed_sleep.get("lowest_heart_rate"),
                "average_hr_sleep": detailed_sleep.get("average_heart_rate"),

                # === Heart Health ===
                "vo2_max": vo2.get("vo2_max"),

                # === Activity ===
                "activity_score": activity.get("score"),
                "steps": activity.get("steps"),
                "active_calories": activity.get("active_calories"),
                "total_calories": activity.get("total_calories"),
                "sedentary_time": activity.get("sedentary_time"),
                "active_time": (activity.get("low_activity_time") or 0) +
                              (activity.get("medium_activity_time") or 0) +
                              (activity.get("high_activity_time") or 0) if activity else None,

                # === SpO2 / Breathing ===
                "spo2_average": spo2.get("spo2_percentage", {}).get("average") if isinstance(spo2.get("spo2_percentage"), dict) else spo2.get("spo2_average"),
                "breathing_average": detailed_sleep.get("average_breath"),
                "breathing_regularity": spo2.get("breathing_disturbance_index"),

                # === Stress ===
                "stress_level": stress_level,
                "stress_score": stress.get("stress_high"),

                # === Workout ===
                "workout_type": workout.get("activity") or workout.get("sport"),
                "workout_duration": self._seconds_to_minutes(workout.get("total_duration")) if workout else None,
                "workout_intensity": workout.get("intensity"),
                "workout_calories": workout.get("calories"),
                "workout_source": workout.get("source"),

                # === Temperature ===
                "temperature_deviation": readiness.get("temperature_deviation"),
                "temperature_trend": readiness.get("temperature_trend_deviation"),
            })
            current += timedelta(days=1)

        return historical

    def _seconds_to_minutes(self, seconds: Optional[int]) -> Optional[int]:
        """Convert seconds to minutes."""
        if seconds is None:
            return None
        return round(seconds / 60)

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
