"""Mock AI provider — returns pre-written advisory text for development.

Even mock text follows the advisory-only language rules.
"""

from app.models.alerts import Alert
from app.models.common import Location
from app.models.transport import TransportOption
from app.providers.base import AIProvider


class MockAIProvider(AIProvider):
    """Returns canned advisory guidance. Uses advisory language only."""

    async def generate_guidance(
        self,
        location: Location,
        alerts: list[Alert],
        transport: list[TransportOption],
        language: str = "en",
    ) -> dict:
        # Determine severity from alerts
        severities = [a.severity for a in alerts] if alerts else []
        has_critical = "critical" in severities
        has_high = "high" in severities

        if has_critical:
            action = "consider_shelter"
            text = (
                "Based on available reports, there may be a significant threat in your area. "
                "You may want to consider seeking shelter in a sturdy building away from "
                "windows and heavy objects. It might be advisable to stay tuned to local "
                "radio or official emergency channels for updates. If you feel it is safe "
                "to move, some travelers in similar situations have found it helpful to "
                "head toward official gathering points. Please contact local emergency "
                "services for guidance specific to your situation."
            )
            steps = [
                "Consider moving to an interior room away from windows",
                "You may want to check local emergency broadcasts for official guidance",
                "It might be helpful to contact your embassy or consulate",
                "Some travelers suggest having identification and essentials ready",
                "Consider informing someone of your location and plans",
            ]
        elif has_high:
            action = "consider_evacuation"
            text = (
                "Reports suggest elevated risk in your area. Some transport options "
                "may still be available. You might want to consider reviewing departure "
                "options while monitoring official channels. It could be advisable to "
                "prepare your belongings and documents in case conditions change. "
                "Travelers in past situations have found it helpful to move earlier "
                "rather than later, but please assess your personal safety first."
            )
            steps = [
                "You may want to review available transport options listed below",
                "Consider preparing essential documents (passport, phone, charger)",
                "It might be advisable to monitor official news channels",
                "Some travelers recommend contacting their airline or travel provider",
                "Consider informing your embassy of your presence and plans",
            ]
        else:
            action = "monitor_situation"
            text = (
                "Based on currently available information, there does not appear to be "
                "an immediate threat requiring urgent action. However, conditions can "
                "change quickly. It may be advisable to stay aware of your surroundings "
                "and keep monitoring official sources. Having a general awareness of "
                "nearby transport options could be helpful."
            )
            steps = [
                "Consider staying aware of local news and official channels",
                "You may want to note the nearest transport hubs for your reference",
                "It could be helpful to keep your phone charged and accessible",
            ]

        return {
            "advisory_text": text,
            "action_suggestion": action,
            "priority_steps": steps,
            "confidence": 0.3,  # Low — this is mock data
            "model": "mock-advisory-v1",
        }

    async def health_check(self) -> bool:
        return True
