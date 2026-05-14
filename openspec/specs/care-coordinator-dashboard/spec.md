# care-coordinator-dashboard Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: JWT authentication for all dashboard access

All dashboard routes and their backing API endpoints require a valid JWT issued to a care coordinator. The system SHALL implement this as described in the scenarios below.

#### Scenario: Unauthenticated access redirected to login

Given a user navigates to any dashboard route without a valid JWT
When the frontend auth guard checks the token
Then the user is redirected to `GET /login`

#### Scenario: JWT stored in memory only

Given a coordinator logs in successfully
When the JWT is issued
Then it is stored in React application memory (not `localStorage` or `sessionStorage`)
And it is lost on page refresh (requiring re-login or a refresh-token flow)

#### Scenario: Expired JWT rejected by API

Given a coordinator's JWT has expired
When the frontend makes an API call
Then the server returns `401 Unauthorized`
And the frontend redirects the user to the login page

---

### Requirement: Patient list view

The coordinator can view all active patients with key adherence indicators and enrol new patients. The system SHALL implement this as described in the scenarios below.

#### Scenario: Patient list loads with adherence summary

Given a coordinator navigates to the patient list page
When the page renders
Then each patient row shows: name, primary condition(s), risk level, last dispensing date, days overdue (if any), and escalation badge (if open case exists)

#### Scenario: Filter by risk level

Given the patient list is loaded
When the coordinator applies the filter `risk_level: high`
Then only high-risk patients are shown

#### Scenario: Search by name

Given the patient list is loaded
When the coordinator types a patient name in the search box
Then the list filters to matching patients in real time

#### Scenario: Enrol new patient from dashboard

Given a coordinator clicks "Enrol New Patient"
When they complete the enrolment form (name, phone, language, conditions)
Then a `Patient` record is created and the onboarding WhatsApp invite is sent (see REQ-PO-001)

---

### Requirement: Patient detail view

Clicking a patient opens a detailed view with their medication history, nudge timeline, and escalation history. The system SHALL implement this as described in the scenarios below.

#### Scenario: Medication list shown

Given a coordinator opens patient `P-001`'s detail page
When the page renders
Then all active `PatientMedication` records are listed with dosage, refill interval, and next due date

#### Scenario: Nudge timeline shown

Given patient `P-001` has 3 past `NudgeCampaign` records
When the coordinator views the nudge timeline
Then each campaign is shown with: medication, trigger date, attempt number, message preview, patient response, and final status

#### Scenario: Dispensing history shown

Given patient `P-001` has `DispensingRecord` entries
When the coordinator views dispensing history
Then records are listed in reverse chronological order with dispensed date, days supply, and source

---

### Requirement: Escalation queue view

A dedicated view surfaces all open and in-progress escalation cases sorted by priority. The system SHALL implement this as described in the scenarios below.

#### Scenario: Escalation queue sorted by priority

Given open escalation cases exist with priorities `urgent`, `high`, and `normal`
When the coordinator navigates to the escalation queue
Then `urgent` cases appear first, then `high`, then `normal`
And within the same priority, cases are sorted by `created_at` ascending (oldest first)

#### Scenario: Filter by status

Given a mix of `open` and `in_progress` cases
When the coordinator selects `status: open`
Then only open cases are shown

#### Scenario: Coordinator assigns and updates a case

Given a coordinator selects an `open` EscalationCase
When they set `assigned_to: "Nurse Lee"`, update status to `in_progress`, and add a note
Then the changes are saved via `PATCH /api/escalations/{id}`
And the case row updates in the list without a full page reload

#### Scenario: Coordinator resolves a case

Given a case in `in_progress` state
When the coordinator clicks "Resolve" and enters resolution notes
Then the case transitions to `resolved`
And it moves out of the active queue but remains accessible via the resolved filter

---

### Requirement: OCR review queue

A dedicated queue shows all `PrescriptionScan` records in `review` or `pending` state awaiting coordinator action. The system SHALL implement this as described in the scenarios below.

#### Scenario: OCR queue shows pending scans

Given three scans in `review` state exist
When a coordinator navigates to the OCR review page
Then all three scans are listed with patient name, upload date, and source (web/WhatsApp)

#### Scenario: Scan detail shows image alongside extracted fields

Given a coordinator selects a scan from the queue
When the scan detail view renders
Then the prescription image is displayed (via signed URL)
And each `ExtractedMedicationField` is shown with its extracted value, confidence score, and an editable correction field
And low-confidence fields (`< 0.75`) are visually highlighted

#### Scenario: Coordinator confirms scan

Given the coordinator has reviewed and corrected all fields
When they click "Confirm"
Then `PATCH /api/prescriptions/{id}/confirm` is called
And the scan transitions to `confirmed`
And medication records are auto-populated (see REQ-OCR-007)
And the scan is removed from the OCR queue

#### Scenario: Coordinator rejects scan

Given the scan image is too blurry to read
When the coordinator clicks "Reject"
Then `PATCH /api/prescriptions/{id}/reject` is called
And the patient receives a notification to re-submit

---

### Requirement: Adherence analytics view

A charts view gives coordinators aggregate insight into programme performance. The system SHALL implement this as described in the scenarios below.

#### Scenario: Adherence rate over time chart

Given nudge campaign data across the past 90 days
When the coordinator navigates to the analytics page
Then a Recharts line chart shows weekly adherence rate (% of campaigns resolved with `confirmed` response)

#### Scenario: Escalation volume chart

Given escalation case data
When the analytics page renders
Then a Recharts bar chart shows escalation count by week, broken down by priority level

#### Scenario: Data scoped to active patients only

Given some patients have been deactivated (`is_active: false`)
When analytics are calculated
Then deactivated patients are excluded from adherence rate and escalation volume metrics

---

### Requirement: No sensitive PII exposed in API responses

The coordinator dashboard MUST not surface NRIC hashes, raw image paths, or internal audit fields in standard API responses.

#### Scenario: Patient API response does not include nric_hash

Given a coordinator calls `GET /api/patients/{id}`
When the response is returned
Then `nric_hash` is absent from the response body

#### Scenario: Prescription scan API response uses signed URL not file path

Given a coordinator calls `GET /api/prescriptions/{id}`
When the response is returned
Then `image_url` is a signed URL (see REQ-OCR-002)
And `image_path` (the raw server-side file path) is absent from the response body

### Requirement: Dose history timeline on patient detail page

The patient detail page SHALL display a chronological timeline of dose events (taken, missed) for each active medication, allowing care coordinators to see adherence patterns at a glance.

#### Scenario: Patient detail shows dose history

Given a care coordinator views the patient detail page for patient 1
When the page loads
Then a "Dose History" section displays the last 30 days of dose events
And each event shows the medication name, status (taken/missed), and timestamp
And missed doses are visually highlighted

#### Scenario: Empty dose history

Given a patient has no dose log records
When the patient detail page loads
Then the dose history section displays "No dose records yet"

---

### Requirement: Aggregate dose adherence on analytics page

The analytics page SHALL display system-wide dose adherence charts including weekly adherence trend and per-medication breakdown.

#### Scenario: Weekly dose adherence chart

Given a care coordinator visits the analytics page
When the page loads
Then a line chart shows weekly dose adherence rate (%) over the selected time period
And the chart is labelled "Dose Adherence Rate"

#### Scenario: Per-medication adherence table

Given a care coordinator visits the analytics page
When the page loads
Then a table shows each medication's adherence rate, total doses, taken count, and missed count
And medications are sorted by adherence rate ascending (worst first) to highlight problem areas

