"""Shared models used across the API."""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["Location", "DataSource", "AdvisoryMeta"]


class Location(BaseModel):
    """GPS coordinates with optional context."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    city: str | None = Field(None, description="City name if known")
    country: str | None = Field(None, description="ISO 3166-1 alpha-2 country code")
    country_name: str | None = Field(None, description="Human-readable country name")


class DataSource(BaseModel):
    """Attribution for a piece of data — where it came from and how fresh."""

    name: str = Field(..., description="Provider name (e.g. 'GDACS', 'USGS')")
    url: str | None = Field(None, description="Link to the original source")
    retrieved_at: datetime = Field(..., description="When this data was fetched (UTC)")
    reliability: str = Field(
        "unverified",
        description="Source reliability: official | verified | unverified | mock",
    )


class AdvisoryMeta(BaseModel):
    """Metadata attached to every AI-generated advisory response.

    This is MANDATORY on any response containing AI-generated text.
    """

    disclaimer: str = Field(..., description="Legal disclaimer text")
    medical_disclaimer: str = Field(..., description="Medical advice disclaimer")
    data_freshness_warning: str = Field(..., description="Data staleness warning")
    generated_at: datetime = Field(..., description="When this advisory was generated (UTC)")
    data_sources: list[DataSource] = Field(
        default_factory=list, description="Sources used to generate this advisory"
    )
    ai_model: str = Field("", description="Which AI model produced this text")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) based on data quality/completeness",
    )
