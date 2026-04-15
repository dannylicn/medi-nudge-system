# Proposal: add-telegram-onboarding-flows

## Why

The current onboarding implementation has two structural gaps that prevent real-world use:

1. **Doctor-initiated flow is broken at the Telegram layer.** The Telegram Bot API does not allow a bot to send the *first* message to a user. `send_invite()` is called with the patient's phone number as `to_phone`, which is not a Telegram `chat_id`. The invite is silently dropped.

2. **Patient self-onboarding via Telegram does not exist.** When an unknown `chat_id` messages the bot the system replies "We don't recognise this account. Please contact your clinic." — blocking any patient-driven entry point.

Additionally, the onboarding state machine in `onboarding_service.py` skips `language_confirmed`, `medication_capture`, `confirm`, and `preferences` states — patients jump directly from consent to `complete` without capturing medications.

## What Changes

### Doctor onboards patient (coordinator-initiated)
- Coordinator creates patient record in the dashboard (existing UI).
- System generates a **one-time invite token** (32-byte URL-safe random string, 72-hour TTL) stored in a new `onboarding_tokens` table.
- System generates a **QR code** (PNG) encoding the deep-link `https://t.me/<BOT_USERNAME>?start=<TOKEN>`.
- QR code is displayed in the coordinator dashboard — coordinator shows the screen or prints it.
- Patient scans the QR code with their phone camera → iOS/Android recognises the `t.me` link → Telegram opens and sends `/start <TOKEN>` to the bot automatically.
- Bot validates token, links `Patient.telegram_chat_id` to the incoming `chat_id`, and advances to the consent step.

### Patient self-onboards from Telegram chat
- Patient opens the bot and sends `/start` (no token).
- Bot responds with an identity verification prompt: asks for the last 4 characters of their NRIC/FIN.
- Patient replies with their NRIC suffix (e.g. `567A`).
- System looks up a patient record by NRIC suffix match + unlinked status.
  - **Match found:** links `telegram_chat_id`, advances to consent step.
  - **No match:** creates a minimal `Patient` record in `self_registering` state, collects name and phone, queues a coordinator review task.
- From consent onward the flow is identical to coordinator-initiated.

### Complete state machine
Wire all missing transitions:
`invited → consent_pending → language_confirmed → medication_capture → confirm → preferences → complete`
