"""User reports endpoint — crowd-sourced ground truth."""

from fastapi import APIRouter, Query

from app.models.reports import ReportStats, UserReport, UserReportResponse
from app.services.report_service import get_area_stats, submit_report

router = APIRouter(prefix="/reports", tags=["User Reports"])


@router.post(
    "",
    response_model=UserReportResponse,
    summary="Submit a user report",
    description=(
        "Submit a ground-level incident report. Reports are rate-limited "
        "and trust-scored. Single reports have LOW trust; multiple "
        "independent confirmations raise trust."
    ),
)
async def post_report(report: UserReport):
    return submit_report(report)


@router.get(
    "/stats/{lat}/{lon}",
    response_model=ReportStats,
    summary="Get report statistics for an area",
)
async def get_stats(
    lat: float,
    lon: float,
    radius_km: float = Query(50, ge=1, le=500),
):
    return get_area_stats(lat, lon, radius_km)
