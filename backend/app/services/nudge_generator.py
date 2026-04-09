"""
Nudge message generator.
Primary path: GPT-4o (when OPENAI_API_KEY is set).
Fallback: multilingual template library.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template library — 4 languages × 3 attempt tones
# Placeholders: {name}, {medication}, {days_overdue}
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[str]] = {
    "en": [
        "Hi {name} 👋 Just a friendly reminder that your {medication} refill is {days_overdue} day(s) overdue. Please collect it when you can to keep your health on track! Reply YES when collected.",
        "Hi {name}, we noticed your {medication} is {days_overdue} day(s) overdue. Consistent medication is important for managing your condition. Please collect your refill soon. Reply YES when done.",
        "Hi {name}, your {medication} is now {days_overdue} day(s) overdue. This is important for your health. Your care coordinator will be in touch. Please collect your refill or reply HELP if you need assistance.",
    ],
    "zh": [
        '您好 {name} 👋 温馨提示：您的 {medication} 补药已逾期 {days_overdue} 天。请尽快领取，保持健康！领取后请回复"已领"。',
        '{name}，您的 {medication} 已逾期 {days_overdue} 天。按时服药对您的健康非常重要。请尽快领取补药。完成后请回复"已领"。',
        '{name}，您的 {medication} 已逾期 {days_overdue} 天。请务必领取补药。您的护理协调员将与您联系。需要帮助请回复"帮助"。',
    ],
    "ms": [
        "Hai {name} 👋 Peringatan mesra: ubat {medication} anda telah lepas {days_overdue} hari. Sila ambil ubat anda untuk menjaga kesihatan! Balas YA selepas mengambil.",
        "Hai {name}, ubat {medication} anda telah tertunggak {days_overdue} hari. Mengambil ubat secara konsisten sangat penting. Sila ambil ubat anda segera. Balas YA apabila selesai.",
        "Hai {name}, ubat {medication} anda sudah {days_overdue} hari tertunggak. Koordinator penjagaan anda akan menghubungi anda tidak lama lagi. Balas BANTUAN jika anda memerlukan sokongan.",
    ],
    "ta": [
        "வணக்கம் {name} 👋 உங்கள் {medication} மீண்டும் நிரப்புவது {days_overdue} நாட்கள் தாமதமாகிவிட்டது. உங்கள் ஆரோக்கியத்தை பராமரிக்க தயவுசெய்து எடுக்கவும்! எடுத்த பிறகு YES என பதிலளிக்கவும்.",
        "{name}, உங்கள் {medication} {days_overdue} நாட்கள் தாமதமாகிவிட்டது. தொடர்ந்து மருந்து எடுப்பது முக்கியம். தயவுசெய்து விரைவில் எடுக்கவும். முடிந்தவுடன் YES என பதிலளிக்கவும்.",
        "{name}, உங்கள் {medication} {days_overdue} நாட்கள் தாமதமாகிவிட்டது. உங்கள் பராமரிப்பு ஒருங்கிணைப்பாளர்近இல் தொடர்பு கொள்வார். உதவி தேவையெனில் HELP என பதிலளிக்கவும்.",
    ],
}

SAFETY_ACK: dict[str, str] = {
    "en": "Thank you for telling us. Your care team has been notified immediately. If you feel seriously unwell, please call 995 or go to the nearest A&E now.",
    "zh": "感谢您告知我们。您的护理团队已立即收到通知。如有严重不适，请立即拨打995或前往最近的急诊室。",
    "ms": "Terima kasih kerana memberitahu kami. Pasukan penjagaan anda telah dimaklumkan segera. Jika anda berasa sangat tidak sihat, sila hubungi 995 atau pergi ke A&E terdekat.",
    "ta": "எங்களுக்கு தெரிவித்தற்கு நன்றி. உங்கள் பராமரிப்பு குழுவிற்கு உடனடியாக தகவல் அனுப்பப்பட்டது. தீவிர உடல்நலக்குறைவு இருந்தால் தயவுசெய்து 995 அழைக்கவும்.",
}

QUESTION_ACK: dict[str, str] = {
    "en": "Thank you for your message. Your question has been received and a care coordinator will get back to you soon.",
    "zh": "感谢您的留言。您的问题已收到，护理协调员将尽快与您联系。",
    "ms": "Terima kasih atas mesej anda. Soalan anda telah diterima dan koordinator penjagaan akan menghubungi anda tidak lama lagi.",
    "ta": "உங்கள் செய்திக்கு நன்றி. உங்கள் கேள்வி பெறப்பட்டது; ஒரு பராமரிப்பு ஒருங்கிணைப்பாளர் விரைவில் உங்களை தொடர்பு கொள்வார்.",
}


def generate_nudge_message(
    name: str,
    medication: str,
    days_overdue: int,
    language: str,
    attempt: int,  # 1-indexed
    condition: str = "",
) -> str:
    """
    Generate a nudge message. Uses GPT-4o when available; falls back to templates.
    """
    if settings.OPENAI_API_KEY:
        try:
            return _llm_generate(name, medication, days_overdue, language, attempt, condition)
        except Exception as exc:
            logger.warning("LLM nudge generation failed, falling back to template: %s", exc)

    return _template_generate(name, medication, days_overdue, language, attempt)


def _template_generate(name: str, medication: str, days_overdue: int, language: str, attempt: int) -> str:
    lang = language if language in TEMPLATES else "en"
    idx = min(attempt - 1, len(TEMPLATES[lang]) - 1)
    template = TEMPLATES[lang][idx]
    return template.format(name=name, medication=medication, days_overdue=days_overdue)


def _llm_generate(
    name: str, medication: str, days_overdue: int, language: str, attempt: int, condition: str
) -> str:
    from openai import OpenAI

    tone_map = {
        1: "friendly and warm reminder — no alarm, just caring",
        2: "gentle concern — mention that consistent medication matters for managing their condition",
        3: "urgency — let them know their care coordinator will follow up; they should act soon",
    }
    tone = tone_map.get(attempt, tone_map[1])
    lang_names = {"en": "English", "zh": "Simplified Chinese", "ms": "Malay", "ta": "Tamil"}
    lang_name = lang_names.get(language, "English")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a warm, non-judgmental healthcare assistant sending a WhatsApp reminder "
                    f"to a patient in Singapore about their medication refill. "
                    f"Write a short (3-4 sentence) message in {lang_name}. "
                    f"Tone: {tone}. "
                    f"End with instructions to reply YES when collected, or HELP for questions. "
                    f"Do not use medical jargon. Be culturally sensitive."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Patient name: {name}\n"
                    f"Medication: {medication}\n"
                    f"Days overdue: {days_overdue}\n"
                    f"Condition: {condition or 'chronic disease'}\n"
                    f"Attempt: {attempt} of 3"
                ),
            },
        ],
        max_tokens=200,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def get_safety_ack(language: str) -> str:
    return SAFETY_ACK.get(language, SAFETY_ACK["en"])


def get_question_ack(language: str) -> str:
    return QUESTION_ACK.get(language, QUESTION_ACK["en"])
