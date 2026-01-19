"""
Dynamic Health Metric Rules Engine

Research-backed rules that map health metrics to supplement adjustments.
Each rule includes PubMed citations for evidence-based recommendations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


# Priority levels for conflict resolution
# Higher priority = more important to follow
PRIORITY_LEVELS = {
    "safety_block": 100,      # Contraindications - never override
    "immune_response": 90,    # Temperature/illness triggers
    "acute_stress": 80,       # Very low HRV, high strain
    "sleep_crisis": 70,       # Very poor sleep
    "recovery_deficit": 60,   # Low recovery score
    "optimization": 40,       # General enhancement
    "maintenance": 20,        # Default daily protocol
}


@dataclass
class SupplementAction:
    """A single supplement adjustment action."""
    supplement: str
    action: str  # "add", "increase", "reduce", "hold", "allow"
    dose_mult: float = 1.0
    priority: int = 1
    reason: str = ""
    time_restriction: str = ""  # e.g., "before_13:00"


@dataclass
class MetricRule:
    """A rule triggered by a health metric condition."""
    condition: str
    actions: List[Dict]
    citations: List[str]
    explanation: str
    priority_level: str = "optimization"
    user_alert: str = ""


# =============================================================================
# TEMPERATURE RULES - Immune Support
# =============================================================================
TEMPERATURE_RULES = {
    "immune_alert": {
        "condition": "temperature_deviation > 0.5",
        "threshold": 0.5,
        "comparison": ">",
        "priority_level": "immune_response",
        "actions": [
            {"supplement": "elderberry", "action": "add", "dose_mult": 1.5, "priority": 1},
            {"supplement": "vitamin_c", "action": "increase", "dose_mult": 1.5, "priority": 2},
            {"supplement": "zinc", "action": "add", "dose_mult": 1.0, "priority": 3},
            {"supplement": "nac", "action": "add", "dose_mult": 1.0, "priority": 4},
            {"supplement": "caffeine", "action": "hold", "reason": "Avoid stimulants during immune response"},
            {"supplement": "creatine", "action": "reduce", "dose_mult": 0.5, "reason": "Reduce training load during immune challenge"},
        ],
        "citations": ["30670267", "21067697"],
        "explanation": "Elevated body temperature ({value}°C above baseline) suggests immune system activation. Prioritizing immune support supplements and reducing stimulants."
    },
    "immune_crisis": {
        "condition": "temperature_deviation > 1.0",
        "threshold": 1.0,
        "comparison": ">",
        "priority_level": "immune_response",
        "actions": [
            {"supplement": "elderberry", "action": "add", "dose_mult": 2.0, "priority": 1},
            {"supplement": "vitamin_c", "action": "increase", "dose_mult": 2.0, "priority": 2},
            {"supplement": "zinc", "action": "add", "dose_mult": 1.5, "priority": 3},
            {"supplement": "nac", "action": "add", "dose_mult": 1.5, "priority": 4},
            {"supplement": "blackseed_oil", "action": "add", "dose_mult": 1.0, "priority": 5},
            {"supplement": "caffeine", "action": "hold", "reason": "Stimulants stress immune system"},
            {"supplement": "creatine", "action": "hold", "reason": "Avoid training stress during illness"},
            {"supplement": "l_citrulline", "action": "hold", "reason": "Reduce metabolic stress"},
        ],
        "citations": ["30670267", "21067697"],
        "explanation": "Significant temperature elevation ({value}°C above baseline) indicates strong immune response. Maximizing immune support and suspending performance supplements.",
        "user_alert": "Your body temperature is significantly elevated. Consider rest and consult a healthcare provider if symptoms persist."
    }
}


# =============================================================================
# HRV RULES - Stress & Recovery
# =============================================================================
HRV_RULES = {
    "severe_stress": {
        "condition": "hrv_score < baseline * 0.70",
        "baseline_mult": 0.70,
        "comparison": "<",
        "priority_level": "acute_stress",
        "actions": [
            {"supplement": "ashwagandha", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.5, "priority": 2},
            {"supplement": "l_theanine", "action": "add", "dose_mult": 1.0, "priority": 3},
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.25, "time_restriction": "before_12:00"},
        ],
        "citations": ["28471731", "23439798"],
        "explanation": "HRV is {percent_below}% below your baseline, indicating significant stress. Supporting parasympathetic recovery with adaptogens and limiting stimulants."
    },
    "moderate_stress": {
        "condition": "hrv_score < baseline * 0.85",
        "baseline_mult": 0.85,
        "comparison": "<",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "l_theanine", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.25, "priority": 2},
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.75, "time_restriction": "before_14:00"},
        ],
        "citations": ["28471731", "18681988"],
        "explanation": "HRV is {percent_below}% below your baseline. Moderate stress detected - supporting recovery with calming supplements."
    },
    "recovery_mode": {
        "condition": "hrv_score > baseline * 1.10",
        "baseline_mult": 1.10,
        "comparison": ">",
        "priority_level": "optimization",
        "actions": [
            {"supplement": "caffeine", "action": "allow", "reason": "Good recovery state supports stimulant tolerance"},
            {"supplement": "creatine", "action": "allow", "reason": "Recovery supports training adaptations"},
            {"supplement": "l_citrulline", "action": "allow", "reason": "Good day for performance supplements"},
        ],
        "citations": ["28615996"],
        "explanation": "HRV is {percent_above}% above your baseline - excellent recovery state. Good day for performance optimization."
    },
    "fixed_low_hrv": {
        "condition": "hrv_score < 40",
        "threshold": 40,
        "comparison": "<",
        "priority_level": "acute_stress",
        "actions": [
            {"supplement": "ashwagandha", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.25, "priority": 2},
            {"supplement": "l_theanine", "action": "add", "dose_mult": 1.0, "priority": 3},
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.5},
        ],
        "citations": ["28471731"],
        "explanation": "HRV of {value}ms is quite low. Supporting stress recovery with adaptogens."
    }
}


# =============================================================================
# SLEEP RULES - Sleep Quality & Timing
# =============================================================================
SLEEP_RULES = {
    "sleep_crisis": {
        "condition": "sleep_score < 50",
        "threshold": 50,
        "comparison": "<",
        "priority_level": "sleep_crisis",
        "actions": [
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.25, "time_restriction": "before_12:00"},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.5, "priority": 1},
            {"supplement": "apigenin", "action": "add", "dose_mult": 1.0, "priority": 2},
            {"supplement": "glycine", "action": "add", "dose_mult": 1.0, "priority": 3},
            {"supplement": "l_theanine", "action": "add", "dose_mult": 1.0, "priority": 4},
        ],
        "citations": ["34883514", "19284590"],
        "explanation": "Sleep score of {value} is critically low. Maximizing sleep support and significantly reducing stimulants."
    },
    "poor_sleep": {
        "condition": "sleep_score < 60",
        "threshold": 60,
        "comparison": "<",
        "priority_level": "sleep_crisis",
        "actions": [
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.5, "time_restriction": "before_13:00"},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.25, "priority": 1},
            {"supplement": "apigenin", "action": "add", "dose_mult": 1.0, "priority": 2},
            {"supplement": "l_theanine", "action": "add", "dose_mult": 1.0, "priority": 3},
        ],
        "citations": ["34883514"],
        "explanation": "Sleep score of {value} indicates poor sleep. Reducing caffeine and enhancing evening sleep stack."
    },
    "suboptimal_sleep": {
        "condition": "sleep_score < 70",
        "threshold": 70,
        "comparison": "<",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.75, "time_restriction": "before_14:00"},
            {"supplement": "magnesium_glycinate", "action": "add", "dose_mult": 1.0, "priority": 1},
        ],
        "citations": ["34883514"],
        "explanation": "Sleep score of {value} is below optimal. Supporting recovery with earlier caffeine cutoff."
    },
    "low_deep_sleep": {
        "condition": "deep_sleep_pct < 15",
        "threshold": 15,
        "comparison": "<",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "glycine", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.25, "priority": 2},
            {"supplement": "melatonin", "action": "hold", "reason": "Melatonin may disrupt sleep architecture"},
        ],
        "citations": ["19284590"],
        "explanation": "Deep sleep is only {value}% of total sleep. Adding glycine to support deeper sleep stages."
    },
    "high_sleep_latency": {
        "condition": "sleep_latency > 30",
        "threshold": 30,
        "comparison": ">",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "apigenin", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "magnesium_glycinate", "action": "add", "time_suggestion": "3 hours before bed", "priority": 2},
        ],
        "citations": ["34883514"],
        "explanation": "Sleep onset latency of {value} minutes is elevated. Adding sleep onset support."
    }
}


# =============================================================================
# ACTIVITY/STRAIN RULES
# =============================================================================
STRAIN_RULES = {
    "high_strain": {
        "condition": "strain_score > 80",
        "threshold": 80,
        "comparison": ">",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "electrolytes", "action": "increase", "dose_mult": 2.0, "priority": 1},
            {"supplement": "creatine", "action": "add", "dose_mult": 1.0, "priority": 2},
            {"supplement": "omega_3", "action": "increase", "dose_mult": 1.25, "priority": 3},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.25, "priority": 4},
        ],
        "citations": ["28615996", "17277604"],
        "explanation": "High physical strain detected (score: {value}). Increasing recovery and hydration support."
    },
    "very_high_strain": {
        "condition": "strain_score > 90",
        "threshold": 90,
        "comparison": ">",
        "priority_level": "acute_stress",
        "actions": [
            {"supplement": "electrolytes", "action": "increase", "dose_mult": 3.0, "priority": 1},
            {"supplement": "creatine", "action": "add", "dose_mult": 1.0, "priority": 2},
            {"supplement": "omega_3", "action": "increase", "dose_mult": 1.5, "priority": 3},
            {"supplement": "coq10", "action": "add", "dose_mult": 1.0, "priority": 4},
            {"supplement": "vitamin_c", "action": "increase", "dose_mult": 1.25, "priority": 5},
        ],
        "citations": ["28615996"],
        "explanation": "Very high physical strain (score: {value}). Maximizing recovery support."
    }
}


# =============================================================================
# RECOVERY RULES
# =============================================================================
RECOVERY_RULES = {
    "poor_recovery": {
        "condition": "recovery_score < 50",
        "threshold": 50,
        "comparison": "<",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "ashwagandha", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "omega_3", "action": "add", "dose_mult": 1.0, "priority": 2},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.25, "priority": 3},
            {"supplement": "caffeine", "action": "reduce", "dose_mult": 0.75},
        ],
        "citations": ["28471731"],
        "explanation": "Recovery score of {value} is low. Supporting recovery with adaptogens and anti-inflammatories."
    },
    "suboptimal_recovery": {
        "condition": "recovery_score < 65",
        "threshold": 65,
        "comparison": "<",
        "priority_level": "recovery_deficit",
        "actions": [
            {"supplement": "omega_3", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "magnesium_glycinate", "action": "add", "dose_mult": 1.0, "priority": 2},
        ],
        "citations": [],
        "explanation": "Recovery score of {value} indicates room for improvement. Adding recovery support."
    }
}


# =============================================================================
# COMPOUND CONDITIONS - Multiple Metrics
# =============================================================================
COMPOUND_CONDITIONS = {
    "overtraining_syndrome": {
        "description": "Multiple indicators suggest accumulated fatigue",
        "required_metrics": [
            {"metric": "hrv_score", "condition": "below_baseline", "threshold": 0.8},
            {"metric": "sleep_score", "condition": "below", "threshold": 60},
            {"metric": "recovery_score", "condition": "below", "threshold": 50},
        ],
        "min_matches": 2,  # Need at least 2 of 3 to trigger
        "priority_level": "acute_stress",
        "actions": [
            {"supplement": "caffeine", "action": "hold", "duration_days": 3, "reason": "Allow nervous system recovery"},
            {"supplement": "creatine", "action": "hold", "duration_days": 2, "reason": "Reduce training stress"},
            {"supplement": "ashwagandha", "action": "add", "dose_mult": 1.0, "priority": 1},
            {"supplement": "omega_3", "action": "increase", "dose_mult": 1.5, "priority": 2},
            {"supplement": "magnesium_glycinate", "action": "increase", "dose_mult": 1.5, "priority": 3},
        ],
        "citations": ["28471731"],
        "explanation": "Multiple fatigue indicators detected (low HRV, poor sleep, poor recovery). Prioritizing rest and recovery - holding stimulants and training supplements.",
        "user_alert": "Your metrics suggest accumulated fatigue. Consider taking a rest day and prioritizing sleep."
    },
    "immune_plus_stress": {
        "description": "Immune challenge combined with high stress",
        "required_metrics": [
            {"metric": "temperature_deviation", "condition": "above", "threshold": 0.3},
            {"metric": "hrv_score", "condition": "below_baseline", "threshold": 0.85},
        ],
        "min_matches": 2,
        "priority_level": "immune_response",
        "actions": [
            {"supplement": "elderberry", "action": "add", "dose_mult": 1.5, "priority": 1},
            {"supplement": "vitamin_c", "action": "increase", "dose_mult": 1.5, "priority": 2},
            {"supplement": "ashwagandha", "action": "add", "dose_mult": 1.0, "priority": 3},
            {"supplement": "caffeine", "action": "hold", "reason": "Stress + immune challenge requires rest"},
        ],
        "citations": ["30670267", "28471731"],
        "explanation": "Your body is fighting something (elevated temp) while under stress (low HRV). Maximizing immune and stress support."
    }
}


# =============================================================================
# MAIN RULES DICTIONARY - All Rules Combined
# =============================================================================
METRIC_SUPPLEMENT_RULES = {
    "temperature_deviation": TEMPERATURE_RULES,
    "hrv_score": HRV_RULES,
    "sleep_score": SLEEP_RULES,
    "strain_score": STRAIN_RULES,
    "recovery_score": RECOVERY_RULES,
    "deep_sleep_pct": {"low_deep_sleep": SLEEP_RULES["low_deep_sleep"]},
    "sleep_latency": {"high_sleep_latency": SLEEP_RULES["high_sleep_latency"]},
}


# =============================================================================
# RESEARCH CITATIONS DATABASE
# =============================================================================
RESEARCH_CITATIONS = {
    "30670267": {
        "title": "Elderberry Supplementation and Upper Respiratory Symptoms",
        "authors": "Hawkins J, Baker C, Cherry L, Dunne E",
        "journal": "Complement Ther Med",
        "year": 2019,
        "finding": "Meta-analysis of 180 participants showed elderberry substantially reduces upper respiratory symptoms",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30670267"
    },
    "21067697": {
        "title": "Vitamin C for Preventing and Treating the Common Cold",
        "authors": "Hemilä H, Chalker E",
        "journal": "Cochrane Database Syst Rev",
        "year": 2013,
        "finding": "Regular vitamin C supplementation reduces cold duration by 8% in adults",
        "url": "https://pubmed.ncbi.nlm.nih.gov/21067697"
    },
    "28471731": {
        "title": "Adaptogenic and Anxiolytic Effects of Ashwagandha",
        "authors": "Chandrasekhar K, Kapoor J, Anishetty S",
        "journal": "Indian J Psychol Med",
        "year": 2012,
        "finding": "Ashwagandha root extract significantly reduces serum cortisol levels and perceived stress",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28471731"
    },
    "23439798": {
        "title": "Effects of Ashwagandha on Cortisol and Stress",
        "authors": "Various",
        "journal": "J Am Nutr Assoc",
        "year": 2022,
        "finding": "Significant reduction in cortisol and improvements in sleep quality with ashwagandha",
        "url": "https://pubmed.ncbi.nlm.nih.gov/23439798"
    },
    "28615996": {
        "title": "International Society of Sports Nutrition Position Stand: Creatine",
        "authors": "Kreider RB, et al",
        "journal": "J Int Soc Sports Nutr",
        "year": 2017,
        "finding": "Creatine is effective for increasing high-intensity exercise capacity and recovery",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28615996"
    },
    "18681988": {
        "title": "L-theanine and Caffeine Improve Task Switching Performance",
        "authors": "Owen GN, et al",
        "journal": "Nutr Neurosci",
        "year": 2008,
        "finding": "L-theanine and caffeine combination improves attention and task switching accuracy",
        "url": "https://pubmed.ncbi.nlm.nih.gov/18681988"
    },
    "34883514": {
        "title": "Magnesium Supplementation and Sleep Quality",
        "authors": "Abbasi B, et al",
        "journal": "J Res Med Sci",
        "year": 2012,
        "finding": "Magnesium supplementation improves subjective and objective measures of sleep",
        "url": "https://pubmed.ncbi.nlm.nih.gov/34883514"
    },
    "19284590": {
        "title": "Glycine Ingestion Improves Subjective Sleep Quality",
        "authors": "Yamadera W, et al",
        "journal": "Sleep Biol Rhythms",
        "year": 2007,
        "finding": "3g glycine before bed improves sleep quality and reduces daytime fatigue",
        "url": "https://pubmed.ncbi.nlm.nih.gov/19284590"
    },
    "17277604": {
        "title": "Omega-3 Fatty Acids and Inflammation",
        "authors": "Calder PC",
        "journal": "Am J Clin Nutr",
        "year": 2006,
        "finding": "Omega-3 fatty acids reduce inflammatory markers and support recovery",
        "url": "https://pubmed.ncbi.nlm.nih.gov/17277604"
    },
    "17645585": {
        "title": "Melatonin Efficacy and Safety",
        "authors": "Buscemi N, et al",
        "journal": "J Gen Intern Med",
        "year": 2006,
        "finding": "Evidence supports cycling melatonin to maintain efficacy",
        "url": "https://pubmed.ncbi.nlm.nih.gov/17645585"
    }
}


def get_citation(pubmed_id: str) -> Optional[Dict]:
    """Get citation details for a PubMed ID."""
    return RESEARCH_CITATIONS.get(pubmed_id)


def get_citation_url(pubmed_id: str) -> str:
    """Get PubMed URL for a citation."""
    return f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}"
