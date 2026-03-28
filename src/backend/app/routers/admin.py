"""Admin panel API endpoints for insurance risk managers."""

from fastapi import APIRouter, Query

from app.services.admin_service import get_dashboard_stats, get_notification_log

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


@router.get(
    "/dashboard",
    summary="Dashboard metrics for risk managers",
    description="Returns user counts, notification stats, ROI estimates, data source status.",
)
async def admin_dashboard():
    return get_dashboard_stats()


@router.get(
    "/logs",
    summary="Notification log",
    description="Recent notification history: who was notified, what was sent, success/failure.",
)
async def admin_logs(limit: int = Query(50, ge=1, le=500)):
    return get_notification_log(limit)
