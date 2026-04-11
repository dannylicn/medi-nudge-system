"""
Telegram inbound webhook endpoint.
Validates the X-Telegram-Bot-Api-Secret-Token header before processing.
"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import Patient, NudgeCampaign, OutboundMessage
from app.services.response_classifier import classify_response
from app.services import nudge_campaign_service, onboarding_service, ocr_service
from app.services.telegram_service import validate_telegram_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

ONBOARDING_STATES = {"invited", "consent_pending"}


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

    # Look up patient by chat_id (stored in phone_number field for Telegram)
    patient = db.query(Patient).filter(Patient.phone_number == chat_id).first()

    if not patient:
        logger.info("Inbound message from unknown chat_id: %s", chat_id)
        _send_reply(chat_id, "We don't recognise this account. Please contact your clinic.")
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
        from app.services.telegram_service import send_text

        if response_type == "side_effect":
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
