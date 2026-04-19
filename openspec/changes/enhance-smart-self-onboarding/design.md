# Design: enhance-smart-self-onboarding

## 1. Fast-Path OCR Confirmation

### State Machine Change

A new intermediate `PrescriptionScan.status` value is introduced: `patient_confirmed`.

```
pending → review               (existing low-confidence path — coordinator blocks)
pending → patient_pending      (new high-confidence path)
         → patient_confirmed   (patient taps Confirm in Telegram)
         → review              (patient taps Edit → drops to coordinator queue)
```

### High-Confidence Gate

`_is_high_confidence(scan)` returns True when:
- All required fields (`medication_name`, `dosage`, `frequency`) have `confidence >= 0.85`
- At least one of `dispense_date` or `expiry_date` is present with `confidence >= 0.75`

When the gate passes, `ocr_service.py` calls `onboarding_service.send_ocr_confirmation_prompt(patient, scan, db)` instead of the existing coordinator queue path.

### Patient-Facing Confirmation Message

Formatted in the patient's language:
```
I've read your prescription label. Does this look correct?

💊 Medication: Metformin 500mg
📋 Dosage: 500mg
🔁 Frequency: Twice daily
📅 Dispense date: 1 Apr 2026

Reply CONFIRM to accept or EDIT to send to your care team for review.
```

### Coordinator Notification

On `patient_confirmed`, an `EscalationCase` is created:
- `reason = "ocr_patient_confirmed"` (new enum value)
- `priority = "low"`
- `send_ack = False` (no Telegram message to patient)

This surfaces in the care coordinator dashboard as an informational item, not an action required.

---

## 2. Reminder-Time Auto-Setup

### Frequency Parsing Map

Implemented in `ocr_service._parse_frequency_to_times(frequency_text)`:

| Extracted text (normalised to lower) | reminder_times |
|---|---|
| once daily / once a day / od | ["08:00"] |
| twice daily / two times / bd | ["08:00", "20:00"] |
| three times daily / tds / tid | ["08:00", "14:00", "20:00"] |
| four times daily / qid | ["08:00", "12:00", "16:00", "20:00"] |
| with meals / before meals | ["07:30", "12:30", "18:30"] |
| at night / nocte | ["21:00"] |
| anything else / None | [] (no times set, patient asked manually) |

### Patient Schedule Confirmation

After reminder_times are inferred, bot sends (example):
```
⏰ I've set up your reminders:
• 8:00 AM and 8:00 PM daily

Reply OK to keep this schedule or type your preferred times (e.g. "7am and 9pm").
```

If the patient types custom times, they are parsed with the LLM and stored; if parsing fails, the coordinator is asked.

---

## 3. LLM Medication Info Card

### Generation Prompt (system)

```
You are a medication information assistant for a Singapore clinic.
Generate a short, safe-to-share medication information message for a patient.
Rules:
- State in ONE sentence what condition this medication is commonly prescribed for.
- List exactly 2-3 common side effects to watch for (NOT rare or serious ones — common ones only).
- Do NOT comment on dosage, drug interactions, or this patient's specific situation.
- End EVERY message with: "Reply SIDE EFFECT if you feel unwell — your care team will respond."
- Write in {language}. Be warm but factual. Max 5 sentences total.
```

### Fallback Templates

If LLM is unavailable, a per-language template is used:
```
ℹ️ About {medication_name}:
This medication helps manage {condition_placeholder}. Common things to watch for include nausea, dizziness, or stomach upset. These often improve after a few days.

Reply SIDE EFFECT if you feel unwell — your care team will respond.
```

`condition_placeholder` is a generic phrase ("your chronic condition") when no condition is stored for the patient.

### Safety Constraints

- Temperature: 0.3 (low variation — consistent, factual output)
- max_tokens: 200 (prevents runaway text)
- If LLM output contains words: "dosage", "interaction", "contraindicated", "stop taking" → discard and use fallback template
- Timing: sent 60 seconds after medication confirmation (not immediately, to allow Telegram delivery of the confirmation ack to land first)

---

## 4. Side-Effect Check-In Campaign

### Trigger

Daily APScheduler job `run_side_effect_checkin_check(db)`:
- Queries `PatientMedication` where `is_active = True` and `created_at` is between 3–4 days ago
- For each, checks no `NudgeCampaign` of type `side_effect_checkin` exists for this patient-medication pair
- Creates a `NudgeCampaign(campaign_type="side_effect_checkin", status="pending")` and sends it

### Message (example, English)

```
Hi {name} 👋 You started {medication} a few days ago. How are you getting on?

Reply:
  ✅ OK — all good
  ⚠️ SIDE EFFECT — feeling unwell
```

### Response Handling

- `OK` → NudgeCampaign status → `resolved`; `DoseLog` entry with `status="no_issue"` and `source="checkin_ok"`
- `SIDE EFFECT` → existing `escalate(reason="side_effect", priority="urgent")` flow

### One-Time Only

`NudgeCampaign` model gets a `campaign_type` field. The scheduler only creates one `side_effect_checkin` per patient-medication pair (ever, not just per activation).
