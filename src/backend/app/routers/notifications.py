"""Notification registration and dispatch endpoints."""

from fastapi import APIRouter, HTTPException

from app.models.notifications import (
    DeviceRegistration,
    DeviceRegistrationResponse,
    NotificationPayload,
    NotificationResult,
)
from app.providers.factory import get_notification_provider
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/register",
    response_model=DeviceRegistrationResponse,
    summary="Register a device for push/SMS notifications",
    description=(
        "Register a mobile device to receive emergency alerts via push "
        "notifications and/or SMS fallback. At least one channel "
        "(device_token for push, phone_number for SMS) must be provided."
    ),
)
async def register_device(registration: DeviceRegistration):
    if not registration.device_token and not registration.phone_number:
        raise HTTPException(
            status_code=422,
            detail="At least one of device_token or phone_number must be provided.",
        )

    service = NotificationService(provider=get_notification_provider())
    return await service.register_device(registration)


@router.post(
    "/send",
    response_model=NotificationResult,
    summary="Send a notification to a registered device",
    description=(
        "Send an emergency notification to a registered device. Attempts "
        "push first; falls back to SMS if push fails or is unavailable."
    ),
)
async def send_notification(payload: NotificationPayload):
    service = NotificationService(provider=get_notification_provider())
    return await service.send_notification(payload)
