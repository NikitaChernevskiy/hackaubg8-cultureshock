"""Azure OpenAI provider — generates advisory guidance via GPT.

The system prompt enforces advisory-only language. The provider adds
a post-processing check to catch any imperative language that slips through.
"""

import json
import logging

from openai import AsyncAzureOpenAI

from app.config import get_settings
from app.constants import AI_SYSTEM_PROMPT
from app.models.alerts import Alert
from app.models.common import Location
from app.models.transport import TransportOption
from app.providers.base import AIProvider

logger = logging.getLogger(__name__)

# Words that should NEVER appear as the start of a sentence in advisory text
_IMPERATIVE_BLOCKLIST = [
    "go to",
    "leave now",
    "evacuate immediately",
    "you must",
    "you need to",
    "do not move",
    "run to",
    "drive to",
    "walk to",
    "head to",
]


def _check_imperative_language(text: str) -> str:
    """Post-process AI output to soften any imperative language that slipped through."""
    lowered = text.lower()
    for phrase in _IMPERATIVE_BLOCKLIST:
        if phrase in lowered:
            logger.warning("Imperative language detected in AI output: '%s'", phrase)
            # Replace with advisory framing
            text = text.replace(
                phrase, f"you may want to consider {phrase.split()[-1]}ing"
            )
            text = text.replace(
                phrase.capitalize(), f"You may want to consider {phrase.split()[-1]}ing"
            )
    return text


class AzureOpenAIProvider(AIProvider):
    """Generates advisory text via Azure OpenAI with legal safeguards."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self._deployment = settings.azure_openai_deployment

    async def generate_guidance(
        self,
        location: Location,
        alerts: list[Alert],
        transport: list[TransportOption],
        language: str = "en",
    ) -> dict:
        # Build structured context for the LLM — real detected data only
        context = {
            "location": {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "city": location.city,
                "country": location.country_name or location.country,
            },
            "alerts": [
                {
                    "type": a.type,
                    "severity": a.severity,
                    "title": a.title,
                    "description": a.description,
                }
                for a in alerts
            ],
            "transport_options": [
                {
                    "type": t.type,
                    "name": t.name,
                    "status": t.status,
                    "status_detail": t.status_detail,
                    "distance_km": t.distance_km,
                }
                for t in transport
            ],
        }

        user_message = (
            f"Emergency context (JSON):\n{json.dumps(context, indent=2)}\n\n"
            f"Language: {language}\n\n"
            "Based on this data, provide:\n"
            "1. A suggested action (one of: consider_shelter, consider_evacuation, "
            "monitor_situation, no_immediate_concern)\n"
            "2. Advisory text (2-3 paragraphs, advisory language ONLY)\n"
            "3. A prioritized list of 3-5 suggested considerations\n\n"
            "Respond in JSON format with keys: action_suggestion, advisory_text, priority_steps"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,  # Low temperature for consistent, careful output
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or "{}"
            parsed = json.loads(raw)

            # Post-process: catch imperative language
            advisory_text = _check_imperative_language(
                parsed.get("advisory_text", "Unable to generate advisory at this time.")
            )

            # Calculate confidence based on data completeness
            confidence = 0.5
            if alerts:
                confidence += 0.25
            if transport:
                confidence += 0.15
            if location.city:
                confidence += 0.1
            confidence = min(confidence, 0.95)  # Never claim 100% confidence

            return {
                "advisory_text": advisory_text,
                "action_suggestion": parsed.get("action_suggestion", "monitor_situation"),
                "priority_steps": parsed.get("priority_steps", []),
                "confidence": confidence,
                "model": f"azure-openai/{self._deployment}",
            }

        except Exception:
            logger.exception("Azure OpenAI call failed")
            return {
                "advisory_text": (
                    "We were unable to generate AI advisory at this time. "
                    "Please rely on official emergency channels and local authorities "
                    "for guidance."
                ),
                "action_suggestion": "monitor_situation",
                "priority_steps": [
                    "Contact local emergency services for current guidance",
                    "Monitor official news and government channels",
                    "Consider contacting your embassy or consulate",
                ],
                "confidence": 0.0,
                "model": "fallback",
            }

    async def health_check(self) -> bool:
        try:
            response = await self._client.chat.completions.create(
                model=self._deployment,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception:
            logger.exception("Azure OpenAI health check failed")
            return False
