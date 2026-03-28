"""Offline data pack endpoint — pre-fetch everything you need."""

from fastapi import APIRouter

from app.models.offline import OfflinePack
from app.services.offline_service import get_offline_pack

router = APIRouter(prefix="/offline", tags=["Offline Packs"])


@router.get(
    "/pack/{country_code}",
    response_model=OfflinePack,
    summary="Download offline data pack for a country",
    description=(
        "Pre-fetch everything needed to function offline: emergency numbers, "
        "embassy info, safe zones, decision rules. Download this while you "
        "still have internet. Target size: < 100KB compressed."
    ),
)
async def download_offline_pack(country_code: str):
    return get_offline_pack(country_code)
