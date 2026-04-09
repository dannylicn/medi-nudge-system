# Tasks: init-core-platform

Ordered implementation checklist for the v1 Medi-Nudge platform. Tasks are sequenced to respect capability dependencies (see `design.md`). Parallelisable groups are marked.

---

## Phase 1 — Backend Foundation

- [x] **T-01** Initialise FastAPI project structure: `app/`, `app/routers/`, `app/services/`, `app/models/`, `app/schemas/`, `app/core/`
- [x] **T-02** Configure SQLAlchemy 2.0 + Alembic; scaffold `DATABASE_URL` env var; verify SQLite dev and PostgreSQL prod paths
- [x] **T-03** Implement `Patient` model + Alembic migration; SHA-256 NRIC hashing helper; phone number E.164 validation
- [x] **T-04** Implement `patient-management` CRUD routes (`POST /api/patients`, `GET /api/patients/{id}`, `PATCH /api/patients/{id}`, soft-delete)
- [x] **T-05** Implement `Medication` + `PatientMedication` models + migrations
- [x] **T-06** Implement medication catalog routes and patient prescription assignment routes
- [x] **T-07** Implement `DispensingRecord` model + ingestion endpoint (`POST /api/dispensing-records`, CSV bulk import)
- [x] **T-08** Implement refill gap detection service (`refill_gap_service.py`): due date calculation, `days_overdue` logic
- [x] **T-09** Wire APScheduler daily cron to `refill_gap_service`; respect `WARNING_DAYS` and `ESCALATION_DAYS` env vars

## Phase 2 — WhatsApp Channel

*(Can start in parallel with Phase 1 after T-03)*

- [x] **T-10** Implement Twilio client wrapper (`whatsapp_service.py`): send text message, send audio message
- [x] **T-11** Implement `OutboundMessage` model + migration; delivery status tracking
- [x] **T-12** Implement Twilio inbound webhook endpoint (`POST /api/webhook/whatsapp`); validate `X-Twilio-Signature` HMAC-SHA1 before any processing
- [x] **T-13** Implement `ResponseClassifier` — keyword + pattern matching to `confirmed | question | side_effect | negative`
- [x] **T-14** Implement Twilio status-callback endpoint (`POST /api/webhook/whatsapp/status`) to update `OutboundMessage.status`

## Phase 3 — Nudge Campaigns

*(Depends on Phase 1 + Phase 2)*

- [x] **T-15** Implement `NudgeCampaign` model + migration; state machine transition helpers
- [x] **T-16** Implement `nudge_generator.py`: GPT-4o path + multilingual template fallback; tone ladder (attempt 1–3)
- [x] **T-17** Implement `nudge_campaign_service.py`: create campaign, generate message, send via `whatsapp_service`, update state
- [x] **T-18** Wire inbound webhook → `ResponseClassifier` → campaign state update
- [x] **T-19** Implement 48h no-reply detection (scheduler job): advance to next attempt or trigger escalation

## Phase 4 — Escalation Management

*(Depends on Phase 3)*

- [x] **T-20** Implement `EscalationCase` model + migration; state machine helpers
- [x] **T-21** Implement `escalation_service.py`: create case with correct priority from trigger reason; assign to coordinator
- [x] **T-22** Expose escalation routes: `GET /api/escalations`, `PATCH /api/escalations/{id}` (update status + notes)

## Phase 5 — Prescription OCR

*(Can run in parallel with Phase 3)*

- [x] **T-23** Implement `PrescriptionScan` + `ExtractedMedicationField` models + migrations
- [x] **T-24** Implement image ingestion: web upload endpoint + WhatsApp media download handler; SHA-256 dedup; encrypted storage
- [x] **T-25** Implement `ocr_service.py`: GPT-4o Vision primary path + Tesseract fallback; return structured JSON; store `ExtractedMedicationField` records with confidence scores
- [x] **T-26** Implement review workflow: flag fields with `confidence < 0.75`; `PATCH /api/prescriptions/{id}/confirm` coordinator endpoint; auto-populate medication records on confirmation
- [x] **T-27** Implement Twilio media webhook integration: patient sends WhatsApp photo → triggers OCR pipeline

