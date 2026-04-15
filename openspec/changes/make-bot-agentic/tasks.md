# Tasks: make-bot-agentic

## Core agent infrastructure

- [x] Create `backend/app/services/agent_service.py` — agent loop with tool-calling, max 3 iterations, fallback to rule-based path when no LLM key
- [x] Define tool registry: `classify_intent`, `verify_medication`, `send_reply`, `escalate`, `confirm_adherence`, `record_medication`, `advance_onboarding`
- [x] Implement `_build_context(patient, db)` — compile patient + active campaign + last 5 messages; strip NRIC hash and raw phone_number
- [x] Implement `_run_llm(context, tools, system_prompt)` — call OpenAI/LLM with tool schemas, return tool call + args
- [x] Implement `_fallback_agent(patient, text, db)` — wraps existing `classify_response()` + webhook branch logic; no behaviour change

## Tool implementations

- [x] `tool_classify_intent(text, language)` → intent string + confidence (pure function, no DB)
- [x] `tool_verify_medication(query, db)` → calls `medication_service.fuzzy_search()`, returns ranked matches
- [x] `tool_send_reply(patient_id, text, db)` → calls `telegram_service.send_text()`, terminal
- [x] `tool_escalate(patient_id, reason, priority, db)` → calls `escalation_service.create_escalation()`, terminal
- [x] `tool_confirm_adherence(campaign_id, db)` → validates open campaign exists, calls `nudge_campaign_service._transition(campaign, "resolved")`, terminal
- [x] `tool_record_medication(patient_id, medication_id, db)` → validates `medication_id` in catalogue, creates `PatientMedication`, terminal
- [x] `tool_advance_onboarding(patient_id, new_state, data, db)` → validates `new_state in ONBOARDING_STATES`, delegates to `onboarding_service`, terminal

## Medication fuzzy search

- [x] Add `medication_service.fuzzy_search(query, db, limit=5)` — SQLite: case-insensitive token overlap scoring; Postgres: `pg_trgm similarity()`; returns `list[{medication, confidence}]`
- [x] Unit test: exact match returns confidence 1.0
- [x] Unit test: typo "metormin" returns Metformin as top result ≥ 0.85
- [x] Unit test: no match returns empty list
- [x] Unit test: `fuzzy_search` never modifies `medications` table

## Webhook integration

- [x] Update `webhook.py`: replace direct `classify_response()` + `nudge_campaign_service.handle_response()` calls with `agent_service.run(patient, message, db)`
- [x] Onboarding messages still route through `onboarding_service` via `tool_advance_onboarding` (not direct call)
- [x] Ensure photo messages are still routed directly to OCR pipeline (agent loop only for text)

## Medicine verification in onboarding

- [x] Update `onboarding_service._handle_medication_capture` option C (manual entry): replace direct `PatientMedication` creation with `agent_service.verify_and_confirm_medication(patient, name, db)`
- [x] Implement `verify_and_confirm_medication`: present match(es) to patient, set patient state to `medication_confirm_pending`, store pending `medication_id` in a transient field or session store
- [x] Add `medication_confirm_pending` to `ONBOARDING_STATES`
- [x] Handle patient confirmation reply → call `tool_record_medication`, advance to `confirm` state
- [x] Handle patient photo reply during verification → OCR pipeline
- [x] Handle no match → prompt photo, create `EscalationCase(reason="unknown_medication")`

## System prompt

- [x] Write `AGENT_SYSTEM_PROMPT` in `agent_service.py` — includes: patient context schema, available tools, language instruction (respond in patient's language), explicit prohibition on medical advice/dosage/interaction guidance

## Tests

- [x] Unit: `_build_context` strips NRIC hash and phone_number from LLM input
- [x] Unit: `tool_confirm_adherence` returns error when no open campaign exists
- [x] Unit: `tool_record_medication` rejects medication_id not in catalogue
- [x] Unit: `tool_advance_onboarding` rejects state not in `ONBOARDING_STATES`
- [x] Integration: Singlish "yeah lah took already" resolves open NudgeCampaign
- [x] Integration: "chest tight" triggers urgent side_effect escalation
- [x] Integration: refill date question answered without escalation
- [x] Integration: agent limit exceeded → escalation + acknowledgement sent
- [x] Integration: LLM key absent → rule-based fallback, same outcome as current behaviour
- [x] Integration: typo medicine name → verification gate → patient confirms → PatientMedication created
- [x] Integration: unknown medicine → photo prompt + unknown_medication escalation
