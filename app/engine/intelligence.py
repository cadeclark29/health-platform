"""
Smart Dosing Intelligence Module

Advanced algorithms for personalized supplement recommendations based on:
- Seasonal factors (Vitamin D)
- Usage patterns (melatonin tolerance)
- Circadian rhythm (magnesium timing)
- Stacking safety (stimulant load)
- Recovery trends (adaptive dosing)
- Age-specific adjustments
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass


@dataclass
class IntelligenceWarning:
    """A warning or recommendation from the intelligence system."""
    type: str  # "warning", "recommendation", "info"
    supplement_id: str
    title: str
    message: str
    action: Optional[str] = None  # Suggested action


@dataclass
class DoseModification:
    """A modification to apply to a dose."""
    supplement_id: str
    multiplier: float  # 1.0 = no change, 1.5 = 50% increase
    reason: str
    source: str  # Which intelligence rule triggered this


class DosingIntelligence:
    """Smart dosing engine with advanced personalization."""

    # Northern latitudes need more Vitamin D in winter
    LATITUDE_ZONES = {
        "northern": 40,  # Above 40°N (NYC, Chicago, Seattle)
        "southern": -40,  # Below 40°S
    }

    def __init__(self):
        pass

    # ==========================================
    # 1. VITAMIN D SEASONALITY
    # ==========================================

    def get_vitamin_d_adjustment(
        self,
        current_date: date = None,
        latitude: float = None,
        sun_exposure_minutes: int = None
    ) -> DoseModification:
        """
        Adjust Vitamin D dose based on season and sun exposure.

        Research: PMID 32690727, 33146667
        - Winter months have reduced UVB, requiring higher supplementation
        - Northern latitudes (>40°N) have minimal vitamin D synthesis Oct-Mar
        - 15-30 min midday sun exposure can provide 10,000-20,000 IU
        """
        if current_date is None:
            current_date = date.today()

        month = current_date.month

        # Determine season (Northern Hemisphere)
        is_winter = month in [11, 12, 1, 2, 3]  # Nov-Mar
        is_summer = month in [5, 6, 7, 8]  # May-Aug

        # Default latitude if not provided (assume US average ~39°N)
        if latitude is None:
            latitude = 39.0

        # Calculate base multiplier
        multiplier = 1.0
        reasons = []

        # Winter adjustment
        if is_winter:
            if latitude > 40:
                multiplier = 1.5  # 50% increase for northern winter
                reasons.append("Winter in northern latitude - minimal UVB")
            else:
                multiplier = 1.25  # 25% increase for other winter
                reasons.append("Winter months - reduced sun exposure")

        # Summer with good sun exposure - can reduce
        elif is_summer and sun_exposure_minutes and sun_exposure_minutes > 20:
            multiplier = 0.5  # Reduce by 50% if getting good sun
            reasons.append(f"Summer with {sun_exposure_minutes}min sun exposure")

        # High latitude year-round needs boost
        if latitude > 50 and not is_summer:
            multiplier *= 1.25
            reasons.append("High latitude location")

        return DoseModification(
            supplement_id="vitamin_d3",
            multiplier=round(multiplier, 2),
            reason="; ".join(reasons) if reasons else "Standard dosing",
            source="seasonality"
        )

    # ==========================================
    # 2. MELATONIN TOLERANCE DETECTION
    # ==========================================

    def check_melatonin_tolerance(
        self,
        consecutive_days: int,
        current_dose: float,
        sleep_quality_trend: List[float] = None
    ) -> Tuple[DoseModification, Optional[IntelligenceWarning]]:
        """
        Detect melatonin tolerance and recommend cycling.

        Research: PMID 17645585, 28648359
        - Exogenous melatonin can suppress natural production
        - Efficacy often decreases after 2-4 weeks continuous use
        - Lower doses (0.3-1mg) often more effective than high doses
        """
        warning = None
        multiplier = 1.0
        reason = "Standard dosing"

        # Check for extended use
        if consecutive_days >= 21:
            warning = IntelligenceWarning(
                type="warning",
                supplement_id="melatonin",
                title="Melatonin Cycling Recommended",
                message=f"You've used melatonin for {consecutive_days} consecutive days. "
                        "Consider taking a 1-week break to maintain sensitivity and "
                        "allow natural melatonin production to recover.",
                action="cycle_off"
            )
            multiplier = 0.0  # Recommend skipping
            reason = "Cycle break recommended after 21+ days"

        elif consecutive_days >= 14:
            warning = IntelligenceWarning(
                type="info",
                supplement_id="melatonin",
                title="Approaching Melatonin Cycle",
                message=f"Day {consecutive_days} of melatonin use. "
                        f"Plan to cycle off in {21 - consecutive_days} days.",
                action=None
            )

        # Check if sleep quality is declining despite melatonin
        if sleep_quality_trend and len(sleep_quality_trend) >= 5:
            recent = sleep_quality_trend[-5:]
            if all(recent[i] <= recent[i-1] for i in range(1, len(recent))):
                # Declining trend
                if not warning:
                    warning = IntelligenceWarning(
                        type="recommendation",
                        supplement_id="melatonin",
                        title="Consider Reducing Melatonin",
                        message="Your sleep quality has been declining. "
                                "Try reducing melatonin dose or cycling off - "
                                "lower doses (0.3-0.5mg) are often more effective.",
                        action="reduce_dose"
                    )
                    multiplier = 0.5
                    reason = "Declining sleep quality - try lower dose"

        return (
            DoseModification(
                supplement_id="melatonin",
                multiplier=multiplier,
                reason=reason,
                source="tolerance_detection"
            ),
            warning
        )

    # ==========================================
    # 3. CIRCADIAN-AWARE MAGNESIUM
    # ==========================================

    def get_magnesium_timing(
        self,
        sleep_onset_time: str = None,  # "23:30" format
        target_bedtime: str = "22:30",
        sleep_onset_latency: int = None  # Minutes to fall asleep
    ) -> Tuple[int, Optional[IntelligenceWarning]]:
        """
        Recommend optimal magnesium timing based on sleep patterns.

        Research: PMID 34883514, 28445426
        - Magnesium glycinate takes 1-2 hours to reach peak effect
        - Late sleep onset suggests taking magnesium earlier
        - Typical recommendation: 1-2 hours before bed
        """
        warning = None
        recommended_hour = 21  # Default: 9pm

        # Parse target bedtime
        try:
            if target_bedtime:
                bed_hour = int(target_bedtime.split(":")[0])
                recommended_hour = bed_hour - 2  # 2 hours before bed
        except:
            pass

        # Adjust for sleep onset issues
        if sleep_onset_latency and sleep_onset_latency > 30:
            # Takes long to fall asleep - take magnesium earlier
            recommended_hour -= 1
            warning = IntelligenceWarning(
                type="recommendation",
                supplement_id="magnesium_glycinate",
                title="Take Magnesium Earlier",
                message=f"Your sleep onset latency is {sleep_onset_latency} minutes. "
                        f"Try taking magnesium around {recommended_hour}:00 "
                        "(3 hours before bed) for better effect.",
                action=None
            )

        # Ensure reasonable bounds
        recommended_hour = max(17, min(22, recommended_hour))

        return recommended_hour, warning

    def get_magnesium_form_recommendation(
        self,
        primary_goal: str,  # "sleep", "cognitive", "muscle", "anxiety"
        current_hour: int
    ) -> Tuple[str, str]:
        """
        Recommend the best magnesium form based on goal and time.

        Forms:
        - Glycinate: Best for sleep and relaxation (PMID 34883514)
        - L-Threonate: Best for cognitive function (PMID 20152124)
        - Both: Can be combined for synergistic effects
        """
        if primary_goal == "cognitive" and current_hour < 17:
            return "magnesium_l_threonate", "L-Threonate crosses blood-brain barrier for cognitive support"
        elif primary_goal == "sleep" or current_hour >= 17:
            return "magnesium_glycinate", "Glycinate form optimal for sleep and relaxation"
        elif primary_goal == "anxiety":
            return "magnesium_glycinate", "Glycinate has calming effects via glycine"
        else:
            return "magnesium_glycinate", "Glycinate is well-absorbed general form"

    # ==========================================
    # 4. SMART STACKING WARNINGS
    # ==========================================

    STIMULANTS = {
        "caffeine": {"strength": 1.0, "duration_hrs": 6},
        "vitamin_b12": {"strength": 0.2, "duration_hrs": 8},  # Mild energizing
    }

    STIMULANT_DAILY_CEILING = 1.5  # Total stimulant load score

    def check_stimulant_stacking(
        self,
        supplements_today: List[Dict],  # [{supplement_id, dose, time_taken}]
        proposed_supplement: str,
        proposed_dose: float
    ) -> Tuple[bool, Optional[IntelligenceWarning]]:
        """
        Check if adding a stimulant would exceed safe daily load.

        Research: PMID 26677204
        - Multiple stimulants can compound effects
        - L-theanine can mitigate caffeine jitters (PMID 18681988)
        """
        if proposed_supplement not in self.STIMULANTS:
            return True, None  # Not a stimulant, allow

        # Calculate current stimulant load
        current_load = 0.0
        has_theanine = False

        for supp in supplements_today:
            supp_id = supp.get("supplement_id")
            if supp_id in self.STIMULANTS:
                # Weight by dose relative to standard (assuming 100mg caffeine standard)
                dose_factor = supp.get("dose", 100) / 100
                current_load += self.STIMULANTS[supp_id]["strength"] * dose_factor
            if supp_id == "l_theanine":
                has_theanine = True

        # Calculate proposed addition
        proposed_strength = self.STIMULANTS[proposed_supplement]["strength"]
        dose_factor = proposed_dose / 100 if proposed_supplement == "caffeine" else 1.0
        proposed_load = proposed_strength * dose_factor

        total_load = current_load + proposed_load

        # Check against ceiling
        if total_load > self.STIMULANT_DAILY_CEILING:
            return False, IntelligenceWarning(
                type="warning",
                supplement_id=proposed_supplement,
                title="Stimulant Limit Reached",
                message=f"Adding {proposed_supplement} would exceed your daily stimulant ceiling. "
                        "Consider skipping or reducing the dose.",
                action="skip"
            )

        # Recommend L-theanine pairing with caffeine
        if proposed_supplement == "caffeine" and not has_theanine and proposed_dose >= 100:
            return True, IntelligenceWarning(
                type="recommendation",
                supplement_id="l_theanine",
                title="Consider Adding L-Theanine",
                message="L-Theanine (200mg) pairs well with caffeine to reduce jitters "
                        "while preserving focus. Recommended 2:1 ratio (theanine:caffeine).",
                action="add_pairing"
            )

        return True, None

    # ==========================================
    # 5. RECOVERY-ADAPTIVE DOSING
    # ==========================================

    def get_recovery_adaptations(
        self,
        recovery_scores: List[float],  # Last 7 days
        strain_scores: List[float],  # Last 7 days
        hrv_trend: List[float] = None
    ) -> List[DoseModification]:
        """
        Adapt supplement doses based on recovery trends.

        Research: PMID 28900017 (omega-3 inflammation), PMID 28445426 (magnesium stress)
        """
        modifications = []

        if not recovery_scores:
            return modifications

        # Use average of available scores (min 1)
        avg_recovery = sum(recovery_scores[-3:]) / len(recovery_scores[-3:])
        avg_strain = sum(strain_scores[-3:]) / len(strain_scores[-3:]) if strain_scores else 50

        # Poor recovery for multiple days
        if avg_recovery < 50:
            # Increase anti-inflammatory support
            modifications.append(DoseModification(
                supplement_id="omega_3",
                multiplier=1.25,
                reason=f"Low recovery ({avg_recovery:.0f}) - increased anti-inflammatory support",
                source="recovery_adaptive"
            ))
            modifications.append(DoseModification(
                supplement_id="magnesium_glycinate",
                multiplier=1.25,
                reason=f"Low recovery ({avg_recovery:.0f}) - enhanced relaxation support",
                source="recovery_adaptive"
            ))

        # High strain load
        if avg_strain > 70:
            modifications.append(DoseModification(
                supplement_id="electrolytes",
                multiplier=1.5,
                reason=f"High strain ({avg_strain:.0f}) - increased electrolyte needs",
                source="recovery_adaptive"
            ))
            modifications.append(DoseModification(
                supplement_id="vitamin_c",
                multiplier=1.25,
                reason=f"High strain ({avg_strain:.0f}) - antioxidant support",
                source="recovery_adaptive"
            ))

        # Declining HRV trend suggests accumulated stress
        if hrv_trend and len(hrv_trend) >= 5:
            recent_hrv = hrv_trend[-5:]
            if recent_hrv[-1] < recent_hrv[0] * 0.85:  # 15% decline
                modifications.append(DoseModification(
                    supplement_id="ashwagandha",
                    multiplier=1.0,  # Ensure it's included, not increased
                    reason="Declining HRV trend - adaptogen support recommended",
                    source="recovery_adaptive"
                ))

        return modifications

    # ==========================================
    # 6. AGE-BASED INTELLIGENCE
    # ==========================================

    def get_age_adjustments(
        self,
        age: int,
        supplements: List[str]
    ) -> Tuple[List[DoseModification], List[IntelligenceWarning]]:
        """
        Apply age-appropriate dose adjustments and recommendations.

        Research:
        - CoQ10 declines with age (PMID 29587774)
        - Melatonin sensitivity increases with age (PMID 15649745)
        - Caffeine metabolism slows with age
        """
        modifications = []
        warnings = []

        if age >= 50:
            # Recommend CoQ10 for energy
            if "coq10" not in supplements:
                warnings.append(IntelligenceWarning(
                    type="recommendation",
                    supplement_id="coq10",
                    title="Consider CoQ10",
                    message="CoQ10 production declines after 50. "
                            "Consider adding 100-200mg daily for cellular energy support.",
                    action="add_supplement"
                ))

            # B12 absorption decreases
            if "vitamin_b12" in supplements:
                modifications.append(DoseModification(
                    supplement_id="vitamin_b12",
                    multiplier=1.25,
                    reason="B12 absorption decreases with age",
                    source="age_based"
                ))

        if age >= 65:
            # Cap melatonin at lower dose
            if "melatonin" in supplements:
                modifications.append(DoseModification(
                    supplement_id="melatonin",
                    multiplier=0.5,  # Cap at 50% of standard
                    reason="Increased melatonin sensitivity over 65",
                    source="age_based"
                ))
                warnings.append(IntelligenceWarning(
                    type="info",
                    supplement_id="melatonin",
                    title="Reduced Melatonin Dose",
                    message="Lower melatonin doses (0.3-1mg) are recommended for adults over 65.",
                    action=None
                ))

            # Reduce caffeine ceiling
            if "caffeine" in supplements:
                modifications.append(DoseModification(
                    supplement_id="caffeine",
                    multiplier=0.75,
                    reason="Slower caffeine metabolism over 65",
                    source="age_based"
                ))

        # Young athletes (under 30) - allow higher creatine for loading
        if age < 30:
            if "creatine" in supplements:
                # No modification needed - standard dose is fine
                # But could add note about loading protocol being safe
                pass

        return modifications, warnings

    # ==========================================
    # 7. LIFESTYLE-BASED INTELLIGENCE
    # ==========================================

    def get_diet_adjustments(
        self,
        diet_type: str  # omnivore, vegetarian, vegan
    ) -> List[DoseModification]:
        """
        Adjust supplements based on dietary restrictions.

        Research:
        - B12: Vegans/vegetarians at high risk of deficiency (PMID: 26502280)
        - Omega-3: Vegans don't get EPA/DHA from diet (PMID: 24679552)
        - Iron: Vegetarians may need more (plant iron less bioavailable)
        """
        modifications = []

        if diet_type == "vegan":
            modifications.append(DoseModification(
                supplement_id="vitamin_b12",
                multiplier=1.5,
                reason="Vegans require B12 supplementation (not available from plant sources)",
                source="diet_based"
            ))
            modifications.append(DoseModification(
                supplement_id="omega_3",
                multiplier=1.5,
                reason="Vegans don't get EPA/DHA from diet - algae-based omega-3 recommended",
                source="diet_based"
            ))

        elif diet_type == "vegetarian":
            modifications.append(DoseModification(
                supplement_id="vitamin_b12",
                multiplier=1.25,
                reason="Vegetarians often have lower B12 levels",
                source="diet_based"
            ))

        return modifications

    def get_activity_adjustments(
        self,
        activity_level: str  # sedentary, light, moderate, active, athlete
    ) -> List[DoseModification]:
        """
        Adjust supplements based on activity level.

        Research:
        - Athletes need more electrolytes (PMID: 17277604)
        - Higher activity = more oxidative stress = more antioxidants
        - Creatine benefits scale with training intensity
        """
        modifications = []

        if activity_level == "athlete":
            modifications.extend([
                DoseModification(
                    supplement_id="electrolytes",
                    multiplier=1.5,
                    reason="Athletes have higher electrolyte needs from sweating",
                    source="activity_based"
                ),
                DoseModification(
                    supplement_id="creatine",
                    multiplier=1.0,  # Standard dose, but prioritize
                    reason="Creatine highly beneficial for athletic performance",
                    source="activity_based"
                ),
                DoseModification(
                    supplement_id="vitamin_c",
                    multiplier=1.25,
                    reason="High training load increases oxidative stress",
                    source="activity_based"
                ),
                DoseModification(
                    supplement_id="magnesium_glycinate",
                    multiplier=1.25,
                    reason="Athletes lose magnesium through sweat",
                    source="activity_based"
                ),
            ])

        elif activity_level == "active":
            modifications.extend([
                DoseModification(
                    supplement_id="electrolytes",
                    multiplier=1.25,
                    reason="Active individuals benefit from electrolyte support",
                    source="activity_based"
                ),
                DoseModification(
                    supplement_id="creatine",
                    multiplier=1.0,
                    reason="Creatine supports active lifestyle",
                    source="activity_based"
                ),
            ])

        elif activity_level == "sedentary":
            # Sedentary individuals may benefit from CoQ10 for energy
            modifications.append(DoseModification(
                supplement_id="coq10",
                multiplier=1.0,
                reason="CoQ10 supports cellular energy for sedentary lifestyles",
                source="activity_based"
            ))

        return modifications

    def get_work_environment_adjustments(
        self,
        work_environment: str,  # office, outdoor, shift, remote
        region: str = None
    ) -> Tuple[List[DoseModification], List[IntelligenceWarning]]:
        """
        Adjust supplements based on work environment.

        Research:
        - Office workers get less vitamin D (PMID: 32690727)
        - Shift workers have disrupted circadian rhythms (PMID: 28648359)
        - Outdoor workers get more sun but need more antioxidants
        """
        modifications = []
        warnings = []

        if work_environment == "office" or work_environment == "remote":
            # Indoor workers need more vitamin D
            modifications.append(DoseModification(
                supplement_id="vitamin_d3",
                multiplier=1.25,
                reason="Indoor work limits sun exposure",
                source="work_environment"
            ))

        elif work_environment == "outdoor":
            # Outdoor workers get sun but need antioxidant protection
            modifications.append(DoseModification(
                supplement_id="vitamin_d3",
                multiplier=0.75,
                reason="Outdoor work provides natural vitamin D synthesis",
                source="work_environment"
            ))
            modifications.append(DoseModification(
                supplement_id="vitamin_c",
                multiplier=1.25,
                reason="UV exposure increases need for antioxidant protection",
                source="work_environment"
            ))

        elif work_environment == "shift":
            # Shift workers have unique circadian challenges
            warnings.append(IntelligenceWarning(
                type="recommendation",
                supplement_id="melatonin",
                title="Shift Worker Sleep Support",
                message="As a shift worker, strategic melatonin use can help reset your circadian rhythm. "
                        "Take 0.5-1mg before your desired sleep time.",
                action=None
            ))
            modifications.append(DoseModification(
                supplement_id="vitamin_d3",
                multiplier=1.5,
                reason="Shift workers often miss peak sun hours",
                source="work_environment"
            ))
            modifications.append(DoseModification(
                supplement_id="magnesium_glycinate",
                multiplier=1.25,
                reason="Magnesium supports sleep quality for irregular schedules",
                source="work_environment"
            ))

        return modifications, warnings

    def get_chronotype_adjustments(
        self,
        chronotype: str,  # early_bird, night_owl, neutral
        bedtime: str = None,
        wake_time: str = None,
        current_hour: int = None
    ) -> Tuple[List[DoseModification], Optional[IntelligenceWarning]]:
        """
        Adjust recommendations based on chronotype and sleep schedule.

        Research:
        - Night owls have different optimal caffeine timing
        - Chronotype affects melatonin secretion patterns
        """
        modifications = []
        warning = None

        if current_hour is None:
            current_hour = datetime.now().hour

        # Night owls can have caffeine slightly later
        if chronotype == "night_owl":
            # Shift caffeine cutoff from 5pm to 6pm for night owls
            if current_hour >= 17 and current_hour < 18:
                warning = IntelligenceWarning(
                    type="info",
                    supplement_id="caffeine",
                    title="Night Owl Caffeine Window",
                    message="As a night owl, you may tolerate caffeine slightly later. "
                            "Monitor your sleep quality if taking caffeine after 5pm.",
                    action=None
                )

        elif chronotype == "early_bird":
            # Early birds should cut caffeine earlier
            if current_hour >= 14:
                warning = IntelligenceWarning(
                    type="recommendation",
                    supplement_id="caffeine",
                    title="Early Bird Caffeine Cutoff",
                    message="As an early bird, consider avoiding caffeine after 2pm "
                            "to protect your earlier sleep schedule.",
                    action=None
                )

        return modifications, warning

    # ==========================================
    # MAIN INTELLIGENCE AGGREGATOR
    # ==========================================

    def get_all_intelligence(
        self,
        user_profile: Dict,
        health_data: Dict = None,
        usage_history: Dict = None,
        current_hour: int = None,
        latitude: float = None
    ) -> Dict:
        """
        Run all intelligence checks and return aggregated results.

        This returns a dictionary keyed by supplement/check type for easy lookup.

        Args:
            user_profile: {age, sex, weight_kg, region, activity_level, work_environment,
                          diet_type, bedtime, wake_time, chronotype}
            health_data: {sleep_score, recovery_score, strain_score, hrv_score}
            usage_history: {supplement_id: {days_used_last_14, last_taken, ...}}
            current_hour: Current hour (0-23)
            latitude: User's latitude for seasonal adjustments

        Returns:
            Dict with all intelligence recommendations and modifications
        """
        if current_hour is None:
            current_hour = datetime.now().hour
        if health_data is None:
            health_data = {}
        if usage_history is None:
            usage_history = {}

        result = {}
        age = user_profile.get("age", 30)
        diet_type = user_profile.get("diet_type")
        activity_level = user_profile.get("activity_level")
        work_environment = user_profile.get("work_environment")
        chronotype = user_profile.get("chronotype")
        bedtime = user_profile.get("bedtime")
        wake_time = user_profile.get("wake_time")

        # 1. Vitamin D seasonality
        vit_d_mod = self.get_vitamin_d_adjustment(latitude=latitude)
        result["vitamin_d"] = {
            "multiplier": vit_d_mod.multiplier,
            "reason": vit_d_mod.reason,
            "recommendation": vit_d_mod.reason if vit_d_mod.multiplier != 1.0 else None
        }

        # 2. Melatonin tolerance
        melatonin_usage = usage_history.get("melatonin", {})
        melatonin_days = melatonin_usage.get("days_used_last_14", 0) if isinstance(melatonin_usage, dict) else 0
        sleep_trend = health_data.get("sleep_score_history", [])
        mel_mod, mel_warn = self.check_melatonin_tolerance(
            melatonin_days,
            0.5,  # Standard dose
            sleep_trend
        )
        result["melatonin"] = {
            "tolerance_detected": melatonin_days >= 14,
            "should_skip": mel_mod.multiplier == 0,
            "consecutive_days": melatonin_days,
            "multiplier": mel_mod.multiplier,
            "recommendation": mel_warn.message if mel_warn else None
        }

        # 3. Magnesium timing
        sleep_latency = health_data.get("sleep_onset_latency")
        recommended_hour, mag_warn = self.get_magnesium_timing(
            sleep_onset_latency=sleep_latency,
            target_bedtime=bedtime
        )
        is_optimal_time = (current_hour >= recommended_hour - 1 and current_hour <= recommended_hour + 1)
        result["magnesium_timing"] = {
            "recommended_hour": recommended_hour,
            "is_optimal_time": is_optimal_time,
            "recommendation": f"Optimal time: around {recommended_hour}:00" if not is_optimal_time else None
        }

        # 4. Magnesium form recommendation
        primary_goal = "sleep" if current_hour >= 18 else "cognitive"
        form, form_reason = self.get_magnesium_form_recommendation(primary_goal, current_hour)
        result["magnesium_form"] = {
            "recommended_form": form,
            "recommendation": form_reason
        }

        # 5. Stimulant stacking - analyze already dispensed today
        result["stimulant_stacking"] = {
            "total_load": 0,
            "ceiling": self.STIMULANT_DAILY_CEILING,
            "warning": None
        }

        # 6. Recovery-adaptive dosing
        recovery_score = health_data.get("recovery_score")
        strain_score = health_data.get("strain_score")
        hrv_score = health_data.get("hrv_score")

        recovery_mods = []
        if recovery_score is not None:
            recovery_scores = [recovery_score]
            strain_scores = [strain_score] if strain_score else []
            hrv_trend = [hrv_score] if hrv_score else []

            raw_mods = self.get_recovery_adaptations(recovery_scores, strain_scores, hrv_trend)
            for mod in raw_mods:
                recovery_mods.append({
                    "supplement_id": mod.supplement_id,
                    "multiplier": mod.multiplier,
                    "reason": mod.reason
                })

        result["recovery_adaptations"] = {
            "recovery_score": recovery_score,
            "strain_score": strain_score,
            "modifications": recovery_mods
        }

        # 7. Age-based adjustments
        all_supplements = ["vitamin_b12", "melatonin", "caffeine", "coq10"]
        age_mods_raw, age_warns = self.get_age_adjustments(age, all_supplements)
        age_mods = []
        for mod in age_mods_raw:
            age_mods.append({
                "supplement_id": mod.supplement_id,
                "multiplier": mod.multiplier,
                "reason": mod.reason
            })

        result["age_adjustments"] = {
            "age": age,
            "modifications": age_mods,
            "recommendations": [w.message for w in age_warns]
        }

        # 8. Diet-based adjustments
        diet_mods = []
        if diet_type:
            raw_diet_mods = self.get_diet_adjustments(diet_type)
            for mod in raw_diet_mods:
                diet_mods.append({
                    "supplement_id": mod.supplement_id,
                    "multiplier": mod.multiplier,
                    "reason": mod.reason
                })

        result["diet_adjustments"] = {
            "diet_type": diet_type,
            "modifications": diet_mods
        }

        # 9. Activity-based adjustments
        activity_mods = []
        if activity_level:
            raw_activity_mods = self.get_activity_adjustments(activity_level)
            for mod in raw_activity_mods:
                activity_mods.append({
                    "supplement_id": mod.supplement_id,
                    "multiplier": mod.multiplier,
                    "reason": mod.reason
                })

        result["activity_adjustments"] = {
            "activity_level": activity_level,
            "modifications": activity_mods
        }

        # 10. Work environment adjustments
        work_mods = []
        work_recommendations = []
        if work_environment:
            raw_work_mods, work_warns = self.get_work_environment_adjustments(work_environment)
            for mod in raw_work_mods:
                work_mods.append({
                    "supplement_id": mod.supplement_id,
                    "multiplier": mod.multiplier,
                    "reason": mod.reason
                })
            work_recommendations = [w.message for w in work_warns]

        result["work_environment_adjustments"] = {
            "work_environment": work_environment,
            "modifications": work_mods,
            "recommendations": work_recommendations
        }

        # 11. Chronotype adjustments
        chronotype_mods = []
        chronotype_recommendation = None
        if chronotype:
            raw_chrono_mods, chrono_warn = self.get_chronotype_adjustments(
                chronotype, bedtime, wake_time, current_hour
            )
            for mod in raw_chrono_mods:
                chronotype_mods.append({
                    "supplement_id": mod.supplement_id,
                    "multiplier": mod.multiplier,
                    "reason": mod.reason
                })
            if chrono_warn:
                chronotype_recommendation = chrono_warn.message

        result["chronotype_adjustments"] = {
            "chronotype": chronotype,
            "modifications": chronotype_mods,
            "recommendation": chronotype_recommendation
        }

        return result


# Singleton instance
dosing_intelligence = DosingIntelligence()
