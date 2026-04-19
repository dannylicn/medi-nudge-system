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
from app.services import telegram_service, escalation_service, sms_service

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
    "voice_preference",
    "voice_selection",
    "self_registering",
    "drop_off_recovery",
    "medication_confirm_pending",
}

LANG_PROMPT_TEXT = (
    "Please select your preferred language / 请选择语言 / Sila pilih bahasa / மொழியைத் தேர்ந்தெடுக்கவும்:"
)
LANG_BUTTONS = [[
    {"text": "English", "callback_data": "1"},
    {"text": "中文", "callback_data": "2"},
    {"text": "Melayu", "callback_data": "3"},
    {"text": "தமிழ்", "callback_data": "4"},
]]

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
    "en": "Let's set up your medications. How would you like to add them?",
    "zh": "让我们设置您的药物，请选择方式：",
    "ms": "Mari kita sediakan ubat anda. Pilih cara:",
    "ta": "மருந்துகளை அமைப்போம். எவ்வாறு சேர்க்க விரும்புகிறீர்கள்?",
}
MEDICATION_BUTTONS = {
    "en": [
        [{"text": "✅ Confirm on file", "callback_data": "1"}],
        [{"text": "📷 Send a photo", "callback_data": "2"}],
        [{"text": "✏️ Enter manually", "callback_data": "3"}],
    ],
    "zh": [
        [{"text": "✅ 确认已有记录", "callback_data": "1"}],
        [{"text": "📷 发送处方照片", "callback_data": "2"}],
        [{"text": "✏️ 手动输入", "callback_data": "3"}],
    ],
    "ms": [
        [{"text": "✅ Sahkan rekod sedia ada", "callback_data": "1"}],
        [{"text": "📷 Hantar foto preskripsi", "callback_data": "2"}],
        [{"text": "✏️ Masukkan manual", "callback_data": "3"}],
    ],
    "ta": [
        [{"text": "✅ ரெக்கார்டை உறுதிப்படுத்தவும்", "callback_data": "1"}],
        [{"text": "📷 புகைப்படம் அனுப்பவும்", "callback_data": "2"}],
        [{"text": "✏️ கைமுறையாக உள்ளிடவும்", "callback_data": "3"}],
    ],
}

PREFERENCES_PROMPT = {
    "en": "Almost done! When would you like to receive reminders?",
    "zh": "快完成了！您希望何时收到提醒？",
    "ms": "Hampir selesai! Bilakah anda ingin menerima peringatan?",
    "ta": "கிட்டத்தட்ட முடிந்தது! எப்போது நினைவூட்டல்கள் வேண்டும்?",
}
PREFERENCES_BUTTONS = {
    "en": [
        [{"text": "☀️ Morning", "callback_data": "1"}, {"text": "🌤 Afternoon", "callback_data": "2"}],
        [{"text": "🌆 Evening", "callback_data": "3"}, {"text": "🔕 No preference", "callback_data": "4"}],
    ],
    "zh": [
        [{"text": "☀️ 早上", "callback_data": "1"}, {"text": "🌤 下午", "callback_data": "2"}],
        [{"text": "🌆 傍晚", "callback_data": "3"}, {"text": "🔕 无偏好", "callback_data": "4"}],
    ],
    "ms": [
        [{"text": "☀️ Pagi", "callback_data": "1"}, {"text": "🌤 Tengahari", "callback_data": "2"}],
        [{"text": "🌆 Petang", "callback_data": "3"}, {"text": "🔕 Tiada pilihan", "callback_data": "4"}],
    ],
    "ta": [
        [{"text": "☀️ காலை", "callback_data": "1"}, {"text": "🌤 மதியம்", "callback_data": "2"}],
        [{"text": "🌆 மாலை", "callback_data": "3"}, {"text": "🔕 விருப்பமில்லை", "callback_data": "4"}],
    ],
}

VOICE_PREFERENCE_PROMPT = {
    "en": "How would you like to receive medication reminders?",
    "zh": "您希望如何收到用药提醒？",
    "ms": "Bagaimana anda mahu menerima peringatan ubat?",
    "ta": "மருந்து நினைவூட்டல்களை எவ்வாறு பெற விரும்புகிறீர்கள்?",
}
VOICE_PREFERENCE_BUTTONS = {
    "en": [[
        {"text": "💬 Text only", "callback_data": "1"},
        {"text": "🔊 Voice only", "callback_data": "2"},
        {"text": "💬🔊 Both", "callback_data": "3"},
    ]],
    "zh": [[
        {"text": "💬 仅文字", "callback_data": "1"},
        {"text": "🔊 仅语音", "callback_data": "2"},
        {"text": "💬🔊 两者", "callback_data": "3"},
    ]],
    "ms": [[
        {"text": "💬 Teks sahaja", "callback_data": "1"},
        {"text": "🔊 Suara sahaja", "callback_data": "2"},
        {"text": "💬🔊 Kedua-dua", "callback_data": "3"},
    ]],
    "ta": [[
        {"text": "💬 உரை மட்டும்", "callback_data": "1"},
        {"text": "🔊 குரல் மட்டும்", "callback_data": "2"},
        {"text": "💬🔊 இரண்டும்", "callback_data": "3"},
    ]],
}

