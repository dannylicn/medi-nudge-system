# Change: Initialise core platform specification baseline

## Why

There is no existing spec baseline for Medi-Nudge. This change establishes canonical requirements for all eight v1 capabilities so every subsequent change can reference, modify, or extend a defined spec rather than building on assumptions.

## What Changes

- **ADDED** `patient-management` spec — Patient CRUD, NRIC SHA-256 privacy, language preferences, soft-delete
- **ADDED** `medication-adherence-tracking` spec — Medication catalog, prescriptions, dispensing records, daily refill gap detection scheduler
- **ADDED** `nudge-campaigns` spec — Campaign lifecycle state machine, LLM + template nudge generation, multilingual tone ladder
- **ADDED** `whatsapp-channel` spec — Twilio send/receive, delivery tracking, inbound webhook with signature validation, response classification
- **ADDED** `escalation-management` spec — EscalationCase lifecycle, priority triage, coordinator assignment
- **ADDED** `patient-onboarding` spec — Consent flow, language selection, medication capture (feed/OCR/manual), reminder preferences, drop-off recovery
- **ADDED** `prescription-ocr` spec — Image ingestion, GPT-4o Vision + Tesseract extraction, confidence-gated human review, medication auto-population
- **ADDED** `care-coordinator-dashboard` spec — React frontend: patient list, escalation queue, OCR review, adherence analytics, JWT auth

## Impact

- Affected specs: all eight capabilities listed above (all new — no modifications)
- Affected code: all of `backend/`, `frontend/` (to be built against these specs)
- Out of scope for v1: ElevenLabs voice cloning, HealthHub live API integration, patient-facing mobile app, multi-tenant support

See `design.md` for architectural decisions, privacy model, state machines, and OWASP security checklist.

## Status

- [ ] Approved
