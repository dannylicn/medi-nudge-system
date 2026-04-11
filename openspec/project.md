# Project Context

## Purpose

**Medi-Nudge** is a personalised, automated medication adherence system targeting chronic disease patients in Singapore. It addresses the ~50% non-adherence rate among patients with diabetes, hypertension, and hyperlipidemia — a key gap in MOH's Healthier SG strategy.

The system uses refill dispensing data and patient behaviour signals to send timely, context-aware nudges via **Telegram** (free Bot API, zero per-message cost), with escalation to care coordinators when needed. Beyond nudges, the channel supports two-way interactions: vitals collection, symptom check-ins, side effect reporting, appointment reminders, refill coordination, lab result notifications, caregiver loops, and conversational Q&A.

**Primary users:**
- Patients with chronic conditions (diabetes, hypertension, hyperlipidemia)
- Care coordinators / nurses at polyclinics
- Caregivers/family members (secondary channel)

---

## Tech Stack

### Backend
| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Framework | FastAPI | Async, OpenAPI docs via Swagger |
| ORM | SQLAlchemy 2.0 (declarative) | |
| Migrations | Alembic | |
| Scheduler | APScheduler (in-process) | Swap to Celery + Redis for prod |
| LLM | OpenAI GPT-4o | Multilingual nudge generation; template fallback when no API key |
| VLM / OCR | GPT-4o Vision (primary), Tesseract (fallback) | Prescription / medicine label extraction |
| Voice TTS | ElevenLabs API | Voice cloning from ~60–90s donor sample; multilingual |
| Messaging | Telegram Bot API | Free; text + photo + inline keyboards; via httpx |
| Auth | JWT (care team login) | Minimal viable for v1 |

### Database
| Environment | Engine |
|---|---|
| Development | SQLite (`medi_nudge.db`) |
| Production | PostgreSQL 15+ |

Connection is driven entirely by the `DATABASE_URL` environment variable — no code changes required to switch.

### Frontend
| Layer | Technology |
|---|---|
| Framework | React + Vite |
| Styling | TailwindCSS |
| Charts | Recharts |
| Auth | JWT stored in memory (not localStorage) |

### Storage
- Development: local filesystem for audio cache and prescription images
- Production: S3 / Azure Blob with private ACL; images served via auth-gated signed URLs only

---

## Project Conventions

### Code Style

- **Python**: Follow PEP 8. Use `snake_case` for variables, functions, and module names. Use `PascalCase` for classes. Keep line length ≤ 100 characters.
- **FastAPI routes**: Group by domain in separate router files under `app/routers/`. Each router has its own `prefix` and `tags`.
- **Pydantic schemas**: Separate `schemas/` directory. Request schemas suffixed `...Request`, response schemas suffixed `...Response` or `...Out`.
- **SQLAlchemy models**: Live in `app/models/`. One file per domain entity or logically grouped entities. Use `relationship()` with `lazy="select"` unless explicitly overridden.
- **Frontend (React)**: `PascalCase` for components and filenames. `camelCase` for hooks, utilities, and variables. Functional components only.

### Architecture Patterns

- **Service layer pattern**: Route handlers are thin — all business logic lives in `app/services/`. Routes only validate input, call a service function, and return the response.
- **Repository pattern (optional for prod)**: Database queries are encapsulated; direct SQLAlchemy session usage is acceptable in v1 services.
- **Event-driven for messaging**: The scheduler triggers `nudge_service.py` which calls `telegram_service.py`. Inbound webhook events are dispatched through a central `webhook_router.py` → `response_classifier.py` → appropriate handler.
- **State machines for core entities**: `NudgeCampaign`, `EscalationCase`, `PrescriptionScan`, and `OutboundMessage` all follow explicit status state machines. Never update status by arbitrary string assignment — use defined transition helpers.
- **LLM with template fallback**: Every LLM call has a non-LLM fallback path. The system must be partially functional with no OpenAI API key.
- **Soft deletes**: Use `is_active = False` rather than `DELETE` for `Patient`, `PatientMedication`, and `VoiceProfile` records.

### Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| API endpoints | `kebab-case` | `/api/nudge-campaigns/{id}/send` |
| Database tables | `snake_case` (plural) | `nudge_campaigns`, `dispensing_records` |
| Environment variables | `SCREAMING_SNAKE_CASE` | `OPENAI_API_KEY`, `DATABASE_URL` |
| Audio cache files | `{patient_id}_{medication_id}_{attempt}.ogg` | `42_7_1.ogg` |

### Environment Variables

```
DATABASE_URL          # SQLite for dev; PostgreSQL URL for prod
OPENAI_API_KEY        # Optional; system degrades gracefully to templates
ELEVENLABS_API_KEY    # Required for voice nudge feature
TELEGRAM_BOT_TOKEN    # Telegram bot token from @BotFather
TELEGRAM_WEBHOOK_SECRET  # Secret token for webhook validation
JWT_SECRET_KEY        # For care team auth
WARNING_DAYS          # Default 3 — days overdue before first nudge
ESCALATION_DAYS       # Default 14 — days overdue before auto-escalation
MAX_NUDGE_ATTEMPTS    # Default 3
```

