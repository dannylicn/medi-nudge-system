"""
ElevenLabs TTS service.
Generates voice nudge audio and caches as .ogg files.
Falls back gracefully when ELEVENLABS_API_KEY is not set.
"""
import hashlib
import logging
import os
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(settings.MEDIA_STORAGE_PATH, "voice_cache")


def _ensure_cache_dir() -> None:
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


def _cache_path(patient_id: int, medication_id: int, attempt: int, text: str) -> str:
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    return os.path.join(CACHE_DIR, f"{patient_id}_{medication_id}_{attempt}_{text_hash}.ogg")


def generate_voice_message(
    text: str,
    voice_id: str,
    patient_id: int,
    medication_id: int = 0,
    attempt: int = 1,
) -> str | None:
    """
    Generate a TTS .ogg file using ElevenLabs.
    Returns the file path on success, None on failure.
    Cache is keyed by patient_id, medication_id, attempt, and message text hash.
    """
    if not settings.ELEVENLABS_API_KEY:
        logger.debug("ELEVENLABS_API_KEY not set — skipping TTS")
        return None

    if not voice_id:
        voice_id = settings.ELEVENLABS_DEFAULT_VOICE_FEMALE
    if not voice_id:
        logger.debug("No voice_id available — skipping TTS")
        return None

    _ensure_cache_dir()
    cached = _cache_path(patient_id, medication_id, attempt, text)
    if os.path.exists(cached):
        logger.debug("TTS cache hit: %s", cached)
        return cached

    try:
        import httpx

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        resp = httpx.post(
            url,
            headers={
                "xi-api-key": settings.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()

        with open(cached, "wb") as f:
            f.write(resp.content)
        logger.info("TTS generated: %s (%d bytes)", cached, len(resp.content))
        return cached

    except Exception as exc:
        logger.error("ElevenLabs TTS failed: %s", exc)
        return None
