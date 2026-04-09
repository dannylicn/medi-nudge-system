# Medi-Nudge System — Design & Architecture Plan

## Problem Statement

Non-adherence to medication is a silent crisis in Singapore's chronic disease management. Studies suggest that nearly 50% of patients with chronic conditions like diabetes, hypertension, and hyperlipidemia do not take their medications as prescribed. This drives avoidable complications, hospitalisations, and downstream costs to the healthcare system — directly undermining MOH's Healthier SG strategy.

Current interventions are largely reactive: patients are counselled at the clinic, and no one follows up until the next appointment (often 3–6 months later).

---

## Proposed Solution

A personalised, automated medication adherence system that uses refill data and patient behaviour signals to deliver timely, context-aware nudges via WhatsApp — the dominant messaging channel in Singapore — with seamless escalation to care coordinators when needed.

---

## Patient Onboarding Journey

The onboarding is designed to be **WhatsApp-first** (lowest friction for Singapore patients), with a **web fallback** for rich capture tasks (OCR upload, consent forms).

### Journey Goals

- Get explicit consent to WhatsApp outreach
- Confirm patient identity + preferred language (en / zh / ms / ta)
- Populate a reliable medication list (import feed, OCR, or manual)
- Establish a first “refill due” baseline (last dispense + days_supply)
- Teach the patient how to respond (confirm / ask / side effects)

### Entry Modes

| Mode | Trigger | Best for |
|---|---|---|
| Clinic-enrolled | Care coordinator enrolls patient in dashboard | v1 rollout, high completion, low fraud |
| Self-enrolled | Patient scans QR at clinic/pharmacy or clicks link | pilots, caregiver-led onboarding |

### Happy Path (Clinic-enrolled)

1. **Care coordinator creates patient** (phone number, name, language if known)
2. **System sends WhatsApp invite**: purpose + consent request
3. **Consent + opt-in**: patient replies “YES” (or taps quick reply)
4. **Language confirmation**: patient selects `English / 中文 / Melayu / தமிழ்`
5. **Medication capture** (choose one)
  - **A. Dispensing feed available**: records imported; patient only confirms
  - **B. OCR**: patient uploads prescription/label photo; system extracts; coordinator reviews
  - **C. Manual**: patient answers a short guided form (name, dose, frequency, refill days)
6. **Confirm meds**: patient confirms summary (or coordinator finalizes from dashboard)
7. **Reminder preferences**: quiet hours + preferred contact window
8. **Welcome + reply guide**: “Reply YES when collected; HELP for questions; SIDE EFFECT if unwell”

### Happy Path (Self-enrolled, QR/link)

1. Patient scans QR → lightweight web page collects phone number
2. System sends WhatsApp invite + consent
3. Continue steps 3–8 above

### Optional Add-ons During Onboarding

#### A) Prescription / Sticker OCR (recommended)

- Patient uploads an image via WhatsApp photo or web upload
- System extracts structured fields → status `review`
- Care coordinator confirms/edits fields → status `confirmed`
- System creates/updates `Medication`, `PatientMedication`, and `DispensingRecord`

#### B) Loved-one Voice Nudges (opt-in)

- Only offered **after** baseline onboarding is complete
- Dual consent (patient + voice donor) captured + timestamped
- Donor provides ~60–90s sample → clone created → test playback approval

### Drop-off Recovery (Critical)

