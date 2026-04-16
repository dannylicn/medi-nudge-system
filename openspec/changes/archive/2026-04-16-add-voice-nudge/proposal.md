# Change: Add voice nudge delivery with default voice selection and optional caregiver cloning

## Why

Elderly and low-literacy patients often miss or ignore text nudges. Hearing a voice reminder is more engaging and accessible. Voice nudges should be available to every patient immediately using a default ElevenLabs voice. Optionally, a caregiver's voice can be cloned for a more personal experience — but this is never a prerequisite.

## What Changes

- **New capability `voice-cloning`**: VoiceProfile model, ElevenLabs TTS service, voice cloning service, audio cache, default voice selection (female/male), dual consent tracking for optional cloning, and voice sample collection from caregivers via Telegram.
- **Modified `patient-onboarding`**: Add `voice_preference` step after `preferences` where patients choose delivery mode (text/voice/both) and select a default voice (female or male). Voice cloning is a separate post-onboarding flow.
- **Modified `nudge-campaigns`**: When the patient's delivery preference includes voice, generate TTS audio using their selected voice (default or cloned) and send as a Telegram voice note. Applies to both refill nudge campaigns and daily reminders.

## Impact

- Affected specs: `voice-cloning` (new), `patient-onboarding`, `nudge-campaigns`
- Affected code:
  - New: `app/models/models.py` (VoiceProfile), `app/services/tts_service.py`, `app/services/voice_clone_service.py`
  - Modified: `app/services/onboarding_service.py`, `app/services/nudge_campaign_service.py`, `app/services/telegram_service.py`, `app/services/daily_reminder_service.py`, `app/core/config.py`
  - New Alembic migration for `voice_profiles` table and Patient columns
  - Frontend: voice profile status and delivery mode on patient detail page
