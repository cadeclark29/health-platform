"""
Supplement Interactions Database

Sources:
- PubMed research articles
- NIH Office of Dietary Supplements
- Examine.com interaction database
- Clinical pharmacology references
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class Interaction:
    """Represents an interaction between two supplements."""
    supplement_a: str
    supplement_b: str
    severity: str  # "minor", "moderate", "major"
    interaction_type: str  # "absorption", "competition", "synergy", "contraindication"
    description: str
    recommendation: str
    pubmed_ids: List[str] = None  # References


@dataclass
class CycleProtocol:
    """Represents cycling requirements for a supplement."""
    supplement_id: str
    on_weeks: int
    off_weeks: int
    max_continuous_days: int
    reason: str
    pubmed_ids: List[str] = None


@dataclass
class DoseAdjustment:
    """Dose adjustments based on user characteristics."""
    supplement_id: str
    factor: str  # "weight", "age", "sex"
    adjustment_type: str  # "per_kg", "multiplier", "max_cap"
    value: float
    condition: Optional[str] = None  # e.g., "age > 65", "sex == female"
    reason: str = ""


class InteractionChecker:
    """Check for supplement interactions and safety concerns."""

    def __init__(self):
        self._load_interactions()
        self._load_cycle_protocols()
        self._load_dose_adjustments()

    def _load_interactions(self):
        """Load supplement interaction database."""
        self.interactions: List[Interaction] = [
            # ZINC - COPPER COMPETITION
            Interaction(
                supplement_a="zinc",
                supplement_b="copper",
                severity="moderate",
                interaction_type="competition",
                description="High-dose zinc (>40mg/day) can inhibit copper absorption, leading to copper deficiency over time.",
                recommendation="If taking zinc >25mg daily for extended periods, consider copper supplementation (2mg) or take them 2+ hours apart.",
                pubmed_ids=["18611146", "21934638"]
            ),

            # CALCIUM - IRON COMPETITION
            Interaction(
                supplement_a="calcium",
                supplement_b="iron",
                severity="moderate",
                interaction_type="absorption",
                description="Calcium significantly reduces iron absorption when taken together.",
                recommendation="Take calcium and iron supplements at least 2 hours apart.",
                pubmed_ids=["21462112", "25466939"]
            ),

            # ZINC - IRON COMPETITION
            Interaction(
                supplement_a="zinc",
                supplement_b="iron",
                severity="minor",
                interaction_type="absorption",
                description="High doses of zinc and iron compete for absorption.",
                recommendation="Take at least 2 hours apart for optimal absorption.",
                pubmed_ids=["25466939"]
            ),

            # VITAMIN D3 - VITAMIN K2 SYNERGY
            Interaction(
                supplement_a="vitamin_d3",
                supplement_b="vitamin_k2",
                severity="minor",
                interaction_type="synergy",
                description="Vitamin K2 helps direct calcium mobilized by Vitamin D3 to bones rather than arteries.",
                recommendation="Consider taking D3 and K2 together for optimal calcium metabolism.",
                pubmed_ids=["28471760", "25636220"]
            ),

            # MAGNESIUM - VITAMIN D SYNERGY
            Interaction(
                supplement_a="magnesium_glycinate",
                supplement_b="vitamin_d3",
                severity="minor",
                interaction_type="synergy",
                description="Magnesium is required for vitamin D metabolism. Deficiency can impair D3 effectiveness.",
                recommendation="Ensure adequate magnesium intake when supplementing vitamin D.",
                pubmed_ids=["29480918"]
            ),
            Interaction(
                supplement_a="magnesium_l_threonate",
                supplement_b="vitamin_d3",
                severity="minor",
                interaction_type="synergy",
                description="Magnesium is required for vitamin D metabolism.",
                recommendation="Ensure adequate magnesium intake when supplementing vitamin D.",
                pubmed_ids=["29480918"]
            ),

            # CAFFEINE - L-THEANINE SYNERGY
            Interaction(
                supplement_a="caffeine",
                supplement_b="l_theanine",
                severity="minor",
                interaction_type="synergy",
                description="L-theanine smooths caffeine's stimulant effects, reducing jitters while preserving alertness.",
                recommendation="Combine at 1:2 ratio (caffeine:theanine) for optimal focus without anxiety.",
                pubmed_ids=["18681988", "21040626"]
            ),

            # MELATONIN - CAFFEINE ANTAGONISM
            Interaction(
                supplement_a="melatonin",
                supplement_b="caffeine",
                severity="moderate",
                interaction_type="contraindication",
                description="Caffeine can reduce melatonin production and counteract its sleep-promoting effects.",
                recommendation="Avoid caffeine within 6-8 hours of taking melatonin. Do not dispense together.",
                pubmed_ids=["33152871"]
            ),

            # OMEGA-3 - VITAMIN E
            Interaction(
                supplement_a="omega_3",
                supplement_b="vitamin_e",
                severity="minor",
                interaction_type="synergy",
                description="Vitamin E helps prevent oxidation of omega-3 fatty acids in the body.",
                recommendation="Consider combined supplementation for enhanced omega-3 stability.",
                pubmed_ids=["17045071"]
            ),

            # NAC - NITROGLYCERIN (medication warning)
            Interaction(
                supplement_a="nac",
                supplement_b="nitroglycerin_med",
                severity="major",
                interaction_type="contraindication",
                description="NAC can enhance nitroglycerin effects, causing severe hypotension.",
                recommendation="Do not combine. Requires medical supervision.",
                pubmed_ids=["2058276"]
            ),

            # ASHWAGANDHA - THYROID MEDICATION
            Interaction(
                supplement_a="ashwagandha",
                supplement_b="thyroid_med",
                severity="major",
                interaction_type="contraindication",
                description="Ashwagandha may increase thyroid hormone levels, requiring medication dose adjustment.",
                recommendation="Avoid in users with thyroid conditions or on thyroid medication without medical supervision.",
                pubmed_ids=["28829155", "31742775"]
            ),

            # GLYCINE - CLOZAPINE (medication warning)
            Interaction(
                supplement_a="glycine",
                supplement_b="clozapine_med",
                severity="major",
                interaction_type="contraindication",
                description="High-dose glycine may reduce clozapine effectiveness.",
                recommendation="Avoid combining without medical supervision.",
                pubmed_ids=["10448680"]
            ),

            # L-CITRULLINE - BLOOD PRESSURE MEDS
            Interaction(
                supplement_a="l_citrulline",
                supplement_b="bp_medication",
                severity="moderate",
                interaction_type="contraindication",
                description="L-citrulline can lower blood pressure, potentially enhancing BP medication effects.",
                recommendation="Monitor blood pressure closely. May require medication adjustment.",
                pubmed_ids=["20386132"]
            ),

            # COENZYME Q10 - BLOOD THINNERS
            Interaction(
                supplement_a="coq10",
                supplement_b="warfarin_med",
                severity="major",
                interaction_type="contraindication",
                description="CoQ10 may reduce warfarin effectiveness by competing for vitamin K pathways.",
                recommendation="Avoid in users on warfarin. Monitor INR if combining.",
                pubmed_ids=["16855178", "7751941"]
            ),

            # VITAMIN K2 - BLOOD THINNERS
            Interaction(
                supplement_a="vitamin_k2",
                supplement_b="warfarin_med",
                severity="major",
                interaction_type="contraindication",
                description="Vitamin K directly antagonizes warfarin's mechanism of action.",
                recommendation="Do not combine. Avoid in users on anticoagulants.",
                pubmed_ids=["23530987"]
            ),

            # MAGNESIUM FORMS - REDUNDANCY
            Interaction(
                supplement_a="magnesium_glycinate",
                supplement_b="magnesium_l_threonate",
                severity="minor",
                interaction_type="competition",
                description="Both are magnesium forms. Combined doses should not exceed daily magnesium limits.",
                recommendation="Total elemental magnesium from all sources should stay under 400mg/day.",
                pubmed_ids=[]
            ),

            # NAC - PROTEIN ABSORPTION
            Interaction(
                supplement_a="nac",
                supplement_b="protein_supplement",
                severity="minor",
                interaction_type="absorption",
                description="NAC competes with amino acids for absorption.",
                recommendation="Take NAC away from meals and protein supplements (30+ min apart).",
                pubmed_ids=[]
            ),

            # CREATINE - CAFFEINE (contested)
            Interaction(
                supplement_a="creatine",
                supplement_b="caffeine",
                severity="minor",
                interaction_type="competition",
                description="Some evidence suggests caffeine may reduce creatine's ergogenic benefits.",
                recommendation="Consider separating doses by a few hours if optimizing athletic performance.",
                pubmed_ids=["8929583", "28455468"]
            ),
        ]

    def _load_cycle_protocols(self):
        """Load cycling requirements for supplements."""
        self.cycle_protocols: Dict[str, CycleProtocol] = {
            "ashwagandha": CycleProtocol(
                supplement_id="ashwagandha",
                on_weeks=8,
                off_weeks=2,
                max_continuous_days=60,
                reason="Adaptogen effects may diminish with continuous use. Cycling maintains efficacy and allows receptor resensitization.",
                pubmed_ids=["28471731"]
            ),
            "melatonin": CycleProtocol(
                supplement_id="melatonin",
                on_weeks=4,
                off_weeks=1,
                max_continuous_days=30,
                reason="Extended use may suppress natural melatonin production. Short-term use recommended.",
                pubmed_ids=["17645585"]
            ),
            "caffeine": CycleProtocol(
                supplement_id="caffeine",
                on_weeks=12,
                off_weeks=1,
                max_continuous_days=90,
                reason="Tolerance develops over time. Periodic breaks help maintain sensitivity.",
                pubmed_ids=["20164566"]
            ),
            "nac": CycleProtocol(
                supplement_id="nac",
                on_weeks=8,
                off_weeks=4,
                max_continuous_days=60,
                reason="Long-term high-dose NAC may affect glutathione homeostasis. Cycling recommended.",
                pubmed_ids=[]
            ),
            "lions_mane": CycleProtocol(
                supplement_id="lions_mane",
                on_weeks=12,
                off_weeks=4,
                max_continuous_days=90,
                reason="Cycling may help maintain neurotrophin sensitivity.",
                pubmed_ids=[]
            ),
        }

    def _load_dose_adjustments(self):
        """Load dose adjustment rules."""
        self.dose_adjustments: Dict[str, List[DoseAdjustment]] = {
            # Creatine: Research shows 3-5g/day is optimal regardless of weight
            # No weight-based adjustment needed - flat 5g is the standard
            # PMID: 28615996, 32359762
            "caffeine": [
                DoseAdjustment(
                    supplement_id="caffeine",
                    factor="weight",
                    adjustment_type="per_kg",
                    value=3.0,  # 3mg per kg
                    condition=None,
                    reason="Caffeine effects scale with body weight. ~200mg for 70kg person."
                ),
                DoseAdjustment(
                    supplement_id="caffeine",
                    factor="age",
                    adjustment_type="multiplier",
                    value=0.75,  # 25% reduction
                    condition="age > 65",
                    reason="Caffeine metabolism slows with age. Reduce dose for older adults."
                )
            ],
            "melatonin": [
                DoseAdjustment(
                    supplement_id="melatonin",
                    factor="age",
                    adjustment_type="max_cap",
                    value=1.0,  # Cap at 1mg for elderly
                    condition="age > 65",
                    reason="Older adults may be more sensitive to melatonin. Start with lower doses."
                )
            ],
            "magnesium_glycinate": [
                DoseAdjustment(
                    supplement_id="magnesium_glycinate",
                    factor="sex",
                    adjustment_type="multiplier",
                    value=0.85,
                    condition="sex == female",
                    reason="RDA for magnesium is slightly lower for women (310-320mg vs 400-420mg for men)."
                )
            ],
            "zinc": [
                DoseAdjustment(
                    supplement_id="zinc",
                    factor="sex",
                    adjustment_type="multiplier",
                    value=0.73,
                    condition="sex == female",
                    reason="RDA for zinc is lower for women (8mg vs 11mg for men)."
                )
            ],
            "vitamin_d3": [
                DoseAdjustment(
                    supplement_id="vitamin_d3",
                    factor="weight",
                    adjustment_type="per_kg",
                    value=40,  # 40 IU per kg
                    condition=None,
                    reason="Vitamin D requirements scale with body weight. Higher doses for overweight individuals."
                )
            ],
            "omega_3": [
                DoseAdjustment(
                    supplement_id="omega_3",
                    factor="weight",
                    adjustment_type="per_kg",
                    value=20,  # 20mg per kg
                    condition=None,
                    reason="Omega-3 requirements may scale with body size for anti-inflammatory effects."
                )
            ],
        }

    def check_interactions(
        self,
        supplements: List[str],
        user_medications: Optional[List[str]] = None
    ) -> List[Interaction]:
        """
        Check for interactions between a list of supplements.

        Args:
            supplements: List of supplement IDs being considered
            user_medications: Optional list of medications user takes

        Returns:
            List of Interaction objects for any found interactions
        """
        found_interactions = []
        medications = user_medications or []

        # Map medication keywords to interaction IDs
        med_mapping = {
            "thyroid": "thyroid_med",
            "levothyroxine": "thyroid_med",
            "synthroid": "thyroid_med",
            "warfarin": "warfarin_med",
            "coumadin": "warfarin_med",
            "blood_thinner": "warfarin_med",
            "anticoagulant": "warfarin_med",
            "nitroglycerin": "nitroglycerin_med",
            "blood_pressure": "bp_medication",
            "lisinopril": "bp_medication",
            "amlodipine": "bp_medication",
            "clozapine": "clozapine_med",
        }

        # Convert medication names to interaction IDs
        med_ids = set()
        for med in medications:
            med_lower = med.lower()
            for keyword, med_id in med_mapping.items():
                if keyword in med_lower:
                    med_ids.add(med_id)

        # Check all combinations
        all_items = list(supplements) + list(med_ids)

        for i, item_a in enumerate(all_items):
            for item_b in all_items[i + 1:]:
                for interaction in self.interactions:
                    if (
                        (interaction.supplement_a == item_a and interaction.supplement_b == item_b) or
                        (interaction.supplement_a == item_b and interaction.supplement_b == item_a)
                    ):
                        found_interactions.append(interaction)

        return found_interactions

    def check_timing_conflicts(
        self,
        supplements: List[str]
    ) -> List[Dict]:
        """
        Check for supplements that shouldn't be taken at the same time.

        Returns list of conflicts with recommended timing separation.
        """
        conflicts = []
        timing_conflicts = {
            ("melatonin", "caffeine"): {
                "separation_hours": 8,
                "reason": "Caffeine blocks adenosine and suppresses melatonin production"
            },
            ("zinc", "iron"): {
                "separation_hours": 2,
                "reason": "Compete for absorption"
            },
            ("calcium", "iron"): {
                "separation_hours": 2,
                "reason": "Calcium significantly reduces iron absorption"
            },
            ("nac", "protein_supplement"): {
                "separation_hours": 0.5,
                "reason": "NAC competes with amino acids for absorption"
            },
        }

        for i, supp_a in enumerate(supplements):
            for supp_b in supplements[i + 1:]:
                pair = tuple(sorted([supp_a, supp_b]))
                if pair in timing_conflicts:
                    conflicts.append({
                        "supplements": list(pair),
                        **timing_conflicts[pair]
                    })

        return conflicts

    def get_cycle_protocol(self, supplement_id: str) -> Optional[CycleProtocol]:
        """Get cycling protocol for a supplement if one exists."""
        return self.cycle_protocols.get(supplement_id)

    def check_cycle_status(
        self,
        supplement_id: str,
        consecutive_days: int
    ) -> Dict:
        """
        Check if a supplement needs cycling based on usage history.

        Args:
            supplement_id: The supplement to check
            consecutive_days: Days the user has been taking it consecutively

        Returns:
            Dict with status and recommendation
        """
        protocol = self.cycle_protocols.get(supplement_id)

        if not protocol:
            return {
                "needs_cycling": False,
                "status": "no_protocol",
                "message": "No cycling protocol defined for this supplement."
            }

        if consecutive_days >= protocol.max_continuous_days:
            return {
                "needs_cycling": True,
                "status": "cycle_now",
                "message": f"You've taken {protocol.supplement_id} for {consecutive_days} days. Consider taking a {protocol.off_weeks}-week break.",
                "off_weeks": protocol.off_weeks,
                "reason": protocol.reason
            }

        warning_threshold = protocol.max_continuous_days - 7  # Warn 1 week before
        if consecutive_days >= warning_threshold:
            days_remaining = protocol.max_continuous_days - consecutive_days
            return {
                "needs_cycling": False,
                "status": "approaching",
                "message": f"Cycle break recommended in {days_remaining} days for {protocol.supplement_id}.",
                "days_until_cycle": days_remaining,
                "reason": protocol.reason
            }

        return {
            "needs_cycling": False,
            "status": "ok",
            "message": f"Continue taking {protocol.supplement_id}.",
            "days_remaining": protocol.max_continuous_days - consecutive_days
        }

    def get_adjusted_dose(
        self,
        supplement_id: str,
        standard_dose: float,
        user_profile: Dict
    ) -> Dict:
        """
        Calculate personalized dose based on user characteristics.

        Args:
            supplement_id: The supplement to dose
            standard_dose: The default recommended dose
            user_profile: Dict with age, sex, weight_kg, height_cm

        Returns:
            Dict with adjusted dose and reasoning
        """
        adjustments = self.dose_adjustments.get(supplement_id, [])

        if not adjustments:
            return {
                "adjusted_dose": standard_dose,
                "adjustments_applied": [],
                "reasoning": "Standard dose applies."
            }

        final_dose = standard_dose
        applied = []

        for adj in adjustments:
            # Check if condition is met
            if adj.condition:
                # Parse simple conditions
                if adj.condition.startswith("age >"):
                    threshold = int(adj.condition.split(">")[1].strip())
                    age = user_profile.get("age")
                    if not age or age <= threshold:
                        continue
                elif adj.condition.startswith("sex =="):
                    target_sex = adj.condition.split("==")[1].strip()
                    if user_profile.get("sex") != target_sex:
                        continue

            # Apply adjustment
            if adj.adjustment_type == "per_kg":
                weight = user_profile.get("weight_kg")
                if weight:
                    calculated = adj.value * weight
                    # For per_kg, use calculated value (may override standard)
                    final_dose = calculated
                    applied.append({
                        "factor": adj.factor,
                        "type": adj.adjustment_type,
                        "result": calculated,
                        "reason": adj.reason
                    })

            elif adj.adjustment_type == "multiplier":
                final_dose *= adj.value
                applied.append({
                    "factor": adj.factor,
                    "type": adj.adjustment_type,
                    "multiplier": adj.value,
                    "reason": adj.reason
                })

            elif adj.adjustment_type == "max_cap":
                if final_dose > adj.value:
                    final_dose = adj.value
                    applied.append({
                        "factor": adj.factor,
                        "type": adj.adjustment_type,
                        "capped_to": adj.value,
                        "reason": adj.reason
                    })

        return {
            "adjusted_dose": round(final_dose, 1),
            "standard_dose": standard_dose,
            "adjustments_applied": applied,
            "reasoning": f"Dose adjusted from {standard_dose} to {round(final_dose, 1)} based on {len(applied)} factor(s)." if applied else "Standard dose applies."
        }

    def get_all_warnings(
        self,
        supplements: List[str],
        user_profile: Optional[Dict] = None,
        user_medications: Optional[List[str]] = None,
        usage_history: Optional[Dict[str, int]] = None
    ) -> Dict:
        """
        Comprehensive safety check returning all warnings.

        Args:
            supplements: List of supplement IDs being recommended
            user_profile: User's profile data
            user_medications: List of medications
            usage_history: Dict of supplement_id -> consecutive days taken

        Returns:
            Dict with all applicable warnings
        """
        result = {
            "interactions": [],
            "timing_conflicts": [],
            "cycle_warnings": [],
            "dose_adjustments": {},
            "contraindication_warnings": []
        }

        # Check interactions
        interactions = self.check_interactions(supplements, user_medications)
        for interaction in interactions:
            result["interactions"].append({
                "supplements": [interaction.supplement_a, interaction.supplement_b],
                "severity": interaction.severity,
                "type": interaction.interaction_type,
                "description": interaction.description,
                "recommendation": interaction.recommendation
            })

        # Check timing conflicts
        result["timing_conflicts"] = self.check_timing_conflicts(supplements)

        # Check cycling requirements
        if usage_history:
            for supp_id, days in usage_history.items():
                if supp_id in supplements:
                    status = self.check_cycle_status(supp_id, days)
                    if status["status"] in ["cycle_now", "approaching"]:
                        result["cycle_warnings"].append({
                            "supplement_id": supp_id,
                            **status
                        })

        # Get dose adjustments
        if user_profile:
            for supp_id in supplements:
                from app.engine.rules import RulesEngine
                rules = RulesEngine()
                config = rules.supplements.get(supp_id)
                if config:
                    adjustment = self.get_adjusted_dose(
                        supp_id,
                        config.standard_dose,
                        user_profile
                    )
                    if adjustment["adjustments_applied"]:
                        result["dose_adjustments"][supp_id] = adjustment

        return result


# Singleton instance
interaction_checker = InteractionChecker()
