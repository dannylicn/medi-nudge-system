# Tasks: deploy-aws-infrastructure

## Phase 1 — Backend Code Changes (no AWS account required)

- [x] **T1** Add `AWS_S3_BUCKET_NAME: str = ""`, `AWS_REGION: str = "ap-southeast-1"`, `ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"`, and `SCHEDULER_ENABLED: bool = True` to `backend/app/core/config.py`
- [x] **T2** Update `backend/app/main.py` to read `allow_origins` from `settings.ALLOWED_ORIGINS.split(",")` instead of the hardcoded list
- [x] **T3** Update `backend/app/core/scheduler.py` to guard `start_scheduler()` / `stop_scheduler()` behind `settings.SCHEDULER_ENABLED`
- [x] **T4** Update `backend/app/services/ocr_service.py` to use `boto3 s3.put_object` when `settings.AWS_S3_BUCKET_NAME` is set; fall back to local filesystem otherwise. Store the S3 object key (not a full URL) in `PrescriptionScan.image_path`
- [x] **T5** Update the prescription list/detail endpoints to generate pre-signed URLs (15-minute TTL) when `AWS_S3_BUCKET_NAME` is set, returning the signed URL as `image_url`
- [x] **T6** Add `boto3>=1.34` to `backend/requirements.txt`
- [x] **T7** Create `backend/app/worker.py` — thin entry point that sets `SCHEDULER_ENABLED=true` and calls `start_scheduler()`, then blocks (e.g. `signal.pause()`)
- [x] **T8** Write/update tests in `backend/tests/` to mock `boto3` for the S3 upload path and assert correct behaviour for both S3 and local fallback paths
  - Depends on: T4, T5

## Phase 2 — Docker

- [x] **T9** Create `backend/Dockerfile`: `python:3.12-slim` base, install `tesseract-ocr` + `libgl1` via apt, copy `requirements.txt`, `pip install`, copy app code, default `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- [x] **T10** Create `backend/.dockerignore` to exclude `venv/`, `__pycache__/`, `.env`, `*.db`, `media/`
- [ ] **T11** Verify the image builds locally and `tesseract --version` runs inside the container
  - Depends on: T9, T10

## Phase 3 — Terraform Infrastructure

- [x] **T12** Create `infra/` directory and Terraform root module (`main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`) targeting `ap-southeast-1`
- [x] **T13** Create `infra/modules/vpc/` — VPC, 2 public + 2 private subnets across 2 AZs, NAT Gateway in each public subnet, S3 Gateway VPC endpoint, VPC flow logs
- [x] **T14** Create `infra/modules/rds/` — RDS PostgreSQL 16 `db.t4g.small`, private subnet group, KMS encryption, Secrets Manager secret for password, security group (ingress from ECS SG only)
- [x] **T15** Create `infra/modules/s3/` — two buckets: `medi-nudge-media-{env}` (SSE-KMS, full public access block, lifecycle rule) and `medi-nudge-frontend-{env}` (private, OAC-only access)
- [x] **T16** Create `infra/modules/ecr/` — ECR repository `medi-nudge-api`, lifecycle policy (keep last 20 images), scan on push enabled
- [x] **T17** Create `infra/modules/ecs/` — ECS cluster, two task definitions (`api` and `scheduler`), two services (`api-service` desired 1–4, `scheduler-service` desired 1), CloudWatch log groups, task/execution IAM roles
- [x] **T18** Create `infra/modules/alb/` — ALB in public subnets, HTTP 80 → HTTPS 301 redirect, HTTPS 443 listener with ACM certificate, target group for ECS port 8000, health check `GET /health`
- [x] **T19** Create `infra/modules/cloudfront/` — distribution pointing to frontend S3 bucket via OAC, custom error response (403 → 200 `index.html`), ACM cert in `us-east-1`
- [x] **T20** Create `infra/modules/iam/` — GitHub Actions OIDC provider, deploy role (ECR push, ECS update-service, ECS run-task, S3 sync, CloudFront invalidation), scoped to `repo:<org>/<repo>:ref:refs/heads/main`
- [x] **T21** Create `infra/environments/staging/` and `infra/environments/production/` as Terraform workspace configs (or `terraform.tfvars` per env)
- [x] **T22** Create S3 backend config (`infra/backend.tf`) with DynamoDB lock table for Terraform state
  - Depends on: T12–T21

## Phase 4 — CI/CD Pipeline

- [x] **T23** Create `.github/workflows/ci-cd.yml` with jobs: `test` → `build` → `migrate` → `deploy` triggered on push to `main`
  - `test`: set up Python 3.12, install deps, run `pytest --cov=app`, run `npm ci && npm run lint` in `frontend/`
  - `build`: OIDC auth, ECR login (`aws-actions/amazon-ecr-login`), `docker buildx build --platform linux/arm64`, push with `$GITHUB_SHA` and `latest` tags, smoke-test `tesseract --version` in container
  - `migrate`: `aws ecs run-task` with command override `alembic upgrade head`, wait for exit 0
  - `deploy-backend`: `aws ecs update-service --force-new-deployment` for `api-service` and `scheduler-service`, then `aws ecs wait services-stable`
  - `deploy-frontend`: `npm run build`, `aws s3 sync dist/ s3://.../ --delete`, `aws cloudfront create-invalidation --paths "/*"`
  - Depends on: T9, T20, T22

## Phase 5 — Documentation

- [x] **T24** Update `README.md`:
  - Add `AWS Deployment` section with `terraform init/plan/apply` instructions for `infra/`
  - Add required GitHub repository secrets/variables (OIDC role ARN, ECR repo, bucket names)
  - Note `SCHEDULER_ENABLED` env var split and `app.worker` entry point
  - Depends on: T1–T23

## Validation

- [x] **V1** All existing `pytest` tests pass after Phase 1 code changes (no regressions) — 59/59 passed
- [x] **V2** New S3 mock tests pass for both upload paths (T8) — 6 new tests passing
- [ ] **V3** Docker image builds successfully, `tesseract --version` passes inside container (T11) — requires Docker daemon
- [ ] **V4** `terraform validate` passes on all modules (T22) — requires `terraform` CLI and AWS provider download
- [ ] **V5** GitHub Actions workflow runs end-to-end on a staging environment push — requires AWS account
- [x] **V6** `openspec validate deploy-aws-infrastructure --strict` passes with no issues
