# Change: Add patient web messaging client

## Why

Patients currently interact with Medi-Nudge exclusively via WhatsApp. Some patients prefer a web-based interface, may not use WhatsApp, or want to review their full message history in a browser. Adding a patient-facing web chat provides an alternative real-time channel that coexists with WhatsApp, using the same backend message pipeline.

## What Changes

- **ADDED** `patient-messaging-client` spec — A new patient-facing web chat UI (React page served from the existing Vite frontend) where patients can view their nudge history and reply. Messages flow through the same `OutboundMessage` / response classification pipeline used by WhatsApp.
- **MODIFIED** `whatsapp-channel` spec — Add a magic-link endpoint that sends a short-lived authenticated URL to the patient's WhatsApp. Add a `channel` field to `OutboundMessage` to distinguish `whatsapp` vs `web` messages.
- **MODIFIED** `care-coordinator-dashboard` spec — Show the message channel (`WhatsApp` / `Web`) on patient detail nudge timeline entries so coordinators have visibility into which channel the patient used.

## Impact

- Affected specs: `patient-messaging-client` (new), `whatsapp-channel` (modified), `care-coordinator-dashboard` (modified)
- Affected code: `backend/app/models/models.py` (add `channel` column to `OutboundMessage`), `backend/app/routers/` (new `messaging.py` router), `backend/app/services/` (new `messaging_service.py`), `frontend/src/pages/` (new `PatientChatPage.jsx`), Alembic migration
- Out of scope: mobile app, push notifications, voice/audio messages in web chat, end-to-end encryption

## Status

- [ ] Approved
