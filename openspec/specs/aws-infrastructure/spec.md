# aws-infrastructure Specification

## Purpose
TBD - created by archiving change deploy-aws-infrastructure. Update Purpose after archive.
## Requirements
### Requirement: Frontend served via CloudFront and private S3

The React/Vite SPA build artifact SHALL be deployed to a private S3 bucket served exclusively through a CloudFront distribution with an Origin Access Control (OAC) policy.

#### Scenario: SPA loads over HTTPS with custom domain

Given a user navigates to `https://app.<domain>`
When CloudFront resolves the request
Then the browser receives the React SPA from S3 via CloudFront with a valid ACM TLS certificate
And the S3 bucket itself returns `403 Forbidden` to any direct request not originating from CloudFront

#### Scenario: Deep-link route returns the SPA index

Given a user navigates directly to `https://app.<domain>/patients/123`
When CloudFront resolves the route (not a known S3 object key)
Then CloudFront returns `index.html` via a custom error response rule (403 → 200 `index.html`)
And the React client-side router handles the path

---

### Requirement: Backend API runs on ECS Fargate behind an ALB

The FastAPI application SHALL run as an ECS Fargate service in private subnets, accessible only through an Application Load Balancer in public subnets.

#### Scenario: HTTPS request reaches the API

Given an authenticated frontend client sends a request to `https://api.<domain>/api/patients`
When the request reaches the ALB
Then ALB terminates TLS using an ACM certificate and forwards the request to an ECS task on port 8000
And the response is returned within the ALB idle timeout

#### Scenario: HTTP is redirected to HTTPS

Given a client sends a request to `http://api.<domain>/api/patients`
When the ALB listener on port 80 receives the request
Then a `301 Redirect` to the HTTPS URL is returned
And no plaintext data is transmitted to the backend

#### Scenario: API service auto-scales on load

Given the ALB request count exceeds the scale-out threshold
When ECS Application Auto Scaling triggers
Then additional tasks are launched (up to `max_capacity`) in under 60 seconds
And no duplicate scheduled jobs occur because scheduler runs in a separate ECS service

---

### Requirement: Scheduler runs as a dedicated ECS Fargate service

The APScheduler background job process SHALL run as a separate ECS Fargate service (desired count fixed at 1) using the same container image as the API service but a different entry-point command.

#### Scenario: Scheduler service starts and registers jobs

Given the `scheduler-service` ECS task starts with `SCHEDULER_ENABLED=true`
When `app.worker` module is invoked
Then the APScheduler `BackgroundScheduler` starts and registers all 4 recurring jobs
And the service blocks indefinitely, keeping the process alive

#### Scenario: API service does not run the scheduler

Given the `api-service` ECS task starts with `SCHEDULER_ENABLED=false`
When `uvicorn app.main:app` is invoked
Then `start_scheduler()` is not called
And the API handles requests without spawning any background threads for scheduling

#### Scenario: Scheduler service crashes and restarts

Given the `scheduler-service` ECS task terminates unexpectedly
When ECS detects the task is unhealthy
Then ECS re-launches a replacement task within the configured `health_check_grace_period`
And jobs resume on the next scheduled interval

---

### Requirement: Database is RDS PostgreSQL in a private subnet

The application database SHALL be RDS PostgreSQL 16 deployed in private subnets with no public accessibility.

#### Scenario: Application connects to RDS via DATABASE_URL

Given `DATABASE_URL` is set to `postgresql+psycopg2://<user>:<password>@<rds-endpoint>:5432/medinudge`
When the FastAPI app starts and SQLAlchemy `create_engine()` is called
Then the database connection pool is established successfully
And all Alembic migrations at `HEAD` are applied before the first API task serves traffic

#### Scenario: RDS credentials are never stored in plaintext

Given AWS Secrets Manager holds the RDS master password under `/medi-nudge/<env>/db-password`
When the ECS task definition is rendered by Terraform
Then the `DATABASE_URL` env var is injected from Secrets Manager using the `secrets` block
And the raw password does not appear in the ECS task definition JSON or CloudWatch Logs

#### Scenario: RDS Multi-AZ failover (production only)

Given the production RDS instance is `Multi-AZ: true`
When the primary DB instance becomes unavailable
Then RDS promotes the standby within 60 seconds
And the application reconnects automatically via SQLAlchemy connection pool retry

---

### Requirement: Prescription images stored in private S3 with SSE-KMS

Prescription images SHALL be stored in a dedicated private S3 bucket with server-side encryption (SSE-KMS) and served only via pre-signed URLs with a 15-minute TTL.

#### Scenario: Image uploaded to S3 instead of local filesystem

Given a care coordinator uploads a prescription image via the web UI
When `ocr_service.store_prescription_image()` is called in a containerised environment (`AWS_S3_BUCKET_NAME` is set)
Then the image bytes are uploaded to `s3://<bucket>/prescriptions/<patient_id>/<hash>_<timestamp>.jpg`
And `PrescriptionScan.image_path` stores the S3 object key (not a local path)
And no local file is written

#### Scenario: Local filesystem fallback when S3 not configured

Given `AWS_S3_BUCKET_NAME` is not set (local development)
When `ocr_service.store_prescription_image()` is called
Then the image is written to the local `MEDIA_STORAGE_PATH` directory as before
And no boto3 calls are made

#### Scenario: Public S3 access is denied at bucket level

Given the `medi-nudge-media-<env>` bucket has `BlockPublicAcls`, `BlockPublicPolicy`, `IgnorePublicAcls`, and `RestrictPublicBuckets` all set to `true`
When an unauthenticated request is made directly to the S3 object URL
Then S3 returns `403 Access Denied`

---

### Requirement: All secrets injected from AWS Secrets Manager at runtime

No plaintext secrets SHALL be baked into the container image, Terraform state, or ECS task definition environment variables.

#### Scenario: Secrets are resolved at ECS task startup

Given Secrets Manager holds all required secrets under the `/medi-nudge/<env>/` prefix
When ECS launches an API task
Then the container environment contains resolved values for `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `ELEVENLABS_API_KEY`, and `DATABASE_URL`
And `docker inspect` on the running container does not show secret values in the environment (ECS redacts them in the console)

---

### Requirement: Observability via CloudWatch

All ECS tasks SHALL emit structured logs to CloudWatch Log Groups and expose CPU/memory metrics via Container Insights.

#### Scenario: API errors are visible in CloudWatch Logs

Given the `api-service` task encounters an unhandled exception
When FastAPI logs the error to stdout
Then the log line appears in `/ecs/medi-nudge-api/<env>` CloudWatch Log Group within 15 seconds
And the log stream is per-task using the ECS task ID

#### Scenario: Alarm fires on elevated 5xx error rate

Given the ALB `HTTPCode_Target_5XX_Count` metric exceeds the threshold for 5 consecutive minutes
When CloudWatch evaluates the alarm
Then the alarm transitions to `ALARM` state
And an SNS notification is delivered to the configured alert topic

