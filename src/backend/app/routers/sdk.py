"""SDK endpoints — insurance company integration.

POST /sdk/register — register a user for monitoring
POST /sdk/check/{user_id} — manually trigger a check for a user
POST /sdk/check-all — check all registered users (monitoring loop)
GET /sdk/users — list registered users
"""

from fastapi import APIRouter, HTTPException

from app.models.sdk import SDKRegistration, SDKRegistrationResponse
from app.services.sdk_service import (
    check_all_users,
    check_and_notify_user,
    get_registered_users,
    get_user,
    register_user,
)

router = APIRouter(prefix="/sdk", tags=["SDK (Insurance Integration)"])


@router.post(
    "/register",
    response_model=SDKRegistrationResponse,
    summary="Register a user for threat monitoring",
    description=(
        "Insurance company registers a traveler. The system monitors their "
        "destination 24/7 and sends SMS + email alerts when threats are detected."
    ),
)
async def sdk_register(reg: SDKRegistration):
    if not reg.email and not reg.phone:
        raise HTTPException(422, "At least one of email or phone must be provided.")
    return register_user(reg)


@router.post(
    "/check/{user_id}",
    summary="Manually trigger a threat check for one user",
    description="Checks all 7 data sources for threats near the user's destination and sends notifications if needed.",
)
async def sdk_check_user(user_id: str):
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return await check_and_notify_user(user)


@router.post(
    "/check-all",
    summary="Check all registered users (monitoring loop)",
    description="Scans all registered users for threats. In production this runs on a cron schedule.",
)
async def sdk_check_all():
    return await check_all_users()


@router.get(
    "/users",
    summary="List registered users",
)
async def sdk_list_users():
    users = get_registered_users()
    return [
        {
            "user_id": u.user_id,
            "destination": u.destination_name,
            "lat": u.destination_lat,
            "lon": u.destination_lon,
            "channels": (["email"] if u.email else []) + (["sms"] if u.phone else []),
            "notifications_sent": u.notification_count,
            "registered_at": u.registered_at.isoformat(),
        }
        for u in users
    ]
