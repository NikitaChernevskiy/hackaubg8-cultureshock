"""Emergency bundle — the critical single-request survival pack."""

from datetime import datetime

from pydantic import BaseModel, Field

from .alerts import Alert
from .common import AdvisoryMeta, DataSource, Location
from .transport import TransportOption

__all__ = ["EmergencyBundleRequest", "EmergencyBundleResponse"]


class EmergencyBundleRequest(BaseModel):
    """Request for the emergency bundle — one call, everything you need.

    The app detects emergencies and tells the user what is happening.
    No user situation input — the system is the source of truth.
    """

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    language: str = Field("en", description="Preferred language (ISO 639-1)")


class EmergencyBundleResponse(BaseModel):
    """The survival pack.

    Designed to be consumed in a single response. Fields are ordered by
    priority — if the connection drops partway, the most critical info
    (threat level, action suggestion, advisory text) comes first in
    serialization order.
    """

    # --- CRITICAL (must arrive first) ---
    threat_level: str = Field(
        ..., description="Overall threat: critical | high | medium | low | none"
    )
    action_suggestion: str = Field(
        ...,
        description=(
            "Suggested action: 'consider_shelter' | 'consider_evacuation' | "
            "'monitor_situation' | 'no_immediate_concern'"
        ),
    )
    advisory_text: str = Field(
        ..., description="AI-generated advisory (suggestions, NOT commands)"
    )
    local_emergency_number: str = Field(
        "", description="Local emergency number"
    )

    # --- HIGH PRIORITY ---
    priority_steps: list[str] = Field(
        default_factory=list,
        description="Ordered list of suggested considerations",
    )
    alerts: list[Alert] = Field(
        default_factory=list, description="Active alerts in the area"
    )

    # --- USEFUL ---
    transport: list[TransportOption] = Field(
        default_factory=list, description="Available transport options"
    )
    embassy_info: str = Field("", description="Nearest embassy/consulate info")

    # --- METADATA (always present) ---
    location: Location = Field(..., description="Resolved location")
    advisory_meta: AdvisoryMeta = Field(
        ..., description="MANDATORY: Disclaimers, sources, confidence"
    )
    bundle_generated_at: datetime = Field(
        ..., description="When this bundle was assembled (UTC)"
    )
    data_sources: list[DataSource] = Field(
        default_factory=list, description="All data sources used"
    )
