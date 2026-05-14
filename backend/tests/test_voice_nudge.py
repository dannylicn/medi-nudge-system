"""Tests for voice nudge feature: TTS, voice cloning, onboarding, delivery."""
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.models.models import Patient, VoiceProfile, Medication, PatientMedication


def _make_patient(db, phone, chat_id=None, delivery_mode="text", voice_id=None):
    p = Patient(
        full_name="Test Patient",
        phone_number=phone,
        telegram_chat_id=chat_id,
        onboarding_state="complete",
        is_active=True,
        nudge_delivery_mode=delivery_mode,
        selected_voice_id=voice_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# TTS service tests
# ---------------------------------------------------------------------------

class TestTTSService:
    def test_no_api_key_returns_none(self, db):
        from app.services.tts_service import generate_voice_message

        with patch("app.services.tts_service.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = ""
            result = generate_voice_message("Hello", "voice123", patient_id=1)
            assert result is None

    def test_no_voice_id_returns_none(self, db):
        from app.services.tts_service import generate_voice_message

        with patch("app.services.tts_service.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test-key"
            mock_settings.ELEVENLABS_DEFAULT_VOICE_FEMALE = ""
            result = generate_voice_message("Hello", "", patient_id=1)
            assert result is None

    def test_cache_hit(self, db, tmp_path):
        from app.services.tts_service import generate_voice_message, _cache_path

        text = "Hello"
        cache_dir = str(tmp_path / "voice_cache")
        (tmp_path / "voice_cache").mkdir(parents=True)

        with patch("app.services.tts_service.CACHE_DIR", cache_dir):
            expected_path = _cache_path(1, 2, 1, text)

        # Create the cache file at the expected path
        os.makedirs(os.path.dirname(expected_path), exist_ok=True)
        with open(expected_path, "wb") as f:
            f.write(b"fake-ogg")

        with patch("app.services.tts_service.settings") as mock_settings, \
             patch("app.services.tts_service.CACHE_DIR", cache_dir):
            mock_settings.ELEVENLABS_API_KEY = "test-key"
            mock_settings.ELEVENLABS_DEFAULT_VOICE_FEMALE = "default"
            result = generate_voice_message("Hello", "voice123", patient_id=1, medication_id=2, attempt=1)
            assert result == expected_path

    def test_api_failure_returns_none(self, db, tmp_path):
        from app.services.tts_service import generate_voice_message

        with patch("app.services.tts_service.settings") as mock_settings, \
             patch("app.services.tts_service.CACHE_DIR", str(tmp_path / "voice_cache")), \
             patch("httpx.post", side_effect=Exception("API error")):
            mock_settings.ELEVENLABS_API_KEY = "test-key"
            mock_settings.ELEVENLABS_DEFAULT_VOICE_FEMALE = "default"
            mock_settings.MEDIA_STORAGE_PATH = str(tmp_path)
            result = generate_voice_message("Hello", "voice123", patient_id=1)
            assert result is None


# ---------------------------------------------------------------------------
# Voice clone service tests
# ---------------------------------------------------------------------------

class TestVoiceCloneService:
    def test_clone_blocked_without_dual_consent(self, db):
        from app.services.voice_clone_service import clone_voice

        patient = _make_patient(db, "+6591000100")
        profile = VoiceProfile(
            patient_id=patient.id,
            donor_name="Caregiver",
            sample_file_path="/tmp/sample.ogg",
            patient_consent_at=datetime.utcnow(),
            donor_consent_at=None,  # Missing donor consent
        )
        db.add(profile)
        db.commit()

        result = clone_voice(db, profile)
        assert result is False

    def test_clone_blocked_without_sample(self, db):
        from app.services.voice_clone_service import clone_voice

        patient = _make_patient(db, "+6591000101")
        profile = VoiceProfile(
            patient_id=patient.id,
            donor_name="Caregiver",
            sample_file_path=None,
            patient_consent_at=datetime.utcnow(),
            donor_consent_at=datetime.utcnow(),
        )
        db.add(profile)
        db.commit()

        result = clone_voice(db, profile)
        assert result is False


# ---------------------------------------------------------------------------
# Onboarding voice preference tests
# ---------------------------------------------------------------------------

class TestVoicePreferenceOnboarding:
    @staticmethod
    def _send_mock():
        m = MagicMock()
        m.status = "sent"
        return m

    def test_text_only_skips_voice_selection(self, db):
        from app.services.onboarding_service import handle_onboarding_reply

        patient = _make_patient(db, "+6591000200", chat_id="800001")
        patient.onboarding_state = "voice_preference"
        db.commit()

        with patch("app.services.telegram_service.send_text") as ms:
            ms.return_value = self._send_mock()
            handle_onboarding_reply(db, patient, "1")  # text only
            db.refresh(patient)
            assert patient.onboarding_state == "complete"
            assert patient.nudge_delivery_mode == "text"
            assert patient.is_active is True

    def test_voice_only_goes_to_selection(self, db):
        from app.services.onboarding_service import handle_onboarding_reply

        patient = _make_patient(db, "+6591000201", chat_id="800002")
        patient.onboarding_state = "voice_preference"
        db.commit()

        with patch("app.services.telegram_service.send_text") as ms:
            ms.return_value = self._send_mock()
            handle_onboarding_reply(db, patient, "2")  # voice only
            db.refresh(patient)
            assert patient.onboarding_state == "voice_selection"
            assert patient.nudge_delivery_mode == "voice"

    def test_voice_selection_female(self, db):
        from app.services.onboarding_service import handle_onboarding_reply

        patient = _make_patient(db, "+6591000202", chat_id="800003")
        patient.onboarding_state = "voice_selection"
        patient.nudge_delivery_mode = "voice"
        db.commit()

        with patch("app.services.telegram_service.send_text") as ms, \
             patch("app.services.onboarding_service.settings") as mock_settings:
            ms.return_value = self._send_mock()
            mock_settings.ELEVENLABS_DEFAULT_VOICE_FEMALE = "rachel-id"
            mock_settings.ELEVENLABS_DEFAULT_VOICE_MALE = "antoni-id"
            mock_settings.TELEGRAM_BOT_USERNAME = "TestBot"
            mock_settings.TELEGRAM_BOT_TOKEN = ""

            handle_onboarding_reply(db, patient, "1")  # female voice
            db.refresh(patient)
            assert patient.onboarding_state == "complete"
            assert patient.selected_voice_id == "rachel-id"

    def test_voice_selection_male(self, db):
        from app.services.onboarding_service import handle_onboarding_reply

        patient = _make_patient(db, "+6591000203", chat_id="800004")
        patient.onboarding_state = "voice_selection"
        patient.nudge_delivery_mode = "both"
        db.commit()

        with patch("app.services.telegram_service.send_text") as ms, \
             patch("app.services.onboarding_service.settings") as mock_settings:
            ms.return_value = self._send_mock()
            mock_settings.ELEVENLABS_DEFAULT_VOICE_FEMALE = "rachel-id"
            mock_settings.ELEVENLABS_DEFAULT_VOICE_MALE = "antoni-id"
            mock_settings.TELEGRAM_BOT_USERNAME = "TestBot"
            mock_settings.TELEGRAM_BOT_TOKEN = ""

            handle_onboarding_reply(db, patient, "2")  # male voice
            db.refresh(patient)
            assert patient.onboarding_state == "complete"
            assert patient.selected_voice_id == "antoni-id"

    def test_drop_off_at_voice_preference_defaults_to_text(self, db):
        from app.services.onboarding_service import handle_drop_off

        patient = _make_patient(db, "+6591000204", chat_id="800005")
        patient.onboarding_state = "voice_preference"
        patient.is_active = False
        db.commit()

        with patch("app.services.telegram_service.send_text") as ms:
            ms.return_value = self._send_mock()
            handle_drop_off(db, patient, retry_count=1)
            db.refresh(patient)
            assert patient.onboarding_state == "complete"
            assert patient.nudge_delivery_mode == "text"
            assert patient.is_active is True


# ---------------------------------------------------------------------------
# Voice delivery fallback tests
# ---------------------------------------------------------------------------

class TestVoiceDeliveryFallback:
    def test_text_mode_no_voice_call(self, db):
        """Patient with text mode should not trigger TTS."""
        patient = _make_patient(db, "+6591000300", chat_id="900001", delivery_mode="text")
        med = Medication(name="Metformin", generic_name="metformin_test_300", default_refill_days=30)
        db.add(med)
        db.commit()

        with patch("app.services.telegram_service.send_keyboard") as mock_send, \
             patch("app.services.tts_service.generate_voice_message") as mock_tts:
            mock_send.return_value = MagicMock(status="sent")

            from app.services.nudge_campaign_service import create_and_send
            campaign = create_and_send(db, patient, med, days_overdue=5)

            mock_tts.assert_not_called()
            assert campaign.status == "sent"

    def test_voice_mode_calls_tts(self, db):
        """Patient with voice mode should trigger TTS."""
        patient = _make_patient(db, "+6591000301", chat_id="900002", delivery_mode="voice", voice_id="test-voice")
        med = Medication(name="Amlodipine", generic_name="amlodipine_test_301", default_refill_days=30)
        db.add(med)
        db.commit()

        with patch("app.services.telegram_service.send_text") as mock_send, \
             patch("app.services.telegram_service.send_voice") as mock_send_voice, \
             patch("app.services.tts_service.generate_voice_message") as mock_tts:
            mock_send.return_value = MagicMock(status="sent")
            mock_send_voice.return_value = MagicMock(status="sent")
            mock_tts.return_value = "/tmp/test.ogg"

            from app.services.nudge_campaign_service import create_and_send
            campaign = create_and_send(db, patient, med, days_overdue=5)

            mock_tts.assert_called_once()
            mock_send_voice.assert_called_once()

    def test_voice_fallback_to_text_on_tts_failure(self, db):
        """When TTS fails, voice-only patient should get text fallback."""
        patient = _make_patient(db, "+6591000302", chat_id="900003", delivery_mode="voice", voice_id="test-voice")
        med = Medication(name="Losartan", generic_name="losartan_test_302", default_refill_days=30)
        db.add(med)
        db.commit()

        with patch("app.services.telegram_service.send_keyboard") as mock_send, \
             patch("app.services.tts_service.generate_voice_message") as mock_tts:
            mock_send.return_value = MagicMock(status="sent")
            mock_tts.return_value = None  # TTS failed

            from app.services.nudge_campaign_service import create_and_send
            campaign = create_and_send(db, patient, med, days_overdue=5)

            # Should fall back to text with button
            mock_send.assert_called()
            assert campaign.status == "sent"
