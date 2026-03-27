"""Mock transport provider — returns sample transport options."""

from datetime import datetime, timezone

from app.models.common import DataSource, Location
from app.models.transport import TransportOption
from app.providers.base import TransportProvider

_MOCK_SOURCE = DataSource(
    name="MockTransportProvider",
    url=None,
    retrieved_at=datetime.now(timezone.utc),
    reliability="mock",
)


class MockTransportProvider(TransportProvider):
    """Returns canned transport options for testing and demos."""

    async def get_transport_options(self, location: Location) -> list[TransportOption]:
        now = datetime.now(timezone.utc)
        return [
            TransportOption(
                id="mock-airport-001",
                type="airport",
                name="International Airport",
                location=Location(
                    latitude=location.latitude + 0.15,
                    longitude=location.longitude + 0.10,
                ),
                status="disrupted",
                status_detail=(
                    "Limited operations — some flights delayed or cancelled. "
                    "Check with your airline. (Mock data)"
                ),
                distance_km=18.5,
                estimated_travel_minutes=35,
                source=_MOCK_SOURCE,
                last_updated=now,
            ),
            TransportOption(
                id="mock-train-001",
                type="train_station",
                name="Central Railway Station",
                location=Location(
                    latitude=location.latitude + 0.02,
                    longitude=location.longitude - 0.03,
                ),
                status="operational",
                status_detail="Services running with minor delays. (Mock data)",
                distance_km=3.2,
                estimated_travel_minutes=12,
                source=_MOCK_SOURCE,
                last_updated=now,
            ),
            TransportOption(
                id="mock-bus-001",
                type="bus_station",
                name="Central Bus Terminal",
                location=Location(
                    latitude=location.latitude - 0.01,
                    longitude=location.longitude + 0.02,
                ),
                status="operational",
                status_detail="Intercity buses operating normally. (Mock data)",
                distance_km=2.1,
                estimated_travel_minutes=8,
                source=_MOCK_SOURCE,
                last_updated=now,
            ),
        ]

    async def health_check(self) -> bool:
        return True