| Drop-off point | Recovery |
|---|---|
| No response to invite | Retry 1–2 times, then open an `EscalationCase` for coordinator follow-up |
| OCR extraction low confidence | Force dashboard review; do not auto-populate |
| Patient confused | Route “HELP” responses to escalation with context |
| Side effect indicated | Immediate escalation with priority `urgent` |

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          MEDI-NUDGE SYSTEM                               │
│                                                                          │
│  ┌──────────────┐    ┌───────────────┐    ┌───────────────────────────┐  │
│  │  Data Ingest │    │  Core Engine  │    │    Care Team Dashboard    │  │
│  │  (NEHR/CSV)  │───▶│  (FastAPI)    │───▶│    (React + Vite)         │  │
│  └──────────────┘    └──────┬────────┘    └───────────────────────────┘  │
│                             │                                             │
│         ┌───────────────────┼───────────────────┐                        │
│         ▼                   ▼                   ▼                        │
│  ┌────────────┐      ┌────────────┐      ┌─────────────┐                 │
│  │  Scheduler │      │  LLM Nudge │      │  Escalation │                 │
│  │(APScheduler)      │  Generator │      │   Manager   │                 │
│  └────────────┘      └─────┬──────┘      └─────────────┘                 │
│                            │                                             │
│               ┌────────────┴────────────┐                               │
│               ▼                         ▼                               │
│       ┌──────────────┐         ┌─────────────────┐                      │
│       │  Text Nudge  │         │  Voice Nudge    │                      │
│       │  (WhatsApp)  │         │  Pipeline       │                      │
│       └──────┬───────┘         └────────┬────────┘                      │
│              │                          │                               │
│              │              ┌───────────▼──────────┐                    │
│              │              │  ElevenLabs API      │                    │
│              │              │  (Voice Clone + TTS) │                    │
│              │              └───────────┬──────────┘                    │
│              │                          │                               │
│              └──────────┬───────────────┘                               │
│                         ▼                                               │
│                  ┌─────────────┐                                        │
│                  │  Twilio API │                                        │
│                  │ (WhatsApp   │                                        │
│                  │  text+audio)│                                        │
│                  └─────────────┘                                        │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │               Prescription / Label OCR Pipeline                  │   │
│  │                                                                  │   │
│  │  Photo upload (web/WhatsApp) ──▶ GPT-4o Vision (VLM)            │   │
│  │     ──▶ Extracted fields ──▶ Human review ──▶ DB auto-populate   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Backend** | Python + FastAPI | Async, fast, clean API docs via Swagger |
| **Database** | SQLite → PostgreSQL | SQLite for dev; easy migration to Postgres for prod |
| **Scheduler** | APScheduler (in-process) | No extra infra for dev; swap to Celery+Redis for prod |
| **LLM** | OpenAI GPT-4o (with fallback templates) | Multilingual personalisation; templates if no API key |
| **Voice Cloning + TTS** | ElevenLabs API | Best-in-class multilingual voice clone from ~1 min of audio; REST API |
| **Audio storage** | Local filesystem → S3/Blob | Generated `.ogg` audio cached by (patient, medication, attempt) |
| **Prescription OCR/VLM** | GPT-4o Vision (primary) + Tesseract OCR (fallback) | VLM handles handwritten, printed, and multilingual labels; Tesseract for structured typed labels without API key |
| **Messaging** | Twilio WhatsApp Business API | Supports both text messages and audio voice note attachments |
| **Frontend** | React + Vite + TailwindCSS + Recharts | Lightweight, fast dashboard |
| **Auth** | Simple JWT (care team login) | Minimal viable for v1 |

---

## Data Model

```
Patient
├── id, nric_hash (SHA-256), full_name, age, phone_number
├── language_preference (en | zh | ms | ta)
├── conditions [ "diabetes", "hypertension", "hyperlipidemia" ]
├── risk_level (low | normal | high)
└── is_active

Medication
├── id, name, generic_name, category
└── default_refill_days

PatientMedication  (junction — a patient's active prescription)
├── patient_id, medication_id
├── dosage, refill_interval_days
└── is_active

DispensingRecord  (ingested from NEHR/pharmacy)
├── patient_id, medication_id
├── dispensed_at, days_supply, quantity
└── source (pharmacy | nehr | manual)

NudgeCampaign  (one campaign per patient+medication gap event)
├── patient_id, medication_id
├── status (pending → sent → responded | escalated | resolved)
├── days_overdue, attempt_number (1–3)
├── message_content, language
└── response, response_type (confirmed | question | side_effect | negative)

EscalationCase
├── nudge_campaign_id, patient_id
├── reason (no_response | side_effect | repeated_non_adherence)
├── priority (normal | high | urgent)
├── status (open | in_progress | resolved)
└── assigned_to, notes

OutboundMessage  (WhatsApp message delivery record)
├── campaign_id, whatsapp_message_id
├── content, sent_at, delivered_at
├── delivery_mode (text | voice)
├── audio_url            # path/URL to generated .ogg file if voice
└── status (sent | delivered | read | failed)

VoiceProfile  (one per patient — the cloned loved-one voice)
├── id, patient_id
├── donor_name           # e.g. "Mei Ling (daughter)"
├── donor_relationship   # spouse | child | parent | sibling | friend
├── elevenlabs_voice_id  # returned after clone; used for all TTS calls
├── sample_duration_s    # duration of original audio sample in seconds
├── language             # en | zh | ms | ta
├── consent_obtained_at  # timestamp of explicit consent
├── consent_by           # who gave consent (patient or donor, with name)
└── is_active

VoiceSample  (raw audio upload record — retained for consent audit trail)
├── id, voice_profile_id
├── file_path            # stored securely; not publicly accessible
├── file_size_bytes
├── uploaded_at
└── uploaded_by_ip       # for audit; hashed

PrescriptionScan  (one record per uploaded image)
├── id, patient_id
├── image_path           # stored securely; not publicly accessible
├── image_hash           # SHA-256 of image bytes (dedup / audit)
├── source               # web_upload | whatsapp_photo | camera
├── ocr_engine           # gpt4o_vision | tesseract
├── raw_extracted_json   # full VLM/OCR output as JSON
├── status               # pending | review | confirmed | rejected
├── confirmed_by         # care_coordinator user id (if manually reviewed)
├── confirmed_at
├── uploaded_at
└── uploaded_by_ip       # hashed

ExtractedMedicationField  (structured fields parsed from a PrescriptionScan)
├── id, scan_id
├── field_name           # medication_name | dosage | frequency | refill_days
│                        # | prescriber | clinic | dispense_date | expiry_date
│                        # | instructions | warnings
├── extracted_value      # raw VLM output
├── confidence           # 0.0–1.0 (VLM self-reported or heuristic)
├── is_corrected         # true if a human edited the value
└── corrected_value      # human-corrected value (if applicable)
```

