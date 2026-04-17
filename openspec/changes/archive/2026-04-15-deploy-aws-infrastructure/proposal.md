# Proposal: deploy-aws-infrastructure

## Summary

Deploy the Medi-Nudge system to AWS using managed services for compute (ECS Fargate), database (RDS PostgreSQL), object storage (S3), networking (VPC, ALB), and CDN (CloudFront). Adds a GitHub Actions CI/CD pipeline for automated testing, container image builds, and zero-downtime ECS deployments.

## Motivation

The system currently targets local development only (SQLite, local filesystem, manual startup). AWS deployment is required for production use with real patients, providing durability, scalability, security, and operational monitoring appropriate for a healthcare application.

## Scope

### In scope
- AWS infrastructure definition (Terraform HCL) covering VPC, ECS Fargate, RDS PostgreSQL, S3, ALB, CloudFront, Secrets Manager, and IAM roles
- GitHub Actions CI/CD workflow: test → build container image → push to ECR → rolling deploy to ECS
- Dockerfile for the FastAPI backend (includes Tesseract OCR)
- Code changes required to run in a containerised, stateless environment:
  - S3-backed file storage replacing local filesystem in `ocr_service.py`
  - CORS origins read from environment variable (`ALLOWED_ORIGINS`) in `main.py`
  - New env vars in `config.py`: `AWS_S3_BUCKET_NAME`, `AWS_REGION`, `ALLOWED_ORIGINS`
  - `boto3` added to `requirements.txt`
- Two new OpenSpec capabilities: `aws-infrastructure` and `cicd-pipeline`
- One spec delta to `prescription-ocr`: explicit S3 storage requirement

### Out of scope
- Celery/Redis migration for APScheduler (noted as a future improvement; scheduler runs as a dedicated ECS task)
- Multi-region or disaster-recovery setup
- WAF, Shield, or advanced DDoS protection
- Kubernetes or non-Fargate compute options
- Database schema changes

## Affected Capabilities

| Capability | Change Type | Summary |
|---|---|---|
| `aws-infrastructure` | ADDED | New capability covering all AWS service requirements |
| `cicd-pipeline` | ADDED | New capability covering automated build and deploy pipeline |
| `prescription-ocr` | MODIFIED | Explicit requirement for S3-backed image storage in production |

## Key Design Decisions

See `design.md` for full rationale. Summary:

1. **Terraform over CDK/CloudFormation** — portable HCL, no compile step, consistent with standard DevOps tooling
2. **ECS Fargate over EC2/EKS** — no node management, right-sized for v1 workload
3. **Dedicated ECS task for APScheduler** — avoids duplicate job execution if API service scales to 2+ tasks; both tasks share the same ECR image, different `CMD`
4. **Telegram webhook over long-polling** — eliminates `poll_telegram.py` process entirely for production; ALB terminates TLS and forwards to the API sidecar
5. **S3 for prescription image storage** — required for stateless containers; existing signed-URL access pattern in the spec is preserved

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| APScheduler duplicate jobs when API scales | Scheduler runs on a dedicated ECS task (desired count: 1) |
| Secrets leaked in container image | All secrets injected via Secrets Manager at runtime; no secrets in Dockerfile or ECR image |
| Tesseract not available in container | Installed via `apt-get` in Dockerfile, validated in CI |
| CORS mismatch after domain change | `ALLOWED_ORIGINS` env var; updated in ECS task definition |
| S3 prescription images publicly accessible | Bucket has `Block Public Access` enabled; images only served via pre-signed URLs (15 min TTL) |
