# Proposal: make-bot-agentic

## Summary

Upgrade the Telegram bot from a simple keyword-matching state machine into an LLM-driven conversational agent that can autonomously handle onboarding, nudge workflows, and medicine verification — all within the Telegram chat.

## Problem

The current bot has two hard limitations:

1. **Rigid keyword matching** — `response_classifier.py` uses regex patterns. Any message that doesn't match a known keyword falls through to "question → escalation". Patients who type naturally in Singlish, mixed languages, or freeform sentences cause spurious escalations that burden care coordinators.

2. **No medicine verification** — During onboarding (manual entry sub-flow) and nudge responses, the bot accepts any string as a medicine name. When a patient types "Metormin" (typo) or "blood pressure pill", it creates a `PatientMedication` record that can never match the catalogue — silently breaking the refill tracking pipeline.

## Proposed Solution

Introduce a lightweight **agent loop** powered by GPT-4o (with a rule-based fallback). The agent:

- Receives the full message + patient context + conversation history
- Selects from a set of **tool actions**: `classify_intent`, `verify_medication`, `send_reply`, `escalate`, `confirm_adherence`, `record_medication`, `advance_onboarding_state`
- Executes the action and observes the result before deciding the next step
- Falls back to direct keyword rules when `OPENAI_API_KEY` is not set

Medicine verification is deliberately read-only: the agent queries the `medications` catalogue for fuzzy matches, presents candidates to the patient for confirmation, and only records a `PatientMedication` when the patient confirms a catalogued entry or the coordinator has already approved it. It never adds new entries to the catalogue.

## Goals

- Conversational nudge responses in natural language (Singlish, mixed English/Chinese, etc.)
- Medicine name fuzzy match + patient-facing disambiguation during onboarding
- Unrecognised medicines flagged to coordinator (not silently stored)
- Adherence confirmations interpreted from natural language, not just "YES"/"SUDAH"
- Fewer spurious escalations for questions the bot can already answer (e.g., refill date, medication name, next appointment)

## Non-Goals

- No new medicines added to the catalogue (handled by coordinator through existing UI)
- No patient-facing medicine information (dosage guidance, interaction checking) — medical safety boundary
- No voice/audio for bot replies (separate feature)
- No multi-turn memory beyond the current conversation window (no vector store)

## Affected Capabilities

| Spec | Type |
|---|---|
| `nudge-campaigns` | MODIFIED — agentic response handling |
| `medication-adherence-tracking` | MODIFIED — medicine verification gate |

## Architecture Overview

See `design.md` for full reasoning.

## Sequencing

1. `nudge-campaigns` spec delta — agentic response handling and intent classification
2. `medication-adherence-tracking` spec delta — medicine verification gate in onboarding

Both can be implemented in parallel; they share only the agent core module.
