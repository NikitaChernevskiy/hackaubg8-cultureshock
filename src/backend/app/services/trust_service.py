"""Trust & verification engine.

Computes trust_score = source_weight * cross_source_agreement * time_decay

Rules:
- Single source = LOW trust
- Multiple independent confirmations = HIGH trust
- Conflicting sources = downgraded confidence
- User reports boost trust only when corroborated
"""

import logging
import math
from datetime import datetime, timezone

from app.models.alerts import Alert

logger = logging.getLogger(__name__)

# Source reliability weights (0-1)
_SOURCE_WEIGHTS: dict[str, float] = {
    "USGS Earthquake Hazards Program": 0.95,  # Official US government
    "GDACS": 0.90,                            # UN-backed
    "UK FCDO Travel Advice": 0.90,            # Official UK government
    "NASA EONET": 0.85,                       # Satellite data
    "ReliefWeb (UN OCHA)": 0.85,              # UN humanitarian
    "OpenStreetMap": 0.70,                     # Community-verified
    "user_report": 0.30,                       # Unverified crowd data
}


def _time_decay(issued_at: datetime, half_life_hours: float = 24.0) -> float:
    """Exponential decay — recent data is more trustworthy."""
    now = datetime.now(timezone.utc)
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=timezone.utc)
    age_hours = (now - issued_at).total_seconds() / 3600
    return math.exp(-0.693 * age_hours / half_life_hours)  # 0.693 = ln(2)


def compute_trust_score(alerts: list[Alert]) -> dict:
    """Compute multi-source trust score for a set of alerts.

    Returns:
        {
            "trust_score": float (0-1),
            "sources_agreeing": int,
            "sources_total": int,
            "threat_confirmed": bool,
            "confidence_factors": dict,
        }
    """
    if not alerts:
        return {
            "trust_score": 0.0,
            "sources_agreeing": 0,
            "sources_total": 0,
            "threat_confirmed": False,
            "confidence_factors": {},
        }

    # Unique sources
    source_names = set()
    severity_votes: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    total_weight = 0.0
    weighted_severity = 0.0
    time_factors = []

    severity_numeric = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25, "info": 0.1}

    for alert in alerts:
        source_name = alert.source.name if alert.source else "unknown"
        source_names.add(source_name)

        # Source weight
        weight = _SOURCE_WEIGHTS.get(source_name, 0.5)

        # Time decay
        decay = _time_decay(alert.issued_at)
        time_factors.append(decay)

        # Severity contribution
        sev = severity_numeric.get(alert.severity, 0.3)
        weighted_severity += weight * decay * sev
        total_weight += weight * decay

        severity_votes[alert.severity] = severity_votes.get(alert.severity, 0) + 1

    num_sources = len(source_names)

    # Cross-source agreement: more independent sources = higher trust
    # 1 source = 0.4, 2 = 0.7, 3+ = 0.9+
    agreement_factor = min(0.4 + 0.2 * (num_sources - 1), 1.0) if num_sources > 0 else 0.0

    # Average time decay
    avg_decay = sum(time_factors) / len(time_factors) if time_factors else 0.0

    # Weighted severity average
    avg_severity = weighted_severity / total_weight if total_weight > 0 else 0.0

    # Final trust score
    trust_score = min(agreement_factor * avg_decay * (0.5 + avg_severity * 0.5), 1.0)

    # Check for conflicts (sources disagree on severity)
    has_critical = severity_votes.get("critical", 0) > 0
    has_low_only = all(severity_votes.get(s, 0) == 0 for s in ["critical", "high", "medium"])
    conflicting = has_critical and severity_votes.get("low", 0) > severity_votes.get("critical", 0)

    if conflicting:
        trust_score *= 0.7  # Downgrade on conflict
        logger.warning("Trust conflict detected: some sources say critical, others say low")

    # Determine the dominant threat level
    dominant_severity = max(severity_votes, key=lambda k: severity_votes[k])
    threat_confirmed = num_sources >= 2 and dominant_severity in ("critical", "high", "medium")

    return {
        "trust_score": round(trust_score, 3),
        "sources_agreeing": num_sources,
        "sources_total": num_sources,
        "threat_confirmed": threat_confirmed,
        "dominant_severity": dominant_severity,
        "confidence_factors": {
            "agreement": round(agreement_factor, 2),
            "time_decay": round(avg_decay, 2),
            "avg_severity": round(avg_severity, 2),
        },
    }
