## ADDED Requirements

### Requirement: VoiceProfile model with dual consent

The system SHALL store voice cloning profiles in a `voice_profiles` table. A VoiceProfile links a patient to a caregiver-donated voice clone. Both patient and donor consent timestamps MUST be recorded before the ElevenLabs clone API is called. Soft-delete via `is_active = False`.

#### Scenario: VoiceProfile created with dual consent

Given a patient has opted for voice nudges and a caregiver is linked
When the patient consents to voice cloning AND the caregiver consents to voice donation
Then a `VoiceProfile` is created with `patient_consent_at` and `donor_consent_at` both set
And `is_active = True`

#### Scenario: Clone API blocked without dual consent

Given a VoiceProfile where `donor_consent_at` is null
When the system attempts to call the ElevenLabs clone API
Then the call is rejected and the VoiceProfile remains without an `elevenlabs_voice_id`

#### Scenario: Consent revoked — soft delete

Given an active VoiceProfile
When the patient or donor revokes consent
Then `VoiceProfile.is_active` is set to `False`
And the voice sample file is deleted from storage
And future nudges fall back to the patient's selected default voice

---

### Requirement: Voice sample collection via Telegram

The system SHALL collect voice samples from caregivers via Telegram voice messages. The caregiver is prompted to read a script of 60-90 seconds. The voice message is downloaded and stored server-side.

#### Scenario: Caregiver sends voice sample

Given a caregiver with a linked Telegram account is prompted to record a voice sample
When the caregiver sends a voice message to the bot
Then the system downloads the `.ogg` file via the Telegram Bot API
And stores it at `MEDIA_STORAGE_PATH/voice_samples/{voice_profile_id}.ogg`
And updates `VoiceProfile.sample_file_path`

#### Scenario: Caregiver sends non-voice message

Given a caregiver is in the voice sample collection state
When the caregiver sends a text message instead of a voice message
Then the bot replies asking them to send a voice message
And no sample is recorded

---

### Requirement: ElevenLabs Instant Voice Cloning

The system SHALL use the ElevenLabs Instant Voice Cloning API to create a cloned voice from the caregiver's sample. The resulting `elevenlabs_voice_id` is stored on the VoiceProfile.

#### Scenario: Successful voice clone

Given a VoiceProfile with both consents and a valid sample file
When the system calls the ElevenLabs IVC API with the `.ogg` sample
Then the returned voice ID is stored in `VoiceProfile.elevenlabs_voice_id`
And `Patient.selected_voice_id` is updated to the cloned voice ID

#### Scenario: ElevenLabs API failure

Given the ElevenLabs API returns an error during cloning
When the system catches the exception
Then the VoiceProfile is kept without an `elevenlabs_voice_id`
And the patient continues to use their selected default voice
And the failure is logged for coordinator review

---

### Requirement: ElevenLabs TTS for voice nudge generation

The system SHALL generate voice nudge audio by calling the ElevenLabs TTS API with a voice ID and message text. Output is cached as `.ogg` files keyed by `{patient_id}_{medication_id}_{attempt}.ogg`.

#### Scenario: TTS cache miss — new audio generated

Given a voice nudge is needed for patient 42, medication 7, attempt 1
And no cached file exists at `voice_cache/42_7_1.ogg`
When the TTS service is called
Then the ElevenLabs TTS API is invoked with the patient's voice ID and message text
And the output is saved to `voice_cache/42_7_1.ogg`

#### Scenario: TTS cache hit — cached audio reused

Given a cached file exists at `voice_cache/42_7_1.ogg`
When the TTS service is called for the same patient, medication, and attempt
Then the cached file is returned without calling the ElevenLabs API

#### Scenario: TTS fallback when ELEVENLABS_API_KEY not set

Given `ELEVENLABS_API_KEY` is not configured
When the TTS service is called
Then no audio is generated
And the system falls back to text-only delivery
And the fallback is logged

---

### Requirement: Default voice selection

The system SHALL provide two pre-made ElevenLabs voices (one female, one male) that patients can choose from. These require no cloning setup and are immediately available.

#### Scenario: Patient selects female default voice

Given the patient is in the voice preference onboarding step
And selects "Female voice"
When the selection is saved
Then `Patient.selected_voice_id` is set to `ELEVENLABS_DEFAULT_VOICE_FEMALE`

#### Scenario: Patient selects male default voice

Given the patient is in the voice preference onboarding step
And selects "Male voice"
When the selection is saved
Then `Patient.selected_voice_id` is set to `ELEVENLABS_DEFAULT_VOICE_MALE`

#### Scenario: No selection — system default used

Given a patient with `selected_voice_id = null` and `nudge_delivery_mode` includes voice
When a voice nudge is generated
Then the system uses `ELEVENLABS_DEFAULT_VOICE_FEMALE` as the fallback voice ID
