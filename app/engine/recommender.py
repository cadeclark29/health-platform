from datetime import datetime, date
from typing import Optional, Dict
from sqlalchemy.orm import Session

from app.models import User, HealthData, DispenseLog, DailyCheckIn
from .rules import RulesEngine
from .llm import LLMPersonalizer
from .interactions import interaction_checker
from .dynamic_intelligence import dynamic_intelligence, SupplementAdjustment


class RecommendationEngine:
    """Main recommendation engine combining rules, dynamic intelligence, and LLM personalization."""

    def __init__(self):
        self.rules = RulesEngine()
        self.llm = LLMPersonalizer()
        self.intelligence = dynamic_intelligence

    async def get_recommendation(
        self,
        user: User,
        db: Session,
        time_override: int = None
    ) -> dict:
        """
        Generate a personalized supplement recommendation for a user.

        Uses personal baselines when available for more accurate triggers.
        Incorporates daily check-in data (subjective reports).

        Args:
            user: The user to generate recommendations for
            db: Database session
            time_override: Optional hour (0-23) to override current time

        Returns:
            Dictionary with recommendations and reasoning
        """
        # Step 1: Determine time of day (using user's bedtime preference)
        time_of_day = self.rules.get_time_of_day(time_override, user.bedtime)

        # Step 2: Get user's latest health data
        health_data = self._get_latest_health_data(user.id, db)

        # Step 3: Get user's personal baseline (if calculated)
        baseline = self._get_user_baseline(user, db)

        # Step 4: Get today's check-in (subjective reports)
        checkin = self._get_todays_checkin(user.id, db)

        # Step 5: Get what's been dispensed today
        dispensed_today = self._get_dispensed_today(user.id, db)

        # Step 6: Get available supplements (filtered by rules)
        available = self.rules.get_available_supplements(
            time_of_day=time_of_day,
            user_allergies=user.allergies or [],
            dispensed_today=dispensed_today
        )

        if not available:
            return {
                "recommendations": [],
                "reasoning": f"No supplements available for {time_of_day} (daily limits reached or time restrictions)",
                "time_of_day": time_of_day,
                "health_snapshot": health_data,
                "using_baseline": baseline is not None
            }

        # Step 7: Analyze health triggers (using personal baseline if available)
        active_triggers = self.rules.analyze_health_triggers(
            health_data,
            baseline=baseline,
            checkin=checkin
        )

        # Step 7b: Evaluate dynamic intelligence rules
        health_state = self.intelligence.evaluate_health_state(
            health_data=health_data,
            baseline=baseline,
            user_profile={
                "weight_kg": user.weight_kg,
                "age": user.age,
                "sex": user.sex
            }
        )

        # Build dynamic adjustments lookup for quick access
        dynamic_adjustments = {}
        for adj in health_state.adjustments:
            if adj.supplement_id not in dynamic_adjustments:
                dynamic_adjustments[adj.supplement_id] = adj
            elif adj.action == "hold":
                # Hold always takes precedence
                dynamic_adjustments[adj.supplement_id] = adj

        # Step 8: Prepare supplements with remaining doses for LLM
        # Apply dynamic adjustment filters (e.g., hold caffeine if immune_alert)
        supplements_for_llm = []
        held_supplements = []

        for supp in available:
            # Check if this supplement should be held due to dynamic rules
            dyn_adj = dynamic_adjustments.get(supp.id)
            if dyn_adj and dyn_adj.action == "hold":
                held_supplements.append({
                    "id": supp.id,
                    "name": supp.name,
                    "reason": dyn_adj.reason or dyn_adj.explanation,
                    "trigger": dyn_adj.trigger_metric
                })
                continue  # Skip this supplement - it's being held

            remaining = self.rules.get_remaining_dose(supp.id, dispensed_today)
            supplements_for_llm.append({
                "id": supp.id,
                "name": supp.name,
                "unit": supp.unit,
                "standard_dose": supp.standard_dose,
                "remaining_dose": remaining,
                "triggers": list(supp.triggers.keys()),
                "dynamic_adjustment": self._get_dynamic_adjustment_info(dyn_adj) if dyn_adj else None
            })

        # Step 9: Get LLM personalized recommendations
        llm_result = await self.llm.personalize_recommendations(
            health_data=health_data,
            active_triggers=active_triggers,
            available_supplements=supplements_for_llm,
            user_goals=user.goals or [],
            time_of_day=time_of_day
        )

        # Step 10: Validate and finalize recommendations
        validated_recommendations = []
        for rec in llm_result.get("recommendations", []):
            supplement_id = rec.get("supplement_id")
            dose = rec.get("dose")

            is_valid, message = self.rules.validate_recommendation(
                supplement_id=supplement_id,
                dose=dose,
                time_of_day=time_of_day,
                user_allergies=user.allergies or [],
                dispensed_today=dispensed_today
            )

            if is_valid:
                config = self.rules.supplements.get(supplement_id)

                # Get personalized dose based on user profile
                user_profile = {
                    "weight_kg": user.weight_kg,
                    "age": user.age,
                    "sex": user.sex
                }
                dose_info = interaction_checker.get_adjusted_dose(
                    supplement_id,
                    config.standard_dose,
                    user_profile
                )

                # Use adjusted dose if available and lower than LLM suggestion
                final_dose = dose
                dose_adjustment = None
                if dose_info.get("adjustments_applied"):
                    adjusted = dose_info["adjusted_dose"]
                    # Use the smaller of LLM suggestion or adjusted dose for safety
                    if adjusted < dose:
                        final_dose = adjusted
                        dose_adjustment = dose_info

                # Build detailed explanation
                matched_triggers = []
                for trigger_name, is_active in active_triggers.items():
                    if is_active and config.triggers.get(trigger_name, False):
                        trigger_explanation = self.rules.get_trigger_explanation(trigger_name, health_data)
                        if trigger_explanation:
                            matched_triggers.append(trigger_explanation)

                # Get dynamic intelligence info if available
                dyn_adj = dynamic_adjustments.get(supplement_id)
                dynamic_info = None
                if dyn_adj:
                    dynamic_info = self.intelligence.get_adjustment_with_research(dyn_adj)
                    # Apply dose multiplier from dynamic rules
                    if dyn_adj.action == "increase" and dyn_adj.dose_multiplier > 1:
                        final_dose = min(final_dose * dyn_adj.dose_multiplier, config.max_daily_dose)
                    elif dyn_adj.action == "reduce" and dyn_adj.dose_multiplier < 1:
                        final_dose = final_dose * dyn_adj.dose_multiplier

                validated_recommendations.append({
                    "supplement_id": supplement_id,
                    "name": config.name,
                    "dose": round(final_dose, 1),
                    "unit": config.unit,
                    "reason": rec.get("reason", ""),
                    "explanation": {
                        "matched_triggers": matched_triggers,
                        "evidence": config.evidence,
                        "standard_dose": config.standard_dose,
                        "max_daily_dose": config.max_daily_dose,
                        "time_windows": config.time_windows,
                        "dose_adjustment": dose_adjustment
                    },
                    "dynamic_intelligence": dynamic_info
                })

        # Step 11: Inject supplements that dynamic intelligence wants to ADD
        # (These are supplements triggered by health conditions that LLM may not have suggested)
        already_recommended = {r["supplement_id"] for r in validated_recommendations}

        for adj in health_state.adjustments:
            if adj.action == "add" and adj.supplement_id not in already_recommended:
                config = self.rules.supplements.get(adj.supplement_id)
                if config is None:
                    continue

                # Check if this supplement is valid for the current time and user
                is_valid, message = self.rules.validate_recommendation(
                    supplement_id=adj.supplement_id,
                    dose=config.standard_dose * adj.dose_multiplier,
                    time_of_day=time_of_day,
                    user_allergies=user.allergies or [],
                    dispensed_today=dispensed_today
                )

                if is_valid:
                    dynamic_info = self.intelligence.get_adjustment_with_research(adj)
                    final_dose = min(
                        config.standard_dose * adj.dose_multiplier,
                        config.max_daily_dose - dispensed_today.get(adj.supplement_id, 0)
                    )

                    validated_recommendations.append({
                        "supplement_id": adj.supplement_id,
                        "name": config.name,
                        "dose": round(final_dose, 1),
                        "unit": config.unit,
                        "reason": adj.explanation or adj.reason,
                        "explanation": {
                            "matched_triggers": [{
                                "trigger": adj.trigger_metric,
                                "description": adj.trigger_condition,
                                "metric": adj.trigger_metric,
                                "actual_value": adj.trigger_value,
                                "threshold": None,
                                "comparison": None
                            }],
                            "evidence": config.evidence,
                            "standard_dose": config.standard_dose,
                            "max_daily_dose": config.max_daily_dose,
                            "time_windows": config.time_windows,
                            "dose_adjustment": None
                        },
                        "dynamic_intelligence": dynamic_info
                    })
                    already_recommended.add(adj.supplement_id)

        # Step 12: Check for interactions between recommended supplements
        recommended_ids = [r["supplement_id"] for r in validated_recommendations]
        interaction_warnings = []
        cycle_warnings = []

        if recommended_ids:
            # Check interactions
            interactions = interaction_checker.check_interactions(
                recommended_ids,
                user.allergies  # May contain medication info
            )
            for interaction in interactions:
                interaction_warnings.append({
                    "supplements": [interaction.supplement_a, interaction.supplement_b],
                    "severity": interaction.severity,
                    "type": interaction.interaction_type,
                    "description": interaction.description,
                    "recommendation": interaction.recommendation
                })

            # Check cycling requirements
            usage_history = self._get_usage_history(user.id, recommended_ids, db)
            for supp_id in recommended_ids:
                days = usage_history.get(supp_id, 0)
                if days > 0:
                    status = interaction_checker.check_cycle_status(supp_id, days)
                    if status["status"] in ["cycle_now", "approaching"]:
                        cycle_warnings.append({
                            "supplement_id": supp_id,
                            **status
                        })

        # Build dynamic intelligence summary
        dynamic_summary = {
            "overall_status": health_state.overall_status,
            "active_conditions": health_state.active_conditions,
            "compound_conditions": [c["name"] for c in health_state.compound_conditions],
            "held_supplements": held_supplements,
            "alerts": health_state.alerts
        }

        return {
            "recommendations": validated_recommendations,
            "reasoning": llm_result.get("reasoning", ""),
            "time_of_day": time_of_day,
            "health_snapshot": health_data,
            "active_triggers": [k for k, v in active_triggers.items() if v],
            "using_baseline": baseline is not None,
            "has_checkin": checkin is not None,
            "interaction_warnings": interaction_warnings,
            "cycle_warnings": cycle_warnings,
            "dynamic_intelligence": dynamic_summary
        }

    def _get_dynamic_adjustment_info(self, adj: SupplementAdjustment) -> Dict:
        """Convert SupplementAdjustment to dict for LLM context."""
        if adj is None:
            return None
        return {
            "action": adj.action,
            "dose_multiplier": adj.dose_multiplier,
            "reason": adj.reason,
            "trigger_metric": adj.trigger_metric,
            "trigger_value": adj.trigger_value,
            "priority_level": adj.priority_level
        }

    def _get_user_baseline(self, user: User, db: Session) -> Optional[Dict]:
        """Get user's personal baseline as a dict, if calculated."""
        from app.models import UserBaseline
        baseline = db.query(UserBaseline).filter(UserBaseline.user_id == user.id).first()
        if baseline:
            return baseline.to_dict()
        return None

    def _get_todays_checkin(self, user_id: str, db: Session) -> Optional[Dict]:
        """Get today's check-in data for the user."""
        today = date.today()
        checkin = db.query(DailyCheckIn).filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.check_in_date == today
        ).first()

        if checkin:
            return checkin.to_dict()
        return None

    def _get_latest_health_data(self, user_id: str, db: Session) -> dict:
        """Get the most recent health data for a user."""
        latest = db.query(HealthData).filter(
            HealthData.user_id == user_id
        ).order_by(HealthData.timestamp.desc()).first()

        if latest:
            return latest.to_dict()

        # Return empty dict if no health data
        return {}

    def _get_dispensed_today(self, user_id: str, db: Session) -> dict[str, float]:
        """Get total dispensed amounts for today."""
        today_start = datetime.combine(date.today(), datetime.min.time())

        logs = db.query(DispenseLog).filter(
            DispenseLog.user_id == user_id,
            DispenseLog.dispensed_at >= today_start
        ).all()

        dispensed = {}
        for log in logs:
            if log.supplement_name not in dispensed:
                dispensed[log.supplement_name] = 0
            dispensed[log.supplement_name] += log.dose

        return dispensed

    def _get_usage_history(
        self,
        user_id: str,
        supplement_ids: list,
        db: Session
    ) -> dict:
        """
        Get consecutive days of use for each supplement.

        Used for cycling protocol checks.
        """
        from datetime import timedelta

        history = {}
        today = date.today()

        for supp_id in supplement_ids:
            consecutive_days = 0
            check_date = today

            # Look back up to 120 days
            for _ in range(120):
                day_start = datetime.combine(check_date, datetime.min.time())
                day_end = datetime.combine(check_date + timedelta(days=1), datetime.min.time())

                log = db.query(DispenseLog).filter(
                    DispenseLog.user_id == user_id,
                    DispenseLog.supplement_name == supp_id,
                    DispenseLog.dispensed_at >= day_start,
                    DispenseLog.dispensed_at < day_end
                ).first()

                if log:
                    consecutive_days += 1
                    check_date -= timedelta(days=1)
                else:
                    break

            if consecutive_days > 0:
                history[supp_id] = consecutive_days

        return history

    def record_dispense(
        self,
        user_id: str,
        supplement_id: str,
        dose: float,
        db: Session
    ) -> DispenseLog:
        """Record that a supplement was dispensed."""
        config = self.rules.supplements.get(supplement_id)
        if config is None:
            raise ValueError(f"Unknown supplement: {supplement_id}")

        log = DispenseLog(
            user_id=user_id,
            supplement_name=supplement_id,
            dose=dose,
            unit=config.unit
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
