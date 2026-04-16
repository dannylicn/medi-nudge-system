## ADDED Requirements

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
