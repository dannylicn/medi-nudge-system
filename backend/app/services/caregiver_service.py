"""
Caregiver notification service.
Sends Telegram messages to registered caregivers when a patient misses
medication doses beyond the configured threshold.
Falls back to WhatsApp/SMS if Telegram is not yet linked.
"""
import logging
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Patient, PatientMedication, Medication
from app.services import escalation_service, sms_service

logger = logging.getLogger(__name__)

CAREGIVER_MESSAGES: dict[str, str] = {
    "en": (
        "Hello {caregiver_name}, this is MediNudge Care System.\n\n"
        "Your family member {patient_name} has missed taking {medications} "
        "for {count} consecutive time(s). "
        "Please help remind them or contact your care coordinator if you need assistance."
    ),
    "zh": (
        "您好 {caregiver_name}，这是 MediNudge 护理系统。\n\n"
        "您的家人 {patient_name} 已连续 {count} 次未服用 {medications}。"
        "请协助提醒他/她，或联系护理协调员寻求帮助。"
    ),
    "ms": (
        "Halo {caregiver_name}, ini adalah Sistem Penjagaan MediNudge.\n\n"
        "Ahli keluarga anda {patient_name} telah terlepas mengambil {medications} "
        "sebanyak {count} kali berturut-turut. "
        "Sila bantu ingatkan mereka atau hubungi koordinator penjagaan jika anda memerlukan bantuan."
    ),
    "ta": (
        "வணக்கம் {caregiver_name}, இது MediNudge பராமரிப்பு அமைப்பு.\n\n"
        "உங்கள் குடும்பத்தினர் {patient_name} தொடர்ச்சியாக {count} முறை "
        "{medications} எடுக்கவில்லை. "
        "அவர்களுக்கு நினைவூட்ட உதவுங்கள் அல்லது உதவி தேவைப்பட்டால் பராமரிப்பு ஒருங்கிணைப்பாளரை தொடர்பு கொள்ளுங்கள்."
    ),
}


def notify_caregiver(
    db: Session,
    patient: Patient,
    missed_medications: list[str],
    consecutive_count: int,
) -> bool:
    """
    Send a notification to the patient's caregiver.
    Tries Telegram first; falls back to WhatsApp/SMS if phone is set but Telegram not linked.
    Returns True if any channel succeeded.
    """
    if not patient.caregiver_telegram_id and not patient.caregiver_phone_number:
        return False

    lang = patient.language_preference if patient.language_preference in CAREGIVER_MESSAGES else "en"
    template = CAREGIVER_MESSAGES[lang]
    med_list = ", ".join(missed_medications)

    message = template.format(
        caregiver_name=patient.caregiver_name or "Caregiver",
        patient_name=patient.full_name.split()[0],
        medications=med_list,
        count=consecutive_count,
    )

    sent = False

    # Try Telegram first (zero cost, instant)
    if patient.caregiver_telegram_id:
        sent = _send_telegram(patient.caregiver_telegram_id, message)

    # Fall back to WhatsApp/SMS if Telegram not linked or failed
    if not sent and patient.caregiver_phone_number:
        sent = sms_service.send_whatsapp(patient.caregiver_phone_number, message)

    if sent:
        # Also create an escalation so the coordinator is aware
        escalation_service.create_escalation(
            db=db,
            patient_id=patient.id,
            reason="repeated_non_adherence",
            priority="high",
        )
        logger.info(
            "Caregiver notified for patient %s (missed %d times: %s)",
            patient.id, consecutive_count, med_list,
        )
    else:
        logger.warning("Failed to notify caregiver for patient %s via any channel", patient.id)

    return sent


def _send_telegram(chat_id: str, text: str) -> bool:
    """Send a raw Telegram message without creating an OutboundMessage record."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — caregiver message not sent")
        return False
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Caregiver Telegram send failed: %s", exc)
        return False
