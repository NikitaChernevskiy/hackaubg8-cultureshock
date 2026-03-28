"""Alert aggregation service."""

from datetime import datetime, timezone

from app.models.alerts import AlertsResponse
from app.models.common import Location
from app.providers.base import AlertProvider


class AlertService:
    """Aggregates alerts from configured providers."""

    def __init__(self, provider: AlertProvider) -> None:
        self._provider = provider

    async def get_alerts_for_location(
        self, lat: float, lon: float, radius_km: float = 100
    ) -> AlertsResponse:
        location = Location(latitude=lat, longitude=lon)
        alerts = await self._provider.get_alerts(location, radius_km)

        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 5))

        sources = list({a.source.name: a.source for a in alerts}.values())

        return AlertsResponse(
            alerts=alerts,
            location=location,
            retrieved_at=datetime.now(timezone.utc),
            sources=sources,
        )
