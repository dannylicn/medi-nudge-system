## MODIFIED Requirements

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
