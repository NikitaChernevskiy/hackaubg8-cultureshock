"""Multi-source alert aggregator — combines all real data providers.

Queries USGS, GDACS, NASA EONET, and ReliefWeb in parallel,
deduplicates results, and returns a unified alert list.
"""

import asyncio
import logging

from app.models.alerts import Alert
from app.models.common import Location
from app.providers.base import AlertProvider
from app.providers.eonet_alerts import EONETAlertProvider
from app.providers.fcdo_alerts import FCDOAlertProvider
from app.providers.meteoalarm_alerts import MeteoalarmProvider
from app.providers.reliefweb_alerts import ReliefWebAlertProvider
from app.providers.usgs_alerts import USGSAlertProvider

logger = logging.getLogger(__name__)


class MultiAlertProvider(AlertProvider):
    """Aggregates alerts from all real data sources in parallel."""

    def __init__(self) -> None:
        self._providers: list[AlertProvider] = [
            USGSAlertProvider(),       # Earthquakes (USGS + GDACS)
            EONETAlertProvider(),      # Wildfires, volcanoes, storms (NASA)
            ReliefWebAlertProvider(),  # Conflicts, humanitarian crises (UN OCHA)
            FCDOAlertProvider(),       # Geopolitical travel advisories (UK gov)
            MeteoalarmProvider(),      # EU severe weather (30+ countries)
        ]

    async def get_alerts(self, location: Location, radius_km: float = 500) -> list[Alert]:
        # Fetch from all providers IN PARALLEL
        tasks = [p.get_alerts(location, radius_km) for p in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_alerts: list[Alert] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                provider_name = type(self._providers[i]).__name__
                logger.error("Provider %s failed: %s", provider_name, result)
                continue
            all_alerts.extend(result)

        # Deduplicate by title similarity (same event from different sources)
        seen_titles: set[str] = set()
        unique_alerts: list[Alert] = []
        for alert in all_alerts:
            # Normalize title for dedup
            key = alert.title.lower().strip()[:60]
            if key not in seen_titles:
                seen_titles.add(key)
                unique_alerts.append(alert)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        unique_alerts.sort(key=lambda a: severity_order.get(a.severity, 5))

        logger.info(
            "Multi-alert: %d total alerts (%d unique) near (%.2f, %.2f)",
            len(all_alerts), len(unique_alerts),
            location.latitude, location.longitude,
        )
        return unique_alerts

    async def health_check(self) -> bool:
        # Healthy if at least one provider works
        tasks = [p.health_check() for p in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return any(r is True for r in results)
