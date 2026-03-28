"""Provider factory — instantiates the right provider based on config.

Swap between mock and real implementations by changing env vars.
"""

from app.config import get_settings
from app.providers.base import AIProvider, AlertProvider, NotificationProvider, TransportProvider


def get_alert_provider() -> AlertProvider:
    """Return the configured alert provider."""
    settings = get_settings()
    if settings.alert_provider == "mock":
        from app.providers.mock_alerts import MockAlertProvider
        return MockAlertProvider()
    if settings.alert_provider in ("usgs", "real"):
        from app.providers.usgs_alerts import USGSAlertProvider
        return USGSAlertProvider()
    raise ValueError(f"Unknown alert provider: {settings.alert_provider}")


def get_transport_provider() -> TransportProvider:
    """Return the configured transport provider."""
    settings = get_settings()
    if settings.transport_provider == "mock":
        from app.providers.mock_transport import MockTransportProvider
        return MockTransportProvider()
    if settings.transport_provider in ("osm", "real"):
        from app.providers.osm_transport import OSMTransportProvider
        return OSMTransportProvider()
    raise ValueError(f"Unknown transport provider: {settings.transport_provider}")


def get_ai_provider() -> AIProvider:
    """Return the configured AI provider."""
    settings = get_settings()
    if settings.ai_provider == "mock":
        from app.providers.mock_ai import MockAIProvider
        return MockAIProvider()
    if settings.ai_provider == "azure_openai":
        from app.providers.azure_openai import AzureOpenAIProvider
        return AzureOpenAIProvider()
    raise ValueError(f"Unknown AI provider: {settings.ai_provider}")


def get_notification_provider() -> NotificationProvider:
    """Return the configured notification provider."""
    settings = get_settings()
    if settings.notification_provider == "mock":
        from app.providers.mock_notifications import MockNotificationProvider
        return MockNotificationProvider()
    if settings.notification_provider == "azure_sms":
        from app.providers.azure_sms import AzureSMSProvider
        return AzureSMSProvider()
    # Future: "firebase", combined providers, etc.
    raise ValueError(f"Unknown notification provider: {settings.notification_provider}")