VOICE_SELECTION_PROMPT = {
    "en": "Choose a voice for your reminders:",
    "zh": "选择提醒语音：",
    "ms": "Pilih suara untuk peringatan anda:",
    "ta": "நினைவூட்டலுக்கு குரல் தேர்ந்தெடுக்கவும்:",
}
VOICE_SELECTION_BUTTONS = {
    "en": [[
        {"text": "👩 Female", "callback_data": "1"},
        {"text": "👨 Male", "callback_data": "2"},
        {"text": "🎙 Record my own", "callback_data": "3"},
    ]],
    "zh": [[
        {"text": "👩 女声", "callback_data": "1"},
        {"text": "👨 男声", "callback_data": "2"},
        {"text": "🎙 录制自己的声音", "callback_data": "3"},
    ]],
    "ms": [[
        {"text": "👩 Wanita", "callback_data": "1"},
        {"text": "👨 Lelaki", "callback_data": "2"},
        {"text": "🎙 Rakam sendiri", "callback_data": "3"},
    ]],
    "ta": [[
        {"text": "👩 பெண் குரல்", "callback_data": "1"},
        {"text": "👨 ஆண் குரல்", "callback_data": "2"},
        {"text": "🎙 சொந்த குரல்", "callback_data": "3"},
    ]],
}

VOICE_RECORD_PROMPT = {
    "en": "Please send a voice message (60-90 seconds) reading the following:\n\n\"Hello, this is a reminder to take your medication. Staying consistent helps manage your health. Remember to collect your refill when it's due.\"\n\nYour voice will be used for your reminders. You can also do this later — a default voice will be used in the meantime.",
    "zh": "请发送一条语音消息（60-90秒），朗读以下内容：\n\n「您好，提醒您按时服药。坚持服药有助于控制您的健康。」\n\n您也可以稍后再录制——目前将使用默认语音。",
    "ms": "Sila hantar mesej suara (60-90 saat) membaca teks berikut:\n\n\"Hai, ini peringatan untuk mengambil ubat anda. Konsisten membantu menjaga kesihatan.\"\n\nAnda juga boleh lakukan nanti — suara lalai akan digunakan buat sementara.",
    "ta": "தயவுசெய்து குரல் செய்தி அனுப்பவும் (60-90 விநாடிகள்):\n\n\"வணக்கம், மருந்து எடுக்க நினைவூட்டல். தொடர்ச்சியாக எடுப்பது ஆரோக்கியத்திற்கு உதவும்.\"\n\nநீங்கள் பின்னர் செய்யலாம் — இப்போதைக்கு இயல்பு குரல் பயன்படுத்தப்படும்.",
}

DELIVERY_MODE_MAP = {"1": "text", "2": "voice", "3": "both"}

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


def generate_caregiver_invite_token(db: Session, patient: Patient) -> str:
    """
    Create a one-time caregiver OnboardingToken and return the deep-link URL.
    Old unused caregiver tokens for this patient are invalidated first.
    """
    now = datetime.utcnow()
    existing = (
        db.query(OnboardingToken)
        .filter(
            OnboardingToken.patient_id == patient.id,
            OnboardingToken.is_caregiver == True,  # noqa: E712
            OnboardingToken.used_at.is_(None),
        )
        .all()
    )
    for t in existing:
        t.used_at = now

    raw = secrets.token_hex(32)
    token_row = OnboardingToken(
        patient_id=patient.id,
        token=raw,
        expires_at=now + timedelta(hours=TOKEN_TTL_HOURS),
        is_caregiver=True,
    )
    db.add(token_row)
    db.commit()

    bot_username = settings.TELEGRAM_BOT_USERNAME or "MediNudgeBot"
    return f"https://t.me/{bot_username}?start={raw}"


