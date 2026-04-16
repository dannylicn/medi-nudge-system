## ADDED Requirements

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