## Phase 6 — Patient Onboarding

*(Depends on Phase 2 + Phase 5)*

- [x] **T-28** Implement onboarding state machine in `onboarding_service.py`: invite → consent → language → medication capture → confirm → preferences → welcome
- [x] **T-29** Implement clinic-enrolled path: coordinator creates patient → system sends WhatsApp invite
- [x] **T-30** Implement self-enrolled path: web landing page collects phone number → system sends invite
- [x] **T-31** Implement consent capture via WhatsApp reply; record consent timestamp and channel
- [x] **T-32** Implement medication capture sub-flows: (A) dispensing feed import, (B) OCR photo, (C) guided manual form
- [x] **T-33** Implement reminder preference capture (quiet hours window)
- [x] **T-34** Implement drop-off recovery: no-response retries (1–2 attempts); escalation case on continued non-response

## Phase 7 — Care Coordinator Dashboard (Frontend)

*(Depends on all backend phases)*

- [x] **T-35** Scaffold React + Vite + TailwindCSS project under `frontend/`
- [x] **T-36** Implement JWT login page + auth context; store token in memory (not localStorage)
- [x] **T-37** Implement patient list view: search, filter by risk level / adherence status, enrol new patient button
- [x] **T-38** Implement patient detail view: medication list, dispensing history, nudge campaign timeline
- [x] **T-39** Implement escalation queue view: list open/in-progress cases, filter by priority; action panel (assign, add notes, resolve)
- [x] **T-40** Implement OCR review queue: display prescription scan image alongside extracted fields; inline edit + confirm/reject
- [x] **T-41** Implement adherence analytics view: Recharts — adherence rate over time, escalation volume by week

## Phase 8 — Auth + Hardening

- [x] **T-42** Implement care coordinator user model + JWT auth endpoints (`POST /api/auth/login`, `POST /api/auth/refresh`)
- [x] **T-43** Apply auth middleware to all dashboard API routes; unauthenticated requests return 401
- [x] **T-44** Add request rate limiting to inbound webhook and public onboarding endpoints
- [x] **T-45** Audit all API responses — ensure no NRIC plaintext, no image paths, no internal IDs leak to frontend beyond intended scope

## Phase 9 — Tests

*(Can be written alongside implementation)*

- [x] **T-46** Unit tests: `refill_gap_service`, `ResponseClassifier`, `nudge_generator` template path, OCR confidence threshold logic
- [x] **T-47** Integration tests: nudge campaign full flow (create → send → inbound confirm → resolve) using `TestClient` + in-memory SQLite
- [x] **T-48** Integration tests: escalation triggers (side_effect reply, 3 failed attempts, ESCALATION_DAYS exceeded)
- [x] **T-49** Integration tests: prescription OCR flow (upload → extract → review → confirm → medication populated)
- [x] **T-50** Webhook security test: invalid Twilio signature returns 403; valid signature processes correctly

## Phase 10 — Frontend Design System: Clinical Serenity

*(Depends on Phase 7 scaffold — T-35. References `stitch-design/merlion_health/DESIGN.md` and all screens under `stitch-design/`.)*

