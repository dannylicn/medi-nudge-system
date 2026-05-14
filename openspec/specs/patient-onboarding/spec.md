# patient-onboarding Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Two enrolment entry modes

The system MUST support coordinator-initiated (token deep-link) and patient self-initiated (Telegram `/start`) entry modes.

#### Scenario: Coordinator-initiated — QR code generated on patient creation

Given a coordinator creates a new patient record with name and phone number
When the patient is saved
Then the system generates a one-time `OnboardingToken` (32-byte random, 72-hour TTL)
And returns `invite_link` and `onboarding_qr_code` (base64-encoded PNG) in the API response
And the coordinator displays or prints the QR code for the patient to scan
And the patient scans it with their phone camera, which opens Telegram and sends `/start <token>`

#### Scenario: Patient-initiated — /start with no token

Given a patient opens the bot and sends `/start` with no token
When the webhook receives the command
Then the bot replies asking for the patient's full NRIC/FIN
And sets the conversation state to `identity_verification`

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

### Requirement: Token-based chat linkage for coordinator-initiated flow

The system MUST use a one-time deep-link token to link a Telegram `chat_id` to a pre-registered `Patient` record, because the Telegram Bot API does not permit bots to initiate conversations.

#### Scenario: Patient taps invite link — valid token

Given the system has issued an `OnboardingToken` for a patient
And the token has not been used and has not expired
When the patient taps the link and Telegram sends `/start <token>` to the bot
Then `Patient.telegram_chat_id` is set to the incoming Telegram `chat.id`
And `OnboardingToken.used_at` is recorded
And the patient's `onboarding_state` advances to `invited`
And the bot sends the consent message immediately

#### Scenario: Patient taps invite link — expired token

Given an `OnboardingToken` whose `expires_at` is in the past
When the patient sends `/start <token>`
Then the bot replies: "This invite link has expired. Please ask your clinic for a new one."
And no state changes are made

#### Scenario: Patient taps invite link — already used token

Given an `OnboardingToken` with `used_at` already set
When the patient sends `/start <token>`
Then the bot replies: "This invite link has already been used. If you need help, reply HELP."
And no state changes are made

---

### Requirement: NRIC-based identity verification for self-initiated flow

When a patient initiates onboarding without a token, the system MUST verify their identity by matching their NRIC hash before linking their Telegram account.

#### Scenario: NRIC matches a pre-registered unlinked patient

Given a patient in `identity_verification` state sends their full NRIC
When the system hashes the input with SHA-256 and queries `patients`
And a match is found where `telegram_chat_id IS NULL`
Then `Patient.telegram_chat_id` is set to the incoming `chat_id`
And the state advances to `invited`
And the consent message is sent

#### Scenario: NRIC does not match any pre-registered patient

Given a patient in `identity_verification` state sends their NRIC
When no matching patient record exists
Then a `Patient` stub is created with `onboarding_state = "self_registering"`
And an `EscalationCase` is created with `reason = "self_registration_review"`, `priority = "normal"`
And the bot replies: "Your registration is under review. A care coordinator will be in touch within 1 business day."

#### Scenario: NRIC already linked to another Telegram account

Given a patient whose `telegram_chat_id` is already set
When a different `chat_id` sends a matching NRIC
Then the bot replies: "This patient record is already linked to another Telegram account. Please contact your clinic."
And no records are modified

---

### Requirement: Complete onboarding state machine transitions

All intermediate states MUST be implemented. The system SHALL NOT advance directly from `consent_pending` to `complete`.

```
invited -> consent_pending -> language_confirmed -> medication_capture -> confirm -> preferences -> voice_preference -> complete
```

#### Scenario: Language selection advances to medication_capture

Given a patient in `consent_pending` state who has consented
When the patient replies with a valid language selection (1-4 or language name)
Then `Patient.language_preference` is set
And `onboarding_state` advances to `language_confirmed`
And the bot immediately sends the medication capture prompt

#### Scenario: Medication capture -- dispensing records available

Given a patient in `medication_capture` state
And the patient has existing `PatientMedication` records imported from a dispensing feed
When the patient replies `1` or `YES` to confirm the displayed list
Then all listed medications are confirmed active
And `onboarding_state` advances to `confirm`

#### Scenario: Medication capture -- photo submitted

Given a patient in `medication_capture` state
When the patient sends a photo message (prescription or label)
Then the image is routed to the OCR pipeline
And the bot replies: "I've received your prescription. I'll process it and get back to you shortly."
And `onboarding_state` remains `medication_capture` until OCR completes

#### Scenario: Medication capture -- manual entry

Given a patient in `medication_capture` state who selects manual entry
When the patient provides medication name, dose, frequency, and refill days
Then each entry is saved as a draft `PatientMedication` with `is_active = False`
And the bot loops until the patient replies `DONE`
Then `onboarding_state` advances to `confirm`

#### Scenario: Confirmation advances to preferences

Given a patient in `confirm` state
When the patient replies `YES` or taps `Confirm`
Then all draft `PatientMedication.is_active` records are set to `True`
And `onboarding_state` advances to `preferences`

#### Scenario: Contact window captured in preferences

