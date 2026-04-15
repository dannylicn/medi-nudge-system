# Tasks: add-telegram-onboarding-flows

## Database & Models

- [x] Add `telegram_chat_id` column to `Patient` model (`String(30), nullable=True, unique=True`)
- [x] Create `OnboardingToken` model (`id`, `patient_id`, `token`, `expires_at`, `used_at`, `created_at`)
- [x] Generate Alembic migration for both changes
- [x] Update all `telegram_service.send_text()` calls that use `patient.phone_number` to use `patient.telegram_chat_id`

## Token generation (coordinator-initiated)

- [x] Add `generate_invite_token(db, patient) → dict` helper in `onboarding_service.py`
  - Creates `OnboardingToken` row with 32-byte random token, TTL = 72 hours
  - Returns `{ invite_link, qr_code_png_b64 }` where `qr_code_png_b64` is a base64-encoded PNG
  - Use `qrcode` library (`pip install qrcode[pil]`) to generate the PNG in-memory — no temp files
- [x] Add `BOT_USERNAME` to `Settings` (read from env)
- [x] Add `qrcode[pil]` to `requirements.txt`
- [x] Call `generate_invite_token` in `POST /api/patients` instead of `send_invite`
- [x] Include `invite_link` and `onboarding_qr_code` (base64 PNG) fields in `PatientOut` schema response

## Self-onboarding & /start handler

- [x] Add `/start` command handling in `webhook.py`:
  - Parse `/start TOKEN` vs `/start` (no token)
  - **With token:** validate token (exists, not expired, not used), link `telegram_chat_id`, mark token used, advance to `invited`, send consent message
  - **Without token:** set state `identity_verification`, send NRIC prompt
- [x] Add `identity_verification` to `ONBOARDING_STATES` set in `webhook.py`
- [x] Add `handle_identity_verification(db, chat_id, text)` in `onboarding_service.py`:
  - Hash the input NRIC, query `Patient` where `nric_hash = X AND telegram_chat_id IS NULL`
  - Match: link `telegram_chat_id`, advance to `invited`, send consent message
  - No match: create `Patient` stub (`onboarding_state = "self_registering"`), send review message, create `EscalationCase(reason="self_registration_review")`
- [x] Handle unknown `chat_id` by routing to self-onboarding instead of "not recognised" message

## Complete state machine

- [x] Add `language_confirmed`, `medication_capture`, `confirm`, `preferences` to `ONBOARDING_STATES`
- [x] Wire `_handle_consent_reply` → sets `language_confirmed` (not `complete`)
- [x] Add `_handle_language_reply` → sets `medication_capture`, sends medication sub-flow prompt
- [x] Add `_handle_medication_capture` → presents 3 options: (A) confirm dispensing records (B) send photo (C) manual entry
  - Sub-flow A: presents any existing `PatientMedication` records for confirmation
  - Sub-flow B: route to OCR pipeline (already exists); set `confirm` state on OCR completion
  - Sub-flow C: guided form messages collecting name/dose/frequency; advance to `confirm` when done
- [x] Add `_handle_confirm_reply` → sets `is_active = true` on draft meds, advance to `preferences`
- [x] Add `_handle_preferences_reply` → captures contact window, advance to `complete`, send welcome message
- [x] Update `handle_onboarding_reply` dispatcher for all new states

## API

- [x] Add `GET /api/patients/{id}/invite-link` endpoint — regenerates token if expired or used, returns `{ invite_link }`
- [x] Add `POST /api/patients/{id}/invite-link` as alias (same behaviour)

## Dashboard integration

- [x] Display QR code image in patient detail page after patient creation (render `onboarding_qr_code` base64 PNG)
- [x] Add a print/download button for the QR code (coordinator can hand printed QR to patient)
- [x] Show `invite_link` as a fallback copy-to-clipboard option below the QR code
- [x] Show onboarding state badge on patient list and detail views

## Tests

- [x] Unit: `generate_invite_token` creates token with correct TTL
- [x] Unit: expired/used token is rejected in `/start TOKEN` handler
- [x] Unit: NRIC hash lookup succeeds and links `telegram_chat_id`
- [x] Unit: unknown NRIC creates stub patient and escalation
- [x] Integration: full coordinator-initiated onboarding state machine (invited → complete)
- [x] Integration: full self-onboarding state machine (identity_verification → complete)
- [x] Integration: drop-off recovery still triggers after 2 missed retries
