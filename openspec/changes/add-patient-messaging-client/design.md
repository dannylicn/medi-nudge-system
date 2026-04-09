# Design: add-patient-messaging-client

## Overview

Adds a patient-facing web chat as a second messaging channel alongside WhatsApp. The chat uses the existing message pipeline — `OutboundMessage`, response classification, and escalation triggers — so care coordinators see a unified view regardless of channel.

---

## Architecture

```
                         ┌──────────────────────┐
                         │  Patient Web Chat     │
                         │  (React SPA page)     │
                         └─────────┬────────────┘
                                   │ REST + SSE / polling
                                   ▼
┌──────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  WhatsApp        │     │   FastAPI Backend     │     │ Care Coordinator│
│  (Twilio)        │────▶│                       │◀────│  Dashboard      │
└──────────────────┘     │  messaging_service.py │     └─────────────────┘
                         │  nudge_campaign_svc   │
                         │  response_classifier  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  OutboundMessage      │
                         │  + channel column     │
                         │  (whatsapp | web)     │
                         └──────────────────────┘
```

---

## Key Decisions

### 1. Channel Abstraction

**Decision:** Add a `channel` column (`VARCHAR(20)`, default `"whatsapp"`) to `OutboundMessage`. All existing records default to `"whatsapp"`. The web chat creates messages with `channel = "web"`.

**Rationale:** Minimal schema change; no new tables needed. The nudge campaign service already writes `OutboundMessage` — it just needs to tag the channel.

### 2. Authentication — Magic Link

**Decision:** Patients authenticate via a magic link sent to their WhatsApp. The link contains a signed JWT with `sub: patient_id`, `purpose: chat`, and a 24-hour expiry. No password or OTP.

**Rationale:**
- WhatsApp is already the verified identity channel (phone number = identity per existing spec).
- No new auth infrastructure required — reuse the existing JWT module with a different `purpose` claim.
- 24-hour expiry limits exposure; patient can request a new link anytime.

### 3. Message Delivery — Polling

**Decision:** The web chat polls `GET /api/messaging/{token}/messages?after={last_id}` every 5 seconds. No WebSocket for v1.

**Rationale:** Simpler to implement and deploy. Message latency of ≤ 5s is acceptable for a health nudge chat (not a real-time conversation app). WebSocket can be added later without API changes.

### 4. Shared Pipeline

**Decision:** Patient replies via web chat go through the same `ResponseClassifier` and campaign state machine as WhatsApp replies. The only difference is the ingest path: WhatsApp → Twilio webhook, Web → REST POST.

**Rationale:** Prevents divergent logic; escalation triggers, side-effect detection, and coordinator alerts work identically regardless of channel.

### 5. Frontend Routing

**Decision:** The patient chat lives at `/chat/{token}` in the existing Vite app, outside the `RequireAuth` guard (it uses its own token-based auth). It is a standalone page with no sidebar/nav — mobile-first responsive design.

**Rationale:** Reuses existing frontend infrastructure. No separate app or deployment needed.

---

## Security

| Risk | Mitigation |
|---|---|
| Token leakage | JWT signed with `JWT_SECRET_KEY`; 24h expiry; `purpose: chat` claim prevents use as coordinator token |
| Replay / sharing | Token is single-patient scoped; coordinator dashboard shows channel so misuse is visible |
| CSRF on POST | Token is in URL path, not cookie — no CSRF vector |
| Message content exposure | Only messages for the authenticated patient are returned; no cross-patient queries possible |
