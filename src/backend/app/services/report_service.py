"""User reporting service — crowd-sourced ground truth with anti-abuse."""

import logging
import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.models.reports import ReportStats, UserReport, UserReportResponse

logger = logging.getLogger(__name__)

# In-memory store (swap for Cosmos DB in production)
_reports: list[dict] = []
_device_rate: dict[str, list[datetime]] = defaultdict(list)

# Rate limiting: max 5 reports per device per hour
_MAX_REPORTS_PER_HOUR = 5
_RATE_WINDOW_SECONDS = 3600


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _check_rate_limit(device_id: str) -> bool:
    """Return True if device is within rate limits."""
    if not device_id:
        return True  # Anonymous — allow but low trust
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - _RATE_WINDOW_SECONDS
    # Clean old entries
    _device_rate[device_id] = [
        t for t in _device_rate[device_id] if t.timestamp() > cutoff
    ]
    return len(_device_rate[device_id]) < _MAX_REPORTS_PER_HOUR


def submit_report(report: UserReport) -> UserReportResponse:
    """Submit a user report with rate limiting."""
    now = datetime.now(timezone.utc)

    # Rate limit check
    if not _check_rate_limit(report.device_id):
        logger.warning("Rate limit exceeded for device %s", report.device_id[:12])
        return UserReportResponse(
            report_id="",
            accepted=False,
            trust_contribution=0,
            reports_in_area=0,
            submitted_at=now,
        )

    # Record rate
    if report.device_id:
        _device_rate[report.device_id].append(now)

    report_id = str(uuid.uuid4())[:12]

    # Store report
    entry = {
        "id": report_id,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "type": report.report_type,
        "description": report.description,
        "severity": report.severity_estimate,
        "device_id": report.device_id,
        "submitted_at": now,
    }
    _reports.append(entry)

    # Count nearby reports (within 50km, last 24h)
    cutoff_24h = now.timestamp() - 86400
    nearby = sum(
        1 for r in _reports
        if r["submitted_at"].timestamp() > cutoff_24h
        and _haversine_km(report.latitude, report.longitude, r["latitude"], r["longitude"]) < 50
    )

    # Trust contribution: single report = low, corroborated = higher
    trust_contribution = min(0.1 * nearby, 0.5)  # Max 0.5 from user reports

    logger.info(
        "USER_REPORT | id=%s | type=%s | lat=%.4f lon=%.4f | nearby=%d | trust=%.2f",
        report_id, report.report_type,
        report.latitude, report.longitude,
        nearby, trust_contribution,
    )

    return UserReportResponse(
        report_id=report_id,
        accepted=True,
        trust_contribution=round(trust_contribution, 2),
        reports_in_area=nearby,
        submitted_at=now,
    )


def get_area_stats(lat: float, lon: float, radius_km: float = 50) -> ReportStats:
    """Get report statistics for an area."""
    now = datetime.now(timezone.utc)
    cutoff_24h = now.timestamp() - 86400
    cutoff_1h = now.timestamp() - 3600

    nearby_24h = [
        r for r in _reports
        if r["submitted_at"].timestamp() > cutoff_24h
        and _haversine_km(lat, lon, r["latitude"], r["longitude"]) < radius_km
    ]
    nearby_1h = [r for r in nearby_24h if r["submitted_at"].timestamp() > cutoff_1h]

    # Dominant type
    type_counts: dict[str, int] = defaultdict(int)
    for r in nearby_24h:
        type_counts[r["type"]] += 1
    dominant = max(type_counts, key=type_counts.get) if type_counts else ""

    # Average severity
    sev_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
    sevs = [sev_map.get(r["severity"], 0) for r in nearby_24h if r["severity"] != "unknown"]
    avg_sev_num = sum(sevs) / len(sevs) if sevs else 0
    avg_sev = "low"
    if avg_sev_num >= 3.5:
        avg_sev = "critical"
    elif avg_sev_num >= 2.5:
        avg_sev = "high"
    elif avg_sev_num >= 1.5:
        avg_sev = "medium"

    # Trust based on volume
    trust = min(len(nearby_24h) * 0.1, 0.8)

    return ReportStats(
        total_reports_24h=len(nearby_24h),
        total_reports_1h=len(nearby_1h),
        dominant_type=dominant,
        avg_severity=avg_sev,
        trust_score=round(trust, 2),
    )
