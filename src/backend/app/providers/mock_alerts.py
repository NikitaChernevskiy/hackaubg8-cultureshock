"""Mock alert provider — returns realistic sample data for development."""

from datetime import datetime, timezone

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.providers.base import AlertProvider

_MOCK_SOURCE = DataSource(
    name="MockAlertProvider",
    url=None,
    retrieved_at=datetime.now(timezone.utc),
    reliability="mock",
)


class MockAlertProvider(AlertProvider):
    """Returns canned alerts for testing and demos."""

    async def get_alerts(self, location: Location, radius_km: float = 100) -> list[Alert]:
        now = datetime.now(timezone.utc)
        return [
            Alert(
                id="mock-eq-001",
                type="earthquake",
                severity="high",
                title="Earthquake reported near your area",
                description=(
                    "A magnitude 5.8 earthquake has been reported approximately "
                    "45km from your location. Aftershocks are possible. "
                    "Source: Mock data for demonstration purposes."
                ),
                issued_at=now,
                expires_at=None,
                location=location,
                radius_km=80,
                source=_MOCK_SOURCE,
                official_url="https://earthquake.usgs.gov",
            ),
            Alert(
                id="mock-infra-002",
                type="infrastructure_failure",
                severity="medium",
                title="Partial power outage reported",
                description=(
                    "Reports indicate intermittent power outages in the region. "
                    "Mobile networks may be affected. "
                    "Source: Mock data for demonstration purposes."
                ),
                issued_at=now,
                expires_at=None,
                location=location,
                radius_km=30,
                source=_MOCK_SOURCE,
                official_url=None,
            ),
        ]

    async def health_check(self) -> bool:
        return True
