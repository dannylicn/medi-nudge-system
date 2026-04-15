"""
Telegram inbound webhook endpoint.
Validates the X-Telegram-Bot-Api-Secret-Token header before processing.
"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import Patient, NudgeCampaign, OutboundMessage, PatientMedication
from app.services.response_classifier import classify_response
from app.services import nudge_campaign_service, onboarding_service, ocr_service
from app.services.telegram_service import validate_telegram_token, send_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

ONBOARDING_STATES = onboarding_service.ONBOARDING_STATES


def _validate_secret(request: Request) -> None:
    """Reject requests with invalid Telegram webhook secret with 403."""
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not validate_telegram_token(token):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")


@router.post("/telegram")
async def inbound_telegram(
    request: Request,
    db: Session = Depends(get_db),
):
    """Main inbound Telegram message handler (Telegram Bot API webhook)."""
    _validate_secret(request)

    update = await request.json()

    message = update.get("message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = message.get("text", "").strip()
    from_user = message.get("from", {})

    if not chat_id:
        return {"ok": True}

    # Handle /start [TOKEN] before patient lookup
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        token_arg = parts[1].strip() if len(parts) > 1 else None
        onboarding_service.handle_start_command(db, chat_id, token_arg)
        return {"ok": True}

    # Look up patient by telegram_chat_id
    patient = db.query(Patient).filter(Patient.telegram_chat_id == chat_id).first()

    if not patient:
        # Route to self-onboarding
        onboarding_service.handle_start_command(db, chat_id, None)
        return {"ok": True}

    # Photo → OCR pipeline
    if message.get("photo"):
        _handle_photo(db, patient, message)
        return {"ok": True}

    if not text:
        return {"ok": True}

    # Onboarding flow
    if patient.onboarding_state in ONBOARDING_STATES:
        onboarding_service.handle_onboarding_reply(db, patient, text)
        return {"ok": True}

    # Active nudge campaign response
    open_campaign: NudgeCampaign | None = (
        db.query(NudgeCampaign)
        .filter(
            NudgeCampaign.patient_id == patient.id,
            NudgeCampaign.status == "sent",
        )
        .order_by(NudgeCampaign.created_at.desc())
        .first()
    )

    response_type = classify_response(text)

    if open_campaign:
        nudge_campaign_service.handle_response(
            db=db,
            campaign=open_campaign,
            response_text=text,
            response_type=response_type,
        )
    else:
        from app.services import escalation_service
        from app.services.nudge_generator import get_safety_ack, get_question_ack

        if response_type == "confirmed" or text.strip().upper() in ("TAKEN", "已服", "SUDAH"):
            # Patient acknowledging a daily reminder — reset missed-dose streak
            _handle_taken(db, patient)
        elif response_type == "side_effect":
            escalation_service.create_escalation(
                db=db, patient_id=patient.id, reason="side_effect", priority="urgent"
            )
            send_text(db, patient.id, patient.phone_number, get_safety_ack(patient.language_preference))
        elif response_type in ("question", "opt_out"):
            escalation_service.create_escalation(
                db=db, patient_id=patient.id, reason="patient_question"
            )
            send_text(db, patient.id, patient.phone_number, get_question_ack(patient.language_preference))

    return {"ok": True}


def _handle_photo(db: Session, patient: Patient, message: dict) -> None:
    """Download Telegram photo and route to OCR pipeline."""
    import httpx
    photos = message.get("photo", [])
    if not photos:
        return
    # Use the largest photo (last in the array)
    file_id = photos[-1].get("file_id")
    if not file_id:
        return
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        # Get file path from Telegram
        file_resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=30,
        )
        file_resp.raise_for_status()
        file_path = file_resp.json()["result"]["file_path"]

        # Download the file
        dl_resp = httpx.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}",
            timeout=30,
        )
        dl_resp.raise_for_status()

        ocr_service.ingest_image(
            db=db,
            patient_id=patient.id,
            image_bytes=dl_resp.content,
            source="telegram_photo",
        )
    except Exception as exc:
        logger.error("Failed to download/process Telegram photo for patient %s: %s", patient.id, exc)


def _send_reply(chat_id: str, text: str) -> None:
    """Quick reply via Telegram (no DB record, for unknown users)."""
    import httpx
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception:
        pass


TAKEN_ACK: dict[str, str] = {
    "en": "Great job! 👍 Your medication has been recorded as taken. Keep it up!",
    "zh": "做得好！👍 您的服药记录已更新。继续保持！",
    "ms": "Bagus sekali! 👍 Ubat anda telah direkodkan sebagai sudah diambil. Teruskan!",
    "ta": "சரிதான்! 👍 உங்கள் மருந்து எடுத்தது பதிவு செய்யப்பட்டது. தொடர்ந்து வாருங்கள்!",
}


def _handle_taken(db: Session, patient: Patient) -> None:
    """Reset missed-dose streak for patient and send ack."""
    from datetime import datetime as _dt
    active_meds = (
        db.query(PatientMedication)
        .filter(
            PatientMedication.patient_id == patient.id,
            PatientMedication.is_active == True,  # noqa: E712
        )
        .all()
    )
    for pm in active_meds:
        pm.last_taken_at = _dt.utcnow()
        pm.consecutive_missed_doses = 0
    db.commit()

    lang = patient.language_preference if patient.language_preference in TAKEN_ACK else "en"
    send_text(db, patient.id, patient.phone_number, TAKEN_ACK[lang])
