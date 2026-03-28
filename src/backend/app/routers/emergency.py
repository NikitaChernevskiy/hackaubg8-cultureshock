"""Emergency bundle endpoint — the critical single-request survival pack.

This is the most important endpoint in the entire API. It returns
everything the app needs in a single compressed response, designed for
scenarios where the user may have only seconds of connectivity remaining.

LEGAL NOTE: Response always includes mandatory advisory_meta with disclaimers.
"""

from fastapi import APIRouter

from app.models.emergency import EmergencyBundleRequest, EmergencyBundleResponse
from app.providers.factory import get_ai_provider, get_alert_provider, get_transport_provider
from app.services.emergency_service import EmergencyService

router = APIRouter(prefix="/emergency", tags=["Emergency Bundle"])


@router.post(
    "/bundle",
    response_model=EmergencyBundleResponse,
    summary="Get complete emergency survival pack",
    description=(
        "**THE CRITICAL ENDPOINT.** Returns everything the app needs in a "
        "single response: threat assessment, AI advisory guidance, active "
        "alerts, transport options, emergency contacts — all in one call.\n\n"
        "Designed for last-second connectivity scenarios. Fields are ordered "
        "by priority: threat level and action suggestion come first so the "
        "most critical info arrives even if the connection drops.\n\n"
        "**Target response size: < 50KB compressed.**\n\n"
        "**IMPORTANT**: All advisory content is for INFORMATIONAL purposes "
        "only. See advisory_meta.disclaimer in the response."
    ),
)
async def get_emergency_bundle(request: EmergencyBundleRequest):
    service = EmergencyService(
        alert_provider=get_alert_provider(),
        transport_provider=get_transport_provider(),
        ai_provider=get_ai_provider(),
    )
    return await service.get_emergency_bundle(
        lat=request.latitude,
        lon=request.longitude,
        language=request.language,
    )
