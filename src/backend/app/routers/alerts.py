"""Alert endpoints."""

from fastapi import APIRouter, Query

from app.models.alerts import AlertsResponse
from app.providers.factory import get_alert_provider
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "/region/{lat}/{lon}",
    response_model=AlertsResponse,
    summary="Get active alerts near a location",
    description=(
        "Returns active emergency alerts within the specified radius of the "
        "given coordinates. Data comes from configured alert providers "
        "(GDACS, USGS, government feeds, etc.)."
    ),
)
async def get_alerts(
    lat: float,
    lon: float,
    radius_km: float = Query(500, ge=1, le=2000, description="Search radius in km"),
):
    service = AlertService(provider=get_alert_provider())
    return await service.get_alerts_for_location(lat, lon, radius_km)
