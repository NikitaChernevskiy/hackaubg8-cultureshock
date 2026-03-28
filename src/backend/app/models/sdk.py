"""SDK models — insurance company integration."""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["SDKRegistration", "SDKRegistrationResponse", "RegisteredUser"]


class SDKRegistration(BaseModel):
    """Insurance company registers a user with their trip details."""
    phone: str = Field("", description="Phone in E.164 format (+359888123456)")
    email: str = Field("", description="User's email address")
    destination_lat: float = Field(..., ge=-90, le=90, description="Trip destination latitude")
    destination_lon: float = Field(..., ge=-180, le=180, description="Trip destination longitude")
    destination_name: str = Field("", description="Destination city/country name")
    language: str = Field("en", description="Preferred language (ISO 639-1)")
    partner_id: str = Field("", description="Insurance company identifier")


class SDKRegistrationResponse(BaseModel):
    """Confirmation of registration."""
    user_id: str
    registered: bool
    channels: list[str] = Field(default_factory=list, description="Active channels: email | sms")
    monitoring_active: bool = True
    registered_at: datetime


class RegisteredUser(BaseModel):
    """Internal representation of a monitored user."""
    user_id: str
    phone: str
    email: str
    destination_lat: float
    destination_lon: float
    destination_name: str
    language: str
    partner_id: str
    registered_at: datetime
    last_notified_at: datetime | None = None
    notification_count: int = 0
