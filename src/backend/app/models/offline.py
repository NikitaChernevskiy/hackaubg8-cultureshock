"""Offline data pack models — everything needed when internet dies."""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["OfflinePack", "Embassy", "EmergencyInfo", "SafeZone"]


class Embassy(BaseModel):
    """Embassy/consulate information."""
    country: str = Field(..., description="Country this embassy represents")
    name: str
    address: str
    phone: str = ""
    latitude: float = 0
    longitude: float = 0


class EmergencyInfo(BaseModel):
    """Emergency numbers and critical info for a country."""
    country_code: str
    country_name: str
    emergency_number: str = "112"
    police: str = ""
    ambulance: str = ""
    fire: str = ""
    tourist_police: str = ""
    language_tips: list[str] = Field(default_factory=list)


class SafeZone(BaseModel):
    """Pre-identified safe locations."""
    name: str
    type: str = Field(..., description="hospital | shelter | embassy | police_station | transit_hub")
    latitude: float
    longitude: float
    notes: str = ""


class OfflinePack(BaseModel):
    """The 'last seconds of internet' package.

    Contains everything a traveler needs to function offline:
    embassies, emergency numbers, safe zones, basic decision rules.
    Target size: < 100KB compressed.
    """
    country_code: str
    country_name: str
    generated_at: datetime
    valid_until: datetime

    emergency: EmergencyInfo
    embassies: list[Embassy] = Field(default_factory=list)
    safe_zones: list[SafeZone] = Field(default_factory=list)

    # Simplified decision rules for offline use
    offline_rules: list[str] = Field(
        default_factory=list,
        description="Simple text rules the app can follow offline"
    )

    # Last known threat state
    last_known_threat_level: str = "unknown"
    last_known_alerts_summary: str = ""
