"""Emergency bundle assembler — the critical single-request endpoint.

Orchestrates all providers in parallel, assembles the survival pack,
and ensures every response carries mandatory disclaimers.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.constants import ADVISORY_DISCLAIMER, DATA_FRESHNESS_WARNING, MEDICAL_DISCLAIMER
from app.models.common import AdvisoryMeta, Location
from app.models.emergency import EmergencyBundleResponse
from app.providers.base import AIProvider, AlertProvider, TransportProvider

logger = logging.getLogger(__name__)


class EmergencyService:
    """Assembles the complete emergency bundle in a single call."""

    def __init__(
        self,
        alert_provider: AlertProvider,
        transport_provider: TransportProvider,
        ai_provider: AIProvider,
    ) -> None:
        self._alerts = alert_provider
        self._transport = transport_provider
        self._ai = ai_provider

    async def get_emergency_bundle(
        self,
        lat: float,
        lon: float,
        language: str = "en",
    ) -> EmergencyBundleResponse:
        location = Location(latitude=lat, longitude=lon)
        now = datetime.now(timezone.utc)

        # Fetch alerts and transport IN PARALLEL — speed is critical
        alerts_task = self._alerts.get_alerts(location, radius_km=100)
        transport_task = self._transport.get_transport_options(location)

        alerts, transport = await asyncio.gather(
            alerts_task, transport_task, return_exceptions=True
        )

        # Handle failures gracefully — partial data is better than no data
        if isinstance(alerts, Exception):
            logger.error("Alert provider failed: %s", alerts)
            alerts = []
        if isinstance(transport, Exception):
            logger.error("Transport provider failed: %s", transport)
            transport = []

        # Generate AI advisory using real detected data
        ai_result = await self._ai.generate_guidance(
            location=location,
            alerts=alerts,
            transport=transport,
            language=language,
        )

        # Determine overall threat level from alerts
        threat_level = self._calculate_threat_level(alerts)

        # Collect all data sources
        all_sources = []
        for a in alerts:
            if a.source not in all_sources:
                all_sources.append(a.source)
        for t in transport:
            if t.source not in all_sources:
                all_sources.append(t.source)

        # Build mandatory advisory metadata
        advisory_meta = AdvisoryMeta(
            disclaimer=ADVISORY_DISCLAIMER,
            medical_disclaimer=MEDICAL_DISCLAIMER,
            data_freshness_warning=DATA_FRESHNESS_WARNING,
            generated_at=now,
            data_sources=all_sources,
            ai_model=ai_result.get("model", "unknown"),
            confidence=ai_result.get("confidence", 0.0),
        )

        bundle = EmergencyBundleResponse(
            # Critical — must arrive first
            threat_level=threat_level,
            action_suggestion=ai_result.get("action_suggestion", "monitor_situation"),
            advisory_text=ai_result.get("advisory_text", ""),
            local_emergency_number="112",  # Default international
            # High priority
            priority_steps=ai_result.get("priority_steps", []),
            alerts=alerts,
            # Useful
            transport=transport,
            embassy_info="",
            # Metadata
            location=location,
            advisory_meta=advisory_meta,
            bundle_generated_at=now,
            data_sources=all_sources,
        )

        # Audit log
        logger.info(
            "EMERGENCY_BUNDLE | lat=%.4f lon=%.4f | threat=%s | action=%s | "
            "alerts=%d | transport=%d | confidence=%.2f",
            lat,
            lon,
            threat_level,
            bundle.action_suggestion,
            len(alerts),
            len(transport),
            advisory_meta.confidence,
        )

        return bundle

    @staticmethod
    def _calculate_threat_level(alerts: list) -> str:
        """Determine overall threat from alert severities."""
        if not alerts:
            return "none"
        severities = {a.severity for a in alerts}
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        if "low" in severities:
            return "low"
        return "none"
