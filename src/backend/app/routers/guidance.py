"""AI advisory guidance endpoint.

LEGAL NOTE: Every response from this endpoint MUST include the advisory_meta
field with full disclaimers. This is enforced at the service layer.
"""

from fastapi import APIRouter

from app.models.guidance import GuidanceRequest, GuidanceResponse
from app.providers.factory import get_ai_provider, get_alert_provider, get_transport_provider
from app.services.alert_service import AlertService
from app.services.guidance_service import GuidanceService
from app.services.transport_service import TransportService

router = APIRouter(prefix="/guidance", tags=["AI Advisory Guidance"])


@router.post(
    "/plan",
    response_model=GuidanceResponse,
    summary="Get AI-generated advisory guidance",
    description=(
        "Generates AI-powered advisory guidance based on the user's location, "
        "current alerts, and transport availability.\n\n"
        "**IMPORTANT**: All guidance is ADVISORY ONLY. Responses include "
        "mandatory legal disclaimers. The AI uses suggestion-based language "
        "('you may want to consider') and never gives commands. Always follow "
        "official emergency service instructions."
    ),
)
async def get_guidance(request: GuidanceRequest):
    # Gather context
    alert_service = AlertService(provider=get_alert_provider())
    transport_service = TransportService(provider=get_transport_provider())

    alerts_resp = await alert_service.get_alerts_for_location(
        request.latitude, request.longitude
    )
    transport_resp = await transport_service.get_transport_for_location(
        request.latitude, request.longitude
    )

    # Generate advisory
    guidance_service = GuidanceService(ai_provider=get_ai_provider())
    return await guidance_service.generate_guidance(
        lat=request.latitude,
        lon=request.longitude,
        alerts=alerts_resp.alerts,
        transport=transport_resp.options,
        user_situation=request.situation,
        language=request.language,
        data_sources=alerts_resp.sources + transport_resp.sources,
    )
