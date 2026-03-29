"""Admin service — metrics, logs, ROI for insurance risk managers."""

from datetime import datetime, timezone
from collections import defaultdict

# Notification log (in-memory, Cosmos DB in production)
_notification_log: list[dict] = []


def log_notification(
    user_id: str,
    email: str,
    alert_title: str,
    decision: str,
    urgency: str,
    channel: str,
    success: bool,
    briefing: str = "",
) -> None:
    """Record a notification in the admin log."""
    _notification_log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "email": email,
        "alert_title": alert_title,
        "decision": decision,
        "urgency": urgency,
        "channel": channel,
        "success": success,
        "briefing": briefing[:200],
    })


def get_dashboard_stats() -> dict:
    """Get admin dashboard statistics."""
    from app.services.sdk_service import _users

    now = datetime.now(timezone.utc)
    total_users = len(_users)
    total_notifications = len(_notification_log)
    successful = sum(1 for n in _notification_log if n["success"])
    failed = total_notifications - successful

    # Channel breakdown
    channels = defaultdict(int)
    for n in _notification_log:
        channels[n["channel"]] += 1

    # Urgency breakdown
    urgencies = defaultdict(int)
    for n in _notification_log:
        urgencies[n["urgency"]] += 1

    # Users with notifications
    notified_users = len(set(n["user_id"] for n in _notification_log))

    # Cost tracking (real, not estimated)
    # Platform: ~$25/mo Azure hosting + ~$0.01/email + ~$0.08/SMS
    platform_cost_monthly = 25.0
    email_cost = channels.get("email", 0) * 0.01  # Azure Comm Services
    sms_cost = channels.get("sms", 0) * 0.08      # Twilio
    total_cost = round(platform_cost_monthly + email_cost + sms_cost, 2)
    cost_per_user = round(total_cost / max(1, total_users), 2)
    cost_per_notification = round((email_cost + sms_cost) / max(1, total_notifications), 4)

    return {
        "timestamp": now.isoformat(),
        "users": {
            "total_registered": total_users,
            "with_email": sum(1 for u in _users.values() if u.email),
            "with_phone": sum(1 for u in _users.values() if u.phone),
            "notified_at_least_once": notified_users,
        },
        "notifications": {
            "total_sent": total_notifications,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / max(1, total_notifications) * 100, 1),
            "by_channel": dict(channels),
            "by_urgency": dict(urgencies),
        },
        "costs": {
            "platform_monthly_usd": platform_cost_monthly,
            "email_cost_usd": round(email_cost, 2),
            "sms_cost_usd": round(sms_cost, 2),
            "total_cost_usd": total_cost,
            "cost_per_user_usd": cost_per_user,
            "cost_per_notification_usd": cost_per_notification,
            "note": "Platform: Azure Container App + OpenAI. Email: $0.01/msg. SMS: $0.08/msg.",
        },
        "data_sources": {
            "count": 7,
            "sources": ["USGS", "GDACS", "NASA EONET", "UK FCDO", "Meteoalarm", "ReliefWeb", "OpenStreetMap"],
            "note": "All free, no API keys. Government and UN sources.",
        },
    }


def get_notification_log(limit: int = 50) -> list[dict]:
    """Get recent notification log entries."""
    return list(reversed(_notification_log[-limit:]))


