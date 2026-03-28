"""SDK endpoints — insurance company integration.

POST /sdk/register — register a user for monitoring
POST /sdk/check/{user_id} — manually trigger a check for a user
POST /sdk/check-all — check all registered users (monitoring loop)
POST /sdk/alert — create a manual alert and notify nearby users (demo)
GET /sdk/users — list registered users
"""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.alerts import Alert
from app.models.common import DataSource, Location
from app.models.sdk import SDKRegistration, SDKRegistrationResponse
from app.services.decision_service import make_decision
from app.services.admin_service import log_notification
from app.services.sdk_service import (
    _generate_situation_briefing,
    _users,
    check_all_users,
    check_and_notify_user,
    get_registered_users,
    get_user,
    register_user,
)
from app.services.geo_service import lookup_country
from app.services.notify_service import send_alert_email, send_alert_sms
from app.services.translation_service import translate_instruction


class ManualAlert(BaseModel):
    """Create a manual alert for demo purposes."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    type: str = Field("earthquake", description="earthquake|flood|wildfire|geopolitical|terrorism|other")
    severity: str = Field("critical", description="critical|high|medium|low")
    title: str = Field(..., description="Alert headline")
    description: str = Field("", description="Detailed description")
    radius_km: float = Field(500, description="Notification radius in km")

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
    if not reg.email:
        raise HTTPException(422, "Email is required.")
    if not reg.gdpr_consent:
        raise HTTPException(422, "GDPR consent is required. User must agree to data processing.")
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


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post(
    "/alert",
    summary="Create a manual alert and notify nearby users (demo)",
    description=(
        "Creates a fake disaster at the given coordinates, runs it through "
        "the decision engine, generates an AI situation briefing, and sends "
        "real email/SMS to all registered users within the notification radius."
    ),
)
async def sdk_manual_alert(alert: ManualAlert):
    now = datetime.now(timezone.utc)

    # Build the alert object
    fake_alert = Alert(
        id=f"manual-{now.strftime('%H%M%S')}",
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description or alert.title,
        issued_at=now,
        location=Location(latitude=alert.lat, longitude=alert.lon),
        radius_km=0,
        source=DataSource(name="Manual Alert (Demo)", url="", retrieved_at=now, reliability="simulated"),
        official_url="",
    )

    alerts = [fake_alert]
    location = Location(latitude=alert.lat, longitude=alert.lon)
    country = lookup_country(alert.lat, alert.lon)

    # Run decision engine
    decision = make_decision(alerts=alerts, transport=[], location=location, data_sources=[fake_alert.source])

    # Generate AI situation briefing
    briefing = await _generate_situation_briefing(alerts, country["name"], "en")

    # Find and notify users within radius
    map_base = "https://cultureshock-api.happywater-e6483408.eastus2.azurecontainerapps.io"
    notified = []

    for user in _users.values():
        # Check if user has a destination set
        if user.destination_lat == 0 and user.destination_lon == 0:
            # No destination — notify ALL registered users for demo
            dist = 0
        else:
            dist = _haversine(alert.lat, alert.lon, user.destination_lat, user.destination_lon)
            if dist > alert.radius_km:
                continue

        map_url = f"{map_base}/map?lat={alert.lat}&lon={alert.lon}"
        instruction = decision.instruction

        if user.language and user.language != "en":
            instruction, _ = await translate_instruction(instruction, decision.fallback_instruction, user.language)

        email_ok = False
        sms_ok = False

        if user.email:
            email_ok = await send_alert_email(
                to_email=user.email,
                subject=f"{decision.action.value} — {alert.title}",
                instruction=instruction,
                threat_summary=briefing,
                emergency_number=country["emergency"],
                map_url=map_url,
                country_name=country["name"],
            )

        if user.phone:
            sms_ok = await send_alert_sms(
                to_phone=user.phone,
                instruction=instruction,
                map_url=map_url,
                emergency_number=country["emergency"],
            )

        user.notification_count += 1
        user.last_notified_at = now
        if user.email:
            log_notification(user.user_id, user.email, alert.title, decision.action.value, decision.urgency.value, "email", email_ok, briefing)
        if user.phone:
            log_notification(user.user_id, user.email, alert.title, decision.action.value, decision.urgency.value, "sms", sms_ok)
        notified.append({
            "user_id": user.user_id,
            "email": user.email,
            "distance_km": round(dist),
            "email_sent": email_ok,
            "sms_sent": sms_ok,
        })

    return {
        "alert": alert.title,
        "severity": alert.severity,
        "location": {"lat": alert.lat, "lon": alert.lon, "country": country["name"]},
        "decision": decision.action.value,
        "urgency": decision.urgency.value,
        "briefing": briefing,
        "users_notified": len(notified),
        "notifications": notified,
    }
