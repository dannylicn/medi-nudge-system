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

