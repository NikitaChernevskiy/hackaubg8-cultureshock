"""Decision engine — THE core logic.

RULE: AI interprets, deterministic rules decide.

Decision tree:
  IF immediate lethal threat → SHELTER
  ELSE IF mobility unsafe    → STAY
  ELSE IF exit viable        → MOVE toward exit
  ELSE                       → MONITOR / reposition

Phase system:
  Phase 1: SURVIVE   (0-5 min)  → shelter, drop/cover
  Phase 2: STABILIZE (5-60 min) → assess, secure, communicate
  Phase 3: EVALUATE  (1-24h)    → plan next move
  Phase 4: ESCAPE    (24h+)     → execute exit if safe
"""

import logging
from datetime import datetime, timezone

from app.constants import ADVISORY_DISCLAIMER, DATA_FRESHNESS_WARNING, MEDICAL_DISCLAIMER
from app.models.alerts import Alert
from app.models.common import AdvisoryMeta, DataSource, Location
from app.models.decision import (
    Action,
    DecisionResponse,
    Phase,
    Urgency,
)
from app.models.transport import TransportOption
from app.services.trust_service import compute_trust_score

logger = logging.getLogger(__name__)

# Severity → numeric for comparison
_SEV_NUM = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0, "none": 0}

# Emergency numbers by country
_EMERGENCY = {
    "BG": "112", "TR": "112", "GR": "112", "RO": "112", "RS": "112",
    "US": "911", "GB": "999", "JP": "110", "IN": "112", "AU": "000",
    "IL": "100", "UA": "112", "SY": "112", "DEFAULT": "112",
}

# Lethal threat types → immediate shelter
_LETHAL_TYPES = {"earthquake", "tsunami", "tornado", "volcanic_eruption"}

# Types where mobility is dangerous
_MOBILITY_UNSAFE = {"earthquake", "flood", "hurricane", "wildfire", "civil_unrest", "terrorism"}

# Types where evacuation makes sense
_EVACUATION_TYPES = {"flood", "wildfire", "volcanic_eruption", "hurricane", "geopolitical"}


def _determine_phase(alerts: list[Alert]) -> Phase:
    """Determine crisis phase from alert timing."""
    if not alerts:
        return Phase.MONITOR if hasattr(Phase, 'MONITOR') else Phase.EVALUATE

    now = datetime.now(timezone.utc)
    newest = max(alerts, key=lambda a: a.issued_at)
    age_minutes = (now - newest.issued_at.replace(tzinfo=timezone.utc)
                   if newest.issued_at.tzinfo is None
                   else now - newest.issued_at).total_seconds() / 60

    max_sev = max(_SEV_NUM.get(a.severity, 0) for a in alerts)

    if max_sev >= 4 and age_minutes < 5:
        return Phase.SURVIVE
    elif max_sev >= 3 and age_minutes < 60:
        return Phase.STABILIZE
    elif age_minutes < 1440:  # 24h
        return Phase.EVALUATE
    else:
        return Phase.ESCAPE


def _find_nearest_safe(transport: list[TransportOption]) -> str:
    """Find nearest operational transport/safe option."""
    operational = [t for t in transport if t.status in ("operational", "unknown")]
    if operational:
        nearest = min(operational, key=lambda t: t.distance_km or 9999)
        return f"{nearest.name} ({nearest.type.replace('_', ' ')}, {nearest.distance_km}km)"
    return ""


