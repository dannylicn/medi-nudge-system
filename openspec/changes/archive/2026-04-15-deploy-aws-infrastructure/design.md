# Design: deploy-aws-infrastructure

## Architecture Diagram

```
Internet
   │
   ├─── CloudFront (HTTPS, custom domain)
   │          └── S3 (React/Vite SPA — dist/)
   │
   └─── ALB (HTTPS :443, ACM certificate)
              └── ECS Fargate Cluster (private subnets)
                     ├── api-service (N tasks, port 8000)
                     │       FastAPI + APScheduler disabled
                     └── scheduler-service (1 task)
                             FastAPI app with ONLY scheduler enabled
                             (CMD override: python -m app.worker)

ECS Tasks → RDS PostgreSQL (private subnet, port 5432)
ECS Tasks → S3 (prescription images, via VPC endpoint for S3)
ECS Tasks → Secrets Manager (runtime secret injection)
ECS Tasks → CloudWatch Logs (log groups per service)
ECS Tasks → External APIs via NAT Gateway:
              Telegram API, OpenAI, ElevenLabs, Twilio
```

---

## AWS Service Selections and Rationale

### Compute: ECS Fargate (not EC2, not EKS)

**Decision:** ECS Fargate with two task definitions — `api` and `scheduler`.

**Rationale:**
- No EC2 instances to patch or manage. Fargate is right-sized for a v1 workload with unpredictable burst traffic (outbound nudge campaigns).
- Avoids Kubernetes complexity (EKS control plane costs ~$72/month for the cluster alone, before nodes).
- `api-service` can auto-scale based on ALB request count; `scheduler-service` is pinned to 1 task to prevent duplicate APScheduler job execution.

**APScheduler separation:**
The current in-process APScheduler works correctly on exactly 1 container but fires duplicate jobs if 2+ API containers are running concurrently. The solution is a minimal override to the startup command:
- `api-service` CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`  (env `SCHEDULER_ENABLED=false`)
- `scheduler-service` CMD: `python -m app.worker` — a thin module that imports only the scheduler and runs it as a standalone process

This requires adding `SCHEDULER_ENABLED` env var to `config.py` and a guard in `scheduler.py`.

### Database: RDS PostgreSQL 16

**Decision:** `db.t4g.small` Multi-AZ for production; `db.t4g.micro` single-AZ for staging.

**Rationale:**
- `DATABASE_URL` env var swap from SQLite → PostgreSQL requires zero application code changes (confirmed from `database.py`).
- `db.t4g` (Graviton) is ~20% cheaper than `db.t3` at equivalent specs.
- Multi-AZ provides <30s automatic failover. Healthcare data requires durability.
- Credentials stored in Secrets Manager, never in task definition plaintext.

**Migration path:** `alembic upgrade head` runs as an ECS one-off task before the first API service deploy (enforced in CI pipeline as a pre-deploy step).

### Object Storage: S3 (private, SSE-KMS)

**Decision:** Two S3 buckets — `medi-nudge-media-{env}` (prescription images) and `medi-nudge-frontend-{env}` (SPA static assets).

**Rationale:**
- Prescription images are considered sensitive health data. Server-side encryption at rest via SSE-KMS. Full S3 public access block enabled.
- Access to prescription images via pre-signed URLs (15-minute TTL) generated server-side — consistent with the existing `prescription-ocr` spec requirement which already mandates signed URLs.
- Frontend bucket is private; CloudFront accesses it via Origin Access Control (OAC), not a public bucket website.
- A VPC Gateway Endpoint for S3 routes S3 traffic through AWS backbone, eliminating NAT Gateway costs for media uploads/downloads.

### Networking: VPC with public/private subnets

```
VPC: 10.0.0.0/16  (2 AZs: ap-southeast-1a, ap-southeast-1b)
  Public subnets  10.0.1.0/24, 10.0.2.0/24  → ALB, NAT Gateway
  Private subnets 10.0.3.0/24, 10.0.4.0/24  → ECS tasks, RDS
```

Security group rules:
- ALB SG: ingress 443 from 0.0.0.0/0
- ECS SG: ingress 8000 from ALB SG only
- RDS SG: ingress 5432 from ECS SG only

### Infrastructure as Code: Terraform

**Decision:** Terraform HCL modules over AWS CDK or CloudFormation.

**Rationale:**
- No compile step (CDK requires Node/Python build); simpler local iteration.
- Standard DevOps tooling with broad documentation and module registry.
- State stored in S3 backend with DynamoDB lock table.
- Modules: `vpc`, `ecs`, `rds`, `s3`, `alb`, `cloudfront`, `iam`

### CI/CD: GitHub Actions

**Decision:** GitHub Actions over AWS CodePipeline/CodeBuild.

**Rationale:**
- Repository is on GitHub; co-locating CI configuration reduces operational surface.
- Matrix testing (Python versions) and caching (pip, npm) are simpler to express.
- OIDC-based IAM authentication (no long-lived AWS keys stored as secrets).

**Pipeline stages:**
```
push → main
  ├── test       (pytest with coverage, frontend eslint)
  ├── build      (docker buildx, multi-platform linux/arm64)
  ├── push       (ECR, tagged with git SHA)
  ├── migrate    (ECS run-task --overrides alembic upgrade head)
  └── deploy     (aws ecs update-service --force-new-deployment)
```

OIDC trust policy limits the GitHub Actions role to pushes from `refs/heads/main` only.

---

## Required Code Changes

| File | Change | Risk |
|---|---|---|
| `backend/app/core/config.py` | Add `AWS_S3_BUCKET_NAME`, `AWS_REGION`, `ALLOWED_ORIGINS`, `SCHEDULER_ENABLED` | Low — additive |
| `backend/app/main.py` | Read `ALLOWED_ORIGINS` from settings; parse comma-separated string | Low |
| `backend/app/services/ocr_service.py` | Replace `open(image_path, "wb")` + `os.makedirs` with `boto3 s3.put_object`; fall back to local if `AWS_S3_BUCKET_NAME` not set | Medium — test coverage needed |
| `backend/app/core/scheduler.py` | Guard `start_scheduler()` behind `settings.SCHEDULER_ENABLED` | Low |
| `backend/requirements.txt` | Add `boto3>=1.34` | Low |
| `backend/Dockerfile` | New file; base `python:3.12-slim`; install `tesseract-ocr` via apt | Low |
| `backend/app/worker.py` | New file; thin entry point that calls `start_scheduler()` and blocks | Low |
| `infra/` | New Terraform root module and sub-modules | N/A (new) |
| `.github/workflows/ci-cd.yml` | New GitHub Actions workflow | N/A (new) |

---

## Security Considerations

- OIDC authentication for GitHub Actions (no static AWS credentials)
- Secrets Manager for all runtime secrets (no env var injection of plaintext secrets in task definitions for sensitive values)
- S3 bucket: `aws:SecureTransport` bucket policy enforces TLS-only access
- RDS: encrypted at rest (KMS), in private subnet, no public endpoint
- Prescription images: SSE-KMS, pre-signed URLs with 15-minute TTL
- ALB: HTTPS only, HTTP-to-HTTPS redirect, TLS 1.2+
- ECS task role: least privilege (S3 scoped to media bucket, Secrets Manager scoped to `/medi-nudge/` prefix)
- VPC flow logs enabled for network audit
