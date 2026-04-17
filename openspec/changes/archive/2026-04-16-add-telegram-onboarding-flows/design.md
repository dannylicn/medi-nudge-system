# Design: add-telegram-onboarding-flows

## Problem: Telegram bots cannot initiate conversations

The Telegram Bot API requires that a user sends the first message to a bot before the bot can reply. This makes the "coordinator creates patient → bot sends invite SMS" pattern impossible with Telegram alone.

**Solution:** Token-based deep-link. The coordinator shares a `t.me` link containing a one-time token. The patient taps it, Telegram opens, the `/start TOKEN` command is sent by the *patient's* client, and the bot now has an open conversation thread.

## OnboardingToken table

```
onboarding_tokens
  id            INTEGER PK
  patient_id    INTEGER FK → patients.id
  token         VARCHAR(64) UNIQUE   -- URL-safe random 32 bytes, hex-encoded
  expires_at    DATETIME             -- UTC, 72 hours from creation
  used_at       DATETIME NULLABLE    -- set when the bot receives /start TOKEN
  created_at    DATETIME
```

Index: `(token)`, `(patient_id)`.

The token is single-use. Once `used_at` is set the bot rejects further attempts with this token.

## Self-registration identity verification

We cannot store the full NRIC to match against, because NRIC is stored only as a SHA-256 hash. The self-onboarding flow therefore:

1. Prompts the patient to enter their full NRIC.
2. Hashes the input with SHA-256 using the existing `hash_sha256()` helper.
3. Queries `patients` where `nric_hash = hash AND telegram_chat_id IS NULL`.
4. On match: links the chat and continues.

If no match is found (patient not pre-registered by a doctor):
- Creates a `Patient` stub with `onboarding_state = "self_registering"`.
- Collects name and phone number over subsequent messages.
- Creates an `EscalationCase(reason="self_registration_review")` so a coordinator can review and approve before nudges begin.
- Patient is informed: "Your registration is under review. A care coordinator will be in touch within 1 business day."

## State machine (complete)

```
[new]
  │
  ├─ coordinator creates patient → token issued → link shared
  │       ↓ patient taps link → /start TOKEN
  │
  ├─ patient sends /start (no token) → identity_verification
  │       ↓ NRIC match → linked
  │       ↓ no match  → self_registering → coordinator review
  │
  ↓
invited
  ↓ YES / consent accepted
consent_pending
  ↓ language selected
language_confirmed
  ↓ medication sub-flow chosen
medication_capture
  ↓ patient confirms med list
confirm
  ↓ contact window set (or 24h timeout → default)
preferences
  ↓
complete

drop_off_recovery  ← scheduler sets this after 2 failed retries at any state
```

## Sequence: coordinator-initiated

```
Coordinator → POST /api/patients         → Patient row + OnboardingToken
Dashboard   ← 201 { ... invite_link }
Coordinator → (copy) share link with patient out-of-band
Patient     → tap link → Telegram sends /start <token>
Bot         → validate token → link telegram_chat_id → state: invited
Bot         → send consent message
Patient     → YES
Bot         → state: consent_pending → language prompt
...
```

## Sequence: patient self-onboard

```
Patient     → /start (no token)
Bot         → "What are the last 4 characters of your NRIC/FIN? (e.g. 567A)"
Patient     → S1234567A
Bot         → hash → query patients
            → match: link chat_id → state: invited → consent message
            → no match: create stub → state: self_registering
                        → "Registration under review..."
                        → EscalationCase(reason=self_registration_review)
```

## Security considerations

- Token is 32 URL-safe random bytes — entropy sufficient to prevent brute force.
- Token expires after 72 hours; `used_at` prevents replay.
- NRIC is hashed before any database query; plaintext never logged.
- `telegram_chat_id` is stored as the Telegram numeric `chat.id` (string) — not the phone number.
- Coordinator-initiated flow uses the `invite_link` from the API response; it is never stored in the DB beyond the token.

## chat_id vs phone_number

Currently `Patient.phone_number` is overloaded as both the real phone number and the Telegram `chat_id`. This change introduces a dedicated `Patient.telegram_chat_id` column (already exists in the model as `caregiver_telegram_id` for caregivers — same pattern). `phone_number` reverts to storing the real phone number only.

All `telegram_service.send_text()` calls for patient messaging must be updated to use `patient.telegram_chat_id` instead of `patient.phone_number`.
