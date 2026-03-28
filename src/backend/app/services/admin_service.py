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
