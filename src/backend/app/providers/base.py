"""Abstract base classes for all external data providers.

Each provider type defines a minimal interface. Implementations can be
mock (for development/hackathon) or real (GDACS, Azure OpenAI, etc.).
Swap providers via the config `*_provider` settings.
"""

from abc import ABC, abstractmethod

from app.models.alerts import Alert
from app.models.common import Location
from app.models.transport import TransportOption


class AlertProvider(ABC):
    """Fetches emergency alerts for a geographic area."""

    @abstractmethod
    async def get_alerts(self, location: Location, radius_km: float = 100) -> list[Alert]:
        """Return active alerts near the given location."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""


class TransportProvider(ABC):
    """Fetches transport availability near a location."""

    @abstractmethod
    async def get_transport_options(self, location: Location) -> list[TransportOption]:
        """Return transport options near the given location."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""


class AIProvider(ABC):
    """Generates advisory text from structured emergency data.

    Implementations MUST enforce advisory-only language (no commands).
    """

    @abstractmethod
    async def generate_guidance(
        self,
        location: Location,
        alerts: list[Alert],
        transport: list[TransportOption],
        user_situation: str = "",
        language: str = "en",
    ) -> dict:
        """Generate advisory guidance text.

        Returns a dict with keys:
        - advisory_text: str — AI-generated advisory
        - action_suggestion: str — high-level suggested action
        - priority_steps: list[str] — ordered considerations
        - confidence: float — 0-1 based on data quality
        - model: str — which model produced this
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""


class NotificationProvider(ABC):
    """Sends notifications via push and/or SMS."""

    @abstractmethod
    async def send_push(self, device_token: str, title: str, body: str, data: dict | None = None) -> bool:
        """Send a push notification. Returns True on success."""

    @abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send an SMS. Returns True on success."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
