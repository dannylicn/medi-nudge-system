# medication-adherence-tracking Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Medication catalog

The system maintains a global medication catalog with brand names, generic names, and default refill intervals. The system SHALL implement this as described in the scenarios below.

#### Scenario: Medication created

Given a coordinator creates a medication with name `Glucophage`, generic name `Metformin`, category `antidiabetic`, and `default_refill_days: 30`
When the record is saved
Then a `Medication` row is created with all fields persisted

#### Scenario: Duplicate prevention

Given a medication named `Metformin` with generic name `Metformin` already exists
When a coordinator attempts to create another entry with the same generic name
Then the system returns `409 Conflict`

---

### Requirement: Patient prescription assignment

Each `PatientMedication` record links a patient to a medication with patient-specific dosage and refill interval. The system SHALL implement this as described in the scenarios below.

#### Scenario: Prescription created

Given patient `P-001` and medication `M-007` (Atorvastatin)
When a coordinator creates a `PatientMedication` with `dosage: "20mg"` and `refill_interval_days: 30`
Then the junction record is saved and `is_active = True`

#### Scenario: Patient-specific refill interval overrides default

Given `Medication.default_refill_days = 30`
When a `PatientMedication` is created with `refill_interval_days: 90` (bulk supply)
Then `refill_interval_days: 90` is used for all refill calculations for that patient-medication pair

#### Scenario: Deactivating a prescription

Given a patient is discontinued from a medication
When a coordinator sets `PatientMedication.is_active = False`
Then the medication is excluded from future refill gap detection runs

---

### Requirement: Dispensing record ingestion

Dispensing records represent actual medication collection events and are the primary input for refill gap detection. The system SHALL implement this as described in the scenarios below.

#### Scenario: Single record created manually

Given patient `P-001` collected `Metformin 500mg` on `2026-03-01` with `days_supply: 30`
When a coordinator or the system creates a `DispensingRecord`
Then the record is saved with `source: manual`

#### Scenario: Bulk CSV import

Given a CSV file containing dispensing records from a pharmacy export
When the coordinator uploads it via `POST /api/dispensing-records/import`
Then all valid rows are imported as `DispensingRecord` entries with `source: pharmacy`
And any malformed rows are reported in the response without blocking valid rows

#### Scenario: Duplicate dispensing record ignored

Given a `DispensingRecord` already exists for patient `P-001`, medication `M-007`, dispensed on `2026-03-01`
When a second import includes the same record
Then the duplicate is skipped and the existing record is unchanged

---

### Requirement: Refill due date calculation

The refill due date is computed as `dispensed_at + days_supply` using the most recent `DispensingRecord` for a patient-medication pair. The system SHALL implement this as described in the scenarios below.

#### Scenario: Due date calculated

Given the most recent dispensing for patient `P-001` / medication `M-007` was on `2026-03-01` with `days_supply: 30`
When the refill gap detector runs on `2026-04-05`
Then `due_date = 2026-03-31` and `days_overdue = 5`

#### Scenario: No dispensing record — patient skipped

Given a `PatientMedication` exists for patient `P-001` / medication `M-007`
And no `DispensingRecord` exists for this pair
When the refill gap detector runs
Then no `NudgeCampaign` is created and no error is raised

---

### Requirement: Daily scheduler triggers nudge creation

The refill gap detection job runs daily and creates a `NudgeCampaign` when `days_overdue >= WARNING_DAYS`. The system SHALL implement this as described in the scenarios below.

#### Scenario: Gap detected — campaign created

Given `WARNING_DAYS = 3` and patient `P-001` / medication `M-007` has `days_overdue = 5`
And no open `NudgeCampaign` exists for this patient-medication pair
When the scheduler runs
Then a new `NudgeCampaign` is created with `status: pending` and `days_overdue: 5`

#### Scenario: Existing open campaign — no duplicate

Given an open `NudgeCampaign` already exists for patient `P-001` / medication `M-007`
When the scheduler runs and `days_overdue` has increased
Then no additional campaign is created
And the existing campaign's `days_overdue` is updated

#### Scenario: Patient within refill window — no action

Given `days_overdue = 1` (below `WARNING_DAYS = 3`)
When the scheduler runs
Then no `NudgeCampaign` is created for this patient-medication pair

---

### Requirement: Auto-escalation threshold

When `days_overdue >= ESCALATION_DAYS`, the system creates an `EscalationCase` regardless of nudge state. The system SHALL implement this as described in the scenarios below.

#### Scenario: Auto-escalation triggered

Given `ESCALATION_DAYS = 14` and patient `P-001` / medication `M-007` has `days_overdue = 14`
When the scheduler runs
Then an `EscalationCase` is created with `reason: repeated_non_adherence` and `priority: high`
Even if no prior `NudgeCampaign` response has been received

### Requirement: DoseLog table records every dose event

The system SHALL maintain a `dose_logs` table that records every dose event (taken, missed, skipped) for audit, analytics, and patient history display. Each record links to a patient, medication, and includes a timestamp, status, and source.

#### Scenario: Patient reports taking medication via TAKEN reply

Given a patient sends "TAKEN" to the bot
When `_handle_taken()` processes the reply
Then a `DoseLog` record is created for each active medication with `status = "taken"`, `source = "patient_reply"`, and `logged_at` set to the current time
And `PatientMedication.last_taken_at` and `consecutive_missed_doses` are updated as before

#### Scenario: Agent confirms adherence for a nudge campaign

Given the agentic handler resolves a nudge campaign as confirmed
When `_tool_confirm_adherence()` runs
Then a `DoseLog` record is created for the campaign's medication with `status = "taken"`, `source = "campaign_confirmed"`

#### Scenario: Missed dose detected by daily reminder service

Given a patient's reminder window passes without a TAKEN reply within the 4-hour grace period
When the next reminder cycle detects the miss
Then a `DoseLog` record is created with `status = "missed"`, `source = "system_detected"`

#### Scenario: Caregiver confirms on behalf of patient

Given a caregiver confirms medication intake for a patient
When the confirmation is processed
Then a `DoseLog` record is created with `status = "taken"`, `source = "caregiver"`

---

### Requirement: Per-patient dose history API

The system SHALL expose an API endpoint to retrieve a patient's dose history with filtering by date range and medication.

#### Scenario: Retrieve dose history for a patient

Given a care coordinator requests `GET /api/patients/{id}/dose-history?days=30`
When the endpoint is called with a valid JWT
Then the response contains a list of `DoseLog` records for that patient within the last 30 days, ordered by `logged_at` descending
And each record includes: `id`, `medication_name`, `status`, `source`, `logged_at`

#### Scenario: Filter dose history by medication

Given a care coordinator requests `GET /api/patients/{id}/dose-history?medication_id=7`
When the endpoint is called
Then only `DoseLog` records for medication 7 are returned

---

### Requirement: Aggregate dose adherence analytics API

The system SHALL expose an API endpoint for system-wide dose adherence analytics, broken down by medication and time period.

#### Scenario: Weekly dose adherence rate across all patients

Given a care coordinator requests `GET /api/analytics/dose-adherence?days=90`
When the endpoint is called
Then the response contains weekly buckets with `total_doses`, `taken_count`, `missed_count`, and `adherence_rate` (taken / total * 100)

#### Scenario: Per-medication adherence breakdown

Given a care coordinator requests `GET /api/analytics/dose-adherence?group_by=medication`
When the endpoint is called
Then the response contains one entry per medication with `medication_name`, `total_doses`, `taken_count`, `missed_count`, and `adherence_rate`

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

