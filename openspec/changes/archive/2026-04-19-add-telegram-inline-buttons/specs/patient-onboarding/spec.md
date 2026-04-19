## ADDED Requirements

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
