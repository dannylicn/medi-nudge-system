"""
Patient onboarding service.
Manages the state machine: invited → consent_pending → language_confirmed
→ medication_capture → confirm → preferences → complete
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Patient, EscalationCase
from app.services import telegram_service, escalation_service

logger = logging.getLogger(__name__)

ONBOARDING_STATES = [
    "invited",
    "consent_pending",
    "complete",
    "drop_off_recovery",
]

LANG_QUICK_REPLIES = "Reply with your language:\n1. English\n2. 中文 (Chinese)\n3. Melayu\n4. தமிழ் (Tamil)"
LANG_MAP = {
    "1": "en", "english": "en",
    "2": "zh", "中文": "zh", "chinese": "zh",
    "3": "ms", "melayu": "ms", "malay": "ms",
    "4": "ta", "தமிழ்": "ta", "tamil": "ta",
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
        "我们将在您的药品需要补充时提醒您。\n\n"
        "使用说明：\n"
        "• 领取药品后请回复 *已领*\n"
        "• 有问题请回复 *帮助*\n"
        "• 服药后不舒服请回复 *副作用*\n"
        "• 随时回复 *停止* 取消服务"
    ),
    "ms": (
        "Selamat datang ke Medi-Nudge! 🎉\n\n"
        "Kami akan mengingatkan anda apabila ubat anda perlu ditambah.\n\n"
        "Cara menggunakan perkhidmatan ini:\n"
        "• Balas *YA* apabila anda mengambil ubat\n"
        "• Balas *BANTUAN* untuk soalan\n"
        "• Balas *KESAN SAMPINGAN* jika anda berasa tidak sihat\n"
        "• Balas *BERHENTI* pada bila-bila masa untuk berhenti"
    ),
    "ta": (
        "Medi-Nudge-க்கு வரவேற்கிறோம்! 🎉\n\n"
        "உங்கள் மருந்துகளை மீண்டும் நிரப்ப வேண்டியிருக்கும்போது நாங்கள் நினைவூட்டுவோம்.\n\n"
        "பயன்பாட்டு வழிகாட்டி:\n"
        "• மருந்து எடுத்தவுடன் *YES* என பதிலளிக்கவும்\n"
        "• கேள்விகள் இருந்தால் *HELP* என பதிலளிக்கவும்\n"
        "• உடல்நலக்குறைவு இருந்தால் *SIDE EFFECT* என பதிலளிக்கவும்\n"
        "• விலக *STOP* என பதிலளிக்கவும்"
    ),
}


def send_invite(db: Session, patient: Patient) -> None:
    """Send initial Telegram invite and set onboarding state."""
    lang = patient.language_preference or "en"
    invite_messages = {
        "en": (
            f"Hi {patient.full_name} 👋 This is Medi-Nudge from your clinic.\n\n"
            "We'd like to support you in managing your medications. "
            "Reply *YES* to join or *NO* to decline.\n\n"
            "Your information will be handled in accordance with PDPA."
        ),
        "zh": (
            f"您好 {patient.full_name} 👋 这是来自您诊所的 Medi-Nudge 服务。\n\n"
            "我们希望帮助您管理用药。回复 *同意* 加入，或 *拒绝* 取消。"
        ),
        "ms": (
            f"Hai {patient.full_name} 👋 Ini adalah Medi-Nudge dari klinik anda.\n\n"
            "Kami ingin membantu anda menguruskan ubat anda. Balas *YA* untuk menyertai atau *TIDAK* untuk menolak."
        ),
        "ta": (
            f"வணக்கம் {patient.full_name} 👋 இது உங்கள் கிளினிக்கிலிருந்து Medi-Nudge.\n\n"
            "உங்கள் மருந்துகளை நிர்வகிக்க உதவ விரும்புகிறோம். சேர *YES* என பதிலளிக்கவும்."
        ),
    }
    message = invite_messages.get(lang, invite_messages["en"])
    telegram_service.send_text(
        db=db, patient_id=patient.id, to_phone=patient.phone_number, body=message
    )
    patient.onboarding_state = "invited"
    db.commit()


def handle_onboarding_reply(db: Session, patient: Patient, text: str) -> None:
    """Route an inbound message through the onboarding state machine."""
    state = patient.onboarding_state
    text_lower = text.strip().lower()

    if state == "invited":
        _handle_invite_reply(db, patient, text_lower)
    elif state == "consent_pending":
        _handle_consent_reply(db, patient, text_lower)


def _handle_invite_reply(db: Session, patient: Patient, text: str) -> None:
    if any(k in text for k in ("yes", "ya", "好", "同意", "setuju")):
        patient.onboarding_state = "consent_pending"
        patient.consent_obtained_at = datetime.utcnow()
        patient.consent_channel = "telegram"
        db.commit()
        telegram_service.send_text(
            db=db,
            patient_id=patient.id,
            to_phone=patient.phone_number,
            body=LANG_QUICK_REPLIES,
        )
    elif any(k in text for k in ("no", "tidak", "不要", "nope")):
        patient.is_active = False
        db.commit()


def _handle_consent_reply(db: Session, patient: Patient, text: str) -> None:
    lang = LANG_MAP.get(text.strip())
    if lang:
        patient.language_preference = lang
        patient.onboarding_state = "complete"
        db.commit()
        welcome = WELCOME_MESSAGES.get(lang, WELCOME_MESSAGES["en"])
        telegram_service.send_text(
            db=db,
            patient_id=patient.id,
            to_phone=patient.phone_number,
            body=welcome,
        )


def handle_drop_off(db: Session, patient: Patient, retry_count: int) -> None:
    """Called by scheduler when patient hasn't responded during onboarding."""
    if retry_count < 2:
        send_invite(db, patient)
    else:
        escalation_service.create_escalation(
            db=db,
            patient_id=patient.id,
            reason="onboarding_drop_off",
        )
        patient.onboarding_state = "drop_off_recovery"
        db.commit()
