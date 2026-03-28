"""SDK service — registration + monitoring + notification dispatch."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.models.common import Location
from app.models.sdk import RegisteredUser, SDKRegistration, SDKRegistrationResponse
from app.providers.factory import get_alert_provider, get_transport_provider
from app.services.decision_service import make_decision
from app.services.geo_service import lookup_country
from app.services.notify_service import send_alert_email, send_alert_sms
from app.services.translation_service import translate_instruction

logger = logging.getLogger(__name__)


async def _generate_situation_briefing(alerts: list, destination: str, language: str) -> str:
    """Generate a situation-specific briefing via Azure OpenAI.

    Called ONCE per new threat detection — not per user.
    Returns a concise, actionable briefing about what's happening.
    """
    from app.config import get_settings
    settings = get_settings()
    if not settings.azure_openai_endpoint or settings.ai_provider == "mock":
        # Fallback: build from alert titles
        titles = [a.title for a in alerts[:5]]
        return ". ".join(titles) + "."

    try:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

        alert_data = "\n".join(
            f"- [{a.severity.upper()}] {a.title}: {a.description[:150]}"
            for a in alerts[:8]
        )

        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": (
                    "You are an emergency briefing system for travelers. Write a SHORT, "
                    "specific situation report (3-4 sentences max) about what is happening "
                    "near the user's destination. Include: what happened, how close, "
                    "what might happen next, and what the user should do RIGHT NOW. "
                    "Use advisory language ('consider', 'you may want to'). "
                    f"Write in {language if language != 'en' else 'English'}."
                )},
                {"role": "user", "content": (
                    f"Destination: {destination}\n\nActive threats:\n{alert_data}"
                )},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        return response.choices[0].message.content or ""
    except Exception:
        logger.exception("Failed to generate situation briefing")
        titles = [a.title for a in alerts[:3]]
        return ". ".join(titles) + "."

# In-memory user registry (Cosmos DB in production)
_users: dict[str, RegisteredUser] = {}

# Base URL for map links
_MAP_BASE = "https://cultureshock-api.happywater-e6483408.eastus2.azurecontainerapps.io"


def register_user(reg: SDKRegistration) -> SDKRegistrationResponse:
    """Register a user for monitoring."""
    user_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc)

    user = RegisteredUser(
        user_id=user_id,
        phone=reg.phone,
        email=reg.email,
        destination_lat=reg.destination_lat,
        destination_lon=reg.destination_lon,
        destination_name=reg.destination_name,
        language=reg.language,
        partner_id=reg.partner_id,
        registered_at=now,
    )
    _users[user_id] = user

    channels = []
    if reg.email:
        channels.append("email")
    if reg.phone:
        channels.append("sms")

    logger.info(
        "SDK_REGISTER | user=%s | dest=%s (%.2f,%.2f) | channels=%s | partner=%s",
        user_id, reg.destination_name, reg.destination_lat, reg.destination_lon,
        channels, reg.partner_id,
    )

    return SDKRegistrationResponse(
        user_id=user_id,
        registered=True,
        channels=channels,
        monitoring_active=True,
        registered_at=now,
    )


def get_registered_users() -> list[RegisteredUser]:
    """Get all registered users."""
    return list(_users.values())


def get_user(user_id: str) -> RegisteredUser | None:
    """Get a specific user."""
    return _users.get(user_id)


async def check_and_notify_user(user: RegisteredUser) -> dict:
    """Check threats for a user and send notifications if needed.

    Returns a summary of what was detected and sent.
    """
    location = Location(latitude=user.destination_lat, longitude=user.destination_lon)

    # Fetch alerts + transport
    alert_provider = get_alert_provider()
    transport_provider = get_transport_provider()

    alerts_result, transport_result = await asyncio.gather(
        alert_provider.get_alerts(location, radius_km=500),
        transport_provider.get_transport_options(location),
        return_exceptions=True,
    )

    alerts = alerts_result if not isinstance(alerts_result, Exception) else []
    transport = transport_result if not isinstance(transport_result, Exception) else []

    # Run decision engine
    sources = list({a.source.name: a.source for a in alerts}.values())
    decision = make_decision(alerts=alerts, transport=transport, location=location, data_sources=sources)

    # Only notify if there's an actual threat (not MONITOR/LOW)
    should_notify = decision.action.value != "MONITOR" or decision.urgency.value != "LOW"

    # Don't spam: check if we already notified recently (within 1 hour)
    now = datetime.now(timezone.utc)
    if user.last_notified_at:
        minutes_since = (now - user.last_notified_at).total_seconds() / 60
        if minutes_since < 60 and not (decision.urgency.value == "HIGH"):
            should_notify = False

    result = {
        "user_id": user.user_id,
        "destination": user.destination_name,
        "action": decision.action.value,
        "urgency": decision.urgency.value,
        "instruction": decision.instruction,
        "threats_found": len(alerts),
        "should_notify": should_notify,
        "email_sent": False,
        "sms_sent": False,
    }

    if not should_notify:
        return result

    # Generate situation-specific briefing via OpenAI (NOT the generic decision text)
    situation_briefing = await _generate_situation_briefing(
        alerts, user.destination_name, user.language,
    )

    # The instruction is the decision engine's action, briefing is the context
    instruction = decision.instruction
    if user.language and user.language != "en":
        instruction, _ = await translate_instruction(
            instruction, decision.fallback_instruction, user.language,
        )

    # Build map URL
    map_url = f"{_MAP_BASE}/map?lat={user.destination_lat}&lon={user.destination_lon}"

    # Country info for emergency number
    country = lookup_country(user.destination_lat, user.destination_lon)

    # Send email with situation-specific briefing
    if user.email:
        result["email_sent"] = await send_alert_email(
            to_email=user.email,
            subject=f"{decision.action.value} — {user.destination_name or country['name']}",
            instruction=instruction,
            threat_summary=situation_briefing,
            emergency_number=decision.local_emergency_number,
            map_url=map_url,
            country_name=user.destination_name or country["name"],
        )

    # Send SMS
    if user.phone:
        result["sms_sent"] = await send_alert_sms(
            to_phone=user.phone,
            instruction=instruction,
            map_url=map_url,
            emergency_number=decision.local_emergency_number,
        )

    # Update user record
    user.last_notified_at = now
    user.notification_count += 1

    logger.info(
        "SDK_NOTIFY | user=%s | action=%s | email=%s | sms=%s | threats=%d",
        user.user_id, decision.action.value,
        result["email_sent"], result["sms_sent"], len(alerts),
    )

    return result


async def check_all_users() -> list[dict]:
    """Check all registered users for threats. Called by the monitoring loop."""
    results = []
    for user in _users.values():
        try:
            r = await check_and_notify_user(user)
            results.append(r)
        except Exception:
            logger.exception("Failed to check user %s", user.user_id)
    return results
