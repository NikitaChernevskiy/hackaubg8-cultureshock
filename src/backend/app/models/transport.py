"""Transport status data models."""

from datetime import datetime

from pydantic import BaseModel, Field

from .common import DataSource, Location

__all__ = ["TransportOption", "TransportResponse"]


class TransportOption(BaseModel):
    """A single transport option (airport, train station, bus, road)."""

    id: str = Field(..., description="Unique identifier")
    type: str = Field(
        ..., description="Transport type: airport | train_station | bus_station | road | port"
    )
    name: str = Field(..., description="Name of the transport hub or route")
    location: Location = Field(..., description="Location of this transport option")
    status: str = Field(
        ..., description="Operational status: operational | disrupted | closed | unknown"
    )
    status_detail: str = Field("", description="Human-readable status explanation")
    distance_km: float | None = Field(None, description="Distance from user in km")
    estimated_travel_minutes: int | None = Field(
        None, description="Estimated travel time from user location in minutes"
    )
    source: DataSource = Field(..., description="Data source for this info")
    last_updated: datetime = Field(..., description="When status was last checked (UTC)")


class TransportResponse(BaseModel):
    """Response for the transport status endpoint."""

    options: list[TransportOption] = Field(default_factory=list)
    location: Location = Field(..., description="User's location")
    retrieved_at: datetime = Field(..., description="When this data was assembled (UTC)")
    sources: list[DataSource] = Field(default_factory=list)
