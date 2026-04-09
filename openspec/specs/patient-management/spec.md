# patient-management Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: NRIC stored as SHA-256 hash only

The system MUST never store, log, or return a patient's NRIC in plaintext. The `Patient` record stores only the SHA-256 hex digest.

#### Scenario: Patient created with NRIC

Given a care coordinator submits a new patient with NRIC `S1234567A`
When the system persists the record
Then `Patient.nric_hash` contains the SHA-256 hex digest of `S1234567A`
And no column in the `patients` table contains the plaintext NRIC
And the NRIC does not appear in any application log

#### Scenario: NRIC lookup for duplicate detection

Given a patient with NRIC `S1234567A` already exists
When a coordinator attempts to create another patient with the same NRIC
Then the system returns a `409 Conflict` response
And no duplicate `Patient` row is created

---

### Requirement: Phone number stored in E.164 format

Patient phone numbers MUST be stored and validated in E.164 format (e.g. `+6591234567`).

#### Scenario: Valid Singapore mobile number

Given a coordinator supplies phone number `91234567`
When the system normalises the number
Then it is stored as `+6591234567`

#### Scenario: Invalid phone number rejected

Given a coordinator supplies phone number `abc123`
When the system validates the number
Then the request is rejected with a `422 Unprocessable Entity` error
And no patient record is created

---

### Requirement: Language preference limited to supported locales

Patients MUST have a language preference of `en`, `zh`, `ms`, or `ta`.

#### Scenario: Supported language accepted

Given a coordinator sets language to `zh`
When the patient record is created
Then `Patient.language_preference` is `zh`

#### Scenario: Unsupported language rejected

Given a coordinator sets language to `fr`
When the request is validated
Then the system returns `422 Unprocessable Entity`

---

### Requirement: Soft delete via is_active flag

Patients are never hard-deleted. Deactivation sets `is_active = False` and preserves all historical records. The system SHALL implement this as described in the scenarios below.

#### Scenario: Coordinator deactivates a patient

Given an active patient with existing nudge campaigns and dispensing records
When a coordinator calls `DELETE /api/patients/{id}` (or `PATCH` with `is_active: false`)
Then `Patient.is_active` is set to `False`
And the patient's nudge campaigns, dispensing records, and escalation cases remain in the database
And the patient no longer appears in the default active-patient list

#### Scenario: Deactivated patient excluded from scheduler

Given a patient with `is_active = False`
When the daily refill gap detection job runs
Then no new `NudgeCampaign` is created for that patient

---

### Requirement: Chronic conditions stored as a JSON array

A patient may have multiple chronic conditions. The `conditions` field is a JSON array of lowercase strings. The system SHALL implement this as described in the scenarios below.

#### Scenario: Multiple conditions recorded

Given a patient has diabetes and hypertension
When their record is created with `conditions: ["diabetes", "hypertension"]`
Then both conditions are persisted and returned in API responses

---

### Requirement: Risk level categorisation

Each patient has a `risk_level` of `low`, `normal`, or `high`. This field drives escalation thresholds and message tone. The system SHALL implement this as described in the scenarios below.

#### Scenario: Default risk level assigned

Given a new patient is created without an explicit risk level
When the record is saved
Then `risk_level` defaults to `normal`

#### Scenario: Risk level updated by coordinator

Given a coordinator updates a patient's risk level to `high`
When they call `PATCH /api/patients/{id}` with `risk_level: "high"`
Then the change is persisted
And the updated risk level is reflected in subsequent nudge and escalation logic

---

### Requirement: Patient list API supports filtering and pagination

The coordinator dashboard requires an efficient patient list endpoint. The system SHALL implement this as described in the scenarios below.

#### Scenario: Filter by active status

Given a mixture of active and inactive patients
When a coordinator calls `GET /api/patients?is_active=true`
Then only patients with `is_active = True` are returned

#### Scenario: Filter by risk level

Given patients with varying risk levels
When a coordinator calls `GET /api/patients?risk_level=high`
Then only high-risk patients are returned

#### Scenario: Pagination

Given 150 active patients
When a coordinator calls `GET /api/patients?page=2&page_size=50`
Then patients 51–100 are returned with total count metadata

