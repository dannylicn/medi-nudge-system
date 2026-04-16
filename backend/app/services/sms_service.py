"""
SMS / WhatsApp delivery service using Twilio.

When TWILIO_ACCOUNT_SID is not configured the message is logged only,
so local development works without real credentials.

Usage:
    sms_service.send(to="+6591234567", body="Your invite link: ...")
    sms_service.send_whatsapp(to="+6591234567", body="...")
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def send(to: str, body: str) -> bool:
    """Send a plain SMS to an E.164 number. Returns True on success."""
    return _deliver(to, body, whatsapp=False)


def send_whatsapp(to: str, body: str) -> bool:
    """Send a WhatsApp message to an E.164 number. Returns True on success."""
    return _deliver(to, body, whatsapp=True)


def _deliver(to: str, body: str, *, whatsapp: bool) -> bool:
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER):
        channel = "WhatsApp" if whatsapp else "SMS"
        logger.info("[%s stub] → %s: %s", channel, to, body)
        return True  # treat as success in dev so flows are not blocked

    try:
        from twilio.rest import Client  # type: ignore
    except ImportError:
        logger.warning("twilio package not installed — message not sent to %s", to)
        return False

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        from_number = settings.TWILIO_FROM_NUMBER
        to_number = to

        if whatsapp:
            if not from_number.startswith("whatsapp:"):
                from_number = f"whatsapp:{from_number}"
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"

        client.messages.create(body=body, from_=from_number, to=to_number)
        logger.info("Message sent to %s", to)
        return True
    except Exception as exc:
        logger.error("Twilio delivery failed to %s: %s", to, exc)
        return False
