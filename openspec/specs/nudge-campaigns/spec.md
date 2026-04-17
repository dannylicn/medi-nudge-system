# nudge-campaigns Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Campaign state machine

A `NudgeCampaign` progresses through a defined set of states. Transitions outside the state machine are rejected. The system SHALL implement this as described in the scenarios below.

```
pending → sent → responded
               → escalated
               → resolved
               → failed
```

#### Scenario: Valid transition — sent after message dispatched

Given a campaign in `pending` state
When the nudge message is successfully dispatched via WhatsApp
Then the campaign transitions to `sent`

#### Scenario: Valid transition — responded after patient replies

Given a campaign in `sent` state
When an inbound patient reply is classified
Then the campaign transitions to `responded`

#### Scenario: Invalid transition rejected

Given a campaign in `responded` state
When code attempts to set its status to `pending`
Then the state machine raises an error and the status is unchanged

---

### Requirement: LLM nudge generation with template fallback

Messages are generated using GPT-4o when `OPENAI_API_KEY` is set. When the key is absent or the API is unavailable, a static multilingual template is used. The system SHALL implement this as described in the scenarios below.

#### Scenario: LLM generation — API key present

Given `OPENAI_API_KEY` is set and the OpenAI API is reachable
When the nudge generator is called for patient `P-001` (language `zh`, attempt 1, medication `Metformin`)
Then a GPT-4o completion is requested with a prompt containing patient name, medication name, language, attempt number, and warm tone instructions
And the returned text is stored as `NudgeCampaign.message_content`

#### Scenario: Template fallback — no API key

Given `OPENAI_API_KEY` is not set
When the nudge generator is called
Then a template from the built-in library is selected for the patient's language and attempt number
And the template is populated with patient name, medication name, and `days_overdue`

#### Scenario: Template fallback — API unreachable

Given `OPENAI_API_KEY` is set but the OpenAI API returns a 5xx error
When the nudge generator catches the exception
Then the template fallback is used transparently
And the failure is logged but does not block message delivery

---

### Requirement: Multilingual message generation

All patient-facing messages MUST be generated in the patient's `language_preference` (`en`, `zh`, `ms`, `ta`).

#### Scenario: Language respected across LLM and template paths

Given patient `P-001` has `language_preference: ms`
When a nudge message is generated via either path
Then the message content is in Malay

#### Scenario: Template library covers all four languages

Given a template is requested for attempt 2, condition `hypertension`, language `ta`
When the template library is queried
Then a Tamil-language template is returned
And no English text is mixed into the output

---

### Requirement: Three-attempt tone ladder

The message tone escalates with each attempt. The system SHALL implement this as described in the scenarios below.

| Attempt | Tone |
|---|---|
| 1 | Friendly reminder |
| 2 | Gentle concern; reference health risk |
| 3 | Urgency; inform that care coordinator will follow up |

#### Scenario: Attempt 1 — warm, non-judgmental

Given `attempt_number = 1`
When a message is generated (LLM or template)
Then the message tone is friendly and does not emphasise risk or consequences

#### Scenario: Attempt 3 — urgency with nurse handoff

Given `attempt_number = 3`
When a message is generated
Then the message includes language indicating the patient's nurse or care team will be in touch
And the escalation service is notified after dispatch

---

### Requirement: Campaign attempt tracking and retry scheduling

The system tracks how many attempts have been made per campaign and schedules the next attempt if no response is received within 48 hours. The system SHALL implement this as described in the scenarios below.

#### Scenario: No response → next attempt scheduled

Given a campaign is in `sent` state
And 48 hours have passed without a patient response
And `attempt_number < MAX_NUDGE_ATTEMPTS` (default 3)
When the retry scheduler job runs
Then `attempt_number` is incremented
And a new message is generated and dispatched

#### Scenario: Max attempts exhausted → escalation

Given a campaign is in `sent` state with `attempt_number = 3`
And 48 hours have passed without a patient response
When the retry scheduler job runs
Then no further message is sent
And an `EscalationCase` is created with `reason: no_response`, `priority: high`
And the campaign transitions to `escalated`

---

### Requirement: Campaign resolved on confirmed response

