"""
ElevenLabs Instant Voice Cloning service.
Clones a caregiver's voice from a single audio sample.
Requires dual consent (patient + donor) before cloning.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import VoiceProfile, Patient

logger = logging.getLogger(__name__)


def clone_voice(db: Session, voice_profile: VoiceProfile) -> bool:
    """
    Call ElevenLabs IVC API to clone a voice from the stored sample.
    Returns True on success, False on failure.
    Requires both patient_consent_at and donor_consent_at to be set.
    """
    is_self_clone = voice_profile.donor_name == "self"
    if is_self_clone:
        if not voice_profile.patient_consent_at:
            logger.error("Cannot clone: patient consent not met for self-clone VoiceProfile %s", voice_profile.id)
            return False
    else:
        if not voice_profile.patient_consent_at or not voice_profile.donor_consent_at:
            logger.error("Cannot clone: dual consent not met for VoiceProfile %s", voice_profile.id)
            return False

    if not voice_profile.sample_file_path:
        logger.error("Cannot clone: no sample file for VoiceProfile %s", voice_profile.id)
        return False

    if not settings.ELEVENLABS_API_KEY:
        logger.warning("ELEVENLABS_API_KEY not set — cannot clone voice")
        return False

    try:
        import httpx

        donor_name = voice_profile.donor_name or "Caregiver"
        with open(voice_profile.sample_file_path, "rb") as f:
            sample_bytes = f.read()

        resp = httpx.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            data={
                "name": f"medi-nudge-{voice_profile.patient_id}-{donor_name}",
                "description": f"Voice for patient {voice_profile.patient_id}",
            },
            files=[("files", (f"sample_{voice_profile.id}.ogg", sample_bytes, "audio/ogg"))],
            timeout=60,
        )
        if resp.status_code != 200:
            logger.error(
                "ElevenLabs clone API returned %s: %s",
                resp.status_code, resp.text,
            )
        resp.raise_for_status()
        data = resp.json()
        voice_profile.elevenlabs_voice_id = data["voice_id"]
        db.commit()

        # Update the patient's selected voice to the cloned one
        patient = db.query(Patient).filter(Patient.id == voice_profile.patient_id).first()
        if patient:
            patient.selected_voice_id = data["voice_id"]
            db.commit()

        logger.info(
            "Voice cloned for VoiceProfile %s: elevenlabs_voice_id=%s",
            voice_profile.id, data["voice_id"],
        )
        return True

    except Exception as exc:
        logger.error("ElevenLabs voice clone failed for VoiceProfile %s: %s", voice_profile.id, exc)
        return False


def delete_voice(db: Session, voice_profile: VoiceProfile) -> bool:
    """
    Delete a cloned voice from ElevenLabs and deactivate the profile.
    Removes the sample file from storage.
    """
    if voice_profile.elevenlabs_voice_id and settings.ELEVENLABS_API_KEY:
        try:
            import httpx

            resp = httpx.delete(
                f"https://api.elevenlabs.io/v1/voices/{voice_profile.elevenlabs_voice_id}",
                headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.error("Failed to delete ElevenLabs voice %s: %s", voice_profile.elevenlabs_voice_id, exc)

    # Delete sample file
    if voice_profile.sample_file_path:
        import os
        try:
            os.remove(voice_profile.sample_file_path)
        except OSError:
            pass

    # Revert patient to default voice
    patient = db.query(Patient).filter(Patient.id == voice_profile.patient_id).first()
    if patient and patient.selected_voice_id == voice_profile.elevenlabs_voice_id:
        patient.selected_voice_id = settings.ELEVENLABS_DEFAULT_VOICE_FEMALE or None

    voice_profile.is_active = False
    voice_profile.elevenlabs_voice_id = None
    voice_profile.sample_file_path = None
    db.commit()
    logger.info("VoiceProfile %s deactivated and sample deleted", voice_profile.id)
    return True
