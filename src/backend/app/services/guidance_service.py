"""AI guidance service — the legal-safeguard layer.

This service:
1. Gathers context (alerts + transport)
2. Calls the AI provider with structured data
3. Wraps EVERY response with mandatory disclaimers
4. Logs what advice was given (audit trail)
"""

import logging
from datetime import datetime, timezone

from app.constants import ADVISORY_DISCLAIMER, DATA_FRESHNESS_WARNING, MEDICAL_DISCLAIMER
from app.models.alerts import Alert
from app.models.common import AdvisoryMeta, DataSource, Location
from app.models.guidance import GuidanceResponse
from app.models.transport import TransportOption
from app.providers.base import AIProvider

logger = logging.getLogger(__name__)

# Emergency numbers by country code (extend as needed)
_EMERGENCY_NUMBERS: dict[str, str] = {
    "US": "911",
    "GB": "999 or 112",
    "EU": "112",
    "BG": "112",
    "TR": "112",
    "JP": "110 (police) / 119 (fire/ambulance)",
    "IN": "112",
    "AU": "000",
    "NZ": "111",
    "DEFAULT": "112 (international emergency number)",
}


class GuidanceService:
    """Generates AI advisory guidance with mandatory legal safeguards."""

    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai = ai_provider

    async def generate_guidance(
        self,
        lat: float,
        lon: float,
        alerts: list[Alert],
        transport: list[TransportOption],
        language: str = "en",
        data_sources: list[DataSource] | None = None,
    ) -> GuidanceResponse:
        location = Location(latitude=lat, longitude=lon)
        now = datetime.now(timezone.utc)

        # Call AI provider
        result = await self._ai.generate_guidance(
            location=location,
            alerts=alerts,
            transport=transport,
            language=language,
        )

        # Look up emergency number
        country = location.country or "DEFAULT"
        emergency_number = _EMERGENCY_NUMBERS.get(
            country, _EMERGENCY_NUMBERS["DEFAULT"]
        )

        # Build mandatory advisory metadata
        advisory_meta = AdvisoryMeta(
            disclaimer=ADVISORY_DISCLAIMER,
            medical_disclaimer=MEDICAL_DISCLAIMER,
            data_freshness_warning=DATA_FRESHNESS_WARNING,
            generated_at=now,
            data_sources=data_sources or [],
            ai_model=result.get("model", "unknown"),
            confidence=result.get("confidence", 0.0),
        )

        response = GuidanceResponse(
            action_suggestion=result.get("action_suggestion", "monitor_situation"),
            advisory_text=result.get("advisory_text", ""),
            priority_steps=result.get("priority_steps", []),
            local_emergency_number=emergency_number,
            embassy_info="",  # Future: embassy lookup by country
            location=location,
            advisory_meta=advisory_meta,
            generated_at=now,
        )

        # Audit log — record what advice was given
        logger.info(
            "ADVISORY_AUDIT | lat=%.4f lon=%.4f | action=%s | confidence=%.2f | "
            "model=%s | alerts=%d | transport=%d",
            lat,
            lon,
            response.action_suggestion,
            advisory_meta.confidence,
            advisory_meta.ai_model,
            len(alerts),
            len(transport),
        )

        return response