### Testing Strategy

- Unit tests for service-layer logic (nudge generation, response classification, OCR extraction parsing).
- Integration tests for API routes using FastAPI `TestClient` with an in-memory SQLite database.
- Mock all external APIs (Telegram, OpenAI, ElevenLabs) in tests — never call real APIs in CI.
- Test state machine transitions explicitly — each valid and invalid transition.

### Git Workflow

- `main` — production-ready code only
- `develop` — integration branch
- Feature branches: `feature/<short-description>`
- Bug fixes: `fix/<short-description>`
- Commit messages: imperative mood, present tense — e.g. `Add OCR confirmation endpoint` not `Added OCR confirmation endpoint`

---

## Domain Context

### Chronic Conditions in Scope (v1)
- **Diabetes** — key medications: Metformin, Gliclazide, Insulin
- **Hypertension** — key medications: Amlodipine, Lisinopril, Losartan, Bisoprolol
- **Hyperlipidemia** — key medications: Atorvastatin, Rosuvastatin

### Refill Gap Logic
- `due_date = last DispensingRecord.dispensed_at + days_supply`
- `days_overdue = today − due_date`
- Nudge triggers at `days_overdue >= WARNING_DAYS` (default: 3)
- Auto-escalation triggers at `days_overdue >= ESCALATION_DAYS` (default: 14)

### Nudge Attempt Tone Ladder
| Attempt | Tone |
|---|---|
| 1 | Friendly reminder |
| 2 | Gentle concern, mention health risk |
| 3 | Urgency + "Your nurse will be in touch" |

### Inbound Response Classification
Patient replies are auto-classified:
- `"collected"` / `"yes"` / `"ok"` / `"done"` → `confirmed` → campaign resolved
- `"side effect"` / `"pain"` / `"rash"` / `"unwell"` → `side_effect` → **URGENT escalation**
- `"?"` / question keywords → `question` → normal escalation for coordinator
- No reply after 48h → schedule next attempt or escalate

### Languages Supported
`en` (English), `zh` (Mandarin Chinese), `ms` (Malay), `ta` (Tamil)
All patient-facing messages must be generated in the patient's `language_preference`.

### Caregiver Loop
With explicit patient consent, a caregiver (`Caregiver` entity linked to `Patient`) can receive adherence alerts and confirm medication on behalf of the patient. Caregiver confirmations are logged with `confirmed_via = "caregiver"`.

### OCR Confidence Threshold
Fields extracted by VLM with `confidence < 0.75` must be flagged for human review. The `PrescriptionScan` status must not advance from `review` to `confirmed` until a care coordinator has verified all low-confidence fields.

---

## Important Constraints

### Regulatory / Privacy (Singapore PDPA)
- **NRIC is never stored in plaintext** — SHA-256 hash only, in `Patient.nric_hash`
- **IP addresses are SHA-256 hashed** before storage in audit fields
- **Prescription images** are encrypted at rest and served only via auth-gated, time-limited signed URLs — never as public URLs
- **Voice samples** are encrypted at rest; used only for the one-time ElevenLabs cloning API call; must be deleted when consent is revoked (`VoiceProfile.is_active = False`)
- **Dual consent required** for voice cloning: both the patient and the voice donor must provide explicit, timestamped consent before a `VoiceProfile` is created
- All consent capture must include a timestamp and the name of the consenting party

### Clinical Safety
- The system must never provide definitive medical advice — Q&A answers must include a "consult your doctor" disclaimer and escalate clinical questions
- Side effect reports must **always** create an `EscalationCase` — they must never be silently dropped
- Post-discharge patients (first 7 days) are treated as high-risk; their check-in failures escalate at a lower threshold

### Technical
- The system must degrade gracefully when `OPENAI_API_KEY` is unset — fall back to template-based nudge messages
- Telegram webhook endpoint must validate the `X-Telegram-Bot-Api-Secret-Token` header on every inbound request
- Audio files cached as `.ogg` and keyed by internal IDs only — never by patient name or NRIC
- Maximum prescription image upload size: 10 MB; accepted formats: JPEG, PNG, WEBP, HEIC (converted to JPEG server-side)

---

## External Dependencies

| Service | Purpose | Fallback |
|---|---|---|
| **Telegram Bot API** | Send/receive Telegram messages and photos | None — core channel |
| **OpenAI GPT-4o** | LLM nudge generation + Vision OCR for prescriptions | Template fallback for nudges; Tesseract for OCR |
| **ElevenLabs API** | Voice cloning + TTS for loved-one voice nudges | Feature disabled; text nudge only |
| **Tesseract OCR** | Fallback OCR for structured typed labels | Only used when GPT-4o Vision unavailable |
| **NEHR / Pharmacy dispensing feed** | Source of `DispensingRecord` data | Manual entry or OCR upload |
| **HealthHub (MOH)** | Potential future integration for lab results and appointments | Out of scope v1 |
