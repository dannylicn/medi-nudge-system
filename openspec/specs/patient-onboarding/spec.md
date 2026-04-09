# patient-onboarding Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Two enrolment entry modes

The system supports clinic-enrolled (coordinator-initiated) and self-enrolled (QR/link) entry modes. The system SHALL implement this as described in the scenarios below.

#### Scenario: Clinic-enrolled — coordinator creates patient and triggers invite

Given a coordinator creates a new patient record with phone number and name
When the patient is saved with `is_active: true`
Then the system automatically dispatches a WhatsApp invite message explaining the programme and requesting consent
And the onboarding state for this patient is set to `invited`

#### Scenario: Self-enrolled — patient submits phone number via web landing page

Given a patient visits the onboarding URL and submits their phone number
When the system receives the registration
Then a `Patient` record is created in a pre-consent state
And a WhatsApp invite is sent as in the clinic-enrolled path

---

### Requirement: Onboarding state machine

Onboarding progresses through defined states. The patient advances by responding to system messages. The system SHALL implement this as described in the scenarios below.

```
invited → consent_pending → language_confirmed → medication_capture
        → complete → drop_off_recovery
```

#### Scenario: States advance in order

Given a patient in `invited` state
When the patient responds `YES` to the invite
Then the state advances to `consent_pending`
And a language selection message is sent

#### Scenario: State does not skip steps

Given a patient in `invited` state
When the system receives a language selection reply before consent
Then the response is ignored or redirected to the consent step
And the patient remains in `invited` state

---

### Requirement: Explicit consent captured via WhatsApp

The patient MUST explicitly consent to WhatsApp outreach before any health-related messages are sent.

#### Scenario: Patient consents

Given a patient in `consent_pending` state
When the patient replies `YES` (or taps the YES quick-reply button)
Then `Patient.consent_obtained_at` is recorded with the current timestamp
And `Patient.consent_channel = whatsapp`
And the onboarding advances to language selection

#### Scenario: Patient declines consent

Given a patient in `consent_pending` state
When the patient replies `NO`
Then `Patient.is_active` is set to `False`
And no further messages are sent to this patient
And the consent refusal is logged

---

### Requirement: Language preference capture

After consent, the patient selects their preferred communication language. The system SHALL implement this as described in the scenarios below.

#### Scenario: Language selected via quick-reply

Given a patient in `consent_pending` state (post-consent)
When the patient taps `English` from the language selection quick-replies
Then `Patient.language_preference` is set to `en`
And the state advances to `medication_capture`

#### Scenario: All four languages available

Given the language selection message is sent
Then the message includes four quick-reply options: `English / 中文 / Melayu / தமிழ்`

---

### Requirement: Medication capture — three sub-flows

After language selection, medications are captured via one of three methods. The system SHALL implement this as described in the scenarios below.

**Sub-flow A: Dispensing feed available**

#### Scenario: Medications imported from dispensing feed

Given the clinic has provided a dispensing record import for this patient
When onboarding reaches the medication capture step
Then the imported medications are presented to the patient as a confirmation list
And the patient can confirm `YES` or note corrections

**Sub-flow B: OCR photo upload**

#### Scenario: Patient uploads prescription photo via WhatsApp

Given the patient is prompted to send a photo of their prescription or medicine label
When the patient sends a WhatsApp photo message
Then the image is routed to the `prescription-ocr` pipeline (see REQ-OCR-001)
And the extracted medications are presented for confirmation after coordinator review

**Sub-flow C: Manual guided form**

#### Scenario: Patient enters medication manually

Given the patient cannot use OCR and no feed is available
When the system walks the patient through a guided form
Then the patient provides medication name, dose, frequency, and refill days for each medication
And each entry is saved as a draft `PatientMedication` pending coordinator confirmation

---

### Requirement: Medication confirmation

Before onboarding is marked complete, the patient confirms the medication list is correct. The system SHALL implement this as described in the scenarios below.

#### Scenario: Patient confirms medication list

Given the system presents a summary of captured medications
When the patient replies `YES` or taps `Confirm`
Then all draft `PatientMedication` records are set to `is_active: true`
And the refill due dates are computed from the most recent dispensing records

---

### Requirement: Reminder preference capture

The system asks patients about their preferred contact window (quiet hours). The system SHALL implement this as described in the scenarios below.

#### Scenario: Patient sets preferred contact time

Given the patient is in the preferences step
When the patient selects `3pm – 6pm`
Then `Patient.quiet_hours_start = 22:00` and `Patient.quiet_hours_end = 15:00` are updated accordingly
*( Or more precisely: their preferred window `15:00–18:00` is stored as `contact_window_start` and `contact_window_end`.)*

#### Scenario: Patient skips preference step

Given the patient does not respond to the preference prompt within 24 hours
When the system's drop-off recovery runs
Then onboarding advances to complete with default contact window (no restriction)

---

### Requirement: Welcome message and reply guide

Upon completing onboarding, a welcome message teaches the patient how to interact with the system. The system SHALL implement this as described in the scenarios below.

#### Scenario: Welcome message sent on completion

Given all required onboarding steps are complete
When the state transitions to `complete`
Then a welcome message is sent containing:
  - Confirmation that they are enrolled
  - Reply keywords: `YES` (medication collected), `HELP` (questions), `SIDE EFFECT` (unwell), `STOP` (opt out)

---

### Requirement: Drop-off recovery

When a patient stops responding mid-onboarding, the system retries and ultimately routes to a coordinator. The system SHALL implement this as described in the scenarios below.

#### Scenario: No response to invite — retry

Given a patient in `invited` state has not responded for 48 hours
When the drop-off recovery job runs
Then a reminder invite is resent (up to 2 retries)

#### Scenario: No response after 2 retries — escalation created

Given a patient has not responded to 2 invite retries
When the drop-off recovery job runs
Then an `EscalationCase` is created with `reason: onboarding_drop_off`, `priority: normal`
And no further automated messages are sent

#### Scenario: Patient confused mid-onboarding

Given a patient sends a freeform message that does not match any expected reply during onboarding
When the webhook handler processes the message
Then an automated reply is sent: "Reply HELP for assistance or wait for your care team to contact you."
And an `EscalationCase` is created with `reason: patient_question`

