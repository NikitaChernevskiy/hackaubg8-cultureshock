"""Notification dispatch service."""

import logging
import uuid
from datetime import datetime, timezone

from app.models.notifications import (
    DeviceRegistration,
    DeviceRegistrationResponse,
    NotificationPayload,
    NotificationResult,
)
from app.providers.base import NotificationProvider

logger = logging.getLogger(__name__)

# In-memory device registry (swap for a database in production)
_device_registry: dict[str, DeviceRegistration] = {}


class NotificationService:
    """Registers devices and dispatches notifications."""

    def __init__(self, provider: NotificationProvider) -> None:
        self._provider = provider

    async def register_device(self, registration: DeviceRegistration) -> DeviceRegistrationResponse:
        device_id = str(uuid.uuid4())
        _device_registry[device_id] = registration

        channels = []
        if registration.device_token:
            channels.append("push")
        if registration.phone_number:
            channels.append("sms")

        logger.info(
            "Device registered: id=%s channels=%s platform=%s",
            device_id,
            channels,
            registration.platform,
        )

        return DeviceRegistrationResponse(
            device_id=device_id,
            channels=channels,
            registered_at=datetime.now(timezone.utc),
        )

    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        device = _device_registry.get(payload.device_id)
        if not device:
            return NotificationResult(
                device_id=payload.device_id,
                channels_attempted=[],
                channels_succeeded=[],
                channels_failed=["unknown_device"],
                sent_at=datetime.now(timezone.utc),
            )

        attempted: list[str] = []
        succeeded: list[str] = []
        failed: list[str] = []

        # Try push first
        if device.device_token:
            attempted.append("push")
            ok = await self._provider.send_push(
                device_token=device.device_token,
                title=payload.title,
                body=payload.body,
                data=payload.data,
            )
            (succeeded if ok else failed).append("push")

        # SMS fallback (or if push failed)
        if device.phone_number and ("push" not in succeeded):
            attempted.append("sms")
            sms_body = f"[{payload.severity.upper()}] {payload.title}: {payload.body}"
            ok = await self._provider.send_sms(
                phone_number=device.phone_number,
                message=sms_body[:160],  # SMS character limit
            )
            (succeeded if ok else failed).append("sms")

        return NotificationResult(
            device_id=payload.device_id,
            channels_attempted=attempted,
            channels_succeeded=succeeded,
            channels_failed=failed,
            sent_at=datetime.now(timezone.utc),
        )
