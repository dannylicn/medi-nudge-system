# Change: enhance-smart-self-onboarding

## Why

The prescription-photo self-onboarding sub-flow requires coordinator review for every OCR scan, even when confidence is high and all fields are present. Patients wait hours or days before their medications are activated — undermining the "self" in self-onboarding.

Separately, once a medication is recorded the bot is silent about what to expect: no info on what the drug treats, no guidance on side effects to watch for, no follow-up after starting something new. Patients who experience mild side effects may not know to report them until it becomes urgent.

## What Changes

1. **Fast-path OCR confirmation** (`prescription-ocr`, `patient-onboarding`): When all extracted fields have confidence ≥ 0.85 and required fields are present, the bot presents a formatted summary to the patient in Telegram for self-confirmation. On confirm, medications are auto-populated immediately. Coordinator receives a low-priority background alert (non-blocking). Low-confidence scans continue through the existing coordinator-review path.

2. **Reminder-time auto-setup** (`medication-adherence-tracking`, `patient-onboarding`): When OCR successfully extracts a `frequency` field (e.g. "twice daily", "with meals"), `PatientMedication.reminder_times` is pre-populated with sensible defaults. The bot shows the inferred schedule to the patient for confirmation or manual override.

3. **Medication info card** (`medication-info-card` — new capability): Immediately after any medication is confirmed (OCR fast-path, coordinator-confirmed OCR, or manual entry), the bot sends a short LLM-generated card in the patient's language: what condition the medication is commonly prescribed for, 2–3 side effects to watch for, and the `SIDE EFFECT` keyword. Temperature is capped at 0.3; a safe template fallback is used when LLM is unavailable.

4. **Proactive side-effect check-in** (`nudge-campaigns`): A new one-time `side_effect_checkin` campaign fires 3 days after a new `PatientMedication` is activated. The bot asks "How are you getting on with [medication]?" with `OK` and `SIDE EFFECT` quick replies.

## Impact

- Affected specs: `prescription-ocr` (modified), `patient-onboarding` (modified), `medication-adherence-tracking` (modified), `nudge-campaigns` (modified), `medication-info-card` (new)
- Affected code:
  - `app/models/models.py` — new `PrescriptionScan.status` value `patient_confirmed`; new `NudgeCampaign.campaign_type` value `side_effect_checkin`
  - `app/services/ocr_service.py` — `_is_high_confidence()` helper, fast-path trigger
  - `app/services/onboarding_service.py` — `patient_pending_ocr_confirmation` state handler, frequency → reminder_times
  - `app/services/medication_info_service.py` — new: LLM info card generation + fallback templates
  - `app/services/side_effect_checkin_service.py` — new: check-in campaign creation job
  - `app/routers/webhook.py` — OCR confirm/edit replies, check-in OK/SIDE EFFECT replies
  - `app/services/nudge_campaign_service.py` — support `side_effect_checkin` type
  - New migration for status enum + campaign_type enum changes