---

## Database Design

### Engine

| Environment | Engine | Notes |
|---|---|---|
| Development | SQLite | Zero-config, single file `medi_nudge.db` |
| Production | PostgreSQL 15+ | Swap `DATABASE_URL` env var; no code changes |

ORM: SQLAlchemy 2.0 (declarative), migrations via Alembic.

---

### Entity Relationship Diagram

```
                     ┌─────────────────┐
                     │    Medication   │
                     │─────────────────│
                     │ id (PK)         │
                     │ name            │
                     │ generic_name    │
                     │ category        │
                     │ default_refill_ │
                     │   days          │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
  ┌───────────────────┐       │    ┌──────────────────────┐
  │  PatientMedication│       │    │   DispensingRecord   │
  │───────────────────│       │    │──────────────────────│
  │ id (PK)           │       │    │ id (PK)              │
  │ patient_id (FK)   │       │    │ patient_id (FK)      │
  │ medication_id (FK)│       │    │ medication_id (FK)   │
  │ dosage            │       │    │ dispensed_at         │
  │ refill_interval_  │       │    │ days_supply          │
  │   days            │       │    │ quantity             │
  │ is_active         │       │    │ source               │
  └─────────┬─────────┘       │    └──────────────────────┘
            │                 │
            └─────────────────┘
                      │ patient_id
                      ▼
             ┌─────────────────┐
             │     Patient     │
             │─────────────────│
             │ id (PK)         │
             │ nric_hash       │◀── SHA-256 only, no plaintext
             │ full_name       │
             │ age             │
             │ phone_number    │
             │ language_pref   │
             │ conditions JSON │
             │ risk_level      │
             │ is_active       │
             └────────┬────────┘
                      │
      ┌───────────────┼────────────────┬─────────────────┐
      ▼               ▼                ▼                 ▼
┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────────┐
│  Nudge   │  │ Escalation   │  │  Voice    │  │ Prescription     │
│ Campaign │  │    Case      │  │  Profile  │  │     Scan         │
│──────────│  │──────────────│  │───────────│  │──────────────────│
│ id (PK)  │  │ id (PK)      │  │ id (PK)   │  │ id (PK)          │
│patient_id│  │ campaign_id  │  │patient_id │  │ patient_id (FK)  │
│medic_id  │  │ patient_id   │  │donor_name │  │ image_path       │
│ status   │  │ reason       │  │donor_rel  │  │ image_hash       │
│days_over │  │ priority     │  │elevenlabs_│  │ source           │
│attempt_# │  │ status       │  │  voice_id │  │ ocr_engine       │
│message   │  │ assigned_to  │  │language   │  │ raw_json         │
│language  │  │ notes        │  │consent_at │  │ status           │
│response  │  └──────────────┘  │is_active  │  │ confirmed_by     │
│resp_type │                    └─────┬─────┘  └────────┬─────────┘
└────┬─────┘                          │                  │
     │                                ▼                  ▼
     ▼                         ┌────────────┐  ┌──────────────────────┐
┌──────────────┐               │ Voice      │  │ ExtractedMedication  │
│  Outbound    │               │ Sample     │  │      Field           │
│  Message     │               │────────────│  │──────────────────────│
│──────────────│               │ id (PK)    │  │ id (PK)              │
│ id (PK)      │               │profile_id  │  │ scan_id (FK)         │
│ campaign_id  │               │ file_path  │  │ field_name           │
│ patient_id   │               │ file_size  │  │ extracted_value      │
│ content      │               │uploaded_at │  │ confidence           │
│ delivery_mode│               │uploaded_ip │  │ is_corrected         │
│ audio_url    │               └────────────┘  │ corrected_value      │
│ status       │                               └──────────────────────┘
└──────────────┘
```

---

### Table Reference

