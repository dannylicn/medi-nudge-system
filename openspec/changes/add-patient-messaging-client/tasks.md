# Tasks: add-patient-messaging-client

Ordered implementation checklist. Dependencies noted per task.

---

## Phase 1 — Backend: Schema & Auth

- [ ] **T-01** Add `channel` column (`VARCHAR(20)`, default `"whatsapp"`, not null) to `OutboundMessage` model; create Alembic migration; backfill existing rows with `"whatsapp"`
- [ ] **T-02** Add `create_patient_chat_token(patient_id)` to `app/core/security.py` — generates a JWT with `sub: patient_id`, `purpose: chat`, 24h expiry; add `verify_patient_chat_token(token)` that validates signature, expiry, and `purpose == "chat"`
- [ ] **T-03** Add `POST /api/messaging/request-link` endpoint (coordinator-authed): accepts `patient_id`, calls `create_patient_chat_token`, sends the link `{FRONTEND_URL}/chat/{token}` to the patient via WhatsApp using `whatsapp_service.send_text()`

## Phase 2 — Backend: Messaging API

*(Depends on Phase 1)*

- [ ] **T-04** Create `app/routers/messaging.py` with patient-token auth (no coordinator JWT): `GET /api/messaging/{token}/messages` — returns paginated `OutboundMessage` records for the patient (both inbound and outbound, both channels), sorted by `sent_at`; validates token via `verify_patient_chat_token`
- [ ] **T-05** Add `GET /api/messaging/{token}/messages?after={last_id}` polling support — returns only messages with `id > last_id` for efficient 5s polling
- [ ] **T-06** Add `POST /api/messaging/{token}/reply` — accepts `{ message: string }`, validates token, creates an inbound reply, routes through `ResponseClassifier` and campaign state machine (same as WhatsApp inbound path); tags messages with `channel: "web"`
- [ ] **T-07** Add `GET /api/messaging/{token}/patient` — returns patient display name and active medications (no NRIC, no internal IDs beyond what's needed for display)

## Phase 3 — Frontend: Patient Chat Page

*(Depends on Phase 2)*

- [ ] **T-08** Create `PatientChatPage.jsx` at route `/chat/:token` — standalone page (no Layout/sidebar), mobile-first, Clinical Serenity design system; renders chat bubbles using `MessagingBubble` component (patient = `secondary-container`, system = `surface-container-highest`)
- [ ] **T-09** Implement message polling: fetch `GET /api/messaging/{token}/messages?after={last_id}` every 5s; auto-scroll to latest message; show patient name and greeting header from `GET /api/messaging/{token}/patient`
- [ ] **T-10** Implement reply input: text input with send button; `POST /api/messaging/{token}/reply`; optimistic UI (show bubble immediately, mark failed on error); disable input if token expired (show "request new link" message)
- [ ] **T-11** Add `/chat/:token` route to `App.jsx` outside `RequireAuth` wrapper

## Phase 4 — Dashboard: Channel Visibility

*(Can run in parallel with Phase 3)*

- [ ] **T-12** Update `PatientDetailPage.jsx` nudge timeline to show channel badge (`WhatsApp` / `Web`) next to each message using `StatusChip` component
- [ ] **T-13** Add "Send Chat Link" button to `PatientDetailPage.jsx` header — calls `POST /api/messaging/request-link` with current patient ID; show success toast

## Phase 5 — Tests

- [ ] **T-14** Unit tests: `create_patient_chat_token` / `verify_patient_chat_token` — valid token, expired token, wrong purpose claim, tampered signature
- [ ] **T-15** Integration tests: `GET /api/messaging/{token}/messages` returns only the authenticated patient's messages; `POST /api/messaging/{token}/reply` triggers response classification and campaign state update; expired token returns `401`
- [ ] **T-16** Integration test: web reply triggers escalation (side_effect keyword via web chat creates escalation case identical to WhatsApp path)

---

## Dependencies Summary

```
Phase 1 (Schema + Auth) → Phase 2 (Messaging API) → Phase 3 (Chat UI)
Phase 1 → Phase 4 (Dashboard channel badge) — parallel with Phase 3
All phases → Phase 5 (Tests)
```

---

## Validation Criteria

Each phase is complete when:
- All route/service-level tests pass
- `openspec validate add-patient-messaging-client --strict` passes
- No OWASP issues introduced (see security section in `design.md`)
