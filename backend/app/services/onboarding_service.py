"""
Patient onboarding service.
Manages the state machine:
  invited → consent_pending → language_confirmed → medication_capture
          → confirm → preferences → complete

Entry paths:
  - Coordinator-initiated: generate_invite_token() → QR code → patient scans → /start TOKEN
  - Patient self-initiated: /start (no token) → identity_verification → NRIC lookup
"""
import base64
import io
import logging
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings, hash_sha256
from app.models.models import EscalationCase, OnboardingToken, Patient, PatientMedication
from app.services import telegram_service, escalation_service

logger = logging.getLogger(__name__)

TOKEN_TTL_HOURS = 72

ONBOARDING_STATES = {
    "identity_verification",
    "invited",
    "consent_pending",
    "language_confirmed",
    "medication_capture",
    "confirm",
    "preferences",
    "self_registering",
    "drop_off_recovery",
    "medication_confirm_pending",
}

LANG_QUICK_REPLIES = (
    "Please select your preferred language / 请选择语言 / Sila pilih bahasa / மொழியைத் தேர்ந்தெடுக்கவும்:\n"
    "1. English\n2. 中文 (Chinese)\n3. Melayu\n4. தமிழ் (Tamil)"
)
LANG_MAP = {
    "1": "en", "english": "en",
    "2": "zh", "中文": "zh", "chinese": "zh",
    "3": "ms", "melayu": "ms", "malay": "ms",
    "4": "ta", "தமிழ்": "ta", "tamil": "ta",
}

CONSENT_MESSAGES = {
    "en": (
        "Hi {name} 👋 This is Medi-Nudge from your clinic.\n\n"
        "We'd like to support you in managing your medications. "
        "Reply *YES* to join or *NO* to decline.\n\n"
        "Your information will be handled in accordance with PDPA."
    ),
    "zh": (
        "您好 {name} 👋 这是来自您诊所的 Medi-Nudge 服务。\n\n"
        "我们希望帮助您管理用药。回复 *同意* 加入，或 *拒绝* 取消。"
    ),
    "ms": (
        "Hai {name} 👋 Ini adalah Medi-Nudge dari klinik anda.\n\n"
        "Kami ingin membantu anda menguruskan ubat anda. Balas *YA* untuk menyertai atau *TIDAK* untuk menolak."
    ),
    "ta": (
        "வணக்கம் {name} 👋 இது உங்கள் கிளினிக்கிலிருந்து Medi-Nudge.\n\n"
        "உங்கள் மருந்துகளை நிர்வகிக்க உதவ விரும்புகிறோம். சேர *YES* என பதிலளிக்கவும் அல்லது *NO* என மறுக்கவும்."
    ),
}

MEDICATION_PROMPT = {
    "en": (
        "Let's set up your medications. How would you like to add them?\n\n"
        "1️⃣ Confirm medications already on file\n"
        "2️⃣ Send a photo of your prescription\n"
        "3️⃣ Enter medications manually\n\n"
        "Reply 1, 2, or 3."
    ),
    "zh": "让我们设置您的药物。\n1️⃣ 确认已有记录\n2️⃣ 发送处方照片\n3️⃣ 手动输入\n\n回复 1、2 或 3。",
    "ms": "Mari kita sediakan ubat anda.\n1️⃣ Sahkan rekod sedia ada\n2️⃣ Hantar foto preskripsi\n3️⃣ Masukkan manual\n\nBalas 1, 2 atau 3.",
    "ta": "மருந்துகளை அமைப்போம்.\n1️⃣ ரெக்கார்டை உறுதிப்படுத்தவும்\n2️⃣ புகைப்படம் அனுப்பவும்\n3️⃣ கைமுறையாக உள்ளிடவும்\n\n1, 2 அல்லது 3 என பதிலளிக்கவும்.",
}

PREFERENCES_PROMPT = {
    "en": (
        "Almost done! When would you like to receive reminders?\n\n"
        "1. Morning (8am–12pm)\n2. Afternoon (12pm–5pm)\n3. Evening (5pm–9pm)\n4. No preference\n\nReply 1–4."
    ),
    "zh": "快完成了！您希望何时收到提醒？\n1. 早上\n2. 下午\n3. 傍晚\n4. 无偏好\n\n回复 1–4。",
    "ms": "Hampir selesai! Bilakah anda ingin menerima peringatan?\n1. Pagi\n2. Tengahari\n3. Petang\n4. Tiada pilihan\n\nBalas 1–4.",
    "ta": "கிட்டத்தட்ட முடிந்தது! எப்போது நினைவூட்டல்கள் வேண்டும்?\n1. காலை\n2. மதியம்\n3. மாலை\n4. விருப்பமில்லை\n\n1–4 என பதிலளிக்கவும்.",
}