def send_caregiver_invite(db: Session, patient: Patient) -> bool:
    """
    Send the caregiver a WhatsApp/SMS invite link if they haven't linked yet.
    Returns True if sent (or stubbed in dev), False if no phone or already linked.
    """
    if not patient.caregiver_phone_number:
        return False
    if patient.caregiver_telegram_id:
        return False  # already linked

    invite_link = generate_caregiver_invite_token(db, patient)
    caregiver_name = patient.caregiver_name or "Caregiver"
    patient_first = patient.full_name.split()[0]

    body = (
        f"Hi {caregiver_name}, you have been listed as a caregiver for {patient_first} "
        f"on Medi-Nudge.\n\n"
        f"Please tap the link below to connect your Telegram account so we can reach you "
        f"if {patient_first} needs help:\n\n"
        f"{invite_link}\n\n"
        f"The link expires in {TOKEN_TTL_HOURS} hours."
    )
    return sms_service.send_whatsapp(patient.caregiver_phone_number, body)


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

        # ── Caregiver invite token ──────────────────────────────────────────
        row = db.query(OnboardingToken).filter(OnboardingToken.token == token_arg).first()
        if row and row.is_caregiver:
            if patient.caregiver_telegram_id and patient.caregiver_telegram_id != chat_id:
                _send_raw(chat_id, "This caregiver slot is already linked. Please contact the clinic if this is an error.")
                return
            patient.caregiver_telegram_id = chat_id
            db.commit()
            _send_raw(
                chat_id,
                f"✅ You are now registered as a caregiver for {patient.full_name.split()[0]} on Medi-Nudge.\n\n"
                "You will be notified here if they miss medications or need assistance.",
            )
            return

        # ── Patient invite token ────────────────────────────────────────────
        if patient.telegram_chat_id and patient.telegram_chat_id != chat_id:
            _send_raw(chat_id, "This patient record is already linked to another account. Please contact your clinic.")
            return
        patient.telegram_chat_id = chat_id
        patient.onboarding_state = "invited"
        db.commit()
        db.refresh(patient)
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
        "voice_preference": _handle_voice_preference_reply,
        "voice_selection": _handle_voice_selection_reply,
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
        _send_patient_keyboard(db, patient, LANG_PROMPT_TEXT, LANG_BUTTONS)
    elif any(k in text for k in ("no", "tidak", "不要", "nope", "拒绝")):
        patient.is_active = False
        db.commit()


def _handle_consent_reply(db: Session, patient: Patient, text: str) -> None:
    lang = LANG_MAP.get(text.strip())
    if lang:
        patient.language_preference = lang
        patient.onboarding_state = "language_confirmed"
        db.commit()
        _send_patient_keyboard(
            db, patient,
            MEDICATION_PROMPT.get(lang, MEDICATION_PROMPT["en"]),
            MEDICATION_BUTTONS.get(lang, MEDICATION_BUTTONS["en"]),
        )
    else:
        _send_patient_keyboard(db, patient, LANG_PROMPT_TEXT, LANG_BUTTONS)


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
            _send_patient_keyboard(
                db, patient,
                "No medications on file yet. How would you like to add them?",
                MEDICATION_BUTTONS.get(lang, MEDICATION_BUTTONS["en"])[1:],  # only photo + manual options
            )
    elif choice == "2":
        _send_patient(db, patient, "Please send a photo of your prescription or medicine label.")
    elif choice == "3":
        patient.onboarding_state = "confirm"
        db.commit()
        _send_patient(db, patient, "Please type the name of your first medication (e.g. Metformin 500mg). Reply *DONE* when finished.")
    else:
        _send_patient_keyboard(
            db, patient,
            MEDICATION_PROMPT.get(lang, MEDICATION_PROMPT["en"]),
            MEDICATION_BUTTONS.get(lang, MEDICATION_BUTTONS["en"]),
        )


def _handle_confirm_reply(db: Session, patient: Patient, text: str) -> None:
    if any(k in text for k in ("yes", "ya", "confirm", "好", "是", "setuju")):
        db.query(PatientMedication).filter(
            PatientMedication.patient_id == patient.id,
            PatientMedication.is_active == False,  # noqa: E712
        ).update({"is_active": True})
        patient.onboarding_state = "preferences"
        db.commit()
        lang = patient.language_preference or "en"
        _send_patient_keyboard(
            db, patient,
            PREFERENCES_PROMPT.get(lang, PREFERENCES_PROMPT["en"]),
            PREFERENCES_BUTTONS.get(lang, PREFERENCES_BUTTONS["en"]),
        )
    elif text.strip() == "done":
        _send_patient(db, patient, "Thank you! Reply *YES* to confirm your medication list.")
    elif any(k in text for k in ("no", "tidak", "不", "nope")):
        lang = patient.language_preference or "en"
        patient.onboarding_state = "medication_capture"
        db.commit()
        _send_patient_keyboard(
            db, patient,
            MEDICATION_PROMPT.get(lang, MEDICATION_PROMPT["en"]),
            MEDICATION_BUTTONS.get(lang, MEDICATION_BUTTONS["en"]),
        )
    else:
        # Treat as manual entry — run through medicine verification gate
        from app.services import agent_service
        agent_service.verify_and_confirm_medication(patient, text, db)


