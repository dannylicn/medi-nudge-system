"""
Telegram inbound webhook endpoint.
Validates the X-Telegram-Bot-Api-Secret-Token header before processing.
"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import Patient, NudgeCampaign, OutboundMessage, PatientMedication, VoiceProfile
from app.services.response_classifier import classify_response
from app.services import nudge_campaign_service, onboarding_service, ocr_service, agent_service
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

    # Check if this is a caregiver (voice sample or consent reply)
    # Only treat as caregiver if this chat_id is NOT also a patient's own telegram_chat_id
    is_patient = db.query(Patient).filter(Patient.telegram_chat_id == chat_id).first() is not None
    if not is_patient:
        caregiver_patient = db.query(Patient).filter(Patient.caregiver_telegram_id == chat_id).first()
        if caregiver_patient:
            voice_msg = message.get("voice")
            if voice_msg:
                _handle_caregiver_voice(db, caregiver_patient, chat_id, voice_msg)
                return {"ok": True}
            if text and _handle_caregiver_text(db, caregiver_patient, chat_id, text):
                return {"ok": True}

    # Look up patient by telegram_chat_id
    patient = db.query(Patient).filter(Patient.telegram_chat_id == chat_id).first()

    if not patient:
        # Route to self-onboarding
        onboarding_service.handle_start_command(db, chat_id, None)
        return {"ok": True}

    # --- Pending action takes priority (bot asked a question, this is the reply) ---
    if patient.pending_action:
        handled = _handle_pending_action(db, patient, message, text)
        if handled:
            return {"ok": True}

    # Photo → OCR pipeline (always takes priority over text routing)
    if message.get("photo"):
        _handle_photo(db, patient, message)
        return {"ok": True}

    # Voice message from patient — route to self-cloning flow
    voice_msg = message.get("voice")
    if voice_msg and patient.onboarding_state == "complete":
        _handle_patient_voice(db, patient, voice_msg)
        return {"ok": True}

    if not text:
        return {"ok": True}

    # Medication confirmation pending (from onboarding manual-entry verification)
    if patient.onboarding_state == "medication_confirm_pending":
        agent_service.handle_medication_confirm_reply(patient, text, db)
        return {"ok": True}

    # Onboarding flow
    if patient.onboarding_state in ONBOARDING_STATES:
        onboarding_service.handle_onboarding_reply(db, patient, text)
        return {"ok": True}

    # Active patient — route through agentic handler (LLM or rule-based fallback)
    agent_service.run(patient, text, db)
    return {"ok": True}


def _handle_pending_action(db: Session, patient: Patient, message: dict, text: str) -> bool:
    """
    Route reply based on what the bot last asked the patient.
    Returns True if handled, False to fall through to normal routing.
    """
    action = patient.pending_action

    if action == "voice_consent":
        if not text:
            return False  # They sent a non-text message, let normal routing handle
        return _handle_voice_consent_reply(db, patient, text)

    if action == "voice_sample_pending":
        voice_msg = message.get("voice")
        if voice_msg:
            _handle_patient_voice(db, patient, voice_msg)
            return True
        if text:
            _send_reply(
                patient.telegram_chat_id,
                "Please send a *voice message* (hold the microphone button). Text won't work for voice cloning.",
            )
            return True
        return False

    # Unknown action — clear it and fall through
    logger.warning("Unknown pending_action '%s' for patient %s, clearing", action, patient.id)
    patient.pending_action = None
    db.commit()
    return False


def _handle_voice_consent_reply(db: Session, patient: Patient, text: str) -> bool:
    """Handle the reply to a voice consent question."""
    from datetime import datetime as _dt

    lower = text.strip().lower()

    profile = (
        db.query(VoiceProfile)
        .filter(
            VoiceProfile.patient_id == patient.id,
            VoiceProfile.is_active == True,
        )
        .order_by(VoiceProfile.created_at.desc())
        .first()
    )

    if any(k in lower for k in ("yes", "ya", "同意", "是", "ok", "okay")):
        patient.pending_action = None
        if profile:
            profile.patient_consent_at = _dt.utcnow()
            if profile.donor_name == "self":
                profile.donor_consent_at = _dt.utcnow()
        db.commit()

        if profile and profile.sample_file_path:
            from app.services.voice_clone_service import clone_voice
            success = clone_voice(db, profile)
            if success:
                _send_reply(patient.telegram_chat_id, "Your voice has been set up for your medication reminders!")
            else:
                _send_reply(patient.telegram_chat_id, "Thank you for your consent. We'll set up voice reminders shortly.")
        else:
            _send_reply(patient.telegram_chat_id, "Thank you for your consent. Please send a voice message (60-90 seconds) to complete the setup.")
            patient.pending_action = "voice_sample_pending"
            db.commit()
        return True

    elif any(k in lower for k in ("no", "tidak", "不", "拒绝", "nope", "cancel")):
        patient.pending_action = None
        if profile:
            profile.is_active = False
        db.commit()
        _send_reply(patient.telegram_chat_id, "No problem. Voice cloning has been cancelled.")
        return True

    else:
        # Didn't understand — re-ask
        _send_reply(patient.telegram_chat_id, "Please reply *YES* to consent or *NO* to decline.")
        return True


def _handle_patient_voice(db: Session, patient: Patient, voice: dict) -> None:
    """Download patient's own voice sample for self-cloning."""
    logger.info("Processing patient voice message for self-clone, patient_id=%s", patient.id)
    import os
    from pathlib import Path

    chat_id = patient.telegram_chat_id

    # Find or create a VoiceProfile for self-cloning
    profile = (
        db.query(VoiceProfile)
        .filter(VoiceProfile.patient_id == patient.id, VoiceProfile.is_active == True)
        .first()
    )
    if not profile:
        profile = VoiceProfile(
            patient_id=patient.id,
            donor_name="self",
            donor_telegram_id=chat_id,
            is_active=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    file_id = voice.get("file_id")
    if not file_id:
        return

    try:
        import httpx
        token = settings.TELEGRAM_BOT_TOKEN
        file_resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=30,
        )
        file_resp.raise_for_status()
        file_path = file_resp.json()["result"]["file_path"]

        dl_resp = httpx.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}",
            timeout=30,
        )
        dl_resp.raise_for_status()

        sample_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "voice_samples")
        Path(sample_dir).mkdir(parents=True, exist_ok=True)
        sample_path = os.path.join(sample_dir, f"{profile.id}.ogg")
        with open(sample_path, "wb") as f:
            f.write(dl_resp.content)

        profile.sample_file_path = sample_path
        patient.pending_action = "voice_consent"
        db.commit()

        _send_reply(
            chat_id,
            "Thank you for recording! Do you consent to your voice being used "
            "for your medication reminders?\n\n"
            "Reply *YES* to consent or *NO* to decline.",
        )
        logger.info("Voice sample saved for patient %s, awaiting consent", patient.id)
    except Exception as exc:
        logger.error("Failed to download patient voice for patient %s: %s", patient.id, exc)


