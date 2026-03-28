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

    # ROI estimate (simplified)
    # Average insurance claim for travel emergency: ~$5,000
    # If even 1 in 10 alerts prevents a claim, ROI is significant
    estimated_claims_prevented = max(1, successful // 10)
    estimated_savings = estimated_claims_prevented * 5000
    sdk_cost_per_month = 25  # Azure hosting
    roi_percentage = round((estimated_savings / max(1, sdk_cost_per_month)) * 100, 0) if sdk_cost_per_month > 0 else 0

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
        "roi": {
            "estimated_claims_prevented": estimated_claims_prevented,
            "estimated_savings_usd": estimated_savings,
            "platform_cost_usd": sdk_cost_per_month,
            "roi_percentage": roi_percentage,
        },
        "data_sources": {
            "count": 7,
            "sources": ["USGS", "GDACS", "NASA EONET", "UK FCDO", "Meteoalarm", "ReliefWeb", "OpenStreetMap"],
        },
    }


def get_notification_log(limit: int = 50) -> list[dict]:
    """Get recent notification log entries."""
    return list(reversed(_notification_log[-limit:]))