Given a patient in `preferences` state
When the patient selects a preferred contact window (e.g. `3pm-6pm`)
Then `Patient.contact_window_start` and `Patient.contact_window_end` are recorded
And `onboarding_state` advances to `voice_preference`

#### Scenario: Voice preference -- text only selected

Given a patient in `voice_preference` state
When the patient selects "Text only" (option 1)
Then `Patient.nudge_delivery_mode` is set to `text`
And `onboarding_state` advances to `complete`
And the welcome message is sent

#### Scenario: Voice preference -- voice selected with voice choice

Given a patient in `voice_preference` state
When the patient selects "Voice only" (option 2) or "Both" (option 3)
Then `Patient.nudge_delivery_mode` is set to `voice` or `both`
And the bot asks: "Choose a voice: 1. Female  2. Male"
And the patient replies with their choice
Then `Patient.selected_voice_id` is set to the corresponding default ElevenLabs voice ID
And `onboarding_state` advances to `complete`
And the welcome message is sent

#### Scenario: Preferences step timed out -- default applied

Given a patient in `preferences` state
When 24 hours pass with no response
Then `onboarding_state` advances to `complete` with no contact window restriction
And `nudge_delivery_mode` defaults to `text`
And the welcome message is sent

### Requirement: telegram_chat_id separate from phone_number

`Patient.telegram_chat_id` MUST be stored as a dedicated column. `Patient.phone_number` MUST store only the real E.164 phone number.

#### Scenario: Message routing uses telegram_chat_id

Given a patient with `telegram_chat_id = "123456789"` and `phone_number = "+6591234567"`
When the system sends a Telegram message to this patient
Then `telegram_service.send_text()` is called with `to=patient.telegram_chat_id`
And `patient.phone_number` is not passed to the Telegram API

### Requirement: Onboarding multi-choice prompts SHALL use inline keyboard buttons

The system SHALL present all multi-choice onboarding options as Telegram inline keyboard buttons rather than numbered text lists. Patients MUST be able to complete every onboarding choice by tapping a button without typing. Text input (e.g. typing "1" or "English") MUST continue to be accepted as a fallback so that the flow remains accessible regardless of how the patient interacts.

#### Scenario: Language selection — patient taps button

Given a patient has just provided consent and the language selection step is reached
When the bot sends the language selection message
Then the message includes four inline keyboard buttons in a single row: "English", "中文", "Melayu", "தமிழ்"
And the message text does NOT include a "Reply 1, 2, 3 or 4" instruction

When the patient taps "English"
Then a `callback_query` update is received with `data = "1"`
And the bot calls `answerCallbackQuery` to acknowledge the tap
And `Patient.language_preference` is set to `"en"`
And `onboarding_state` advances to `language_confirmed`

#### Scenario: Medication capture method — patient taps button

Given a patient whose `onboarding_state` is `language_confirmed`
When the bot sends the medication capture prompt
Then the message includes three inline keyboard buttons: "✅ Confirm on file", "📷 Send a photo", "✏️ Enter manually"
And each button's `callback_data` is "1", "2", or "3" respectively
And the message text does NOT include a "Reply 1, 2, or 3" instruction

When the patient taps "📷 Send a photo"
Then the bot receives `callback_query.data = "2"`
And the onboarding sub-flow B (OCR photo upload) is entered

#### Scenario: Contact time preference — patient taps button

Given a patient in the preferences step
When the bot sends the contact time preference prompt
Then the message includes four inline keyboard buttons: "☀️ Morning", "🌤 Afternoon", "🌆 Evening", "🔕 No preference"
And each button's `callback_data` is "1", "2", "3", or "4" respectively

When the patient taps "☀️ Morning"
Then `Patient.contact_window_start` and `Patient.contact_window_end` are set to the morning window (08:00–12:00)
And `onboarding_state` advances to `voice_preference`

#### Scenario: Delivery mode — patient taps button

Given a patient in the `voice_preference` step
When the bot sends the delivery mode selection prompt
Then the message includes three inline keyboard buttons: "💬 Text only", "🔊 Voice only", "💬🔊 Both"
And each button's `callback_data` is "1", "2", or "3" respectively

When the patient taps "💬 Text only"
Then `Patient.nudge_delivery_mode` is set to `"text"`
And `onboarding_state` advances to `complete`

#### Scenario: Voice selection — patient taps button

Given a patient in `voice_preference` state who chose voice or both
When the bot sends the voice selection prompt
Then the message includes three inline keyboard buttons: "👩 Female", "👨 Male", "🎙 Record my own"
And each button's `callback_data` is "1", "2", or "3" respectively

When the patient taps "👩 Female"
Then `Patient.selected_voice_id` is set to the default female ElevenLabs voice ID
And `onboarding_state` advances to `complete`

#### Scenario: Text input fallback still accepted

Given a patient receives an onboarding prompt with inline keyboard buttons
When the patient types "2" as a text message rather than tapping a button
Then the bot accepts "2" and routes it identically to a button tap with `callback_data = "2"`
And the onboarding state advances correctly

#### Scenario: Button tap on unknown chat_id routes to self-onboarding

Given a `callback_query` is received from a `chat_id` not linked to any Patient record
When the webhook processes the callback
Then the bot calls `answerCallbackQuery` to acknowledge the tap
And the self-onboarding flow is initiated for that `chat_id`

