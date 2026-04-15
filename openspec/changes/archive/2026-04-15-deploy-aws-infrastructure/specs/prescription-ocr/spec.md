# prescription-ocr Specification Delta

## MODIFIED Requirements

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
