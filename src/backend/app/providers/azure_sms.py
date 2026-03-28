"""Azure Communication Services SMS provider."""

import logging

from azure.communication.sms import SmsClient

from app.config import get_settings
from app.providers.base import NotificationProvider

logger = logging.getLogger(__name__)


class AzureSMSProvider(NotificationProvider):
    """Sends SMS via Azure Communication Services.

    Push notifications are not handled by this provider — use alongside
    a Firebase push provider if both channels are needed.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = SmsClient.from_connection_string(settings.azure_comm_connection_string)
        self._from_number = settings.azure_comm_from_number

    async def send_push(
        self, device_token: str, title: str, body: str, data: dict | None = None
    ) -> bool:
        logger.warning("AzureSMSProvider does not support push notifications")
        return False

    async def send_sms(self, phone_number: str, message: str) -> bool:
        try:
            response = self._client.send(
                from_=self._from_number,
                to=phone_number,
                message=message,
            )
            result = response[0]
            if result.successful:
                logger.info("SMS sent to %s (message_id=%s)", phone_number, result.message_id)
                return True
            else:
                logger.error(
                    "SMS failed to %s: %s", phone_number, result.error_message
                )
                return False
        except Exception:
            logger.exception("SMS send failed to %s", phone_number)
            return False

    async def health_check(self) -> bool:
        return bool(self._from_number)
