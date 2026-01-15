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

    BLEND_SYSTEM_PROMPT = """You are an AI supplement expert helping users create custom supplement blends.

Your role is to suggest supplements based on the user's goals and needs. You must:
1. Only recommend supplements from the provided catalog
2. Suggest appropriate doses within safe limits (never exceed max_daily_dose)
3. Provide clear reasoning for each supplement choice
4. Consider synergies between supplements (e.g., D3+K2, caffeine+L-theanine)
5. Warn about any timing considerations (e.g., caffeine only in morning)

You are NOT a doctor. These are general wellness suggestions, not medical advice.

Respond in JSON format with this structure:
{
    "blend_name": "suggested name for this blend",
    "blend_icon": "single emoji that represents this blend",
    "supplements": [
        {
            "supplement_id": "string (must match catalog id)",
            "dose": number (within max_daily_dose),
            "reason": "brief explanation of why this supplement helps"
        }
    ],
    "summary": "1-2 sentence summary of what this blend is designed for",
    "timing": "when to take this blend (morning/afternoon/evening)"
}"""

    async def suggest_blend(
        self,
        user_request: str,
        supplement_catalog: List[dict],
        user_profile: Optional[dict] = None
    ) -> dict:
        """Use LLM to suggest a custom blend based on user's description."""
        if self.client is None:
            return self._fallback_blend_suggestion(user_request, supplement_catalog)

        # Build the prompt
        user_message = self._build_blend_prompt(user_request, supplement_catalog, user_profile)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.BLEND_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=1500
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"LLM error in blend suggestion: {e}")
            return self._fallback_blend_suggestion(user_request, supplement_catalog)

    def _build_blend_prompt(
        self,
        user_request: str,
        supplement_catalog: List[dict],
        user_profile: Optional[dict]
    ) -> str:
        """Build prompt for blend suggestion."""
        prompt = f"""## User's Request
"{user_request}"
"""

        if user_profile:
            prompt += f"""
## User Profile
- Age: {user_profile.get('age', 'Unknown')}
- Sex: {user_profile.get('sex', 'Unknown')}
- Weight: {user_profile.get('weight_kg', 'Unknown')} kg
"""

        prompt += """
## Available Supplement Catalog
"""
        for supp in supplement_catalog:
            benefits = ', '.join(supp.get('benefits', [])[:3])
            prompt += f"""
### {supp['name']} (id: {supp['id']})
- Standard dose: {supp['standard_dose']} {supp['unit']}
- Max daily: {supp['max_daily_dose']} {supp['unit']}
- Best time: {', '.join(supp.get('time_windows', ['any']))}
- Benefits: {benefits}
- Description: {supp.get('description', 'N/A')}
"""

        prompt += """
Based on the user's request, suggest 3-6 supplements that would create an effective blend. Consider supplement synergies and timing. Provide a suggested blend name and icon emoji."""

        return prompt

    def _fallback_blend_suggestion(
        self,
        user_request: str,
        supplement_catalog: List[dict]
    ) -> dict:
        """Simple keyword-based fallback for blend suggestions."""
        request_lower = user_request.lower()
        suggestions = []

        # Simple keyword matching
        keyword_map = {
            "sleep": ["magnesium_glycinate", "glycine", "melatonin", "apigenin", "l_theanine"],
            "energy": ["caffeine", "vitamin_b12", "coq10", "creatine"],
            "focus": ["caffeine", "l_theanine", "lions_mane", "creatine"],
            "stress": ["ashwagandha", "l_theanine", "magnesium_glycinate"],
            "recovery": ["creatine", "omega_3", "magnesium_glycinate", "zinc"],
            "immune": ["vitamin_c", "zinc", "vitamin_d3", "blackseed_oil"],
            "workout": ["creatine", "l_citrulline", "caffeine", "electrolytes"],
            "mood": ["omega_3", "vitamin_d3", "ashwagandha", "magnesium_glycinate"],
        }

        matched_ids = set()
        for keyword, supp_ids in keyword_map.items():
            if keyword in request_lower:
                matched_ids.update(supp_ids)

        # Build suggestions from matched supplements
        for supp in supplement_catalog:
            if supp['id'] in matched_ids and len(suggestions) < 5:
                suggestions.append({
                    "supplement_id": supp['id'],
                    "dose": supp['standard_dose'],
                    "reason": f"Supports {supp.get('benefits', ['general wellness'])[0].lower()}"
                })

        # Default to basic stack if no matches
        if not suggestions:
            defaults = ["vitamin_d3", "omega_3", "magnesium_glycinate"]
            for supp in supplement_catalog:
                if supp['id'] in defaults:
                    suggestions.append({
                        "supplement_id": supp['id'],
                        "dose": supp['standard_dose'],
                        "reason": "Essential daily nutrient"
                    })

        return {
            "blend_name": "Custom Blend",
            "blend_icon": "🧪",
            "supplements": suggestions,
            "summary": "A blend suggested based on your goals (AI unavailable for detailed analysis)",
            "timing": "morning"
        }


# Singleton instance
llm_personalizer = LLMPersonalizer()
