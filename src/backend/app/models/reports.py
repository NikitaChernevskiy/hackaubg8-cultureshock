"""User report models — crowd-sourced ground truth."""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["UserReport", "UserReportResponse", "ReportStats"]


class UserReport(BaseModel):
    """A user-submitted incident report."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    report_type: str = Field(
        ..., description="earthquake | flood | fire | conflict | infrastructure | other"
    )
    description: str = Field(..., max_length=500)
    severity_estimate: str = Field("unknown", description="low | medium | high | critical | unknown")
    device_id: str = Field("", description="Anonymous device identifier for rate limiting")


class UserReportResponse(BaseModel):
    """Confirmation of report submission."""
    report_id: str
    accepted: bool
    trust_contribution: float = Field(
        0, description="How much this report affected the trust score (0-1)"
    )
    reports_in_area: int = Field(0, description="Total recent reports within 50km")
    submitted_at: datetime


class ReportStats(BaseModel):
    """Aggregate stats for an area."""
    total_reports_24h: int = 0
    total_reports_1h: int = 0
    dominant_type: str = ""
    avg_severity: str = ""
    trust_score: float = 0
