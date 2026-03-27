"""Mock notification provider — logs instead of sending."""

import logging

from app.providers.base import NotificationProvider

logger = logging.getLogger(__name__)


class MockNotificationProvider(NotificationProvider):
    """Logs notification attempts instead of sending them. For development."""

    async def send_push(
        self, device_token: str, title: str, body: str, data: dict | None = None
    ) -> bool:
        logger.info(
            "[MOCK PUSH] token=%s title='%s' body='%s' data=%s",
            device_token[:20] + "..." if len(device_token) > 20 else device_token,
            title,
            body[:80],
            data,
        )
        return True

    async def send_sms(self, phone_number: str, message: str) -> bool:
        logger.info(
            "[MOCK SMS] to=%s message='%s'",
            phone_number,
            message[:80],
        )
        return True

    async def health_check(self) -> bool:
        return True
