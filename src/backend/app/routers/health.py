"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.providers.factory import (
    get_ai_provider,
    get_alert_provider,
    get_notification_provider,
    get_transport_provider,
)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Service health check",
    description="Returns service status and provider health.",
)
async def health_check():
    settings = get_settings()

    # Check each provider
    providers_health = {}
    for name, factory in [
        ("alerts", get_alert_provider),
        ("transport", get_transport_provider),
        ("ai", get_ai_provider),
        ("notifications", get_notification_provider),
    ]:
        try:
            provider = factory()
            healthy = await provider.health_check()
            providers_health[name] = "healthy" if healthy else "unhealthy"
        except Exception as e:
            providers_health[name] = f"error: {e}"

    all_healthy = all(v == "healthy" for v in providers_health.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": providers_health,
    }
