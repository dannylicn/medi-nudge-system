# patient-onboarding Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
invited → consent_pending → language_confirmed → medication_capture → confirm → preferences → complete
```

#### Scenario: Language selection advances to medication_capture

Given a patient in `consent_pending` state who has consented
When the patient replies with a valid language selection (1–4 or language name)
Then `Patient.language_preference` is set
And `onboarding_state` advances to `language_confirmed`
And the bot immediately sends the medication capture prompt

#### Scenario: Medication capture — dispensing records available

Given a patient in `medication_capture` state
And the patient has existing `PatientMedication` records imported from a dispensing feed
When the patient replies `1` or `YES` to confirm the displayed list
Then all listed medications are confirmed active
And `onboarding_state` advances to `confirm`

#### Scenario: Medication capture — photo submitted

Given a patient in `medication_capture` state
When the patient sends a photo message (prescription or label)
Then the image is routed to the OCR pipeline
And the bot replies: "I've received your prescription. I'll process it and get back to you shortly."
And `onboarding_state` remains `medication_capture` until OCR completes

#### Scenario: Medication capture — manual entry

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
When the patient selects a preferred contact window (e.g. `3pm–6pm`)
Then `Patient.contact_window_start` and `Patient.contact_window_end` are recorded
And `onboarding_state` advances to `complete`
And the welcome message is sent

#### Scenario: Preferences step timed out — default applied

Given a patient in `preferences` state
When 24 hours pass with no response
Then `onboarding_state` advances to `complete` with no contact window restriction
And the welcome message is sent

---

### Requirement: telegram_chat_id separate from phone_number

`Patient.telegram_chat_id` MUST be stored as a dedicated column. `Patient.phone_number` MUST store only the real E.164 phone number.

#### Scenario: Message routing uses telegram_chat_id

Given a patient with `telegram_chat_id = "123456789"` and `phone_number = "+6591234567"`
When the system sends a Telegram message to this patient
Then `telegram_service.send_text()` is called with `to=patient.telegram_chat_id`
And `patient.phone_number` is not passed to the Telegram API