CONTACT_WINDOWS = {
    "1": ("08:00", "12:00"),
    "2": ("12:00", "17:00"),
    "3": ("17:00", "21:00"),
    "4": (None, None),
}

WELCOME_MESSAGES = {
    "en": (
        "Welcome to Medi-Nudge! 🎉\n\n"
        "We'll remind you when your medications are due for refill.\n\n"
        "How to use this service:\n"
        "• Reply *YES* when you've collected your medication\n"
        "• Reply *HELP* if you have questions\n"
        "• Reply *SIDE EFFECT* if you feel unwell after taking your medicine\n"
        "• Reply *STOP* at any time to opt out"
    ),
    "zh": (
        "欢迎使用 Medi-Nudge！🎉\n\n"
        "• 领取药品后请回复 *已领*\n• 有问题请回复 *帮助*\n• 服药后不舒服请回复 *副作用*\n• 随时回复 *停止* 取消服务"
    ),
    "ms": (
        "Selamat datang ke Medi-Nudge! 🎉\n\n"
        "• Balas *YA* apabila anda mengambil ubat\n• Balas *BANTUAN* untuk soalan\n"
        "• Balas *KESAN SAMPINGAN* jika tidak sihat\n• Balas *BERHENTI* untuk berhenti"
    ),
    "ta": (
        "Medi-Nudge-க்கு வரவேற்கிறோம்! 🎉\n\n"
        "• *YES* — மருந்து எடுத்தவுடன்\n• *HELP* — கேள்விகள்\n"
        "• *SIDE EFFECT* — உடல்நலக்குறைவு\n• *STOP* — விலக"
    ),
}


# ---------------------------------------------------------------------------
# Token + QR generation
# ---------------------------------------------------------------------------

def generate_invite_token(db: Session, patient: Patient) -> dict:
    """
    Create a one-time OnboardingToken and return the deep-link + base64 QR PNG.
    Existing unused tokens for this patient are invalidated first.
    """
    now = datetime.utcnow()
    existing = (
        db.query(OnboardingToken)
        .filter(OnboardingToken.patient_id == patient.id, OnboardingToken.used_at.is_(None))
        .all()
    )
    for t in existing:
        t.used_at = now

    raw = secrets.token_hex(32)
    token_row = OnboardingToken(
        patient_id=patient.id,
        token=raw,
        expires_at=now + timedelta(hours=TOKEN_TTL_HOURS),
    )
    db.add(token_row)
    db.commit()

    bot_username = settings.TELEGRAM_BOT_USERNAME or "MediNudgeBot"
    invite_link = f"https://t.me/{bot_username}?start={raw}"
    qr_b64 = _generate_qr_b64(invite_link)
    return {"invite_link": invite_link, "qr_code_png_b64": qr_b64}


def _generate_qr_b64(data: str) -> str:
    try:
        import qrcode  # type: ignore
        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except ImportError:
        logger.warning("qrcode library not installed — QR generation skipped")
        return ""


def validate_and_consume_token(db: Session, raw_token: str) -> "Patient | None":
    row = db.query(OnboardingToken).filter(OnboardingToken.token == raw_token).first()
    if not row or row.used_at is not None or datetime.utcnow() > row.expires_at:
        return None
    row.used_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row.patient


# ---------------------------------------------------------------------------
# /start entry point (called from webhook)
# ---------------------------------------------------------------------------