def seed_demo_data() -> dict:
    """Populate admin panel with realistic demo data for presentations."""
    from datetime import timedelta
    from app.models.sdk import RegisteredUser
    from app.services.sdk_service import _users

    now = datetime.now(timezone.utc)

    # --- Seed demo users ---
    demo_users = [
        ("demo-001", "anna.mueller@allianz.de", "+4917612345678", 37.22, 37.01, "Kahramanmaraş, Turkey", "de", "allianz-de"),
        ("demo-002", "james.smith@mondialcare.co.uk", "+447911123456", 24.45, 54.65, "Abu Dhabi, UAE", "en", "mondial-care"),
        ("demo-003", "sofia.ivanova@euroins.bg", "+359888765432", 39.47, -0.38, "Valencia, Spain", "bg", "euroins-bg"),
        ("demo-004", "tanaka.yuki@tokio-marine.jp", "+818012345678", 37.50, 137.24, "Ishikawa, Japan", "ja", "tokio-marine"),
        ("demo-005", "carlos.garcia@mapfre.es", "+34612345678", 32.09, 34.78, "Tel Aviv, Israel", "es", "mapfre-es"),
        ("demo-006", "marie.dupont@axa.fr", "+33612345678", 41.01, 28.98, "Istanbul, Turkey", "fr", "axa-fr"),
    ]

    for uid, email, phone, lat, lon, dest, lang, partner in demo_users:
        if uid not in _users:
            _users[uid] = RegisteredUser(
                user_id=uid, email=email, phone=phone,
                destination_lat=lat, destination_lon=lon,
                destination_name=dest, language=lang, partner_id=partner,
                registered_at=now - timedelta(hours=12),
                notification_count=0,
            )

    # --- Seed demo notification log ---
    demo_logs = [
        (now - timedelta(minutes=45), "demo-001", "anna.mueller@allianz.de", "M7.8 Earthquake — Kahramanmaraş, Turkey", "SHELTER", "HIGH", "email", True,
         "A magnitude 7.8 earthquake struck near your destination. Take cover immediately."),
        (now - timedelta(minutes=44), "demo-001", "anna.mueller@allianz.de", "M7.8 Earthquake — Kahramanmaraş, Turkey", "SHELTER", "HIGH", "sms", True, ""),
        (now - timedelta(minutes=30), "demo-002", "james.smith@mondialcare.co.uk", "Drone strike on ADNOC depot — Abu Dhabi", "EVACUATE", "HIGH", "email", True,
         "Houthi drone strike on ADNOC fuel depot. Missiles intercepted near airport. Consider departing via Dubai."),
        (now - timedelta(minutes=29), "demo-002", "james.smith@mondialcare.co.uk", "Drone strike on ADNOC depot — Abu Dhabi", "EVACUATE", "HIGH", "sms", True, ""),
        (now - timedelta(minutes=20), "demo-003", "sofia.ivanova@euroins.bg", "DANA extreme rainfall — Valencia", "STAY", "HIGH", "email", True,
         "400mm of rain in 8 hours. Flash flooding across Valencia. Do not attempt to drive."),
        (now - timedelta(minutes=19), "demo-003", "sofia.ivanova@euroins.bg", "DANA extreme rainfall — Valencia", "STAY", "HIGH", "sms", False, ""),
        (now - timedelta(minutes=15), "demo-004", "tanaka.yuki@tokio-marine.jp", "M7.5 Earthquake — Noto Peninsula", "SHELTER", "HIGH", "email", True,
         "Major earthquake and tsunami warning on the Sea of Japan coast. Move to high ground."),
        (now - timedelta(minutes=14), "demo-004", "tanaka.yuki@tokio-marine.jp", "Tsunami Warning — Sea of Japan", "SHELTER", "HIGH", "sms", True, ""),
        (now - timedelta(minutes=10), "demo-005", "carlos.garcia@mapfre.es", "FCDO advises against ALL travel — Israel", "EVACUATE", "HIGH", "email", True,
         "Large-scale security incident. Ben Gurion Airport closed. Consider Haifa Port to Cyprus."),
        (now - timedelta(minutes=5), "demo-006", "marie.dupont@axa.fr", "M4.2 Earthquake near Istanbul", "MONITOR", "MEDIUM", "email", True,
         "Minor earthquake detected 80km from Istanbul. No immediate danger but stay alert."),
    ]

    _notification_log.clear()
    for ts, uid, email, title, action, urgency, channel, success, briefing in demo_logs:
        _notification_log.append({
            "timestamp": ts.isoformat(),
            "user_id": uid,
            "email": email,
            "alert_title": title,
            "decision": action,
            "urgency": urgency,
            "channel": channel,
            "success": success,
            "briefing": briefing[:200],
        })

    # Update user notification counts
    for uid in _users:
        count = sum(1 for l in _notification_log if l["user_id"] == uid)
        _users[uid].notification_count = count
        if count:
            _users[uid].last_notified_at = now

    return {"seeded_users": len(demo_users), "seeded_notifications": len(demo_logs)}