#### Patient
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `nric_hash` | String(64) UNIQUE | SHA-256 of NRIC — no plaintext stored |
| `full_name` | String(200) | |
| `age` | Integer | |
| `phone_number` | String(30) | E.164 format e.g. `+6591234567` |
| `language_preference` | String(10) | `en` \| `zh` \| `ms` \| `ta` |
| `conditions` | JSON | `["diabetes", "hypertension"]` |
| `risk_level` | String(20) | `low` \| `normal` \| `high` |
| `is_active` | Boolean | Soft-delete flag |
| `created_at` / `updated_at` | DateTime | Auto-managed |

#### Medication
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name` | String(200) | Brand name e.g. `Glucophage` |
| `generic_name` | String(200) | e.g. `Metformin` |
| `category` | String(100) | `antidiabetic` \| `antihypertensive` \| `lipid_lowering` |
| `default_refill_days` | Integer | Default 30 |

#### PatientMedication *(junction)*
| Column | Type | Notes |
|---|---|---|
| `patient_id` | FK → Patient | |
| `medication_id` | FK → Medication | |
| `dosage` | String(100) | e.g. `500mg` |
| `refill_interval_days` | Integer | Overrides `Medication.default_refill_days` |
| `is_active` | Boolean | |

#### DispensingRecord
| Column | Type | Notes |
|---|---|---|
| `patient_id` | FK → Patient | |
| `medication_id` | FK → Medication | |
| `dispensed_at` | DateTime | |
| `days_supply` | Integer | Drives refill-due calculation |
| `quantity` | Integer | Number of tablets/units |
| `source` | String(100) | `pharmacy` \| `nehr` \| `manual` \| `ocr` |

#### NudgeCampaign
| Column | Type | Notes |
|---|---|---|
| `patient_id` | FK → Patient | |
| `medication_id` | FK → Medication | |
| `status` | String(50) | See state machine below |
| `days_overdue` | Integer | At time of trigger |
| `attempt_number` | Integer | 1–3 |
| `message_content` | Text | Generated message text |
| `language` | String(10) | Language used for this message |
| `response` | Text | Patient's reply text |
| `response_type` | String(50) | `confirmed` \| `question` \| `side_effect` \| `negative` \| `none` |

#### EscalationCase
| Column | Type | Notes |
|---|---|---|
| `nudge_campaign_id` | FK → NudgeCampaign | |
| `patient_id` | FK → Patient | |
| `reason` | String(200) | `no_response` \| `side_effect` \| `repeated_non_adherence` \| `patient_question` |
| `priority` | String(20) | `low` \| `normal` \| `high` \| `urgent` |
| `status` | String(50) | `open` \| `in_progress` \| `resolved` |
| `assigned_to` | String(200) | Care coordinator name/ID |
| `notes` | Text | Free-text coordinator notes |

#### OutboundMessage
| Column | Type | Notes |
|---|---|---|
| `campaign_id` | FK → NudgeCampaign | |
| `patient_id` | FK → Patient | |
| `whatsapp_message_id` | String(200) | Twilio SID for delivery tracking |
| `content` | Text | Message text |
| `delivery_mode` | String(20) | `text` \| `voice` |
| `audio_url` | String | Path/URL to `.ogg` file (voice only) |
| `status` | String(50) | `sent` \| `delivered` \| `read` \| `failed` |

#### VoiceProfile
| Column | Type | Notes |
|---|---|---|
| `patient_id` | FK → Patient | One active profile per patient |
| `donor_name` | String(200) | e.g. `Mei Ling (daughter)` |
| `donor_relationship` | String(50) | `spouse` \| `child` \| `parent` \| `sibling` \| `friend` |
| `elevenlabs_voice_id` | String(200) | Returned by ElevenLabs; used for all TTS |
| `sample_duration_s` | Integer | Duration of original recording |
| `language` | String(10) | Language of the voice sample |
| `consent_obtained_at` | DateTime | Dual consent timestamp |
| `consent_by` | String(200) | Name of consenting party |
| `is_active` | Boolean | False = revoked |

#### VoiceSample
| Column | Type | Notes |
|---|---|---|
| `voice_profile_id` | FK → VoiceProfile | |
| `file_path` | String | Encrypted; not publicly accessible |
| `file_size_bytes` | Integer | |
| `uploaded_at` | DateTime | |
| `uploaded_by_ip` | String | SHA-256 hashed for audit |

#### PrescriptionScan
| Column | Type | Notes |
|---|---|---|
| `patient_id` | FK → Patient | |
| `image_path` | String | Encrypted; served via auth-gated endpoint only |
| `image_hash` | String(64) | SHA-256 for deduplication |
| `source` | String(50) | `web_upload` \| `whatsapp_photo` \| `camera` |
| `ocr_engine` | String(50) | `gpt4o_vision` \| `tesseract` |
| `raw_extracted_json` | JSON | Full VLM/OCR output |
| `status` | String(50) | See state machine below |
| `confirmed_by` | Integer | Care coordinator user ID |
| `confirmed_at` | DateTime | |

#### ExtractedMedicationField
| Column | Type | Notes |
|---|---|---|
| `scan_id` | FK → PrescriptionScan | |
| `field_name` | String(100) | `medication_name` \| `dosage` \| `frequency` \| `refill_days` \| `prescriber` \| `clinic` \| `dispense_date` \| `expiry_date` \| `instructions` \| `warnings` |
| `extracted_value` | Text | Raw VLM/OCR output |
| `confidence` | Float | 0.0–1.0; fields < 0.75 flagged for review |
| `is_corrected` | Boolean | True if human edited |
| `corrected_value` | Text | Human-corrected value |

---

### Status State Machines

**NudgeCampaign.status**
```
pending ──▶ sent ──▶ responded
                 ├──▶ escalated
                 ├──▶ resolved
                 └──▶ failed
