## 1. Data model and migration
- [x] 1.1 Add `nudge_delivery_mode` (String, default "text") and `selected_voice_id` (String, nullable) columns to `Patient` model
- [x] 1.2 Create `VoiceProfile` model (see design.md data model)
- [x] 1.3 Add `ELEVENLABS_DEFAULT_VOICE_FEMALE` and `ELEVENLABS_DEFAULT_VOICE_MALE` to Settings
- [x] 1.4 Create Alembic migration for new columns and table
- [x] 1.5 Add Pydantic schemas for VoiceProfile and updated Patient response

## 2. TTS and voice cloning service
- [x] 2.1 Create `app/services/tts_service.py` — ElevenLabs TTS wrapper with `.ogg` caching (`generate_voice_message()`)
- [x] 2.2 Create `app/services/voice_clone_service.py` — ElevenLabs IVC wrapper (`clone_voice()`, `delete_voice()`)
- [x] 2.3 Add `send_voice()` method to `telegram_service.py` — sends `.ogg` via Telegram `sendVoice` API

## 3. Onboarding: voice preference step
- [x] 3.1 Add `voice_preference` and `voice_selection` to `ONBOARDING_STATES` in `onboarding_service.py`
- [x] 3.2 Modify `_handle_preferences_reply()` to advance to `voice_preference` instead of `complete`
- [x] 3.3 Implement `_handle_voice_preference_reply()` — text/voice/both selection
- [x] 3.4 Implement `_handle_voice_selection_reply()` — female/male default voice picker
- [x] 3.5 Wire new handlers into `handle_onboarding_reply()` dispatch
- [x] 3.6 Update `handle_drop_off()` to handle timeout at `voice_preference` (default to text)

## 4. Voice nudge delivery
- [x] 4.1 Modify `nudge_campaign_service.create_and_send()` — after text send, generate and send voice if applicable
- [x] 4.2 Modify `daily_reminder_service._send_due_reminders()` — add voice delivery alongside text
- [x] 4.3 Ensure all voice failures fall back to text silently

## 5. Voice cloning flow (optional post-onboarding)
- [x] 5.1 Add webhook handler for caregiver voice messages (detect voice message from caregiver chat_id)
- [x] 5.2 Implement voice sample download and storage
- [x] 5.3 Implement caregiver consent collection flow
- [x] 5.4 Trigger ElevenLabs IVC when dual consent is complete
- [x] 5.5 Update `patient.selected_voice_id` to cloned voice on success

## 6. Dashboard integration
- [x] 6.1 Display voice profile status on PatientDetailPage (active/pending/none)
- [x] 6.2 Show `nudge_delivery_mode` in patient detail
- [x] 6.3 Add button to trigger voice cloning flow for a patient (coordinator action)

## 7. Tests
- [x] 7.1 Unit tests for `tts_service.py` (cache hit/miss, ElevenLabs mock, fallback)
- [x] 7.2 Unit tests for `voice_clone_service.py` (consent validation, API mock)
- [x] 7.3 Integration tests for voice preference onboarding step
- [x] 7.4 Integration tests for voice nudge delivery in campaign service
- [x] 7.5 Test voice fallback to text when ElevenLabs unavailable