- [x] **T-51** Extend `tailwind.config.js` with Clinical Serenity color tokens: `primary` (`#006565`), `primary-container` (`#008080`), `secondary` (`#206393`), `secondary-container` (`#90c9ff`), `surface` (`#f7fafc`), `surface-container-low` (`#f1f4f6`), `surface-container-lowest` (`#ffffff`), `surface-container-highest` (`#e0e3e5`), `on-surface` (`#181c1e`), `tertiary-container` (`#338236`), `error` (`#ba1a1a`), `error-container` (`#ffdad6`), `outline-variant` (`#bdc9c8`), `primary-fixed` (`#93f2f2`); add custom `borderRadius` key `pill` mapped to `9999px`
- [x] **T-52** Import Manrope and Inter from Google Fonts in `index.html`; define typography scale in `tailwind.config.js` (`fontFamily.display` → Manrope, `fontFamily.body` → Inter); update `index.css` CSS custom properties to replace current `--sans`/`--heading` vars with the Clinical Serenity equivalents and remove legacy accent/purple tokens
- [x] **T-53** Restyle `Layout.jsx`: set page background to `surface` (`#f7fafc`), sidebar/nav background to `surface-container-low` (`#f1f4f6`); remove all `border`/`divide` utilities; apply ambient shadow (`shadow-[0_4px_24px_rgba(24,28,30,0.04)]`) to floating panels; enforce the no-line rule — use background-color shifts only for section boundaries
- [x] **T-54** Restyle `LoginPage.jsx` to match `stitch-design/welcome_to_clinical_serenity/code.html`: full-viewport `surface` background, centred glassmorphism card (`bg-white/80 backdrop-blur-[20px]`), gradient primary CTA button (`bg-gradient-to-br from-primary to-primary-container rounded-full`), Manrope display headline, Inter body, no border on input fields (use `surface-container-highest` fill + `primary-fixed` focus ring)
- [x] **T-55** Restyle `PatientsPage.jsx` to match `stitch-design/care_coordinator_portal/code.html` and `stitch-design/patient_search_intake/code.html`: patient rows as `surface-container-lowest` cards on `surface-container-low` background; status chips using `tertiary-container`/`error-container` fills, no borders; search input with `surface-container-highest` fill; enrol button with gradient pill style
- [x] **T-56** Restyle `PatientDetailPage.jsx` to match `stitch-design/patient_preview_activation/code.html` and `stitch-design/clinical_medication_plan/code.html`: medication list as nested `surface-container-lowest` cards; data labels in `primary-fixed-dim`; section spacing via whitespace (tokens `6`/`8`) not dividers; Manrope for numeric adherence % values
- [x] **T-57** Restyle `EscalationsPage.jsx` to match `stitch-design/intervention_workflow/code.html` and `stitch-design/coordinator_alert_vitals/code.html`: escalation case rows as `surface-container-lowest` cards; priority chips using `error-container` (high) / `tertiary-container` (medium); action panel (assign, notes, resolve) with `surface-container-low` pane; restyle `AnalyticsPage.jsx` charts (Recharts) to use `primary` and `secondary` stroke colours, `surface-container-lowest` chart background
- [x] **T-58** Restyle `OcrReviewPage.jsx` to match `stitch-design/upload_prescription/code.html`, `stitch-design/extraction_complete/code.html`, and `stitch-design/review_information/code.html`: prescription image panel on `surface-container-low`; extracted fields with `surface-container-highest` input fills; confidence `< 0.75` fields highlighted with `error-container` background; confirm/reject actions using gradient pill (confirm) and outlined pill (reject) buttons
- [x] **T-59** Build shared component library under `frontend/src/components/ui/`: `PrimaryButton` (gradient pill), `OutlineButton`, `StatusChip` (accepts `variant: on-track | non-adherence | pending`), `ClinicalCard` (tonal layering wrapper), `FormInput` (Clinical Serenity states: default / focus `primary-fixed` ring / error `error-container`), `MessagingBubble` (patient `secondary-container` / clinician `surface-container-highest`); replace ad-hoc inline styles in all pages with these components

---

## Dependencies Summary

```
Phase 1 (Foundation) → Phase 2 (WhatsApp) → Phase 3 (Nudges) → Phase 4 (Escalation)
Phase 1 → Phase 5 (OCR)
Phase 2 + Phase 5 → Phase 6 (Onboarding)
All backend phases → Phase 7 (Dashboard)
All phases → Phase 8 (Hardening) → Phase 9 (Tests)
Phase 7 → Phase 10 (Clinical Serenity Design System)
```

Parallelisable after Phase 1: **Phase 2** and **Phase 5** can run concurrently.

---

## Validation Criteria

Each phase is complete when:
- All route/service-level unit tests pass
- Integration tests pass on in-memory SQLite
- `openspec validate init-core-platform --strict` passes
- No OWASP issues introduced (see security checklist in `design.md`)
