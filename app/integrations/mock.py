import random
from datetime import datetime

from .base import WearableIntegration, NormalizedHealthData


class MockIntegration(WearableIntegration):
    """Mock wearable integration for testing and development."""

    def __init__(self, scenario: str = "average"):
        """
        Initialize mock with a scenario.

        Scenarios:
        - "average": Normal, healthy readings
        - "poor_sleep": Low sleep scores
        - "high_strain": High physical strain
        - "stressed": Low HRV, high stress indicators
        - "recovering": Good recovery, moderate everything else
        - "random": Randomized values
        """
        self.scenario = scenario

    async def fetch_latest_data(self, access_token: dict = None) -> NormalizedHealthData:
        """Generate mock health data based on scenario."""
        scenarios = {
            "average": {
                "sleep_score": 75,
                "hrv_score": 70,
                "recovery_score": 72,
                "strain_score": 50,
                "resting_hr": 58,
                "sleep_duration_hrs": 7.5,
                "deep_sleep_pct": 20,
                "rem_sleep_pct": 22,
            },
            "poor_sleep": {
                "sleep_score": 45,
                "hrv_score": 55,
                "recovery_score": 50,
                "strain_score": 40,
                "resting_hr": 65,
                "sleep_duration_hrs": 5.5,
                "deep_sleep_pct": 12,
                "rem_sleep_pct": 15,
            },
            "high_strain": {
                "sleep_score": 70,
                "hrv_score": 60,
                "recovery_score": 55,
                "strain_score": 85,
                "resting_hr": 62,
                "sleep_duration_hrs": 7.0,
                "deep_sleep_pct": 18,
                "rem_sleep_pct": 20,
            },
            "stressed": {
                "sleep_score": 60,
                "hrv_score": 40,
                "recovery_score": 45,
                "strain_score": 60,
                "resting_hr": 70,
                "sleep_duration_hrs": 6.5,
                "deep_sleep_pct": 15,
                "rem_sleep_pct": 18,
            },
            "recovering": {
                "sleep_score": 85,
                "hrv_score": 80,
                "recovery_score": 88,
                "strain_score": 30,
                "resting_hr": 52,
                "sleep_duration_hrs": 8.5,
                "deep_sleep_pct": 25,
                "rem_sleep_pct": 25,
            },
            "random": {
                "sleep_score": random.randint(30, 95),
                "hrv_score": random.randint(30, 95),
                "recovery_score": random.randint(30, 95),
                "strain_score": random.randint(20, 90),
                "resting_hr": random.randint(45, 75),
                "sleep_duration_hrs": round(random.uniform(4.5, 9.5), 1),
                "deep_sleep_pct": random.randint(10, 30),
                "rem_sleep_pct": random.randint(15, 28),
            },
        }

        data = scenarios.get(self.scenario, scenarios["average"])

        return NormalizedHealthData(
            **data,
            source="mock",
            timestamp=datetime.utcnow()
        )

    def get_auth_url(self, redirect_uri: str) -> str:
        """Mock auth URL - just returns a placeholder."""
        return f"mock://auth?redirect_uri={redirect_uri}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Mock token exchange - returns fake tokens."""
        return {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_at": 9999999999
        }
