## MODIFIED Requirements

### Requirement: High-confidence fast-path patient confirmation

The system SHALL provide a fast-path OCR confirmation flow that allows patients to self-confirm high-confidence extractions without waiting for coordinator review.

> **Modification:** When OCR extraction yields high confidence across all required fields, the scan bypasses coordinator blocking review and proceeds via a patient-led confirmation flow.

The system SHALL classify a scan as "high confidence" when all of `medication_name`, `dosage`, and `frequency` have `confidence >= 0.85` AND at least one of `dispense_date` or `expiry_date` is present with `confidence >= 0.75`.

For high-confidence scans, the system SHALL:
1. Set `PrescriptionScan.status = "patient_pending"` (new status)
2. Send a formatted field summary to the patient in Telegram for confirmation
3. On patient `CONFIRM`: transition to `patient_confirmed`, auto-populate medication records, and create a low-priority `EscalationCase(reason="ocr_patient_confirmed")` for coordinator awareness
4. On patient `EDIT`: transition to `review` and route through the existing coordinator queue

For low-confidence scans (any required field below 0.85), behaviour is unchanged: status → `review`, coordinator must confirm before medication records are created.

#### Scenario: High-confidence scan — patient confirms

Given a PrescriptionScan where medication_name confidence is 0.92, dosage confidence is 0.88, frequency confidence is 0.90, and dispense_date confidence is 0.80
When OCR processing completes
Then `PrescriptionScan.status` is set to `patient_pending`
And the bot sends a formatted field summary to the patient with CONFIRM and EDIT options
When the patient replies CONFIRM
Then `PrescriptionScan.status` transitions to `patient_confirmed`
And `Medication`, `PatientMedication`, and `DispensingRecord` records are auto-populated
And an `EscalationCase` with `reason="ocr_patient_confirmed"` and `priority="low"` is created
And no blocking coordinator action is required

#### Scenario: High-confidence scan — patient requests edit

Given a PrescriptionScan in `patient_pending` status
When the patient replies EDIT
Then `PrescriptionScan.status` transitions to `review`
And the scan is routed to the coordinator review queue as normal
And the patient receives: "I've sent this to your care team for review. We'll update your records shortly."

#### Scenario: Low-confidence scan — unchanged coordinator path

Given a PrescriptionScan where `dosage` has confidence 0.60
When OCR processing completes
Then `PrescriptionScan.status` is set to `review`
And the existing coordinator review flow is triggered unchanged
And no patient-facing confirmation message is sent

#### Scenario: Existing requirement superseded for high-confidence scans

> The prior requirement stating "Auto-population without any human check is not permitted in v1" is superseded for high-confidence scans by this modification. The patient's CONFIRM reply constitutes a human check. Coordinator review remains mandatory for low-confidence scans.