def handle_start_command(db: Session, chat_id: str, token_arg: "str | None") -> None:
    if token_arg:
        patient = validate_and_consume_token(db, token_arg)
        if patient is None:
            row = db.query(OnboardingToken).filter(OnboardingToken.token == token_arg).first()
            if row and row.used_at:
                _send_raw(chat_id, "This invite link has already been used. If you need help, reply HELP.")
            else:
                _send_raw(chat_id, "This invite link has expired. Please ask your clinic for a new one.")
            return
        if patient.telegram_chat_id and patient.telegram_chat_id != chat_id:
            _send_raw(chat_id, "This patient record is already linked to another account. Please contact your clinic.")
            return
        patient.telegram_chat_id = chat_id
        patient.onboarding_state = "invited"
        db.commit()
        _send_consent(db, patient)
        return

    existing = db.query(Patient).filter(Patient.telegram_chat_id == chat_id).first()
    if existing:
        if existing.onboarding_state == "complete":
            _send_raw(chat_id, "You're already enrolled in Medi-Nudge. Reply HELP for assistance.")
        else:
            handle_onboarding_reply(db, existing, "")
        return

    stub = Patient(
        full_name="Unknown",
        phone_number=f"tg_{chat_id}",
        telegram_chat_id=chat_id,
        onboarding_state="identity_verification",
        is_active=False,
    )
    db.add(stub)
    db.commit()
    _send_raw(
        chat_id,
        "Welcome to Medi-Nudge! 👋\n\n"
        "To link your account, please enter your full NRIC/FIN number (e.g. S1234567A).",
    )


# ---------------------------------------------------------------------------
# State machine dispatcher
# ---------------------------------------------------------------------------

def handle_onboarding_reply(db: Session, patient: Patient, text: str) -> None:
    state = patient.onboarding_state
    text_lower = text.strip().lower()

    dispatch = {
        "identity_verification": handle_identity_verification,
        "invited": _handle_invite_reply,
        "consent_pending": _handle_consent_reply,
        "language_confirmed": _handle_language_reply,
        "medication_capture": _handle_medication_capture,
        "confirm": _handle_confirm_reply,
        "preferences": _handle_preferences_reply,
    }

    handler = dispatch.get(state)
    if handler:
        handler(db, patient, text_lower)
    else:
        _send_patient(db, patient, "Reply HELP for assistance or wait for your care team to contact you.")
        escalation_service.create_escalation(db=db, patient_id=patient.id, reason="patient_question")


def handle_identity_verification(db: Session, patient: Patient, text: str) -> None:
    chat_id = patient.telegram_chat_id
    nric_input = text.strip().upper()
    if not nric_input:
        _send_raw(chat_id, "Please enter your NRIC/FIN number to continue.")
        return

    nric_hash = hash_sha256(nric_input)
    matched = (
        db.query(Patient)
        .filter(Patient.nric_hash == nric_hash, Patient.telegram_chat_id.is_(None))
        .first()
    )

    if matched:
        patient.telegram_chat_id = None  # release unique value before assigning to matched
        db.flush()
        matched.telegram_chat_id = chat_id
        matched.onboarding_state = "invited"
        db.delete(patient)
        db.commit()
        _send_consent(db, matched)
        return

    patient.onboarding_state = "self_registering"
    db.commit()
    escalation_service.create_escalation(db=db, patient_id=patient.id, reason="self_registration_review")
    _send_raw(
        chat_id,
        "Your registration is under review. "
        "A care coordinator will be in touch within 1 business day.",
    )


def _send_consent(db: Session, patient: Patient) -> None:
    lang = patient.language_preference or "en"
    msg = CONSENT_MESSAGES.get(lang, CONSENT_MESSAGES["en"]).format(name=patient.full_name)
    _send_patient(db, patient, msg)


def _handle_invite_reply(db: Session, patient: Patient, text: str) -> None:
    if any(k in text for k in ("yes", "ya", "好", "同意", "setuju")):
        patient.onboarding_state = "consent_pending"
        patient.consent_obtained_at = datetime.utcnow()
        patient.consent_channel = "telegram"
        db.commit()
        _send_patient(db, patient, LANG_QUICK_REPLIES)
    elif any(k in text for k in ("no", "tidak", "不要", "nope", "拒绝")):
        patient.is_active = False
        db.commit()


def _handle_consent_reply(db: Session, patient: Patient, text: str) -> None:
    lang = LANG_MAP.get(text.strip())
    if lang:
        patient.language_preference = lang
        patient.onboarding_state = "language_confirmed"
        db.commit()
        _send_patient(db, patient, MEDICATION_PROMPT.get(lang, MEDICATION_PROMPT["en"]))
    else:
        _send_patient(db, patient, LANG_QUICK_REPLIES)


def _handle_language_reply(db: Session, patient: Patient, text: str) -> None:
    _handle_medication_capture(db, patient, text)


