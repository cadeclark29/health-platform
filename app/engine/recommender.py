from datetime import datetime, date
from sqlalchemy.orm import Session

from app.models import User, HealthData, DispenseLog
from .rules import RulesEngine
from .llm import LLMPersonalizer


class RecommendationEngine:
    """Main recommendation engine combining rules and LLM personalization."""

    def __init__(self):
        self.rules = RulesEngine()
        self.llm = LLMPersonalizer()

    async def get_recommendation(
        self,
        user: User,
        db: Session,
        time_override: int = None
    ) -> dict:
        """
        Generate a personalized supplement recommendation for a user.

        Args:
            user: The user to generate recommendations for
            db: Database session
            time_override: Optional hour (0-23) to override current time

        Returns:
            Dictionary with recommendations and reasoning
        """
        # Step 1: Determine time of day
        time_of_day = self.rules.get_time_of_day(time_override)

        # Step 2: Get user's latest health data
        health_data = self._get_latest_health_data(user.id, db)

        # Step 3: Get what's been dispensed today
        dispensed_today = self._get_dispensed_today(user.id, db)

        # Step 4: Get available supplements (filtered by rules)
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
                "health_snapshot": health_data
            }

        # Step 5: Analyze health triggers
        active_triggers = self.rules.analyze_health_triggers(health_data)

        # Step 6: Prepare supplements with remaining doses for LLM
        supplements_for_llm = []
        for supp in available:
            remaining = self.rules.get_remaining_dose(supp.id, dispensed_today)
            supplements_for_llm.append({
                "id": supp.id,
                "name": supp.name,
                "unit": supp.unit,
                "standard_dose": supp.standard_dose,
                "remaining_dose": remaining,
                "triggers": list(supp.triggers.keys())
            })

        # Step 7: Get LLM personalized recommendations
        llm_result = await self.llm.personalize_recommendations(
            health_data=health_data,
            active_triggers=active_triggers,
            available_supplements=supplements_for_llm,
            user_goals=user.goals or [],
            time_of_day=time_of_day
        )

        # Step 8: Validate and finalize recommendations
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

                # Build detailed explanation
                matched_triggers = []
                for trigger_name, is_active in active_triggers.items():
                    if is_active and config.triggers.get(trigger_name, False):
                        trigger_explanation = self.rules.get_trigger_explanation(trigger_name, health_data)
                        if trigger_explanation:
                            matched_triggers.append(trigger_explanation)

                validated_recommendations.append({
                    "supplement_id": supplement_id,
                    "name": config.name,
                    "dose": dose,
                    "unit": config.unit,
                    "reason": rec.get("reason", ""),
                    "explanation": {
                        "matched_triggers": matched_triggers,
                        "evidence": config.evidence,
                        "standard_dose": config.standard_dose,
                        "max_daily_dose": config.max_daily_dose,
                        "time_windows": config.time_windows
                    }
                })

        return {
            "recommendations": validated_recommendations,
            "reasoning": llm_result.get("reasoning", ""),
            "time_of_day": time_of_day,
            "health_snapshot": health_data,
            "active_triggers": [k for k, v in active_triggers.items() if v]
        }

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
