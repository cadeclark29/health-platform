from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedHealthData:
    """Standardized health data format from any wearable source."""
    sleep_score: Optional[float] = None  # 0-100
    hrv_score: Optional[float] = None  # 0-100
    recovery_score: Optional[float] = None  # 0-100
    strain_score: Optional[float] = None  # 0-100
    resting_hr: Optional[int] = None
    sleep_duration_hrs: Optional[float] = None
    deep_sleep_pct: Optional[float] = None
    rem_sleep_pct: Optional[float] = None
    source: str = "unknown"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "sleep_score": self.sleep_score,
            "hrv_score": self.hrv_score,
            "recovery_score": self.recovery_score,
            "strain_score": self.strain_score,
            "resting_hr": self.resting_hr,
            "sleep_duration_hrs": self.sleep_duration_hrs,
            "deep_sleep_pct": self.deep_sleep_pct,
            "rem_sleep_pct": self.rem_sleep_pct,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


class WearableIntegration(ABC):
    """Abstract base class for wearable integrations."""

    @abstractmethod
    async def fetch_latest_data(self, access_token: dict) -> NormalizedHealthData:
        """Fetch and normalize the latest health data from the wearable."""
        pass

    @abstractmethod
    def get_auth_url(self, redirect_uri: str) -> str:
        """Get the OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access token."""
        pass