def _handle_medication_capture(db: Session, patient: Patient, text: str) -> None:
    lang = patient.language_preference or "en"
    choice = text.strip()

    if choice == "1":
        meds = db.query(PatientMedication).filter(PatientMedication.patient_id == patient.id).all()
        if meds:
            from app.models.models import Medication as MedModel
            lines = []
            for pm in meds:
                med = db.query(MedModel).filter(MedModel.id == pm.medication_id).first()
                if med:
                    lines.append(f"• {med.name}" + (f" ({pm.dosage})" if pm.dosage else ""))
            _send_patient(
                db, patient,
                "Your medications on file:\n\n" + "\n".join(lines) + "\n\nIs this correct? Reply *YES* to confirm or *NO* to re-enter."
            )
            patient.onboarding_state = "confirm"
            db.commit()
        else:
            _send_patient(db, patient, "No medications on file. Send a photo (reply 2) or enter manually (reply 3).")
    elif choice == "2":
        _send_patient(db, patient, "Please send a photo of your prescription or medicine label.")
    elif choice == "3":
        patient.onboarding_state = "confirm"
        db.commit()
        _send_patient(db, patient, "Please type the name of your first medication (e.g. Metformin 500mg). Reply *DONE* when finished.")
    else:
        _send_patient(db, patient, MEDICATION_PROMPT.get(lang, MEDICATION_PROMPT["en"]))


def _handle_confirm_reply(db: Session, patient: Patient, text: str) -> None:
    if any(k in text for k in ("yes", "ya", "confirm", "好", "是", "setuju")):
        db.query(PatientMedication).filter(
            PatientMedication.patient_id == patient.id,
            PatientMedication.is_active == False,  # noqa: E712
        ).update({"is_active": True})
        patient.onboarding_state = "preferences"
        db.commit()
        lang = patient.language_preference or "en"
        _send_patient(db, patient, PREFERENCES_PROMPT.get(lang, PREFERENCES_PROMPT["en"]))
    elif text.strip() == "done":
        _send_patient(db, patient, "Thank you! Reply *YES* to confirm your medication list.")
    elif any(k in text for k in ("no", "tidak", "不", "nope")):
        lang = patient.language_preference or "en"
        patient.onboarding_state = "medication_capture"
        db.commit()
        _send_patient(db, patient, MEDICATION_PROMPT.get(lang, MEDICATION_PROMPT["en"]))
    else:
        # Treat as manual entry — run through medicine verification gate
        from app.services import agent_service
        agent_service.verify_and_confirm_medication(patient, text, db)


def _handle_preferences_reply(db: Session, patient: Patient, text: str) -> None:
    choice = text.strip()
    window = CONTACT_WINDOWS.get(choice)
    if window is None:
        lang = patient.language_preference or "en"
        _send_patient(db, patient, PREFERENCES_PROMPT.get(lang, PREFERENCES_PROMPT["en"]))
        return
    start, end = window
    patient.contact_window_start = start
    patient.contact_window_end = end
    patient.onboarding_state = "complete"
    patient.is_active = True
    db.commit()
    lang = patient.language_preference or "en"
    _send_patient(db, patient, WELCOME_MESSAGES.get(lang, WELCOME_MESSAGES["en"]))


# ---------------------------------------------------------------------------
# Drop-off recovery
# ---------------------------------------------------------------------------

def handle_drop_off(db: Session, patient: Patient, retry_count: int) -> None:
    if patient.onboarding_state == "preferences" and retry_count >= 1:
        patient.contact_window_start = None
        patient.contact_window_end = None
        patient.onboarding_state = "complete"
        patient.is_active = True
        db.commit()
        lang = patient.language_preference or "en"
        _send_patient(db, patient, WELCOME_MESSAGES.get(lang, WELCOME_MESSAGES["en"]))
        return

    if retry_count < 2:
        if patient.telegram_chat_id:
            _send_consent(db, patient)
    else:
        escalation_service.create_escalation(db=db, patient_id=patient.id, reason="onboarding_drop_off")
        patient.onboarding_state = "drop_off_recovery"
        db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send_patient(db: Session, patient: Patient, body: str) -> None:
    if not patient.telegram_chat_id:
        logger.warning("Cannot send to patient %s — telegram_chat_id not set", patient.id)
        return
    telegram_service.send_text(db=db, patient_id=patient.id, to_phone=patient.telegram_chat_id, body=body)


def _send_raw(chat_id: str, body: str) -> None:
    import httpx
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.info("Simulated reply to %s: %s", chat_id, body)
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": body, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as exc:
        logger.error("Failed to send raw message to %s: %s", chat_id, exc)


def send_invite(db: Session, patient: Patient) -> None:
    """Legacy shim — now generates invite token instead of direct message."""
    generate_invite_token(db, patient)