def _handle_preferences_reply(db: Session, patient: Patient, text: str) -> None:
    choice = text.strip()
    window = CONTACT_WINDOWS.get(choice)
    if window is None:
        lang = patient.language_preference or "en"
        _send_patient_keyboard(
            db, patient,
            PREFERENCES_PROMPT.get(lang, PREFERENCES_PROMPT["en"]),
            PREFERENCES_BUTTONS.get(lang, PREFERENCES_BUTTONS["en"]),
        )
        return
    start, end = window
    patient.contact_window_start = start
    patient.contact_window_end = end
    patient.onboarding_state = "voice_preference"
    db.commit()
    lang = patient.language_preference or "en"
    _send_patient_keyboard(
        db, patient,
        VOICE_PREFERENCE_PROMPT.get(lang, VOICE_PREFERENCE_PROMPT["en"]),
        VOICE_PREFERENCE_BUTTONS.get(lang, VOICE_PREFERENCE_BUTTONS["en"]),
    )


def _handle_voice_preference_reply(db: Session, patient: Patient, text: str) -> None:
    choice = text.strip()
    mode = DELIVERY_MODE_MAP.get(choice)
    if mode is None:
        lang = patient.language_preference or "en"
        _send_patient_keyboard(
            db, patient,
            VOICE_PREFERENCE_PROMPT.get(lang, VOICE_PREFERENCE_PROMPT["en"]),
            VOICE_PREFERENCE_BUTTONS.get(lang, VOICE_PREFERENCE_BUTTONS["en"]),
        )
        return

    patient.nudge_delivery_mode = mode
    if mode == "text":
        _complete_onboarding(db, patient)
    else:
        patient.onboarding_state = "voice_selection"
        db.commit()
        lang = patient.language_preference or "en"
        _send_patient_keyboard(
            db, patient,
            VOICE_SELECTION_PROMPT.get(lang, VOICE_SELECTION_PROMPT["en"]),
            VOICE_SELECTION_BUTTONS.get(lang, VOICE_SELECTION_BUTTONS["en"]),
        )


def _handle_voice_selection_reply(db: Session, patient: Patient, text: str) -> None:
    choice = text.strip()
    if choice == "1":
        patient.selected_voice_id = settings.ELEVENLABS_DEFAULT_VOICE_FEMALE or None
    elif choice == "2":
        patient.selected_voice_id = settings.ELEVENLABS_DEFAULT_VOICE_MALE or None
    elif choice == "3":
        # Use default voice now; patient will send a voice message post-onboarding to clone
        patient.selected_voice_id = settings.ELEVENLABS_DEFAULT_VOICE_FEMALE or None
        db.commit()
        lang = patient.language_preference or "en"
        _send_patient(db, patient, VOICE_RECORD_PROMPT.get(lang, VOICE_RECORD_PROMPT["en"]))
        _complete_onboarding(db, patient)
        return
    else:
        lang = patient.language_preference or "en"
        _send_patient_keyboard(
            db, patient,
            VOICE_SELECTION_PROMPT.get(lang, VOICE_SELECTION_PROMPT["en"]),
            VOICE_SELECTION_BUTTONS.get(lang, VOICE_SELECTION_BUTTONS["en"]),
        )
        return
    _complete_onboarding(db, patient)


def _complete_onboarding(db: Session, patient: Patient) -> None:
    """Finalize onboarding: set state to complete, send welcome, invite caregiver."""
    patient.onboarding_state = "complete"
    patient.is_active = True
    db.commit()
    lang = patient.language_preference or "en"
    _send_patient(db, patient, WELCOME_MESSAGES.get(lang, WELCOME_MESSAGES["en"]))

    # Send caregiver invite via WhatsApp/SMS if phone is set and not yet linked
    try:
        send_caregiver_invite(db, patient)
    except Exception as exc:
        logger.warning("Caregiver invite send failed for patient %s: %s", patient.id, exc)


# ---------------------------------------------------------------------------
# Drop-off recovery
# ---------------------------------------------------------------------------

def handle_drop_off(db: Session, patient: Patient, retry_count: int) -> None:
    # Voice preference or voice selection timeout — default to text, complete onboarding
    if patient.onboarding_state in ("voice_preference", "voice_selection") and retry_count >= 1:
        patient.nudge_delivery_mode = "text"
        _complete_onboarding(db, patient)
        return

    if patient.onboarding_state == "preferences" and retry_count >= 1:
        patient.contact_window_start = None
        patient.contact_window_end = None
        _complete_onboarding(db, patient)
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


def _send_patient_keyboard(db: Session, patient: Patient, body: str, buttons: list) -> None:
    if not patient.telegram_chat_id:
        logger.warning("Cannot send keyboard to patient %s — telegram_chat_id not set", patient.id)
        return
    telegram_service.send_keyboard(
        db=db, patient_id=patient.id, to_phone=patient.telegram_chat_id, body=body, buttons=buttons
    )


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