```

**EscalationCase.status**
```
open ──▶ in_progress ──▶ resolved
```

**PrescriptionScan.status**
```
pending ──▶ review ──▶ confirmed
                   └──▶ rejected
```

**OutboundMessage.status**
```
sent ──▶ delivered ──▶ read
     └──▶ failed
```

---

### Privacy & Security Notes

| Concern | Approach |
|---|---|
| NRIC | SHA-256 hash only; plaintext never stored or logged |
| IP addresses | SHA-256 hashed before storage in `uploaded_by_ip` fields |
| Prescription images | Encrypted at rest; served only via auth-gated API; never public URLs |
| Voice samples | Encrypted at rest; used only for one-time cloning call; deleted on consent revocation |
| Audio cache files | Stored server-local or S3 with private ACL; keyed by internal IDs not patient names |

---

## Core Flows

### 1 — Refill Gap Detection (runs daily via scheduler)

```
For each active PatientMedication:
  last_dispense = latest DispensingRecord for (patient, medication)
  due_date      = last_dispense.dispensed_at + days_supply
  days_overdue  = today − due_date

  if days_overdue >= WARNING_DAYS (default 3):
    if no open NudgeCampaign already exists → create one, trigger nudge
  if days_overdue >= ESCALATION_DAYS (default 14):
    auto-escalate regardless of nudge state
```

### 2 — Nudge Generation

```
Input:  patient profile, medication, days_overdue, language, attempt #

If OPENAI_API_KEY set:
  → GPT-4o with structured prompt (tone: warm, non-judgmental, culturally aware)
Else:
  → Fallback template library (4 languages × 3 conditions × 3 attempt tones)

Output: personalised WhatsApp message text
```

**Attempt tone ladder:**

| Attempt | Tone |
|---|---|
| 1 | Friendly reminder |
| 2 | Gentle concern, mention health risk |
| 3 | Urgency + "Your nurse will be in touch" |

### 3 — Inbound Response Triage (Twilio webhook)

```
Patient replies → Twilio webhook → POST /api/webhook/whatsapp

Auto-classify response:
  "collected" / "yes" / "ok"     → response_type = confirmed, campaign resolved
  "side effect" / "pain" / etc.  → response_type = side_effect, escalate URGENT
  "?" / question keywords        → response_type = question, escalate for nurse
  No reply after 48h             → schedule next attempt or escalate
```

### 4 — Escalation

```
Triggers:
  a) attempt_number > MAX_NUDGE_ATTEMPTS (3) with no confirmed response
  b) response_type = side_effect
  c) days_overdue >= ESCALATION_DAYS

Creates EscalationCase:
  priority = urgent  (side_effect)
           = high    (>3 attempts no response)
           = normal  (question / routine)

Dashboard surfaces these for care coordinators to action.
```

### 5 — Prescription / Medicine Label OCR

This feature lets a patient or care coordinator upload a photo of a prescription slip or medicine sticker (pharmacy label). A VLM automatically extracts the medication details and pre-populates the system — eliminating manual data entry errors.

#### 5a — Image Ingestion

```
Upload channels:
  a) Web form (frontend /scan-prescription page) — drag-and-drop image upload
  b) WhatsApp photo message → Twilio media webhook → POST /api/prescriptions/scan
     (patient sends a photo directly to the WhatsApp nudge number)

File handling:
  • Accept: JPEG, PNG, WEBP, HEIC (converted to JPEG server-side)
  • Max size: 10 MB
  • SHA-256 hash computed on arrival for deduplication
  • Image stored encrypted at rest; never returned in API responses as raw bytes
  • PrescriptionScan record created with status = pending
