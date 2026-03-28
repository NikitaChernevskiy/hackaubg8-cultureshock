"""Alert data models."""

from datetime import datetime

from pydantic import BaseModel, Field

from .common import DataSource, Location

__all__ = ["Alert", "AlertsResponse"]


class Alert(BaseModel):
    """A single emergency alert."""

    id: str = Field(..., description="Unique alert identifier")
    type: str = Field(..., description="Emergency type (earthquake, flood, geopolitical, etc.)")
    severity: str = Field(..., description="Severity: critical | high | medium | low | info")
    title: str = Field(..., description="Short headline")
    description: str = Field(..., description="Detailed description of the alert")
    issued_at: datetime = Field(..., description="When the alert was issued (UTC)")
    expires_at: datetime | None = Field(None, description="When the alert expires (UTC)")
    location: Location | None = Field(None, description="Affected area center point")
    radius_km: float | None = Field(None, description="Affected radius in km")
    source: DataSource = Field(..., description="Where this alert came from")
    official_url: str | None = Field(None, description="Link to official alert page")


class AlertsResponse(BaseModel):
    """Response for the alerts endpoint."""

    alerts: list[Alert] = Field(default_factory=list)
    location: Location = Field(..., description="Location these alerts are for")
    retrieved_at: datetime = Field(..., description="When this data was assembled (UTC)")
    sources: list[DataSource] = Field(default_factory=list)
