"""Decision engine models — ONE deterministic instruction output."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .common import AdvisoryMeta, Location

__all__ = ["DecisionRequest", "DecisionResponse", "Action", "Phase", "Urgency"]


class Action(str, Enum):
    """Deterministic actions — the system picks exactly ONE."""
    SHELTER = "SHELTER"      # Immediate lethal threat → shelter in place
    STAY = "STAY"            # Unsafe to move → remain where you are
    MOVE = "MOVE"            # Exit viable → move toward exit corridor
    EVACUATE = "EVACUATE"    # Organized evacuation recommended
    MONITOR = "MONITOR"      # No immediate threat → stay aware


class Phase(str, Enum):
    """Crisis phase — determines what kind of action is appropriate."""
    SURVIVE = "SURVIVE"      # 0-5 min: immediate survival
    STABILIZE = "STABILIZE"  # 5-60 min: assess, secure, communicate
    EVALUATE = "EVALUATE"    # 1-24h: plan next move
    ESCAPE = "ESCAPE"        # 24h+: execute exit if safe


class Urgency(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecisionRequest(BaseModel):
    """Input to the decision engine."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    connectivity_status: str = Field("online", description="online | degraded | offline")
    language: str = Field("en")


class DecisionResponse(BaseModel):
    """THE output. One instruction. One fallback. No ambiguity.

    The user should understand what to do in ≤2 seconds.
    """
    # --- THE INSTRUCTION (must arrive first) ---
    instruction: str = Field(
        ..., description="Human-readable instruction: 'STAY INDOORS — EARTHQUAKE AFTERSHOCKS POSSIBLE'"
    )
    action: Action = Field(..., description="Deterministic action code")
    urgency: Urgency = Field(..., description="How urgent")
    phase: Phase = Field(..., description="Current crisis phase")
    confidence: float = Field(..., ge=0, le=1, description="Decision confidence (0-1)")

    # --- FALLBACK ---
    fallback_instruction: str = Field(
        ..., description="If primary fails or conditions change"
    )
    fallback_action: Action = Field(...)

    # --- CONTEXT (compact) ---
    threat_summary: str = Field("", description="One-line threat description")
    local_emergency_number: str = Field("112")
    nearest_safe_option: str = Field("", description="Nearest shelter/station/embassy if relevant")

    # --- TRUST ---
    trust_score: float = Field(0, ge=0, le=1, description="Data trust: multi-source agreement")
    sources_agreeing: int = Field(0, description="Number of sources confirming threat")
    sources_total: int = Field(0, description="Total sources queried")

    # --- METADATA ---
    location: Location = Field(...)
    advisory_meta: AdvisoryMeta = Field(...)
    decided_at: datetime = Field(...)
