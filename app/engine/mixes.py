"""
Pre-Set Supplement Mixes

Quick-select blends for different needs/moods. Each mix is personalized
based on user profile (weight, age, sex) and respects daily limits.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MixComponent:
    """A supplement in a mix with its dose multiplier."""
    supplement_id: str
    dose_multiplier: float = 1.0  # Multiplier of standard dose
    required: bool = True  # If false, can be omitted if unavailable


@dataclass
class SupplementMix:
    """A pre-defined supplement blend."""
    id: str
    name: str
    icon: str
    description: str
    time_windows: List[str]  # When this mix can be dispensed
    components: List[MixComponent]
    category: str  # "energy", "recovery", "sleep", "wellness", "performance"
    color: str  # UI accent color


# Define all available mixes
SUPPLEMENT_MIXES: Dict[str, SupplementMix] = {
    "wake_me_up": SupplementMix(
        id="wake_me_up",
        name="Wake Me Up",
        icon="☀️",
        description="Start your day with energy and focus",
        time_windows=["morning"],
        components=[
            MixComponent("caffeine", 1.0),
            MixComponent("l_theanine", 1.0),  # Smooths caffeine
            MixComponent("vitamin_b12", 1.0),
            MixComponent("vitamin_d3", 1.0),
        ],
        category="energy",
        color="#FFB800"
    ),

    "night_drink": SupplementMix(
        id="night_drink",
        name="Night Drink",
        icon="🌙",
        description="Wind down and optimize sleep quality",
        time_windows=["evening"],
        components=[
            MixComponent("magnesium_glycinate", 1.0),
            MixComponent("glycine", 1.0),
            MixComponent("apigenin", 1.0),
            MixComponent("melatonin", 0.5, required=False),  # Lower dose, optional
        ],
        category="sleep",
        color="#6B5BFF"
    ),

    "pre_workout": SupplementMix(
        id="pre_workout",
        name="Pre-Workout",
        icon="🔥",
        description="Maximize performance and endurance",
        time_windows=["morning", "afternoon"],
        components=[
            MixComponent("caffeine", 1.5),  # Slightly higher
            MixComponent("l_citrulline", 1.0),
            MixComponent("creatine", 1.0),
            MixComponent("vitamin_b12", 1.0),
        ],
        category="performance",
        color="#FF4D4D"
    ),

    "post_workout": SupplementMix(
        id="post_workout",
        name="Post-Workout",
        icon="💪",
        description="Accelerate recovery and reduce soreness",
        time_windows=["morning", "afternoon", "evening"],
        components=[
            MixComponent("creatine", 1.0),
            MixComponent("electrolytes", 1.0),
            MixComponent("magnesium_glycinate", 0.5),
            MixComponent("omega_3", 1.0),
            MixComponent("vitamin_c", 0.5),
        ],
        category="recovery",
        color="#00D68F"
    ),

    "stressed": SupplementMix(
        id="stressed",
        name="Stressed",
        icon="🧘",
        description="Calm your mind and lower cortisol",
        time_windows=["morning", "afternoon", "evening"],
        components=[
            MixComponent("ashwagandha", 1.0),
            MixComponent("l_theanine", 1.0),
            MixComponent("magnesium_glycinate", 0.5),
            MixComponent("magnesium_l_threonate", 0.5, required=False),
        ],
        category="wellness",
        color="#9B59B6"
    ),

    "immune_boost": SupplementMix(
        id="immune_boost",
        name="Immune Boost",
        icon="🛡️",
        description="Support your immune system when feeling run down",
        time_windows=["morning", "afternoon", "evening"],
        components=[
            MixComponent("vitamin_c", 1.5),
            MixComponent("zinc", 1.0),
            MixComponent("vitamin_d3", 1.0),
            MixComponent("nac", 1.0),
            MixComponent("blackseed_oil", 1.0, required=False),
        ],
        category="wellness",
        color="#3498DB"
    ),

    "focus_mode": SupplementMix(
        id="focus_mode",
        name="Focus Mode",
        icon="🎯",
        description="Enhance concentration and mental clarity",
        time_windows=["morning", "afternoon"],
        components=[
            MixComponent("caffeine", 0.75),  # Moderate caffeine
            MixComponent("l_theanine", 1.5),  # Higher theanine for smooth focus
            MixComponent("lions_mane", 1.0),
            MixComponent("vitamin_b12", 0.5),
        ],
        category="energy",
        color="#00CED1"
    ),

    "recovery_day": SupplementMix(
        id="recovery_day",
        name="Recovery Day",
        icon="🔄",
        description="Rest day support for muscle repair",
        time_windows=["morning", "afternoon", "evening"],
        components=[
            MixComponent("omega_3", 1.0),
            MixComponent("magnesium_glycinate", 1.0),
            MixComponent("coq10", 1.0),
            MixComponent("vitamin_c", 0.5),
            MixComponent("creatine", 1.0),
        ],
        category="recovery",
        color="#2ECC71"
    ),

    "low_energy": SupplementMix(
        id="low_energy",
        name="Low Energy",
        icon="⚡",
        description="Combat fatigue without the jitters",
        time_windows=["morning", "afternoon"],
        components=[
            MixComponent("vitamin_b12", 1.5),
            MixComponent("coq10", 1.0),
            MixComponent("vitamin_d3", 1.0),
            MixComponent("l_theanine", 0.5),
            MixComponent("caffeine", 0.5, required=False),  # Optional light caffeine
        ],
        category="energy",
        color="#F39C12"
    ),

    "jet_lag": SupplementMix(
        id="jet_lag",
        name="Jet Lag Reset",
        icon="✈️",
        description="Reset your circadian rhythm after travel",
        time_windows=["evening"],
        components=[
            MixComponent("melatonin", 1.0),
            MixComponent("magnesium_glycinate", 1.0),
            MixComponent("glycine", 0.5),
            MixComponent("vitamin_b12", 0.5),  # For next-day energy
        ],
        category="sleep",
        color="#8E44AD"
    ),

    "hangover": SupplementMix(
        id="hangover",
        name="Morning After",
        icon="🍋",
        description="Recover from a rough night out",
        time_windows=["morning", "afternoon"],
        components=[
            MixComponent("nac", 1.0),  # Liver support
            MixComponent("vitamin_c", 1.5),
            MixComponent("electrolytes", 2.0),  # Extra hydration
            MixComponent("vitamin_b12", 1.0),
            MixComponent("magnesium_glycinate", 0.5),
        ],
        category="recovery",
        color="#E74C3C"
    ),

    "brain_fog": SupplementMix(
        id="brain_fog",
        name="Clear Mind",
        icon="🧠",
        description="Cut through mental haze and think clearly",
        time_windows=["morning", "afternoon"],
        components=[
            MixComponent("lions_mane", 1.0),
            MixComponent("magnesium_l_threonate", 1.0),
            MixComponent("omega_3", 0.5),
            MixComponent("vitamin_b12", 1.0),
            MixComponent("l_theanine", 0.5),
        ],
        category="energy",
        color="#1ABC9C"
    ),

    "daily_foundation": SupplementMix(
        id="daily_foundation",
        name="Daily Foundation",
        icon="💎",
        description="Essential daily nutrients for overall health",
        time_windows=["morning"],
        components=[
            MixComponent("vitamin_d3", 1.0),
            MixComponent("vitamin_k2", 1.0),
            MixComponent("omega_3", 1.0),
            MixComponent("magnesium_glycinate", 0.5),
        ],
        category="wellness",
        color="#34495E"
    ),
}


class MixEngine:
    """Engine for generating personalized supplement mixes."""

    def __init__(self):
        from app.engine.rules import RulesEngine
        from app.engine.interactions import interaction_checker

        self.rules = RulesEngine()
        self.interactions = interaction_checker
        self.mixes = SUPPLEMENT_MIXES

    def get_available_mixes(self, time_of_day: str) -> List[SupplementMix]:
        """Get mixes available for the current time of day."""
        return [
            mix for mix in self.mixes.values()
            if time_of_day in mix.time_windows
        ]

    def get_mix_by_id(self, mix_id: str) -> Optional[SupplementMix]:
        """Get a specific mix by ID."""
        return self.mixes.get(mix_id)

    def calculate_mix_doses(
        self,
        mix: SupplementMix,
        user_profile: Dict,
        dispensed_today: Dict[str, float] = None
    ) -> Dict:
        """
        Calculate personalized doses for a mix.

        Args:
            mix: The supplement mix to calculate
            user_profile: User's profile (weight_kg, age, sex)
            dispensed_today: Already dispensed supplements today

        Returns:
            Dict with supplements, doses, and any warnings
        """
        if dispensed_today is None:
            dispensed_today = {}

        supplements = []
        warnings = []
        skipped = []

        for component in mix.components:
            config = self.rules.supplements.get(component.supplement_id)
            if not config:
                if component.required:
                    skipped.append({
                        "supplement_id": component.supplement_id,
                        "reason": "Supplement not found in catalog"
                    })
                continue

            # Get personalized dose
            base_dose = config.standard_dose * component.dose_multiplier
            adjusted = self.interactions.get_adjusted_dose(
                component.supplement_id,
                base_dose,
                user_profile
            )
            dose = adjusted["adjusted_dose"]

            # Check remaining daily allowance
            already_dispensed = dispensed_today.get(component.supplement_id, 0)
            remaining = config.max_daily_dose - already_dispensed

            if remaining <= 0:
                if component.required:
                    skipped.append({
                        "supplement_id": component.supplement_id,
                        "name": config.name,
                        "reason": "Daily limit reached"
                    })
                continue

            # Cap at remaining allowance
            final_dose = min(dose, remaining)
            if final_dose < dose * 0.5:
                # Less than half the intended dose - warn user
                warnings.append({
                    "supplement_id": component.supplement_id,
                    "name": config.name,
                    "message": f"Reduced to {final_dose}{config.unit} (daily limit)"
                })

            supplements.append({
                "supplement_id": component.supplement_id,
                "name": config.name,
                "dose": round(final_dose, 1),
                "unit": config.unit,
                "standard_dose": config.standard_dose,
                "adjusted_from": round(base_dose, 1) if adjusted["adjustments_applied"] else None,
                "adjustments": adjusted["adjustments_applied"] if adjusted["adjustments_applied"] else None
            })

        # Check for interactions between mix components
        supplement_ids = [s["supplement_id"] for s in supplements]
        interactions = self.interactions.check_interactions(supplement_ids)

        interaction_warnings = []
        for interaction in interactions:
            # Filter out synergies from warnings (they're intentional in mixes)
            if interaction.interaction_type != "synergy":
                interaction_warnings.append({
                    "supplements": [interaction.supplement_a, interaction.supplement_b],
                    "severity": interaction.severity,
                    "type": interaction.interaction_type,
                    "description": interaction.description,
                    "recommendation": interaction.recommendation
                })

        return {
            "mix_id": mix.id,
            "mix_name": mix.name,
            "mix_icon": mix.icon,
            "mix_description": mix.description,
            "supplements": supplements,
            "warnings": warnings,
            "skipped": skipped,
            "interaction_warnings": interaction_warnings,
            "total_supplements": len(supplements)
        }

    def get_smart_recommendation(
        self,
        health_data: Dict,
        time_of_day: str,
        user_profile: Dict
    ) -> Optional[str]:
        """
        Recommend a mix based on health data.

        Analyzes wearable data to suggest the most appropriate mix.
        """
        sleep_score = health_data.get("sleep_score")
        hrv_score = health_data.get("hrv_score")
        recovery_score = health_data.get("recovery_score")
        strain_score = health_data.get("strain_score")

        # Morning recommendations
        if time_of_day == "morning":
            # Poor sleep last night
            if sleep_score and sleep_score < 60:
                return "wake_me_up"

            # High strain yesterday, need recovery
            if strain_score and strain_score > 75:
                return "recovery_day"

            # Low HRV (stressed)
            if hrv_score and hrv_score < 50:
                return "stressed"

            # Default good morning
            return "daily_foundation"

        # Afternoon recommendations
        elif time_of_day == "afternoon":
            # Energy crash
            if sleep_score and sleep_score < 55:
                return "low_energy"

            # Stressed
            if hrv_score and hrv_score < 45:
                return "stressed"

            # Need focus
            return "focus_mode"

        # Evening recommendations
        elif time_of_day == "evening":
            # High strain day
            if strain_score and strain_score > 70:
                return "post_workout"

            # Poor recovery
            if recovery_score and recovery_score < 55:
                return "recovery_day"

            # Default evening
            return "night_drink"

        return None


# Singleton instance
mix_engine = MixEngine()
