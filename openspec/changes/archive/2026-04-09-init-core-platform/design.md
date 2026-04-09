# Design: init-core-platform

## Overview

This document captures the architectural decisions and cross-cutting patterns that apply across all v1 capabilities of Medi-Nudge. Every subsequent capability spec should be read in light of these decisions.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          MEDI-NUDGE SYSTEM                               │
│                                                                          │
│  ┌──────────────┐    ┌───────────────┐    ┌───────────────────────────┐  │
│  │  Data Ingest │    │  Core Engine  │    │    Care Team Dashboard    │  │
│  │  (CSV/NEHR)  │───▶│  (FastAPI)    │───▶│    (React + Vite)         │  │
│  └──────────────┘    └──────┬────────┘    └───────────────────────────┘  │
│                             │                                             │
│         ┌───────────────────┼───────────────────┐                        │
│         ▼                   ▼                   ▼                        │
│  ┌────────────┐      ┌────────────┐      ┌─────────────┐                 │
│  │  Scheduler │      │  LLM Nudge │      │  Escalation │                 │
│  │(APScheduler)      │  Generator │      │   Manager   │                 │
│  └────────────┘      └─────┬──────┘      └─────────────┘                 │
│                            │                                             │
│                   ┌────────▼────────┐                                    │
│                   │  Text Nudge     │                                    │
│                   │  (WhatsApp)     │                                    │
│                   └────────┬────────┘                                    │
│                            │                                             │
│                     ┌──────▼──────┐                                      │
│                     │ Twilio API  │                                      │
│                     └─────────────┘                                      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │               Prescription / Label OCR Pipeline                  │   │
│  │  Photo upload ──▶ GPT-4o Vision ──▶ Human review ──▶ DB update   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

### 1. Service Layer Pattern

**Decision:** Route handlers are thin — all business logic lives in `app/services/`. Routes validate input, call a service, and return a response.

**Rationale:** Keeps routes testable in isolation; services can be called by both the HTTP layer and the cron scheduler without duplication.

### 2. State Machines for Core Entities

**Decision:** `NudgeCampaign`, `EscalationCase`, `PrescriptionScan`, and `OutboundMessage` all follow explicit status state machines. Transitions are enforced by service-layer helpers, not arbitrary column updates.

```
NudgeCampaign:   pending → sent → responded | escalated | resolved | failed
EscalationCase:  open → in_progress → resolved
PrescriptionScan: pending → review → confirmed | rejected
OutboundMessage: sent → delivered → read | failed
```

**Rationale:** Prevents corrupt states; makes audit trails clear; simplifies coordinator dashboard filtering.

### 3. LLM with Template Fallback

**Decision:** Every LLM invocation (nudge generation, Q&A) has a non-LLM code path. When `OPENAI_API_KEY` is unset, the system uses a curated multilingual template library.

**Rationale:** System must be testable and partially deployable without API credentials. Reduces cost for low-complexity messages.

### 4. Privacy Model

**Decision:**
- NRIC is SHA-256 hashed before storage. Plaintext NRIC never touches the database, logs, or API responses.
- IP addresses in audit fields are SHA-256 hashed before storage.
- Prescription images and voice samples are encrypted at rest and never served via public URLs — only via auth-gated, time-limited signed URLs.

**Rationale:** PDPA compliance; minimises data breach impact.

### 5. Twilio Webhook Signature Validation

**Decision:** Every inbound POST to `/api/webhook/whatsapp` must validate the `X-Twilio-Signature` HMAC-SHA1 header before processing. Requests with invalid signatures return `403`.

**Rationale:** OWASP broken access control / SSRF — prevents spoofed inbound messages from being injected into the system.

### 6. Database Strategy

**Decision:** SQLite for development (`medi_nudge.db`); PostgreSQL 15+ for production. Connection is controlled entirely by the `DATABASE_URL` environment variable. ORM is SQLAlchemy 2.0 with Alembic migrations.

**Rationale:** Zero-config local dev; production-grade switch requires only env var change.

### 7. Soft Deletes

**Decision:** `Patient`, `PatientMedication`, and `VoiceProfile` use `is_active = False` for deletion rather than `DELETE`.

**Rationale:** Preserves audit trail; allows re-activation; prevents orphaned FK references in campaign and escalation history.

### 8. Scheduler

**Decision:** APScheduler (in-process) for v1; designed to swap to Celery + Redis for production scale.

**Rationale:** No additional infrastructure for development. Refill gap detection runs as a daily cron job; reminder preference windows are respected per-patient.

---

## Cross-Capability Data Flow

### Refill Nudge Flow (Happy Path)

```
[Scheduler — daily]
  → RefillGapDetector scans PatientMedication × DispensingRecord
  → Creates NudgeCampaign (status: pending)
  → NudgeGenerator produces multilingual message (LLM or template)
  → WhatsAppService sends via Twilio → OutboundMessage (status: sent)
  → Twilio status callback → OutboundMessage updated (delivered/read/failed)
  → Patient replies → Twilio inbound webhook
  → ResponseClassifier categorises reply
  → NudgeCampaign status updated (responded/escalated)
  → EscalationCase created if needed
```

### OCR Flow

```
[Patient or coordinator uploads image]
  → Image hashed + stored encrypted
  → PrescriptionScan created (status: pending)
  → VLM extraction → ExtractedMedicationField records created with confidence scores
  → Low-confidence fields (< 0.75) → status: review → coordinator notified
  → Coordinator reviews + confirms → status: confirmed
  → Medication/PatientMedication/DispensingRecord auto-populated
```

---

## Capability Dependency Map

```
patient-management
  ↑ required by: all others

medication-adherence-tracking
  ↑ required by: nudge-campaigns, prescription-ocr, care-coordinator-dashboard

whatsapp-channel
  ↑ required by: nudge-campaigns, patient-onboarding

nudge-campaigns
  ↑ required by: escalation-management, care-coordinator-dashboard

escalation-management
  ↑ required by: care-coordinator-dashboard

patient-onboarding
  ↑ depends on: patient-management, whatsapp-channel, prescription-ocr

prescription-ocr
  ↑ required by: care-coordinator-dashboard, patient-onboarding

care-coordinator-dashboard
  ↑ depends on: all others (read-only + action surface)
```

---

## Security Checklist (OWASP Top 10 Alignment)

| Risk | Mitigation |
|---|---|
| Broken Access Control | JWT auth on all dashboard endpoints; care team role required; webhook signature validation |
| Cryptographic Failures | NRIC + IPs SHA-256 hashed; images + audio encrypted at rest; JWT secrets from env var |
| Injection (SQL) | SQLAlchemy ORM parameterised queries only; no raw SQL with user input |
| Injection (XSS) | React escapes output by default; no dangerouslySetInnerHTML |
| Insecure Design | State machines prevent invalid transitions; side effects always escalate |
| Security Misconfiguration | Secrets from env vars only; no credentials in code; private S3 ACL for media |
| Identification & Auth Failures | JWT with short expiry; no patient-facing auth (WhatsApp phone number is identity) |
| Data Integrity | Image SHA-256 hash for dedup + tamper detection; Alembic migrations versioned |
| SSRF | Outbound HTTP only to whitelisted domains (Twilio, OpenAI, ElevenLabs); no user-controlled URLs fetched |
