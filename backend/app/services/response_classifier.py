"""
Classifies inbound Telegram replies into response types.
Uses keyword/pattern matching; defaults to 'question' for unrecognised messages.
"""
import re

CONFIRMED_PATTERNS = [
    r"\b(yes|ya|ok|okay|done|collected|taken|got it|received|acknowledged|好|可以|boleh|iya|sudah)\b"
]
SIDE_EFFECT_PATTERNS = [
    r"\b(side effect|side-effect|pain|rash|dizzy|dizziness|unwell|sick|nausea|nauseous|vomit\w*|reaction|不舒服|痛|gatal|sakit|loya)\b"
]
NEGATIVE_PATTERNS = [
    r"\b(no\b|nope|cannot|can't|stop\b|don't want|don'?t|tak mau|tidak buat|tidak ambil|不要|quit\b|haven'?t\b|belum)\b"
]
QUESTION_PATTERNS = [
    r"\?",
    r"\b(how|what|when|why|where|which|can i|should i|boleh|bagaimana|怎么|what if|is it|does|will)\b",
]
OPT_OUT_PATTERNS = [
    r"\b(stop|unsubscribe|opt.?out|cancel|quit)\b"
]


def classify_response(text: str) -> str:
    """
    Returns one of: 'confirmed', 'side_effect', 'question', 'negative', 'opt_out'
    Defaults to 'question' as a conservative fallback.
    """
    lowered = text.lower().strip()

    # Opt-out checked first to respect user wishes
    for pat in OPT_OUT_PATTERNS:
        if re.search(pat, lowered):
            return "opt_out"

    for pat in SIDE_EFFECT_PATTERNS:
        if re.search(pat, lowered):
            return "side_effect"

    for pat in CONFIRMED_PATTERNS:
        if re.search(pat, lowered):
            return "confirmed"

    for pat in NEGATIVE_PATTERNS:
        if re.search(pat, lowered):
            return "negative"

    for pat in QUESTION_PATTERNS:
        if re.search(pat, lowered):
            return "question"

    # Conservative fallback — route to coordinator
    return "question"
