"""Decision engine endpoint — ONE instruction, no ambiguity.

This is the primary endpoint for the app. It replaces the old
emergency bundle with a deterministic decision.
"""

import asyncio

from fastapi import APIRouter

from app.models.common import Location
from app.models.decision import DecisionRequest, DecisionResponse
from app.providers.factory import get_ai_provider, get_alert_provider, get_transport_provider
from app.services.decision_service import make_decision

router = APIRouter(prefix="/decision", tags=["Decision Engine"])


@router.post(
    "",
    response_model=DecisionResponse,
    summary="Get ONE deterministic instruction",
    description=(
        "**THE core endpoint.** Aggregates all data sources, computes trust "
        "scores, and returns exactly ONE instruction: SHELTER, STAY, MOVE, "
        "EVACUATE, or MONITOR.\n\n"
        "The user should understand what to do in ≤2 seconds.\n\n"
        "AI is NOT the decision maker — a deterministic rule engine makes "
        "the final call based on trust-weighted multi-source data."
    ),
)
async def get_decision(request: DecisionRequest):
    location = Location(latitude=request.latitude, longitude=request.longitude)

    # Fetch data in parallel
    alert_provider = get_alert_provider()
    transport_provider = get_transport_provider()

    alerts_task = alert_provider.get_alerts(location, radius_km=500)
    transport_task = transport_provider.get_transport_options(location)

    alerts, transport = await asyncio.gather(
        alerts_task, transport_task, return_exceptions=True
    )

    if isinstance(alerts, Exception):
        alerts = []
    if isinstance(transport, Exception):
        transport = []

    # Collect sources
    sources = list({a.source.name: a.source for a in alerts}.values())
    sources += list({t.source.name: t.source for t in transport}.values())

    return make_decision(
        alerts=alerts,
        transport=transport,
        location=location,
        data_sources=sources,
    )
