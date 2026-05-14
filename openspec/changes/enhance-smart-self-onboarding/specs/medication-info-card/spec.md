## ADDED Requirements

### Requirement: Medication info card sent after medication confirmation

After any medication is confirmed during onboarding (via OCR fast-path, coordinator-confirmed OCR, or manual entry), the system SHALL send the patient a short medication information card in their preferred language.

The card MUST include:
1. What condition the medication is commonly prescribed for (one sentence)
2. Exactly 2–3 common side effects to watch for (non-alarming, common only)
3. The instruction: "Reply SIDE EFFECT if you feel unwell — your care team will respond."

The card MUST NOT include: dosage instructions, drug interactions, contraindications, or any personalised clinical advice.

#### Scenario: Info card generated via LLM and sent

Given patient `P-001` has confirmed `Metformin 500mg` during onboarding
And `OPENAI_API_KEY` is set and reachable
When the medication is activated
Then `medication_info_service.generate_info_card("Metformin", "en")` is called
And the LLM returns a card within the safety constraints (no dosage/interaction language)
And the card is sent to the patient via Telegram approximately 60 seconds after the confirmation ack
And `PatientMedication.med_info_card_sent_at` is set to the send timestamp

#### Scenario: Info card content safety filter — fallback used

Given the LLM response contains the word "dosage" or "interaction" or "contraindicated" or "stop taking"
When the content safety filter runs
Then the LLM-generated text is discarded
And the fallback template is used instead
And the event is logged as `med_info_card_safety_fallback`

#### Scenario: LLM unavailable — template fallback used

Given `OPENAI_API_KEY` is not set or the LLM call times out
When `generate_info_card()` is called
Then the system uses a pre-written template:
  "ℹ️ About {medication_name}: This medication helps manage your chronic condition. Common things to watch for include nausea, dizziness, or stomach upset — these often improve after a few days. Reply SIDE EFFECT if you feel unwell — your care team will respond."
And the template is rendered in the patient's language from a static translation map

#### Scenario: Info card sent in patient's preferred language

Given patient `P-002` with `language_preference = "zh"` confirms `Amlodipine`
When the info card is generated
Then the LLM generates the card in Simplified Chinese
And the SIDE EFFECT keyword instruction uses the Chinese equivalent

#### Scenario: Info card not resent on re-activation

Given `PatientMedication` for patient `P-001` / `Metformin` has `med_info_card_sent_at` already set
When the medication is re-confirmed or re-activated
Then no new info card is sent
And `med_info_card_sent_at` is not updated
