import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SupplementConfig:
    """Configuration for a single supplement."""
    id: str
    name: str
    unit: str
    max_daily_dose: float
    standard_dose: float
    time_windows: List[str]
    triggers: Dict[str, bool]
    contraindications: List[str]
    evidence: str = ""


class RulesEngine:
    """Rule-based safety layer for supplement recommendations."""

    def __init__(self, supplements_path: str = None):
        if supplements_path is None:
            supplements_path = Path(__file__).parent.parent.parent / "supplements.json"
        self.supplements = self._load_supplements(supplements_path)

    def _load_supplements(self, path: str) -> Dict[str, SupplementConfig]:
        """Load supplement configurations from JSON."""
        with open(path, "r") as f:
            data = json.load(f)

        supplements = {}
        for s in data["supplements"]:
            supplements[s["id"]] = SupplementConfig(**s)
        return supplements

    def get_time_of_day(self, hour: int = None) -> str:
        """Determine time of day category."""
        if hour is None:
            hour = datetime.now().hour

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        else:
            return "evening"

    def get_available_supplements(
        self,
        time_of_day: str,
        user_allergies: List[str] = None,
        dispensed_today: Dict[str, float] = None
    ) -> List[SupplementConfig]:
        """Get supplements available for dispensing based on rules."""
        if user_allergies is None:
            user_allergies = []
        if dispensed_today is None:
            dispensed_today = {}

        available = []

        for supplement_id, config in self.supplements.items():
            # Check time window
            if time_of_day not in config.time_windows:
                continue

            # Check contraindications (allergies)
            if any(allergy in config.contraindications for allergy in user_allergies):
                continue

            # Check daily limit
            already_dispensed = dispensed_today.get(supplement_id, 0)
            if already_dispensed >= config.max_daily_dose:
                continue

            available.append(config)

        return available

    def get_remaining_dose(
        self,
        supplement_id: str,
        dispensed_today: Dict[str, float] = None
    ) -> float:
        """Calculate remaining allowable dose for a supplement."""
        if dispensed_today is None:
            dispensed_today = {}

        config = self.supplements.get(supplement_id)
        if config is None:
            return 0

        already_dispensed = dispensed_today.get(supplement_id, 0)
        return max(0, config.max_daily_dose - already_dispensed)

    def validate_recommendation(
        self,
        supplement_id: str,
        dose: float,
        time_of_day: str,
        user_allergies: List[str] = None,
        dispensed_today: Dict[str, float] = None
    ) -> Tuple[bool, str]:
        """Validate a supplement recommendation against safety rules."""
        if user_allergies is None:
            user_allergies = []
        if dispensed_today is None:
            dispensed_today = {}

        config = self.supplements.get(supplement_id)
        if config is None:
            return False, f"Unknown supplement: {supplement_id}"

        # Check time window
        if time_of_day not in config.time_windows:
            return False, f"{config.name} cannot be dispensed in the {time_of_day}"

        # Check contraindications
        for allergy in user_allergies:
            if allergy in config.contraindications:
                return False, f"{config.name} is contraindicated for users with {allergy}"

        # Check daily limit
        already_dispensed = dispensed_today.get(supplement_id, 0)
        if already_dispensed + dose > config.max_daily_dose:
            remaining = config.max_daily_dose - already_dispensed
            return False, f"Exceeds daily limit. Max remaining: {remaining}{config.unit}"

        return True, "OK"

    # Threshold definitions for explainability
    TRIGGER_THRESHOLDS = {
        "poor_sleep": {"metric": "sleep_score", "threshold": 60, "comparison": "<", "description": "Sleep score below 60"},
        "poor_sleep_quality": {"metric": "sleep_score", "threshold": 65, "comparison": "<", "description": "Sleep quality below 65"},
        "poor_sleep_onset": {"metric": "sleep_score", "threshold": 55, "comparison": "<", "description": "Sleep score below 55"},
        "low_sleep_score": {"metric": "sleep_score", "threshold": 60, "comparison": "<", "description": "Sleep score below 60"},
        "sleep_optimization": {"metric": "sleep_score", "threshold": 80, "comparison": "<", "description": "Sleep score below optimal (80)"},
        "fatigue": {"metric": "sleep_duration_hrs", "threshold": 6, "comparison": "<", "description": "Less than 6 hours of sleep"},
        "low_hrv": {"metric": "hrv_score", "threshold": 50, "comparison": "<", "description": "HRV score below 50"},
        "high_stress": {"metric": "hrv_score", "threshold": 45, "comparison": "<", "description": "HRV score below 45 (high stress)"},
        "poor_recovery": {"metric": "recovery_score", "threshold": 55, "comparison": "<", "description": "Recovery score below 55"},
        "recovery_needed": {"metric": "recovery_score", "threshold": 60, "comparison": "<", "description": "Recovery score below 60"},
        "muscle_recovery": {"metric": "recovery_score", "threshold": 70, "comparison": "<", "description": "Recovery score below 70"},
        "high_strain": {"metric": "strain_score", "threshold": 70, "comparison": ">", "description": "Strain score above 70"},
        "dehydration": {"metric": "strain_score", "threshold": 75, "comparison": ">", "description": "Strain score above 75"},
        "high_inflammation": {"metric": "strain_score", "threshold": 60, "comparison": ">", "description": "Strain score above 60"},
        "low_energy": {"metric": "composite", "threshold": 60, "comparison": "<", "description": "Combined sleep+recovery below 60"},
        "low_sunlight": {"metric": "default", "threshold": None, "comparison": None, "description": "Default: assume limited sun exposure"},
        "immune_support": {"metric": "user_reported", "threshold": None, "comparison": None, "description": "User-reported need"},
        "illness": {"metric": "user_reported", "threshold": None, "comparison": None, "description": "User-reported illness"},
    }

    def analyze_health_triggers(self, health_data: dict) -> Dict[str, bool]:
        """Analyze health data and determine which triggers are active."""
        triggers = {}

        sleep_score = health_data.get("sleep_score")
        hrv_score = health_data.get("hrv_score")
        recovery_score = health_data.get("recovery_score")
        strain_score = health_data.get("strain_score")
        sleep_duration = health_data.get("sleep_duration_hrs")

        # Sleep-related triggers
        if sleep_score is not None:
            triggers["poor_sleep"] = sleep_score < 60
            triggers["poor_sleep_quality"] = sleep_score < 65
            triggers["poor_sleep_onset"] = sleep_score < 55
            triggers["low_sleep_score"] = sleep_score < 60
            triggers["sleep_optimization"] = sleep_score < 80

        if sleep_duration is not None:
            triggers["fatigue"] = sleep_duration < 6

        # Stress/HRV triggers
        if hrv_score is not None:
            triggers["low_hrv"] = hrv_score < 50
            triggers["high_stress"] = hrv_score < 45

        # Recovery triggers
        if recovery_score is not None:
            triggers["poor_recovery"] = recovery_score < 55
            triggers["recovery_needed"] = recovery_score < 60
            triggers["muscle_recovery"] = recovery_score < 70

        # Strain triggers
        if strain_score is not None:
            triggers["high_strain"] = strain_score > 70
            triggers["dehydration"] = strain_score > 75

        # Energy triggers (composite)
        if sleep_score is not None and recovery_score is not None:
            triggers["low_energy"] = (sleep_score + recovery_score) / 2 < 60

        # Default triggers (can be enabled by user or time-based)
        triggers["immune_support"] = False  # User can enable
        triggers["illness"] = False  # User can report
        triggers["low_sunlight"] = True  # Assume yes for supplement recommendation
        triggers["high_inflammation"] = strain_score > 60 if strain_score else False

        return triggers

    def get_trigger_explanation(self, trigger_name: str, health_data: dict) -> Optional[dict]:
        """Get detailed explanation for why a trigger is active."""
        threshold_info = self.TRIGGER_THRESHOLDS.get(trigger_name)
        if not threshold_info:
            return None

        metric = threshold_info["metric"]
        threshold = threshold_info["threshold"]
        comparison = threshold_info["comparison"]
        description = threshold_info["description"]

        # Handle composite metric
        if metric == "composite":
            sleep_score = health_data.get("sleep_score")
            recovery_score = health_data.get("recovery_score")
            if sleep_score is not None and recovery_score is not None:
                actual_value = (sleep_score + recovery_score) / 2
            else:
                return None
        elif metric in ("default", "user_reported"):
            return {
                "trigger": trigger_name,
                "description": description,
                "metric": metric,
                "actual_value": None,
                "threshold": None,
                "comparison": None
            }
        else:
            actual_value = health_data.get(metric)
            if actual_value is None:
                return None

        return {
            "trigger": trigger_name,
            "description": description,
            "metric": metric,
            "actual_value": round(actual_value, 1) if actual_value else None,
            "threshold": threshold,
            "comparison": comparison
        }

    def match_supplements_to_triggers(
        self,
        active_triggers: Dict[str, bool],
        available_supplements: List[SupplementConfig]
    ) -> List[Tuple[SupplementConfig, List[str]]]:
        """Match supplements to active health triggers."""
        matches = []

        for supplement in available_supplements:
            matched_triggers = []
            for trigger_name, is_active in active_triggers.items():
                if is_active and supplement.triggers.get(trigger_name, False):
                    matched_triggers.append(trigger_name)

            if matched_triggers:
                matches.append((supplement, matched_triggers))

        # Sort by number of matched triggers (more matches = higher priority)
        matches.sort(key=lambda x: len(x[1]), reverse=True)

        return matches
