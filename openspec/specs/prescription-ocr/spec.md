# prescription-ocr Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Image ingestion via web upload and WhatsApp photo

> **Modification:** The storage backend for prescription images is now explicitly environment-dependent. In containerised/production environments where `AWS_S3_BUCKET_NAME` is configured, images MUST be stored in S3. Local filesystem storage is permitted only when `AWS_S3_BUCKET_NAME` is not set (local development).

The existing requirement scenarios are unchanged. The following scenarios are added:

#### Scenario: Web upload stored to S3 in production

Given a care coordinator uploads a JPEG prescription image in a production environment where `AWS_S3_BUCKET_NAME` is set
When the image is accepted and deduplicated
Then the image bytes are uploaded to `s3://<bucket>/prescriptions/<patient_id>/<hash16>_<ts>.jpg` via `boto3`
And `PrescriptionScan.image_path` stores the S3 object key (e.g. `prescriptions/42/abc123_1713000000.jpg`)
And no file is written to the local container filesystem

#### Scenario: Image stored locally when S3 not configured

Given a developer is running the system locally without `AWS_S3_BUCKET_NAME`
When a prescription image is uploaded
Then the image is written to the local path under `MEDIA_STORAGE_PATH/prescriptions/<patient_id>/`
And `PrescriptionScan.image_path` stores the absolute local path
And no boto3 call is attempted

### Requirement: Image never returned as public URL or raw bytes

> **Modification:** `image_url` in the API response MUST be a pre-signed S3 URL when S3 storage is in use. The 15-minute TTL requirement is unchanged. In local development mode (no S3), the image may be served via a signed local endpoint.

#### Scenario: Image URL in API response is a pre-signed S3 URL (production)

Given `AWS_S3_BUCKET_NAME` is configured and a coordinator requests `GET /api/prescriptions/{id}`
When the response is serialised
Then `image_url` is a pre-signed `s3.generate_presigned_url` URL with `ExpiresIn=900` (15 minutes)
And the URL requires no additional authentication header to retrieve (the signature is embedded)
And the bucket is not publicly accessible

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

