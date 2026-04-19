# Spec Delta: medication-adherence-tracking (make-bot-agentic)

## ADDED Requirements

### Requirement: Medicine verification gate before PatientMedication creation
When a patient types a medicine name during the onboarding manual-entry sub-flow, the system MUST fuzzy-search the `medications` catalogue before creating a `PatientMedication` record. A `PatientMedication` MUST only be created when the patient has confirmed a specific catalogued entry.

**Replaces:** current behaviour where any free-text string is stored verbatim as a medication name

#### Scenario: High-confidence single match presented for confirmation
Given a patient types "metormin" (typo) during medication capture
When `verify_medication("metormin")` is called
Then the system MUST return "Metformin" as the top candidate with confidence ≥ 0.85
And the bot MUST send: "Did you mean **Metformin** (Diabetes)? Reply YES to confirm or type the full name."
And no PatientMedication MUST be created yet

#### Scenario: Patient confirms candidate — record created
Given the bot has presented "Metformin" as a candidate
And the patient replies "yes"
When the agent calls `record_medication(patient_id, medication_id=<metformin_id>)`
Then a PatientMedication record MUST be created with the correct medication_id
And the medication_id MUST reference a row in the `medications` table

#### Scenario: Multiple candidates presented as numbered list
Given a patient types "blood pressure pill"
When `verify_medication("blood pressure pill")` returns 3 candidates (Amlodipine, Losartan, Bisoprolol)
Then the bot MUST send a numbered list of the candidates with category hints
And no PatientMedication MUST be created yet

#### Scenario: No catalogue match — escalation and photo prompt
Given a patient types "Warfexin 5mg" and no match is found above 0.3 confidence
When `verify_medication("Warfexin 5mg")` returns no results
Then the bot MUST ask the patient to send a photo of the medicine label
And an EscalationCase MUST be created with reason "unknown_medication"
And the coordinator MUST be notified to add the medicine to the catalogue if valid
And NO PatientMedication MUST be created

#### Scenario: Patient sends photo after no match — OCR pipeline activated
Given the bot has asked the patient to send a photo
And the patient sends a photo message
When the photo arrives at the webhook
Then the existing OCR pipeline MUST be invoked
And if OCR extracts a medicine with a catalogue match, `record_medication` MUST be called
And if OCR cannot match, the PrescriptionScan MUST be queued for coordinator review

### Requirement: Fuzzy medication search — read-only catalogue query
The system MUST expose a `medication_service.fuzzy_search(query, limit=5)` function that returns ranked catalogue matches. This function MUST be purely read-only and MUST NOT modify the `medications` table.

#### Scenario: Exact name match ranked first
Given "Metformin" exists in the catalogue
When `fuzzy_search("Metformin")` is called
Then the first result MUST be the Metformin entry with confidence 1.0

#### Scenario: Token overlap match for generic name
Given "Atorvastatin" exists as a generic_name in the catalogue
When `fuzzy_search("ator vastatin")` is called
Then the result MUST include the Atorvastatin entry

#### Scenario: Query with no match returns empty list
Given "zylomycin" does not exist in the catalogue
When `fuzzy_search("zylomycin")` is called
Then the result MUST be an empty list

#### Scenario: Catalogue never modified via fuzzy_search
Given any input query
When `fuzzy_search` is called
Then the `medications` table row count MUST be identical before and after the call
