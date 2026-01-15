import json
from typing import Dict, List, Optional
from openai import AsyncOpenAI

from app.config import get_settings


class LLMPersonalizer:
    """LLM-based personalization layer for supplement recommendations."""

    SYSTEM_PROMPT = """You are an AI health assistant that provides personalized supplement recommendations.

Your role is to analyze health data and recommend supplements from a predefined list. You must:
1. Only recommend supplements from the provided available list
2. Consider the user's health metrics, goals, and active triggers
3. Provide clear reasoning for each recommendation
4. Prioritize recommendations based on the user's current needs
5. Never exceed the remaining dose limits provided

You are NOT a doctor. These are supplement recommendations for general wellness, not medical advice.

Respond in JSON format with this structure:
{
    "recommendations": [
        {
            "supplement_id": "string",
            "dose": number,
            "reason": "string explaining why this supplement based on current health data"
        }
    ],
    "reasoning": "string with overall analysis of user's health state and recommendation rationale"
}"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def personalize_recommendations(
        self,
        health_data: dict,
        active_triggers: Dict[str, bool],
        available_supplements: List[dict],
        user_goals: List[str] = None,
        time_of_day: str = "morning"
    ) -> dict:
        """Use LLM to personalize and rank supplement recommendations."""
        if self.client is None:
            # Fallback to rule-based only if no API key
            return self._fallback_recommendations(available_supplements, active_triggers)

        if user_goals is None:
            user_goals = []

        # Build the prompt
        user_message = self._build_prompt(
            health_data,
            active_triggers,
            available_supplements,
            user_goals,
            time_of_day
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            # Fallback to rule-based if LLM fails
            print(f"LLM error: {e}")
            return self._fallback_recommendations(available_supplements, active_triggers)

    def _build_prompt(
        self,
        health_data: dict,
        active_triggers: Dict[str, bool],
        available_supplements: List[dict],
        user_goals: List[str],
        time_of_day: str
    ) -> str:
        """Build the user prompt for the LLM."""
        # Format active triggers
        active_trigger_names = [k for k, v in active_triggers.items() if v]

        prompt = f"""Current time of day: {time_of_day}

## User's Health Data
- Sleep Score: {health_data.get('sleep_score', 'N/A')}
- HRV Score: {health_data.get('hrv_score', 'N/A')}
- Recovery Score: {health_data.get('recovery_score', 'N/A')}
- Strain Score: {health_data.get('strain_score', 'N/A')}
- Sleep Duration: {health_data.get('sleep_duration_hrs', 'N/A')} hours
- Resting Heart Rate: {health_data.get('resting_hr', 'N/A')} bpm

## Active Health Triggers
{', '.join(active_trigger_names) if active_trigger_names else 'None'}

## User's Health Goals
{', '.join(user_goals) if user_goals else 'General wellness'}

## Available Supplements (with remaining daily allowance)
"""
        for supp in available_supplements:
            prompt += f"\n- {supp['name']} ({supp['id']}): up to {supp['remaining_dose']}{supp['unit']}, triggers: {', '.join(supp['triggers'])}"

        prompt += """

Based on this health data and available supplements, recommend which supplements would be most beneficial right now. Only recommend supplements that address the active triggers or support the user's goals. Limit to 3-5 most relevant supplements."""

        return prompt

    def _fallback_recommendations(
        self,
        available_supplements: List[dict],
        active_triggers: Dict[str, bool]
    ) -> dict:
        """Fallback to rule-based recommendations if LLM is unavailable."""
        recommendations = []
        active_trigger_names = {k for k, v in active_triggers.items() if v}

        for supp in available_supplements:
            supp_triggers = set(supp.get("triggers", []))
            matched = supp_triggers & active_trigger_names

            if matched:
                recommendations.append({
                    "supplement_id": supp["id"],
                    "dose": min(supp["standard_dose"], supp["remaining_dose"]),
                    "reason": f"Addresses: {', '.join(matched)}"
                })

        # Limit to top 5
        recommendations = recommendations[:5]

        return {
            "recommendations": recommendations,
            "reasoning": "Rule-based recommendations (LLM unavailable)"
        }
