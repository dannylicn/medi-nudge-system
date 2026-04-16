## Context

The system currently delivers nudges as text-only Telegram messages. The project spec already references ElevenLabs for voice cloning and defines conventions (`.ogg` cache, `VoiceProfile` soft-delete, PDPA dual consent), but no implementation exists. This change introduces voice nudge delivery with two tiers: a default ElevenLabs voice that any patient can use immediately, and optional caregiver voice cloning as a personal upgrade.

**Stakeholders:** patients (recipients), caregivers (voice donors), care coordinators (manage consent/profiles).

## Goals / Non-Goals

**Goals:**
- Allow patients to receive nudges as Telegram voice notes using a default ElevenLabs voice
- Let patients pick their preferred default voice during onboarding (warm female / warm male)
- Optionally clone a caregiver's voice for a more personal experience (not required)
- Enforce dual consent (patient + donor) only when voice cloning is used
- Degrade gracefully: text fallback when ElevenLabs is unavailable

**Non-Goals:**
- Real-time voice calls or audio streaming
- Patient self-voice cloning (only caregiver voices for now)
- Voice-based response classification (inbound remains text-only)

## Decisions

### 1. Two-tier voice: default voice for everyone, cloning as optional upgrade
- **Decision:** Selecting voice delivery uses a pre-made ElevenLabs voice immediately. Caregiver voice cloning is offered separately and is never a prerequisite.
- **Why:** Voice nudge value (accessibility, low-literacy support) should not be gated on having a caregiver. Cloning adds emotional connection but is a bonus.

### 2. Patient picks a default voice during onboarding
- **Decision:** Offer 2 curated default voices (one warm female, one warm male). Patient picks one. If skipped, a system default is used.
- **Why:** Giving patients a choice increases comfort and engagement. Two options keeps the flow simple.
- **Pre-made voices used:**
  - Female: `Rachel` (calm, warm, multilingual)
  - Male: `Antoni` (warm, friendly, multilingual)
- **Config:** `ELEVENLABS_DEFAULT_VOICE_FEMALE` and `ELEVENLABS_DEFAULT_VOICE_MALE` settings store the voice IDs. Changeable without code changes.

### 3. Voice sample collection via Telegram voice message (when cloning)
- **Decision:** The caregiver records a voice sample by sending a Telegram voice message to the bot after being prompted (~60-90 seconds).
- **Why:** Lowest friction -- caregivers are already onboarded via Telegram.
- **Alternatives considered:** Dashboard audio upload (requires coordinator involvement), phone call recording (complex).

### 4. ElevenLabs Instant Voice Cloning (IVC)
- **Decision:** Use ElevenLabs Instant Voice Cloning API (single sample, no training wait).
- **Why:** ~60s sample is enough for IVC; results available immediately. Supports all 4 project languages (en, zh, ms, ta).

### 5. Audio cache as `.ogg` keyed by internal IDs
- **Decision:** Cache TTS output as `{patient_id}_{medication_id}_{attempt}.ogg` in `MEDIA_STORAGE_PATH/voice_cache/`.
- **Why:** Avoids redundant ElevenLabs API calls. Convention already defined in project.md.
- **Cache invalidation:** Regenerate when message content changes (different attempt, different days_overdue bracket).

### 6. Delivery preference and voice selection stored on Patient model
- **Decision:** Add two fields to `Patient`:
  - `nudge_delivery_mode`: `text` (default), `voice`, `both`
  - `selected_voice_id`: the ElevenLabs voice ID chosen during onboarding (default or cloned)
- **Why:** Simple, queryable, set once during onboarding. Can be changed later via dashboard.

### 7. Onboarding state machine extension
- **Decision:** Insert `voice_preference` state between `preferences` and `complete`.
- **Why:** Natural position -- after contact window selection, before the welcome message.
- **Backward compatible:** Existing patients with `onboarding_state = "complete"` default to `text` delivery.

### 8. Dual consent only required for cloning
- **Decision:** `VoiceProfile` stores `patient_consent_at` and `donor_consent_at`. Both MUST be non-null before the ElevenLabs clone API is called.
- **Why:** PDPA dual consent applies to voice cloning specifically, not to using a stock TTS voice.

