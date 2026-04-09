# prescription-ocr Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Image ingestion via web upload and WhatsApp photo

Prescription images can be submitted through two channels: a web upload form and a WhatsApp multimedia message. The system SHALL implement this as described in the scenarios below.

#### Scenario: Web upload

Given a care coordinator or patient navigates to the prescription scan upload page
When they upload a JPEG/PNG/WEBP/HEIC file (≤ 10 MB)
Then the image is accepted, converted to JPEG if needed, and stored encrypted at rest
And a `PrescriptionScan` record is created with `status: pending` and `source: web_upload`

#### Scenario: WhatsApp photo

Given a patient sends a photo via WhatsApp during or after onboarding
When the Twilio media webhook delivers the image URL
Then the system downloads the image, hashes it (SHA-256), stores it encrypted
And a `PrescriptionScan` record is created with `source: whatsapp_photo`

#### Scenario: File too large — rejected

Given a user uploads a file larger than 10 MB
When the system validates the upload
Then a `413 Payload Too Large` error is returned
And no `PrescriptionScan` record is created

#### Scenario: Duplicate image detected — not re-ingested

Given a `PrescriptionScan` with SHA-256 hash `abc123` already exists for patient `P-001`
When the same image is submitted again
Then no new record is created
And the existing scan ID is returned in the response

---

### Requirement: Image never returned as public URL or raw bytes

Prescription images MUST only be accessible via authenticated, time-limited signed URLs. They MUST never appear in unauthenticated API responses.

#### Scenario: Image URL in API response is a signed URL

Given a coordinator requests details for `PrescriptionScan` via `GET /api/prescriptions/{id}`
When the response is returned
Then `image_url` contains a time-limited signed URL valid for at most 15 minutes
And the URL requires a valid JWT to access

#### Scenario: Unauthenticated image access blocked

Given an attacker attempts to access the raw image path directly without a JWT
When the request reaches the image serving layer
Then a `401 Unauthorized` response is returned

---

### Requirement: VLM extraction via GPT-4o Vision (primary)

When `OPENAI_API_KEY` is set and the API is reachable, GPT-4o Vision is used to extract structured fields from the prescription image. The system SHALL implement this as described in the scenarios below.

#### Scenario: Successful extraction

Given `OPENAI_API_KEY` is set and the image is readable
When the OCR service submits the image to GPT-4o Vision
Then the model returns a JSON object with fields: `medication_name`, `generic_name`, `dosage`, `frequency`, `refill_days`, `prescriber`, `clinic`, `dispense_date`, `expiry_date`, `instructions`, `warnings`
And `ExtractedMedicationField` records are created for each field with `confidence` score
And `PrescriptionScan.ocr_engine = gpt4o_vision`

#### Scenario: Partial extraction — missing optional fields

Given the image is a pharmacy sticker that does not include prescriber name
When GPT-4o Vision processes it
Then optional fields (`prescriber`, `clinic`) are returned as `null` with `confidence: 0.0`
And required fields (`medication_name`, `dosage`) are extracted normally

---

### Requirement: Tesseract fallback when GPT-4o Vision is unavailable

When `OPENAI_API_KEY` is not set or the API is unavailable, Tesseract OCR is used. The system SHALL implement this as described in the scenarios below.

#### Scenario: Tesseract fallback activated

Given `OPENAI_API_KEY` is not set
When the OCR service is invoked
Then Tesseract is used to extract text
And `PrescriptionScan.ocr_engine = tesseract`
And the extracted text is parsed with heuristic field detection

#### Scenario: Tesseract extraction returns lower confidence

Given Tesseract processes a handwritten prescription
When confidence scores are computed heuristically
Then fields with low recognition quality have `confidence < 0.75`
And these fields are automatically flagged for human review

---

### Requirement: Confidence threshold gates human review

Fields with `confidence < 0.75` MUST be reviewed by a care coordinator before the scan is confirmed.

#### Scenario: Low-confidence field flagged

Given `ExtractedMedicationField` for `dosage` has `confidence: 0.60`
When the extraction completes
Then `PrescriptionScan.status` is set to `review`
And a task is visible in the coordinator OCR review queue
And the specific low-confidence field is highlighted for attention

#### Scenario: All fields above threshold — auto-advance to review skipped

Given all `ExtractedMedicationField` records have `confidence >= 0.75`
When the extraction completes
Then `PrescriptionScan.status` advances to `review` for coordinator confirmation (still requires sign-off)

> **Note:** Even if all fields are high-confidence, a coordinator MUST confirm before medication records are auto-populated. Auto-population without any human check is not permitted in v1.

---

### Requirement: Coordinator review and confirmation

A care coordinator reviews extracted fields, corrects any errors, and confirms or rejects the scan. The system SHALL implement this as described in the scenarios below.

#### Scenario: Coordinator confirms scan with corrections

Given a `PrescriptionScan` in `review` state with a low-confidence `dosage: "50mg"` (correct value: `500mg`)
When the coordinator updates `ExtractedMedicationField.corrected_value = "500mg"` and calls `PATCH /api/prescriptions/{id}/confirm`
Then `is_corrected = true` for the dosage field
And `PrescriptionScan.status` transitions to `confirmed`
And `confirmed_by` and `confirmed_at` are recorded

#### Scenario: Coordinator rejects scan

Given a `PrescriptionScan` in `review` state where the image is unreadable
When the coordinator calls `PATCH /api/prescriptions/{id}/reject`
Then `PrescriptionScan.status` transitions to `rejected`
And no medication records are created or modified
And the patient is notified to re-submit a clearer image

---

### Requirement: Auto-populate medication records on confirmation

When a scan is confirmed, the system creates or updates `Medication`, `PatientMedication`, and `DispensingRecord` records based on the confirmed extracted fields. The system SHALL implement this as described in the scenarios below.

#### Scenario: New medication auto-created

Given a confirmed scan for a medication not yet in the catalog
When the confirmation triggers auto-population
Then a new `Medication` record is created from `medication_name` and `generic_name`
And a `PatientMedication` is created with the confirmed `dosage` and `refill_interval_days`
And a `DispensingRecord` is created with `source: ocr` and the confirmed `dispense_date` and `days_supply`

#### Scenario: Existing medication matched

Given the extracted `generic_name: Metformin` matches an existing `Medication` record
When the confirmation triggers auto-population
Then the existing `Medication` record is reused (no duplicate created)
And only `PatientMedication` and `DispensingRecord` are created/updated