def make_decision(
    alerts: list[Alert],
    transport: list[TransportOption],
    location: Location,
    ai_summary: str = "",
    data_sources: list[DataSource] | None = None,
) -> DecisionResponse:
    """THE decision function. Deterministic. One instruction out.

    AI is NOT the final authority — it provides context only.
    Rules engine makes the call.
    """
    now = datetime.now(timezone.utc)

    # --- TRUST SCORING ---
    trust = compute_trust_score(alerts)

    # --- CLASSIFY THREATS ---
    max_severity = 0
    threat_types: set[str] = set()
    threat_descriptions: list[str] = []
    has_geopolitical = False

    for alert in alerts:
        sev = _SEV_NUM.get(alert.severity, 0)
        if sev > max_severity:
            max_severity = sev
        threat_types.add(alert.type)
        if sev >= 2:
            threat_descriptions.append(alert.title)
        if alert.type == "geopolitical":
            has_geopolitical = True

    # --- PHASE ---
    phase = _determine_phase(alerts)

    # --- DECISION TREE (deterministic) ---
    # Priority 1: Immediate lethal threat → SHELTER
    has_lethal = bool(threat_types & _LETHAL_TYPES) and max_severity >= 3
    # Priority 2: Unsafe to move → STAY
    has_mobility_risk = bool(threat_types & _MOBILITY_UNSAFE) and max_severity >= 2
    # Priority 3: Exit viable → MOVE / EVACUATE
    has_exit_option = bool(transport) and any(
        t.status in ("operational", "unknown") for t in transport
    )
    has_evac_trigger = bool(threat_types & _EVACUATION_TYPES) and max_severity >= 3

    # Geopolitical: if FCDO says "advise against all travel", that's a MOVE signal
    if has_geopolitical and max_severity >= 4:
        has_evac_trigger = True

    # --- MAKE THE CALL ---
    if has_lethal and phase in (Phase.SURVIVE, Phase.STABILIZE):
        action = Action.SHELTER
        urgency = Urgency.HIGH
        instruction = _build_shelter_instruction(alerts, threat_types)
        fallback_action = Action.STAY
        fallback = "If shelter is not available, stay low and away from windows and heavy objects."
    elif has_lethal and phase in (Phase.EVALUATE, Phase.ESCAPE):
        # Lethal threat but not immediate — evaluate exit
        action = Action.STAY
        urgency = Urgency.HIGH
        instruction = "STAY WHERE YOU ARE — assess conditions before moving. Aftershocks or secondary threats possible."
        fallback_action = Action.SHELTER
        fallback = "If conditions worsen, take shelter immediately in a sturdy structure."
    elif has_evac_trigger and has_exit_option:
        action = Action.EVACUATE if phase in (Phase.EVALUATE, Phase.ESCAPE) else Action.MOVE
        urgency = Urgency.HIGH if max_severity >= 4 else Urgency.MEDIUM
        nearest = _find_nearest_safe(transport)
        instruction = f"PREPARE TO LEAVE — conditions warrant departure. Nearest option: {nearest}" if nearest else "PREPARE TO LEAVE — check transport options and plan your route."
        fallback_action = Action.STAY
        fallback = "If transport is unavailable, stay in a secure location and contact your embassy."
    elif has_mobility_risk:
        action = Action.STAY
        urgency = Urgency.MEDIUM
        instruction = "STAY IN YOUR CURRENT LOCATION — moving is currently risky. Monitor for updates."
        fallback_action = Action.SHELTER
        fallback = "If your location becomes unsafe, move to the nearest sturdy building."
    elif max_severity >= 2:
        action = Action.MONITOR
        urgency = Urgency.MEDIUM
        instruction = "STAY ALERT — threats detected in your region. Be ready to act."
        fallback_action = Action.STAY
        fallback = "Keep monitoring official channels. Have your documents and essentials ready."
    else:
        action = Action.MONITOR
        urgency = Urgency.LOW
        instruction = "NO IMMEDIATE THREAT — stay aware of your surroundings."
        fallback_action = Action.MONITOR
        fallback = "Continue monitoring. Conditions can change rapidly."

    # --- CONFIDENCE ---
    # Base confidence from trust score, modified by decision clarity
    confidence = trust["trust_score"]
    if max_severity >= 3 and trust["sources_agreeing"] >= 2:
        confidence = min(confidence + 0.15, 0.98)
    if not alerts:
        confidence = 0.5  # No data = uncertain

    # --- THREAT SUMMARY ---
    threat_summary = ""
    if threat_descriptions:
        threat_summary = "; ".join(threat_descriptions[:3])
        if len(threat_descriptions) > 3:
            threat_summary += f" (+{len(threat_descriptions) - 3} more)"

    # --- EMERGENCY NUMBER ---
    country = location.country or "DEFAULT"
    emergency = _EMERGENCY.get(country, _EMERGENCY["DEFAULT"])

    # --- BUILD RESPONSE ---
    advisory_meta = AdvisoryMeta(
        disclaimer=ADVISORY_DISCLAIMER,
        medical_disclaimer=MEDICAL_DISCLAIMER,
        data_freshness_warning=DATA_FRESHNESS_WARNING,
        generated_at=now,
        data_sources=data_sources or [],
        ai_model="deterministic-rule-engine-v1",
        confidence=confidence,
    )

    # Audit log
    logger.info(
        "DECISION | lat=%.4f lon=%.4f | action=%s | urgency=%s | phase=%s | "
        "confidence=%.2f | trust=%.2f | sources=%d | threats=%s",
        location.latitude, location.longitude,
        action.value, urgency.value, phase.value,
        confidence, trust["trust_score"],
        trust["sources_agreeing"],
        ",".join(threat_types) or "none",
    )

    return DecisionResponse(
        instruction=instruction,
        action=action,
        urgency=urgency,
        phase=phase,
        confidence=round(confidence, 2),
        fallback_instruction=fallback,
        fallback_action=fallback_action,
        threat_summary=threat_summary,
        local_emergency_number=emergency,
        nearest_safe_option=_find_nearest_safe(transport),
        trust_score=round(trust["trust_score"], 2),
        sources_agreeing=trust["sources_agreeing"],
        sources_total=trust["sources_total"],
        location=location,
        advisory_meta=advisory_meta,
        decided_at=now,
    )


def _build_shelter_instruction(alerts: list[Alert], types: set[str]) -> str:
    """Build a specific shelter instruction based on threat type."""
    if "earthquake" in types:
        return "TAKE COVER NOW — earthquake detected. Get under sturdy furniture, away from windows."
    if "tsunami" in types:
        return "MOVE TO HIGH GROUND IMMEDIATELY — tsunami warning active."
    if "tornado" in types:
        return "GO TO BASEMENT OR INTERIOR ROOM NOW — tornado warning."
    if "volcanic_eruption" in types:
        return "SHELTER INDOORS — volcanic activity detected. Close windows and doors."
    return "TAKE SHELTER NOW — immediate threat detected in your area."
