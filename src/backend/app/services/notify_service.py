"""Notification service — sends real emails (and SMS when configured) via Azure Communication Services."""

import logging

from azure.communication.email import EmailClient

from app.config import get_settings

logger = logging.getLogger(__name__)

_SENDER = "DoNotReply@443d0cd2-aa0b-4414-8590-b277b9f84e38.azurecomm.net"


def _get_email_client() -> EmailClient | None:
    settings = get_settings()
    if not settings.azure_comm_connection_string:
        return None
    try:
        return EmailClient.from_connection_string(settings.azure_comm_connection_string)
    except Exception:
        logger.exception("Failed to create email client")
        return None


async def send_alert_email(
    to_email: str,
    subject: str,
    instruction: str,
    threat_summary: str,
    emergency_number: str,
    map_url: str,
    country_name: str,
) -> bool:
    """Send a real alert email via Azure Communication Services."""
    client = _get_email_client()
    if not client:
        logger.warning("Email client not configured, skipping email to %s", to_email)
        return False

    html_body = f"""
    <div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;background:#0b0b12;color:#e4e4ef;padding:24px;border-radius:12px;">
      <h1 style="color:#6366f1;font-size:22px;margin:0 0 4px;">Amygdala</h1>
      <p style="color:#6b6b85;font-size:12px;margin:0 0 20px;">Emergency Travel Advisory</p>

      <div style="background:#ef4444;color:white;padding:16px;border-radius:10px;margin-bottom:16px;">
        <div style="font-size:12px;font-weight:bold;text-transform:uppercase;margin-bottom:8px;">⚠ ALERT — {country_name}</div>
        <div style="font-size:20px;font-weight:800;line-height:1.3;">{instruction}</div>
      </div>

      <div style="background:#1e1e30;padding:14px;border-radius:8px;margin-bottom:16px;">
        <div style="font-size:11px;color:#6b6b85;text-transform:uppercase;margin-bottom:6px;">Detected Threats</div>
        <div style="font-size:14px;line-height:1.6;">{threat_summary}</div>
      </div>

      <a href="{map_url}" style="display:block;text-align:center;background:#6366f1;color:white;padding:16px;border-radius:10px;font-size:16px;font-weight:bold;text-decoration:none;margin-bottom:16px;">
        🗺 Open Navigation Map
      </a>

      <div style="background:#1e1e30;padding:14px;border-radius:8px;margin-bottom:16px;text-align:center;">
        <div style="font-size:12px;color:#6b6b85;margin-bottom:4px;">Local Emergency Number</div>
        <div style="font-size:28px;font-weight:800;color:#ef4444;">{emergency_number}</div>
      </div>

      <p style="font-size:9px;color:#444;line-height:1.5;">
        Advisory only — not professional emergency advice. Follow local authorities.
        Data sources: USGS, GDACS, NASA, FCDO, Meteoalarm, ReliefWeb, OpenStreetMap.
      </p>
    </div>
    """

    plain_text = f"""AMYGDALA EMERGENCY ALERT — {country_name}

{instruction}

THREATS: {threat_summary}

NAVIGATION MAP: {map_url}

EMERGENCY NUMBER: {emergency_number}

Advisory only. Follow local authorities."""

    try:
        message = {
            "senderAddress": _SENDER,
            "recipients": {"to": [{"address": to_email}]},
            "content": {
                "subject": f"⚠ AMYGDALA ALERT — {subject}",
                "plainText": plain_text,
                "html": html_body,
            },
        }
        poller = client.begin_send(message)
        result = poller.result()
        logger.info("EMAIL_SENT | to=%s | status=%s | id=%s", to_email, result["status"], result["id"])
        return result["status"] == "Succeeded"
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


async def send_alert_sms(
    to_phone: str,
    instruction: str,
    map_url: str,
    emergency_number: str,
) -> bool:
    """Send SMS via Azure Communication Services (requires purchased phone number)."""
    settings = get_settings()
    if not settings.azure_comm_connection_string or not settings.azure_comm_from_number:
        logger.warning("SMS not configured (no from_number), skipping SMS to %s", to_phone)
        return False

    try:
        from azure.communication.sms import SmsClient
        client = SmsClient.from_connection_string(settings.azure_comm_connection_string)

        # SMS is 160 chars max, keep it tight
        body = f"⚠ AMYGDALA: {instruction[:80]} Map: {map_url} Emergency: {emergency_number}"

        response = client.send(from_=settings.azure_comm_from_number, to=to_phone, message=body[:160])
        result = response[0]
        if result.successful:
            logger.info("SMS_SENT | to=%s | id=%s", to_phone, result.message_id)
            return True
        else:
            logger.error("SMS_FAILED | to=%s | error=%s", to_phone, result.error_message)
            return False
    except Exception:
        logger.exception("Failed to send SMS to %s", to_phone)
        return False
