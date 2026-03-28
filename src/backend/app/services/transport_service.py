"""Transport status service."""

from datetime import datetime, timezone

from app.models.common import Location
from app.models.transport import TransportResponse
from app.providers.base import TransportProvider


class TransportService:
    """Fetches and ranks transport options near a location."""

    def __init__(self, provider: TransportProvider) -> None:
        self._provider = provider

    async def get_transport_for_location(
        self, lat: float, lon: float
    ) -> TransportResponse:
        location = Location(latitude=lat, longitude=lon)
        options = await self._provider.get_transport_options(location)

        # Sort: operational first, then by distance
        status_order = {"operational": 0, "disrupted": 1, "unknown": 2, "closed": 3}
        options.sort(
            key=lambda t: (status_order.get(t.status, 4), t.distance_km or 9999)
        )

        sources = list({t.source.name: t.source for t in options}.values())

        return TransportResponse(
            options=options,
            location=location,
            retrieved_at=datetime.now(timezone.utc),
            sources=sources,
        )