```

#### 5b — VLM / OCR Extraction

```
Primary path — GPT-4o Vision:
  POST to OpenAI Chat Completions API with image_url content type
  System prompt instructs model to return structured JSON:
  {
    "medication_name":  "Metformin HCl",
    "generic_name":     "Metformin",
    "dosage":           "500mg",
    "frequency":        "Twice daily after meals",
    "refill_days":      30,
    "prescriber":       "Dr Tan Wei Ming",
    "clinic":           "Toa Payoh Polyclinic",
    "dispense_date":    "2026-03-20",
    "expiry_date":      "2027-03-20",
    "instructions":     "Take with food. Avoid alcohol.",
    "warnings":         ["May cause stomach upset"],
    "language_detected": "en",
    "confidence":        0.94
  }

Fallback path — Tesseract OCR (when OPENAI_API_KEY not set):
  • Run Tesseract with language packs: eng + chi_sim + msa + tam
  • Apply regex patterns to extract dosage, frequency, dates from raw text
  • Confidence set to 0.5; always requires human review

All extracted fields saved as ExtractedMedicationField rows.
Scan status updated to: review
```

#### 5c — Human Review & Confirmation

```
Dashboard (Prescription Scans page) shows:
  • Thumbnail of uploaded image
  • Side-by-side: extracted field | confidence badge | editable input
  • Fields with confidence < 0.75 highlighted in amber for attention
  • "Confirm & Save" button → triggers auto-populate
  • "Reject" button → marks scan as rejected, notifies uploader

Auto-populate on confirmation:
  1. Look up or create Medication record (by name + generic_name)
  2. Create or update PatientMedication (dosage, refill_interval_days)
  3. Create DispensingRecord (dispense_date, days_supply = refill_days, source = "ocr")
  4. Scan status → confirmed
  5. NudgeCampaign refill timer reset based on new dispense date
```

#### 5d — WhatsApp Self-Service Flow (patient-initiated)

```
Patient sends photo to WhatsApp number:
  1. Twilio webhook fires → /api/webhook/whatsapp (existing)
  2. Media URL detected → routed to prescription scan handler
  3. System replies: "Thanks! I've scanned your prescription.
     Your care team will review it shortly."
  4. After coordinator confirms:
     System sends: "Your medication record for [name] has been updated.
     Your next reminder is scheduled for [date]."
```

---

### 6 — Personalised Voice Nudge Pipeline

This feature lets a patient nominate a loved one (e.g. spouse, child) whose voice is cloned once, then used to deliver every subsequent nudge as a WhatsApp voice note — making the reminder feel personal and familiar.

#### 6a — Voice Donor Onboarding (one-time setup)

```
Patient (or family member) visits onboarding link or WhatsApp flow:

  Step 1 — Consent gate
    • Patient: "I consent to having a family member's voice used for my reminders"
    • Donor:   "I consent to my voice being cloned for [patient name]'s medication reminders"
    • Both consents timestamped and stored in VoiceProfile.consent_obtained_at

  Step 2 — Audio sample collection
    • Donor records ~60–90 seconds of natural speech
      (prompted script provided in chosen language)
    • Upload via:
        a) Web form (frontend /voice-enroll page), OR
        b) WhatsApp voice message → Twilio webhook → POST /api/voice/sample

  Step 3 — Voice cloning
    • Backend uploads audio to ElevenLabs Instant Voice Cloning API
    • ElevenLabs returns a voice_id
    • Stored in VoiceProfile.elevenlabs_voice_id
    • Original sample retained encrypted for audit; not used again

  Step 4 — Test playback
    • System generates a short test phrase in the donor's cloned voice
    • Sent to patient via WhatsApp for approval before going live
```

#### 6b — Voice Nudge Delivery (per nudge campaign)

```
When NudgeCampaign is triggered:

  Check: does patient have an active VoiceProfile?
    YES →  Voice nudge path:
      1. LLM (or template) generates message text as usual
      2. POST to ElevenLabs TTS API:
           voice_id   = VoiceProfile.elevenlabs_voice_id
           text       = nudge message text
           model      = eleven_multilingual_v2
           language   = patient.language_preference
      3. Receive audio bytes → save as .ogg (Opus, WhatsApp-compatible)
      4. Cache file keyed by (patient_id, medication_id, attempt, lang)
      5. Send via Twilio WhatsApp media message (MMS with audio attachment)
      6. Also send the text version as a caption for accessibility

    NO  →  Text nudge path (existing flow, unchanged)

  On ElevenLabs failure:
    → Log error, fall back to text nudge automatically
    → Alert care team if voice delivery fails on 3 consecutive campaigns
