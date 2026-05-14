"""
Medication information card generator.
Primary: LLM-generated (GPT-4o / Ollama).
Fallback: static multilingual templates.
Safety filter: discards any LLM output containing clinical guidance words.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

_SAFETY_WORDS = ("dosage", "interaction", "contraindicated", "stop taking")

_FALLBACK_TEMPLATES: dict[str, str] = {
    "en": (
        "ℹ️ About {name}:\n"
        "This medication helps manage your chronic condition. "
        "Common things to watch for include nausea, dizziness, or stomach upset — "
        "these often improve after a few days.\n\n"
        "Reply SIDE EFFECT if you feel unwell — your care team will respond."
    ),
    "zh": (
        "ℹ️ 关于 {name}：\n"
        "这种药物有助于控制您的慢性病。"
        "常见的注意事项包括恶心、头晕或胃部不适——这些通常在几天后改善。\n\n"
        "如感不适，请回复「副作用」——您的护理团队会回应。"
    ),
    "ms": (
        "ℹ️ Tentang {name}:\n"
        "Ubat ini membantu mengawal keadaan kronik anda. "
        "Perkara biasa yang perlu diperhatikan termasuk loya, pening, atau sakit perut — "
        "ini selalunya bertambah baik selepas beberapa hari.\n\n"
        "Balas KESAN SAMPINGAN jika anda berasa tidak sihat — pasukan penjagaan anda akan bertindak balas."
    ),
    "ta": (
        "ℹ️ {name} பற்றி:\n"
        "இந்த மருந்து உங்கள் நாள்பட்ட நோயை கட்டுப்படுத்த உதவுகிறது. "
        "கவனிக்க வேண்டிய பொதுவான அறிகுறிகள்: குமட்டல், தலைச்சுற்றல் அல்லது வயிற்று வலி — "
        "இவை சில நாட்களில் சரியாகும்.\n\n"
        "உடல்நலக்குறைவு இருந்தால் SIDE EFFECT என பதிலளிக்கவும் — உங்கள் குழு பதிலளிக்கும்."
    ),
}

_LANG_NAMES = {"en": "English", "zh": "Simplified Chinese", "ms": "Malay", "ta": "Tamil"}


def generate_info_card(
    medication_name: str,
    language: str,
    condition: str | None = None,
) -> str:
    """Generate a safe, brief medication information card for a patient.

    Uses LLM when available. Falls back to static templates. A content safety
    filter rejects any LLM output that contains clinical guidance words.
    """
    if settings.OPENAI_API_KEY or settings.LLM_BASE_URL:
        try:
            content = _llm_info_card(medication_name, language, condition)
            if any(w in content.lower() for w in _SAFETY_WORDS):
                logger.warning(
                    "Info card safety filter triggered for '%s' — using fallback template",
                    medication_name,
                )
            else:
                return content
        except Exception as exc:
            logger.warning(
                "Info card LLM failed for '%s': %s — using fallback template",
                medication_name,
                exc,
            )

    tmpl = _FALLBACK_TEMPLATES.get(language, _FALLBACK_TEMPLATES["en"])
    return tmpl.format(name=medication_name)


_CHECKIN_FALLBACK: dict[str, str] = {
    "en": (
        "Hi {name} 👋 You've been taking {medication} for a few days now. "
        "Common things to watch for include nausea, dizziness, or stomach upset. "
        "How are you feeling? Share in your own words — we're here to help."
    ),
    "zh": (
        "您好 {name} 👋 您服用 {medication} 已经几天了。"
        "常见的注意事项包括恶心、头晕或胃部不适。"
        "您感觉怎么样？请用您自己的话告诉我们——我们在这里帮助您。"
    ),
    "ms": (
        "Hai {name} 👋 Anda telah mengambil {medication} selama beberapa hari. "
        "Perkara biasa yang perlu diperhatikan termasuk loya, pening atau sakit perut. "
        "Bagaimana perasaan anda? Kongsikan dengan kata-kata anda sendiri — kami sedia membantu."
    ),
    "ta": (
        "வணக்கம் {name} 👋 நீங்கள் {medication} எடுக்கத் தொடங்கி சில நாட்கள் ஆகிறது. "
        "குமட்டல், தலைச்சுற்றல் அல்லது வயிற்று வலி பொதுவான அறிகுறிகள். "
        "நீங்கள் எப்படி உணர்கிறீர்கள்? உங்கள் சொந்த வார்த்தைகளில் சொல்லுங்கள் — நாங்கள் உதவ இங்கே இருக்கிறோம்."
    ),
}


def generate_checkin_message(
    medication_name: str,
    language: str,
    patient_name: str,
    condition: str | None = None,
) -> str:
    """Generate a personalised side-effect check-in message.

    Names specific side effects for the medication and invites the patient
    to reply in free text. No button instructions are included.
    """
    if settings.OPENAI_API_KEY or settings.LLM_BASE_URL:
        try:
            content = _llm_checkin_message(medication_name, language, patient_name, condition)
            if not content:
                raise ValueError("LLM returned empty content")
            return content
        except Exception as exc:
            logger.warning(
                "Check-in message LLM failed for '%s': %s — using fallback",
                medication_name, exc,
            )
    return _CHECKIN_FALLBACK.get(language, _CHECKIN_FALLBACK["en"]).format(
        name=patient_name, medication=medication_name,
    )


def _llm_checkin_message(
    medication_name: str, language: str, patient_name: str, condition: str | None
) -> str:
    from openai import OpenAI

    lang_name = _LANG_NAMES.get(language, "English")
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY or "ollama",
        base_url=settings.LLM_BASE_URL or None,
    )
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a warm medication support assistant for a Singapore clinic. "
                    f"Generate a short, friendly check-in message to a patient who started "
                    f"taking a medication a few days ago. "
                    f"Rules:\n"
                    f"- Greet them by first name warmly.\n"
                    f"- Name 2-3 specific common side effects to watch for with THIS medication "
                    f"(not generic ones — be specific to the drug).\n"
                    f"- Ask how they are feeling in an open, inviting way that encourages them "
                    f"to reply in their own words.\n"
                    f"- Do NOT include any button instructions, keywords like 'SIDE EFFECT', "
                    f"or reply prompts.\n"
                    f"- Write in {lang_name}. Be warm, conversational, not clinical. Max 4 sentences."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Patient first name: {patient_name}\n"
                    f"Medication: {medication_name}\n"
                    f"Condition: {condition or 'chronic disease'}"
                ),
            },
        ],
        temperature=0.4,
        max_tokens=200,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("LLM returned empty content")
    return content


def _llm_info_card(medication_name: str, language: str, condition: str | None) -> str:
    from openai import OpenAI

    lang_name = _LANG_NAMES.get(language, "English")
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY or "ollama",
        base_url=settings.LLM_BASE_URL or None,
    )
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medication information assistant for a Singapore clinic. "
                    "Generate a short, safe-to-share medication information message for a patient. "
                    "Rules:\n"
                    "- State in ONE sentence what condition this medication is commonly prescribed for.\n"
                    "- List exactly 2-3 common side effects to watch for (common ones only, not rare or serious).\n"
                    "- Do NOT comment on dosage, drug interactions, or this patient's specific situation.\n"
                    f"- End EVERY message with: 'Reply SIDE EFFECT if you feel unwell — your care team will respond.'\n"
                    f"- Write in {lang_name}. Be warm but factual. Max 5 sentences total."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Medication: {medication_name}\n"
                    f"Patient condition: {condition or 'chronic disease'}"
                ),
            },
        ],
        temperature=0.3,
        max_tokens=200,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("LLM returned empty content")
    return content
