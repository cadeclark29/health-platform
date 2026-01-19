"""
Dynamic Intelligence Engine

Evaluates real-time health metrics against research-backed rules to generate
personalized supplement recommendations with explanations and citations.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

from .metric_rules import (
    METRIC_SUPPLEMENT_RULES,
    COMPOUND_CONDITIONS,
    PRIORITY_LEVELS,
    RESEARCH_CITATIONS,
    get_citation,
    get_citation_url,
)


@dataclass
class SupplementAdjustment:
    """A recommended supplement adjustment."""
    supplement_id: str
    action: str  # "add", "increase", "reduce", "hold", "allow"
    dose_multiplier: float
    priority: int
    priority_level: str
    reason: str
    trigger_metric: str
    trigger_value: Optional[float]
    trigger_condition: str
    citations: List[str]
    explanation: str
    time_restriction: str = ""
    user_alert: str = ""


@dataclass
class HealthStateAssessment:
    """Assessment of current health state based on metrics."""
    active_conditions: List[Dict]
    compound_conditions: List[Dict]
    adjustments: List[SupplementAdjustment]
    overall_status: str  # "optimal", "suboptimal", "stressed", "recovery_needed", "immune_alert"
    alerts: List[str]


class DynamicIntelligenceEngine:
    """
    Research-backed dynamic supplement intelligence engine.

    Evaluates real-time health metrics against thresholds and personal baselines
    to produce context-aware supplement recommendations with research citations.
    """

    def evaluate_health_state(
        self,
        health_data: Dict,
        baseline: Optional[Dict] = None,
        user_profile: Optional[Dict] = None,
    ) -> HealthStateAssessment:
        """
        Comprehensive evaluation of current health state.

        Args:
            health_data: Current health metrics from wearables
            baseline: User's personal baseline (if available)
            user_profile: User's profile data

        Returns:
            HealthStateAssessment with active conditions and recommended adjustments
        """
        active_conditions = []
        all_adjustments = []
        alerts = []

        # Check each metric against its rules
        for metric_name, metric_rules in METRIC_SUPPLEMENT_RULES.items():
            metric_value = health_data.get(metric_name)

            if metric_value is None:
                continue

            for rule_name, rule in metric_rules.items():
                triggered, trigger_info = self._check_rule(
                    rule=rule,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    baseline=baseline
                )

                if triggered:
                    active_conditions.append({
                        "rule_name": rule_name,
                        "metric": metric_name,
                        "value": metric_value,
                        "condition": rule.get("condition"),
                        "priority_level": rule.get("priority_level", "optimization"),
                        "explanation": self._format_explanation(
                            rule.get("explanation", ""),
                            metric_value,
                            baseline,
                            metric_name
                        )
                    })

                    # Convert rule actions to SupplementAdjustment objects
                    for action in rule.get("actions", []):
                        adjustment = SupplementAdjustment(
                            supplement_id=action["supplement"],
                            action=action["action"],
                            dose_multiplier=action.get("dose_mult", 1.0),
                            priority=action.get("priority", 99),
                            priority_level=rule.get("priority_level", "optimization"),
                            reason=action.get("reason", ""),
                            trigger_metric=metric_name,
                            trigger_value=metric_value,
                            trigger_condition=rule.get("condition", ""),
                            citations=rule.get("citations", []),
                            explanation=self._format_explanation(
                                rule.get("explanation", ""),
                                metric_value,
                                baseline,
                                metric_name
                            ),
                            time_restriction=action.get("time_restriction", ""),
                            user_alert=rule.get("user_alert", "")
                        )
                        all_adjustments.append(adjustment)

                    # Collect alerts
                    if rule.get("user_alert"):
                        alerts.append(rule["user_alert"])

        # Check compound conditions
        compound_matches = self._check_compound_conditions(health_data, baseline)
        for compound in compound_matches:
            active_conditions.append({
                "rule_name": compound["name"],
                "metric": "compound",
                "value": None,
                "condition": compound["description"],
                "priority_level": compound.get("priority_level", "optimization"),
                "explanation": compound.get("explanation", "")
            })

            for action in compound.get("actions", []):
                adjustment = SupplementAdjustment(
                    supplement_id=action["supplement"],
                    action=action["action"],
                    dose_multiplier=action.get("dose_mult", 1.0),
                    priority=action.get("priority", 99),
                    priority_level=compound.get("priority_level", "optimization"),
                    reason=action.get("reason", ""),
                    trigger_metric="compound",
                    trigger_value=None,
                    trigger_condition=compound["description"],
                    citations=compound.get("citations", []),
                    explanation=compound.get("explanation", ""),
                    user_alert=compound.get("user_alert", "")
                )
                all_adjustments.append(adjustment)

            if compound.get("user_alert"):
                alerts.append(compound["user_alert"])

        # Resolve conflicts
        resolved_adjustments = self._resolve_conflicts(all_adjustments)

        # Determine overall status
        overall_status = self._determine_overall_status(active_conditions)

        return HealthStateAssessment(
            active_conditions=active_conditions,
            compound_conditions=compound_matches,
            adjustments=resolved_adjustments,
            overall_status=overall_status,
            alerts=alerts
        )

    def _check_rule(
        self,
        rule: Dict,
        metric_name: str,
        metric_value: float,
        baseline: Optional[Dict]
    ) -> Tuple[bool, Dict]:
        """Check if a rule is triggered by the current metric value."""
        condition = rule.get("condition", "")

        # Check for baseline comparison
        if "baseline" in condition:
            if baseline is None:
                return False, {}

            baseline_mult = rule.get("baseline_mult")
            comparison = rule.get("comparison", "<")

            # Get baseline value for this metric
            baseline_info = self._get_baseline_for_metric(metric_name, baseline)
            if baseline_info is None:
                return False, {}

            baseline_value = baseline_info.get("mean")
            if baseline_value is None:
                return False, {}

            threshold = baseline_value * baseline_mult

            if comparison == "<":
                triggered = metric_value < threshold
            elif comparison == ">":
                triggered = metric_value > threshold
            else:
                triggered = False

            return triggered, {"threshold": threshold, "baseline_value": baseline_value}

        # Check for fixed threshold
        threshold = rule.get("threshold")
        comparison = rule.get("comparison")

        if threshold is not None and comparison:
            if comparison == "<":
                triggered = metric_value < threshold
            elif comparison == ">":
                triggered = metric_value > threshold
            elif comparison == "<=":
                triggered = metric_value <= threshold
            elif comparison == ">=":
                triggered = metric_value >= threshold
            else:
                triggered = False

            return triggered, {"threshold": threshold}

        return False, {}

    def _get_baseline_for_metric(self, metric_name: str, baseline: Dict) -> Optional[Dict]:
        """Get baseline statistics for a metric."""
        # Map metric names to baseline keys
        metric_to_baseline = {
            "hrv_score": "hrv",
            "sleep_score": "sleep_score",
            "recovery_score": "recovery_score",
            "strain_score": "strain_score",
            "sleep_duration_hrs": "sleep_duration",
        }

        baseline_key = metric_to_baseline.get(metric_name, metric_name)
        return baseline.get(baseline_key)

    def _check_compound_conditions(
        self,
        health_data: Dict,
        baseline: Optional[Dict]
    ) -> List[Dict]:
        """Check for compound conditions that require multiple metrics."""
        matched_conditions = []

        for condition_name, condition in COMPOUND_CONDITIONS.items():
            required_metrics = condition.get("required_metrics", [])
            min_matches = condition.get("min_matches", len(required_metrics))

            matches = 0
            for req in required_metrics:
                metric = req["metric"]
                cond_type = req["condition"]
                threshold = req["threshold"]

                metric_value = health_data.get(metric)
                if metric_value is None:
                    continue

                if cond_type == "below":
                    if metric_value < threshold:
                        matches += 1
                elif cond_type == "above":
                    if metric_value > threshold:
                        matches += 1
                elif cond_type == "below_baseline" and baseline:
                    baseline_info = self._get_baseline_for_metric(metric, baseline)
                    if baseline_info:
                        baseline_value = baseline_info.get("mean")
                        if baseline_value and metric_value < (baseline_value * threshold):
                            matches += 1

            if matches >= min_matches:
                matched_conditions.append({
                    "name": condition_name,
                    **condition
                })

        return matched_conditions

    def _resolve_conflicts(
        self,
        adjustments: List[SupplementAdjustment]
    ) -> List[SupplementAdjustment]:
        """
        Resolve conflicts when multiple rules affect the same supplement.

        Priority order (higher = more important):
        1. Safety blocks (contraindications)
        2. Immune response (temperature/illness)
        3. Acute stress (very low HRV)
        4. Sleep crisis
        5. Recovery deficit
        6. Optimization
        7. Maintenance
        """
        if not adjustments:
            return []

        # Group by supplement
        by_supplement: Dict[str, List[SupplementAdjustment]] = {}
        for adj in adjustments:
            if adj.supplement_id not in by_supplement:
                by_supplement[adj.supplement_id] = []
            by_supplement[adj.supplement_id].append(adj)

        resolved = []
        for supplement_id, adj_list in by_supplement.items():
            # Sort by priority level (higher = more important)
            adj_list.sort(
                key=lambda a: PRIORITY_LEVELS.get(a.priority_level, 0),
                reverse=True
            )

            # Take the highest priority adjustment
            winner = adj_list[0]

            # Special handling: "hold" always wins over other actions
            # (safety is paramount)
            for adj in adj_list:
                if adj.action == "hold":
                    winner = adj
                    break

            resolved.append(winner)

        # Sort final list by priority for display
        resolved.sort(
            key=lambda a: (PRIORITY_LEVELS.get(a.priority_level, 0), -a.priority),
            reverse=True
        )

        return resolved

    def _determine_overall_status(self, active_conditions: List[Dict]) -> str:
        """Determine overall health status from active conditions."""
        if not active_conditions:
            return "optimal"

        priority_levels = [c.get("priority_level", "optimization") for c in active_conditions]

        if "immune_response" in priority_levels:
            return "immune_alert"
        if "acute_stress" in priority_levels:
            return "stressed"
        if "sleep_crisis" in priority_levels:
            return "sleep_deficit"
        if "recovery_deficit" in priority_levels:
            return "recovery_needed"

        return "suboptimal"

    def _format_explanation(
        self,
        template: str,
        value: float,
        baseline: Optional[Dict],
        metric_name: str
    ) -> str:
        """Format explanation string with actual values."""
        if not template:
            return ""

        result = template

        # Replace {value} placeholder
        if value is not None:
            result = result.replace("{value}", str(round(value, 1)))

        # Calculate and replace baseline comparison placeholders
        if baseline:
            baseline_info = self._get_baseline_for_metric(metric_name, baseline)
            if baseline_info:
                baseline_value = baseline_info.get("mean")
                if baseline_value and value is not None:
                    percent_below = round((1 - value / baseline_value) * 100, 1)
                    percent_above = round((value / baseline_value - 1) * 100, 1)
                    result = result.replace("{percent_below}", str(percent_below))
                    result = result.replace("{percent_above}", str(percent_above))

        return result

    def get_adjustment_with_research(
        self,
        adjustment: SupplementAdjustment
    ) -> Dict:
        """Get adjustment with full research details."""
        citations_detail = []
        for pubmed_id in adjustment.citations:
            citation = get_citation(pubmed_id)
            if citation:
                citations_detail.append({
                    "pubmed_id": pubmed_id,
                    "url": get_citation_url(pubmed_id),
                    **citation
                })

        return {
            "supplement_id": adjustment.supplement_id,
            "action": adjustment.action,
            "dose_multiplier": adjustment.dose_multiplier,
            "reason": adjustment.reason,
            "trigger": {
                "metric": adjustment.trigger_metric,
                "value": adjustment.trigger_value,
                "condition": adjustment.trigger_condition
            },
            "explanation": adjustment.explanation,
            "research": {
                "citations": citations_detail,
                "citation_ids": adjustment.citations
            },
            "time_restriction": adjustment.time_restriction,
            "user_alert": adjustment.user_alert,
            "priority_level": adjustment.priority_level
        }


# Singleton instance
dynamic_intelligence = DynamicIntelligenceEngine()