```

#### 6c — Attempt Tone Ladder (voice)

| Attempt | Prompt framing for LLM | Example (English) |
|---|---|---|
| 1 | Warm, casual reminder from loved one | *"Hi Dad, it's Sarah. Just a quick reminder to pick up your metformin today — love you!"* |
| 2 | Gentle concern, personal | *"Dad, it's Sarah again. I noticed you haven't picked up your medicine yet. Please do — I worry about you."* |
| 3 | Caring urgency | *"Dad, please collect your medication today. The clinic nurse will call you if I can't reach you. I love you and want you to be well."* |

---

## API Surface (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/api/patients` | List / create patients |
| GET, PUT | `/api/patients/{id}` | Get / update a patient |
| GET, POST | `/api/medications` | List / create medications |
| POST, GET | `/api/dispensing` | Bulk ingest / list dispensing records |
| GET | `/api/campaigns` | List campaigns (filter: status, date, patient) |
| GET, PATCH | `/api/campaigns/{id}` | Get / manually update a campaign |
| GET, PATCH | `/api/escalations` | List open cases / assign & resolve |
| GET | `/api/analytics/summary` | KPI summary |
| GET | `/api/analytics/adherence-trend` | Time-series adherence data |
| GET | `/api/analytics/language-breakdown` | Breakdown by language |
| POST | `/api/webhook/whatsapp` | Twilio inbound message webhook |
| POST | `/api/admin/trigger-scan` | Manually trigger refill gap scan |
| GET, POST | `/api/voice/profiles` | List / create voice profiles for a patient |
| GET, DELETE | `/api/voice/profiles/{id}` | Get / revoke a voice profile |
| POST | `/api/voice/sample` | Upload audio sample (web or WhatsApp relay) |
| POST | `/api/voice/enroll/{patient_id}` | Trigger full enrolment pipeline (clone + test) |
| GET | `/api/voice/profiles/{id}/test` | Re-generate and send test playback message |
| POST | `/api/prescriptions/scan` | Upload prescription image (web or WhatsApp relay) |
| GET | `/api/prescriptions/scans` | List all scans (filter: patient, status) |
| GET | `/api/prescriptions/scans/{id}` | Get scan details + extracted fields |
| PATCH | `/api/prescriptions/scans/{id}/review` | Submit corrected fields + confirm or reject |
| GET | `/api/prescriptions/scans/{id}/image` | Serve image securely (auth-gated, no public URL) |

---

## Dashboard Pages

| Page | What it shows |
|---|---|
| **Overview** | KPI cards: adherence rate, active campaigns, open escalations, messages sent today |
| **Patients** | Searchable patient table, risk level badge, last refill date |
| **Campaigns** | All nudge campaigns with status filter; view message content |
| **Escalations** | Prioritised case queue; assign to care coordinator; add notes |
| **Analytics** | Adherence trend chart, breakdown by condition / language / age group |
| **Voice Profiles** | Per-patient voice enrolment status; upload portal; consent audit; playback test; revoke |
| **Prescription Scans** | Upload portal; side-by-side image + extracted fields; confidence indicators; review & confirm; audit trail |

---

## Development Phases

### Phase 1 — Core Backend (Foundation)
- [ ] `config.py`, `database.py`, `models.py`
- [ ] CRUD for patients, medications, dispensing records
- [ ] Refill gap detection logic
- [ ] Fallback nudge templates (4 languages)

### Phase 2 — Messaging Pipeline
- [ ] LLM nudge generator (OpenAI + fallback)
- [ ] Twilio WhatsApp send + inbound webhook
- [ ] Response classifier
- [ ] Escalation engine

### Phase 3 — Scheduler + Seed Data
- [ ] APScheduler daily scan job
- [ ] Seed script with realistic SG patient data

### Phase 4 — Frontend Dashboard
- [ ] React + Vite scaffold with TailwindCSS
- [ ] Overview, Patients, Campaigns, Escalations, Analytics pages

### Phase 5 — Polish
- [ ] JWT auth for care team login
- [ ] Docker Compose (backend + frontend)
- [ ] Environment config, validation, error handling

### Phase 6 — Prescription / Label OCR
- [ ] `PrescriptionScan` and `ExtractedMedicationField` data models
- [ ] Image upload API + secure storage (`/api/prescriptions/*`)
- [ ] GPT-4o Vision extraction service (`services/prescription_ocr.py`)
- [ ] Tesseract OCR fallback with regex post-processing
- [ ] WhatsApp photo message handling (extend Twilio webhook)
- [ ] Review & confirm flow + auto-populate to medications/dispensing
- [ ] Frontend: Prescription Scans page — upload, review, edit fields, confirm
- [ ] Patient-facing WhatsApp self-service confirmation messages

