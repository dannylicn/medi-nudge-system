## MODIFIED Requirements

### Requirement: OCR sub-flow B supports patient-led fast-path confirmation

The system SHALL present a structured OCR field summary to the patient for self-confirmation when all required fields are extracted with high confidence during the `medication_capture` onboarding state.

> **Modification:** When OCR completes with high confidence, the bot presents a structured summary to the patient for self-confirmation, rather than waiting for coordinator review.

The onboarding state machine gains a new transient state: `patient_pending_ocr_confirmation`. The state MUST advance to `confirm` on patient confirmation; on patient EDIT it MUST fall back to `medication_capture` (waiting) and the coordinator queue handles the rest.

#### Scenario: Photo upload triggers patient-facing OCR confirmation (high confidence)

Given a patient in `medication_capture` state who sends a photo
And OCR extraction completes with all required fields at confidence >= 0.85
When the fast-path gate passes
Then `Patient.onboarding_state` advances to `patient_pending_ocr_confirmation`
And the bot sends a formatted summary: medication name, dosage, frequency, and dispense date
And the bot prompts: "Reply CONFIRM if correct, or EDIT to have your care team review it."

#### Scenario: Patient confirms OCR in Telegram — onboarding advances

Given a patient in `patient_pending_ocr_confirmation` state
When the patient replies CONFIRM
Then `PrescriptionScan.status` transitions to `patient_confirmed`
And `Medication`, `PatientMedication`, and `DispensingRecord` records are created
And `Patient.onboarding_state` advances to `confirm`
And the bot sends the medication confirmation summary and medication info card

#### Scenario: Patient requests edit — drops to coordinator queue

Given a patient in `patient_pending_ocr_confirmation` state
When the patient replies EDIT
Then `PrescriptionScan.status` transitions to `review`
And `Patient.onboarding_state` returns to `medication_capture` (waiting)
And the bot replies: "Understood — your care team will review this and update your records shortly."

#### Scenario: Low-confidence OCR during onboarding — unchanged

Given a patient in `medication_capture` state who sends a photo
And OCR extraction yields any required field below confidence 0.85
When OCR processing completes
Then `Patient.onboarding_state` remains `medication_capture`
And the bot replies: "I've received your prescription. Your care team will review it and get back to you shortly."
And the existing coordinator review flow is triggered

---

### Requirement: Reminder schedule confirmed by patient after OCR frequency parsing

After a medication is auto-populated from an OCR fast-path confirmation, the system SHALL infer a reminder schedule from the extracted frequency field and present it to the patient for confirmation or override.

#### Scenario: Frequency parsed — patient confirms inferred schedule

Given a confirmed medication with OCR-extracted frequency "twice daily"
When the system parses the frequency
Then `PatientMedication.reminder_times` is set to ["08:00", "20:00"]
And the bot sends: "⏰ I've set up your reminders: 8:00 AM and 8:00 PM daily. Reply OK to keep this or tell me your preferred times."
When the patient replies OK
Then `PatientMedication.reminder_times` is saved unchanged

#### Scenario: Frequency parsed — patient overrides with custom times

Given the bot has sent an inferred schedule prompt
When the patient replies "7am and 9pm"
Then the system parses the custom times (via LLM or regex)
And `PatientMedication.reminder_times` is updated to ["07:00", "21:00"]
And the bot confirms: "Got it — I'll remind you at 7:00 AM and 9:00 PM."

#### Scenario: Frequency unknown — patient asked directly

Given a confirmed medication where OCR frequency field is absent or unrecognised
When the system cannot infer a schedule
Then the bot asks: "When would you like to be reminded to take {medication}? (e.g. '8am' or '8am and 9pm')"
And the patient's reply is parsed and stored as `PatientMedication.reminder_times`