When a patient confirms they have collected or taken their medication, the campaign is marked resolved. The system SHALL implement this as described in the scenarios below.

#### Scenario: Patient confirms collection

Given a campaign in `sent` state
When the inbound response is classified as `confirmed`
Then `NudgeCampaign.response_type = confirmed`
And the campaign transitions to `resolved`
And no `EscalationCase` is created

---

### Requirement: Side effect response triggers urgent escalation

A side effect report from the patient MUST always trigger an `EscalationCase` with `priority: urgent`.

#### Scenario: Side effect reply received

Given a campaign in `sent` state
When the inbound response is classified as `side_effect`
Then `NudgeCampaign.response_type = side_effect`
And an `EscalationCase` is created immediately with `priority: urgent`
And the campaign transitions to `escalated`
And a safety acknowledgement message is sent to the patient

---

### Requirement: Question response creates normal escalation

Unresolved patient questions are routed to a care coordinator. The system SHALL implement this as described in the scenarios below.

#### Scenario: Patient asks a question

Given a campaign in `sent` state
When the inbound response is classified as `question`
Then `NudgeCampaign.response_type = question`
And an `EscalationCase` is created with `reason: patient_question`, `priority: normal`
And an acknowledgement message is sent to the patient confirming that their question has been received

### Requirement: Voice nudge delivery via Telegram voice note

When a patient's `nudge_delivery_mode` is `voice` or `both`, the system SHALL generate a TTS audio file using the patient's selected ElevenLabs voice and send it as a Telegram voice note. Text is always generated first; voice is layered on top.

#### Scenario: Voice-only delivery -- successful

Given a patient with `nudge_delivery_mode = "voice"` and a valid `selected_voice_id`
And `ELEVENLABS_API_KEY` is configured
When a nudge campaign message is generated
Then the system calls ElevenLabs TTS with the voice ID and message text
And sends the resulting `.ogg` as a Telegram voice note via `sendVoice`
And `OutboundMessage.delivery_mode` is set to `audio`

#### Scenario: Both delivery -- text and voice sent together

Given a patient with `nudge_delivery_mode = "both"` and a valid `selected_voice_id`
When a nudge campaign message is generated
Then the system sends a text message via `sendMessage`
And sends a voice note via `sendVoice`
And two `OutboundMessage` records are created (one `text`, one `audio`)

#### Scenario: Voice delivery fallback -- ElevenLabs unavailable

Given a patient with `nudge_delivery_mode = "voice"`
And the ElevenLabs TTS API call fails or `ELEVENLABS_API_KEY` is not set
When a nudge campaign message is generated
Then the system falls back to text-only delivery
And `OutboundMessage.delivery_mode` is set to `text`
And the fallback is logged

#### Scenario: Voice delivery fallback -- no voice ID

Given a patient with `nudge_delivery_mode = "voice"` but `selected_voice_id` is null
And no default voice ID is configured
When a nudge campaign message is generated
Then the system falls back to text-only delivery

---

### Requirement: Telegram sendVoice integration

The system SHALL support sending `.ogg` audio files as Telegram voice notes using the `sendVoice` Bot API method.

#### Scenario: Voice note sent successfully

Given a valid `.ogg` file and a patient with a linked `telegram_chat_id`
When `telegram_service.send_voice()` is called
Then the file is posted to `https://api.telegram.org/bot{TOKEN}/sendVoice` as multipart form data
And an `OutboundMessage` record is created with `delivery_mode = "audio"`
And the Telegram `message_id` is stored

#### Scenario: Voice note send failure

Given a valid `.ogg` file
When the Telegram `sendVoice` API returns an error
Then `OutboundMessage.status` is set to `failed`
And the error is logged

---

### Requirement: Daily reminder voice delivery

Voice delivery SHALL also apply to daily medication reminders (not just refill nudge campaigns). The same voice selection and fallback logic applies.

#### Scenario: Daily reminder sent as voice

Given a patient with `nudge_delivery_mode = "voice"` and active medications due now
When the daily reminder service generates a reminder
Then the reminder text is converted to audio via ElevenLabs TTS
And sent as a Telegram voice note