### Phase 7 — Personalised Voice Nudges
- [ ] `VoiceProfile` and `VoiceSample` data models
- [ ] Voice enrolment API routes (`/api/voice/*`)
- [ ] ElevenLabs voice cloning integration (`services/voice_clone.py`)
- [ ] ElevenLabs TTS generation + `.ogg` caching (`services/voice_tts.py`)
- [ ] Twilio audio message delivery (extend `services/whatsapp.py`)
- [ ] Inbound WhatsApp voice sample relay (Twilio webhook extension)
- [ ] Consent capture and audit trail storage
- [ ] Frontend: Voice Profiles page — enrol, test playback, revoke
- [ ] Graceful fallback to text if voice unavailable

---

## Key Design Decisions

**Privacy:** NRIC is stored as SHA-256 hash only. No PII in logs.

**Graceful degradation:** System works fully without OpenAI key (templates) and without Twilio key (simulation mode — messages logged to DB, not sent).

**Configurable thresholds:** `WARNING_DAYS`, `ESCALATION_DAYS`, `MAX_NUDGE_ATTEMPTS` all env-var controlled — no code changes needed per clinic.

**Idempotent gap detection:** The daily scan won't create duplicate campaigns if one already exists for a patient+medication gap.

**Voice consent is mandatory and dual:** Both the patient *and* the voice donor must give explicit, timestamped consent before any cloning occurs. Consent can be revoked at any time, which deactivates the profile and deletes the ElevenLabs voice clone via their API.

**Voice samples are biometric data:** Raw audio samples are stored encrypted, access-controlled, and never used for any purpose other than the one-time cloning call. They are retained solely for regulatory audit and are deleted upon consent revocation.

**Voice delivery is always opt-in:** Patients without an active VoiceProfile automatically receive text nudges — no degradation of service.

**Audio caching:** Generated `.ogg` files are cached by `(patient_id, medication_id, attempt_number, language)` to avoid redundant ElevenLabs API calls for identical messages. Cache is invalidated on voice profile update or revocation.

**ElevenLabs model:** `eleven_multilingual_v2` is used to support all four Singapore languages (English, Mandarin, Malay, Tamil) from a single cloned voice.

**Prescription images are sensitive health data:** Images are stored encrypted, never served via public URLs, and only accessible through auth-gated API endpoints. They are deleted upon patient request or after a configurable retention period (default 1 year).

**VLM extraction is advisory, not authoritative:** All OCR/VLM results require human confirmation before any medication or dispensing record is created or modified. The system can never autonomously modify a patient's prescription data without a care coordinator sign-off.

**Multilingual label support:** GPT-4o Vision handles mixed-language labels (e.g., English instructions + Chinese characters) natively. Tesseract fallback uses separate language packs (eng, chi_sim, msa, tam) run in parallel.

**Deduplication:** Image SHA-256 hashes prevent the same prescription photo from creating duplicate scan records.

---

## Folder Structure (Target)

```
medi-nudge-system/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── database.py           # SQLAlchemy engine + session
│   │   ├── models.py             # ORM models
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── patients.py
│   │   │   ├── medications.py
│   │   │   ├── dispensing.py
│   │   │   ├── campaigns.py
│   │   │   ├── escalations.py
│   │   │   ├── analytics.py
│   │   │   ├── prescriptions.py
│   │   │   └── webhook.py
│   │   └── services/
│   │       ├── refill_scanner.py   # Gap detection logic
│   │       ├── nudge_generator.py  # LLM + template nudge builder
│   │       ├── whatsapp.py         # Twilio send wrapper (text + audio)
│   │       ├── response_triage.py  # Classify inbound replies
│   │       ├── escalation.py       # Escalation engine
│   │       ├── voice_clone.py      # ElevenLabs voice cloning API client
│   │       ├── voice_tts.py        # ElevenLabs TTS + .ogg caching
│   │       └── prescription_ocr.py # GPT-4o Vision + Tesseract extraction
│   ├── scheduler.py              # APScheduler jobs
│   ├── seed.py                   # Demo data seeder
│   ├── requirements.txt
│   ├── .env.example
│   ├── audio_cache/              # Cached .ogg voice nudge files (gitignored)
│   └── prescription_uploads/     # Encrypted prescription images (gitignored)
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Overview.tsx
│   │   │   ├── Patients.tsx
│   │   │   ├── Campaigns.tsx
│   │   │   ├── Escalations.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── PrescriptionScans.tsx  # Upload, review, field editing, confirm
│   │   │   └── VoiceProfiles.tsx      # Voice enrolment, consent, playback test
│   │   ├── components/
│   │   └── api/                  # Axios API client
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── DESIGN.md
```
