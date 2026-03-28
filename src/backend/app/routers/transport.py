"""Transport status endpoints."""

from fastapi import APIRouter

from app.models.transport import TransportResponse
from app.providers.factory import get_transport_provider
from app.services.transport_service import TransportService

router = APIRouter(prefix="/transport", tags=["Transport"])


@router.get(
    "/status/{lat}/{lon}",
    response_model=TransportResponse,
    summary="Get transport options near a location",
    description=(
        "Returns available transport options (airports, train stations, bus "
        "terminals, etc.) near the given coordinates, sorted by operational "
        "status and distance."
    ),
)
async def get_transport_status(lat: float, lon: float):
    service = TransportService(provider=get_transport_provider())
    return await service.get_transport_for_location(lat, lon)
