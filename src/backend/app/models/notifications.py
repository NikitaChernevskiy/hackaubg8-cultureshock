"""Notification models for push and SMS channels."""

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = [
    "DeviceRegistration",
    "DeviceRegistrationResponse",
    "NotificationPayload",
    "NotificationResult",
]


class DeviceRegistration(BaseModel):
    """Register a device for push notifications and/or SMS fallback."""

    device_token: str | None = Field(
        None, description="Firebase Cloud Messaging device token"
    )
    phone_number: str | None = Field(
        None,
        description="Phone number in E.164 format (e.g. +14155551234) for SMS fallback",
    )
    platform: str = Field(
        "unknown", description="Device platform: ios | android | unknown"
    )
    language: str = Field("en", description="Preferred language (ISO 639-1)")


class DeviceRegistrationResponse(BaseModel):
    """Confirmation of device registration."""

    device_id: str = Field(..., description="Assigned device identifier")
    channels: list[str] = Field(
        default_factory=list, description="Registered channels: push | sms"
    )
    registered_at: datetime = Field(..., description="Registration timestamp (UTC)")


class NotificationPayload(BaseModel):
    """Payload for sending a notification (internal/admin use)."""

    device_id: str = Field(..., description="Target device ID")
    title: str = Field(..., max_length=200, description="Notification title")
    body: str = Field(..., max_length=1000, description="Notification body")
    severity: str = Field("info", description="Alert severity level")
    data: dict | None = Field(None, description="Optional structured payload")


class NotificationResult(BaseModel):
    """Result of a notification send attempt."""

    device_id: str
    channels_attempted: list[str] = Field(default_factory=list)
    channels_succeeded: list[str] = Field(default_factory=list)
    channels_failed: list[str] = Field(default_factory=list)
    sent_at: datetime