def _handle_caregiver_voice(db: Session, patient: Patient, chat_id: str, voice: dict) -> None:
    """Download caregiver voice sample and store for cloning."""
    import os
    from pathlib import Path

    # Find or create a pending VoiceProfile
    profile = (
        db.query(VoiceProfile)
        .filter(VoiceProfile.patient_id == patient.id, VoiceProfile.is_active == True)
        .first()
    )
    if not profile:
        profile = VoiceProfile(
            patient_id=patient.id,
            donor_name=patient.caregiver_name,
            donor_telegram_id=chat_id,
            is_active=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    file_id = voice.get("file_id")
    if not file_id:
        return

    try:
        import httpx
        token = settings.TELEGRAM_BOT_TOKEN
        file_resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=30,
        )
        file_resp.raise_for_status()
        file_path = file_resp.json()["result"]["file_path"]

        dl_resp = httpx.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}",
            timeout=30,
        )
        dl_resp.raise_for_status()

        sample_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "voice_samples")
        Path(sample_dir).mkdir(parents=True, exist_ok=True)
        sample_path = os.path.join(sample_dir, f"{profile.id}.ogg")
        with open(sample_path, "wb") as f:
            f.write(dl_resp.content)

        profile.sample_file_path = sample_path
        db.commit()

        # Ask for consent
        _send_reply(
            chat_id,
            f"Thank you for recording! Do you consent to your voice being used "
            f"for medication reminders for {patient.full_name.split()[0]}?\n\n"
            f"Reply *YES* to consent or *NO* to decline.",
        )
    except Exception as exc:
        logger.error("Failed to download caregiver voice for patient %s: %s", patient.id, exc)


def _handle_caregiver_text(db: Session, patient: Patient, chat_id: str, text: str) -> bool:
    """Handle caregiver consent reply for voice cloning. Returns True if handled."""
    profile = (
        db.query(VoiceProfile)
        .filter(
            VoiceProfile.patient_id == patient.id,
            VoiceProfile.donor_telegram_id == chat_id,
            VoiceProfile.is_active == True,
            VoiceProfile.sample_file_path.isnot(None),
            VoiceProfile.donor_consent_at.is_(None),
        )
        .first()
    )
    if not profile:
        return False  # Not in consent flow — let normal routing handle

    from datetime import datetime as _dt
    lower = text.strip().lower()
    if any(k in lower for k in ("yes", "ya", "同意", "是")):
        profile.donor_consent_at = _dt.utcnow()
        db.commit()

        # If patient consent is also present, trigger cloning
        if profile.patient_consent_at:
            from app.services.voice_clone_service import clone_voice
            success = clone_voice(db, profile)
            if success:
                _send_reply(chat_id, "Your voice has been set up for reminders. Thank you!")
            else:
                _send_reply(chat_id, "Thank you for your consent. We'll set up the voice reminders shortly.")
        else:
            _send_reply(chat_id, "Thank you for your consent! Voice reminders will be activated once the patient also consents.")
        return True
    elif any(k in lower for k in ("no", "tidak", "不", "拒绝")):
        profile.is_active = False
        db.commit()
        _send_reply(chat_id, "No problem. Voice cloning has been cancelled.")
        return True

    return False  # Not a consent reply


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
    send_text(db, patient.id, patient.telegram_chat_id or patient.phone_number, TAKEN_ACK[lang])
