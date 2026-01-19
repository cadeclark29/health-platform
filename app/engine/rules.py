import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from app.engine.interactions import interaction_checker


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
    research: Optional[Dict] = None  # Research citations with pubmed_id, finding, mechanism


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

    def get_time_of_day(self, hour: int = None, user_bedtime: str = None) -> str:
        """
        Determine time of day category.

        Categories:
        - morning: Wake up through noon (5am-12pm)
        - afternoon: Midday through pre-bedtime (12pm until 1hr before bedtime)
        - bedtime: 1 hour before bedtime through early morning (default 9pm-5am)

        Args:
            hour: Override current hour (0-23)
            user_bedtime: User's bedtime in "HH:MM" format (default "22:00")
        """
        if hour is None:
            hour = datetime.now().hour

        # Parse user's bedtime (default 22:00 / 10pm)
        bedtime_hour = 22
        if user_bedtime:
            try:
                bedtime_hour = int(user_bedtime.split(":")[0])
            except (ValueError, IndexError):
                pass

        # Bedtime window starts 1 hour before actual bedtime
        bedtime_start = bedtime_hour - 1
        if bedtime_start < 0:
            bedtime_start = 23

        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < bedtime_start:
            return "afternoon"
        else:
            return "bedtime"

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
        # Temperature-based immune triggers
        "immune_alert": {"metric": "temperature_deviation", "threshold": 0.5, "comparison": ">", "description": "Body temperature 0.5°C+ above baseline"},
        "immune_crisis": {"metric": "temperature_deviation", "threshold": 1.0, "comparison": ">", "description": "Significant temperature elevation (1°C+ above baseline)"},
    }

    def analyze_health_triggers(
        self,
        health_data: dict,
        baseline: Optional[dict] = None,
        checkin: Optional[dict] = None
    ) -> Dict[str, bool]:
        """
        Analyze health data and determine which triggers are active.

        Args:
            health_data: Current health metrics from wearables
            baseline: User's personal baseline (if available)
            checkin: Today's check-in data (subjective reports)

        If baseline is provided, uses personalized thresholds based on
        deviation from the user's normal. Otherwise falls back to
        population-based fixed thresholds.
        """
        triggers = {}

        sleep_score = health_data.get("sleep_score")
        hrv_score = health_data.get("hrv_score")
        recovery_score = health_data.get("recovery_score")
        strain_score = health_data.get("strain_score")
        sleep_duration = health_data.get("sleep_duration_hrs")

        # Use personalized thresholds if baseline available
        if baseline:
            triggers.update(self._analyze_with_baseline(health_data, baseline))
        else:
            # Fallback to fixed thresholds
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

            triggers["high_inflammation"] = strain_score > 60 if strain_score else False

        # Check-in based triggers (subjective reports override objective data)
        if checkin:
            stress_level = checkin.get("stress_level")
            energy_level = checkin.get("energy_level")
            sleep_quality = checkin.get("sleep_quality")

            # User reports high stress (4 or 5) - trigger regardless of HRV
            if stress_level is not None and stress_level >= 4:
                triggers["high_stress"] = True
                triggers["low_hrv"] = True  # Treat reported stress same as low HRV

            # User reports low energy (1 or 2)
            if energy_level is not None and energy_level <= 2:
                triggers["low_energy"] = True
                triggers["fatigue"] = True

            # User reports poor sleep (1 or 2)
            if sleep_quality is not None and sleep_quality <= 2:
                triggers["poor_sleep"] = True
                triggers["poor_sleep_quality"] = True

        # Default triggers (can be enabled by user or time-based)
        triggers["immune_support"] = False  # User can enable
        triggers["illness"] = False  # User can report
        triggers["low_sunlight"] = True  # Assume yes for supplement recommendation

        # Temperature-based immune triggers
        temperature_deviation = health_data.get("temperature_deviation")
        if temperature_deviation is not None:
            triggers["immune_alert"] = temperature_deviation > 0.5
            triggers["immune_crisis"] = temperature_deviation > 1.0
            # Also activate immune support if temperature is elevated
            if temperature_deviation > 0.5:
                triggers["immune_support"] = True
                triggers["illness"] = True  # Treat elevated temp as potential illness
        else:
            triggers["immune_alert"] = False
            triggers["immune_crisis"] = False

        return triggers

    def _analyze_with_baseline(self, health_data: dict, baseline: dict) -> Dict[str, bool]:
        """
        Analyze triggers using personal baseline instead of fixed thresholds.

        A metric triggers an alert if it's significantly below the user's
        personal average (more than 1 standard deviation).
        """
        triggers = {}

        def is_significantly_low(current, mean, std, metric_name):
            """Check if current value is significantly below personal baseline."""
            if current is None or mean is None:
                return False
            if std is None or std == 0:
                # No variance data, use 15% threshold
                return current < (mean * 0.85)
            # More than 1 std deviation below mean
            return current < (mean - std)

        def is_significantly_high(current, mean, std):
            """Check if current value is significantly above personal baseline."""
            if current is None or mean is None:
                return False
            if std is None or std == 0:
                return current > (mean * 1.15)
            return current > (mean + std)

        sleep_score = health_data.get("sleep_score")
        hrv_score = health_data.get("hrv_score")
        recovery_score = health_data.get("recovery_score")
        strain_score = health_data.get("strain_score")
        sleep_duration = health_data.get("sleep_duration_hrs")

        # Get baseline values
        sleep_baseline = baseline.get("sleep_score", {})
        hrv_baseline = baseline.get("hrv", {})
        recovery_baseline = baseline.get("recovery_score", {})
        strain_baseline = baseline.get("strain_score", {})
        sleep_dur_baseline = baseline.get("sleep_duration", {})

        # Sleep triggers - below personal baseline
        if sleep_score is not None:
            is_low = is_significantly_low(
                sleep_score,
                sleep_baseline.get("mean"),
                sleep_baseline.get("std"),
                "sleep"
            )
            triggers["poor_sleep"] = is_low
            triggers["poor_sleep_quality"] = is_low
            triggers["low_sleep_score"] = is_low
            triggers["sleep_optimization"] = sleep_score < (sleep_baseline.get("mean", 80) * 0.95) if sleep_baseline.get("mean") else sleep_score < 80

        # HRV triggers - below personal baseline indicates stress
        if hrv_score is not None:
            is_low = is_significantly_low(
                hrv_score,
                hrv_baseline.get("mean"),
                hrv_baseline.get("std"),
                "hrv"
            )
            triggers["low_hrv"] = is_low
            triggers["high_stress"] = is_low

        # Recovery triggers
        if recovery_score is not None:
            is_low = is_significantly_low(
                recovery_score,
                recovery_baseline.get("mean"),
                recovery_baseline.get("std"),
                "recovery"
            )
            triggers["poor_recovery"] = is_low
            triggers["recovery_needed"] = is_low
            triggers["muscle_recovery"] = is_low

        # Strain triggers - above personal baseline
        if strain_score is not None:
            is_high = is_significantly_high(
                strain_score,
                strain_baseline.get("mean"),
                strain_baseline.get("std")
            )
            triggers["high_strain"] = is_high
            triggers["dehydration"] = is_high
            triggers["high_inflammation"] = is_high

        # Sleep duration
        if sleep_duration is not None:
            is_low = is_significantly_low(
                sleep_duration,
                sleep_dur_baseline.get("mean"),
                sleep_dur_baseline.get("std"),
                "sleep_duration"
            )
            triggers["fatigue"] = is_low

        # Energy composite
        if sleep_score is not None and recovery_score is not None:
            sleep_mean = sleep_baseline.get("mean", 70)
            recovery_mean = recovery_baseline.get("mean", 70)
            personal_energy_baseline = (sleep_mean + recovery_mean) / 2
            current_energy = (sleep_score + recovery_score) / 2
            triggers["low_energy"] = current_energy < (personal_energy_baseline * 0.85)

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

    def check_interactions(
        self,
        supplement_ids: List[str],
        user_medications: Optional[List[str]] = None
    ) -> List[Dict]:
        """Check for interactions between supplements."""
        interactions = interaction_checker.check_interactions(
            supplement_ids,
            user_medications
        )
        return [
            {
                "supplements": [i.supplement_a, i.supplement_b],
                "severity": i.severity,
                "type": i.interaction_type,
                "description": i.description,
                "recommendation": i.recommendation
            }
            for i in interactions
        ]

    def get_adjusted_dose(
        self,
        supplement_id: str,
        user_profile: Dict
    ) -> Dict:
        """Get personalized dose based on user profile."""
        config = self.supplements.get(supplement_id)
        if not config:
            return {"adjusted_dose": 0, "adjustments_applied": [], "reasoning": "Unknown supplement"}

        return interaction_checker.get_adjusted_dose(
            supplement_id,
            config.standard_dose,
            user_profile
        )

    def get_cycle_status(
        self,
        supplement_id: str,
        consecutive_days: int
    ) -> Dict:
        """Check if supplement needs cycling."""
        return interaction_checker.check_cycle_status(supplement_id, consecutive_days)

    def get_all_safety_warnings(
        self,
        supplement_ids: List[str],
        user_profile: Optional[Dict] = None,
        user_medications: Optional[List[str]] = None,
        usage_history: Optional[Dict[str, int]] = None
    ) -> Dict:
        """Get comprehensive safety warnings for a set of supplements."""
        return interaction_checker.get_all_warnings(
            supplement_ids,
            user_profile,
            user_medications,
            usage_history
        )
