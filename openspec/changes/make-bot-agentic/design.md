# Design: make-bot-agentic

## Current Architecture

```
Telegram message
    → webhook.py
        → classify_response() [regex]
        → nudge_campaign_service.handle_response() [fixed branches]
          OR onboarding_service.handle_onboarding_reply() [state machine]
```

Every branch dispatches to a hard-coded handler. Anything unrecognised → "question" → escalation.

## Target Architecture

```
Telegram message
    → webhook.py
        → agent_service.run(patient, message, context)
            → [LLM loop]  ← system prompt + patient context + history
                → tool: classify_intent(text) → intent + confidence
                → tool: verify_medication(name) → catalogue matches
                → tool: send_reply(text) → Telegram API
                → tool: escalate(reason) → EscalationCase
                → tool: confirm_adherence(campaign_id) → NudgeCampaign.status=resolved
                → tool: record_medication(patient_id, medication_id) → PatientMedication
                → tool: advance_onboarding(patient_id, new_state, data) → Patient
            ← terminal action or max_iterations exceeded → fallback escalation
    [if OPENAI_API_KEY not set]
        → rule_agent_fallback(patient, message) [existing logic, unchanged]
```

## Agent Design

### Single-context window
The agent receives a compact context object on every turn. No vector store, no cross-session memory. Context includes:
- Patient record (name, language, conditions, onboarding_state, is_active)
- Active nudge campaign (if any): medication name, days_overdue, attempt_number
- Last 5 OutboundMessages (for continuity)
- Current onboarding state (if in onboarding)

### Tool-calling loop
- Max 3 iterations per turn to bound latency and cost
- Each iteration: LLM chooses one tool → execute → observe result → decide next
- Terminal conditions: `send_reply` called, `escalate` called, or iteration limit hit
- Iteration limit → safe fallback: escalate with `reason="agent_limit_exceeded"` + send acknowledgement

### Tool definitions

| Tool | Description | Guard |
|------|-------------|-------|
| `classify_intent` | Determine patient intent from free text | No DB side effects |
| `verify_medication` | Fuzzy-search medication catalogue by name | Read-only |
| `send_reply` | Send a Telegram message to the patient | Terminal |
| `escalate` | Create EscalationCase | Terminal |
| `confirm_adherence` | Mark open NudgeCampaign resolved | Only when campaign open |
| `record_medication` | Add PatientMedication for a confirmed catalogue entry | Only with catalogue match |
| `advance_onboarding` | Transition patient to next onboarding state | Only during onboarding |

### Fallback chain
1. LLM agent (when `OPENAI_API_KEY` or `LLM_BASE_URL` set)
2. Rule-based fallback (existing `classify_response()` logic — unchanged)

The rule-based fallback must remain fully functional so the system works in environments without an LLM API key.

## Medicine Verification Design

### Problem
The manual-entry sub-flow in onboarding (`medication_capture` state, option C) currently stores whatever string the patient types as a `PatientMedication`. If the name doesn't match the catalogue, the campaign scheduler can never find a refill date → silent failure.

### Solution: verification gate
1. Patient types a medicine name
2. Agent calls `verify_medication(name)` → fuzzy search on `medications.name` and `medications.generic_name` (SQLite: case-insensitive LIKE; Postgres: pg_trgm trigram index)
3. **Exact or high-confidence match (≥ 0.85):** present single candidate for confirmation  
   > "Did you mean **Metformin** (for Diabetes)? Reply YES to confirm or type the full name."
4. **Multiple candidates (2–4):** present numbered list for selection
5. **No match or low confidence:** inform patient, ask them to send a photo of the medicine label instead; create `EscalationCase(reason="unknown_medication")` so coordinator can add to catalogue if needed
6. **Patient confirms:** `record_medication` tool creates `PatientMedication`
7. **Patient sends photo:** route to existing OCR pipeline

The catalogue is **never modified** by this flow. New entries happen via the coordinator dashboard only.

### Fuzzy matching approach
- SQLite: `LOWER(name) LIKE '%<token>%'` for each word token in the input, scored by token overlap ratio
- Postgres (production): `similarity(name, input) > 0.3` using `pg_trgm`
- Wrapped in `medication_service.fuzzy_search(query, limit=5)` — pure read, no DB writes

## Cost and Latency

- Each agent turn = 1–3 LLM calls, ~500–1500 tokens per call
- GPT-4o: ~$0.005–0.015 per patient message
- Target p95 latency: < 5s end-to-end (Telegram timeout is 60s)
- Fallback triggers immediately if LLM errors, so patient always gets a response

## Security Considerations

- System prompt includes explicit prohibition on medical advice, dosage guidance, and drug interactions
- Tool guards prevent `record_medication` without a verified catalogue match
- `advance_onboarding` can only move to states defined in `ONBOARDING_STATES` — no arbitrary state injection
- All LLM output is passed through the tool executor, never executed as code

## What Is Not Changed

- `response_classifier.py` — kept as-is, used by the fallback path
- Onboarding state machine transitions — agent calls `advance_onboarding` which delegates to existing `onboarding_service` handlers
- NudgeCampaign state machine — agent calls `confirm_adherence` which uses existing `_transition()` helper
- Medication catalogue — read-only from agent; writes only via coordinator API