## Data Model

### VoiceProfile (new table: `voice_profiles`)
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| patient_id | FK -> patients | One-to-one (active) |
| donor_name | String(200) | Caregiver name |
| donor_telegram_id | String(30) | Caregiver's chat_id |
| elevenlabs_voice_id | String(100) | Returned by clone API |
| sample_file_path | String(500) | Server-side path to raw `.ogg` |
| patient_consent_at | DateTime | Patient approved voice cloning |
| donor_consent_at | DateTime | Donor approved voice use |
| is_active | Boolean | Soft delete; revoking consent sets False |
| created_at | DateTime | |

### Patient (modified)
| Column | Type | Notes |
|---|---|---|
| nudge_delivery_mode | String(10) | `text` (default), `voice`, `both` |
| selected_voice_id | String(100) | ElevenLabs voice ID (default or cloned); nullable |

### Settings (new keys)
| Key | Default | Notes |
|---|---|---|
| ELEVENLABS_DEFAULT_VOICE_FEMALE | `""` | Voice ID for the female default option (Rachel) |
| ELEVENLABS_DEFAULT_VOICE_MALE | `""` | Voice ID for the male default option (Antoni) |

## Flow: Voice Preference During Onboarding

```
1. Patient reaches voice_preference step
2. Bot asks: "How would you like to receive medication reminders?"
   -> 1. Text only  2. Voice only  3. Both text and voice
3. If voice or both:
   a. Bot asks: "Choose a voice for your reminders:"
      -> 1. Female voice  2. Male voice
   b. Store selected_voice_id from the chosen default
   c. Voice nudges are immediately available using this voice
4. Advance to complete (welcome message)

Voice cloning is NOT part of onboarding -- it is triggered separately
(see below).
```

## Flow: Voice Cloning (optional, post-onboarding)

```
Triggered via: dashboard action by coordinator, or future patient command.

1. Verify caregiver is linked (caregiver_telegram_id set)
2. Record patient consent (patient_consent_at = now)
3. Send Telegram message to caregiver:
   "Hi [name], [patient] would like to hear your voice in their
    medication reminders. Please send a 60-90 second voice message
    reading the following text: [script]"
4. Caregiver sends voice message -> bot downloads .ogg -> stores at sample_file_path
5. Bot asks caregiver: "Do you consent to your voice being used for
   medication reminders for [patient]?"
6. Caregiver replies YES -> donor_consent_at = now
7. Both consents present -> call ElevenLabs IVC API -> store elevenlabs_voice_id
8. Update patient.selected_voice_id to the cloned voice
9. Future nudges use the cloned voice
```

## Flow: Voice Nudge Delivery

```
1. nudge_campaign_service.create_and_send() generates text message as usual
2. Check patient.nudge_delivery_mode:
   - "text" -> send text only (current behavior, no change)
   - "voice" or "both":
     a. Determine voice_id = patient.selected_voice_id
        (falls back to ELEVENLABS_DEFAULT_VOICE_FEMALE if null)
     b. If ELEVENLABS_API_KEY not set -> fall back to text only
     c. Check audio cache for existing .ogg
     d. If cache miss: call ElevenLabs TTS with voice_id + message text -> save .ogg
     e. Send .ogg as Telegram voice note via sendVoice API
     f. If "both": also send text message
     g. If voice send fails: fall back to text
3. OutboundMessage.delivery_mode records what was actually sent ("text" or "audio")
```

## Risks / Trade-offs

- **ElevenLabs API cost:** ~$0.18/min for TTS. Mitigated by caching and short messages (~15-20s each).
- **ElevenLabs downtime:** Always fall back to text. OutboundMessage.delivery_mode tracks actual delivery.
- **Voice sample quality:** Telegram voice messages are Opus-encoded .ogg, which ElevenLabs accepts.
- **PDPA compliance:** Dual consent enforced at model level for cloning only; default voice needs no special consent.

## Open Questions

- None -- all clarifications resolved during proposal discussion.
