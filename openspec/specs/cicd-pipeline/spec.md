# cicd-pipeline Specification

## Purpose
TBD - created by archiving change deploy-aws-infrastructure. Update Purpose after archive.
## Requirements
### Requirement: All commits to main are automatically tested before deploy

Every push to the `main` branch SHALL trigger a pipeline that runs the full test suite for both backend and frontend before any build or deployment step proceeds.

#### Scenario: Backend tests pass — pipeline continues

Given a developer pushes a commit to `main`
When the `test` GitHub Actions job runs
Then `pytest` executes the full test suite under `backend/tests/` with the virtual environment
And the job succeeds only if all tests pass and coverage does not drop below the configured threshold
And the `build` job starts only after `test` succeeds

#### Scenario: Backend tests fail — deploy is blocked

Given a developer pushes a commit to `main` with a test failure
When the `test` job runs
Then `pytest` exits with a non-zero code
And the `build` and `deploy` jobs are skipped
And GitHub marks the commit check as failed

#### Scenario: Frontend lint passes

Given the `test` job runs
When `npm run lint` is executed in `frontend/`
Then ESLint reports no errors
And the step is marked successful

---

### Requirement: Container image is built and pushed to ECR on every successful test

A Docker image for the backend SHALL be built and pushed to Amazon ECR after every successful test run on `main`, tagged with the full git commit SHA.

#### Scenario: Image is built and pushed with commit SHA tag

Given the `test` job has succeeded
When the `build` job runs
Then `docker buildx build` produces a `linux/arm64` image (for Graviton ECS tasks)
And the image is pushed to `<account>.dkr.ecr.<region>.amazonaws.com/medi-nudge-api:<SHA>`
And an additional `latest` tag is pushed to the same repository

#### Scenario: build job authenticates to ECR via OIDC, not static keys

Given the GitHub Actions runner starts the `build` job
When the `aws-actions/configure-aws-credentials` step runs
Then authentication uses an OIDC token with the `oidcProviderArn` and `roleArn` configured for the repository
And no `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` GitHub secrets are required

#### Scenario: Tesseract is present in the built image

Given the Dockerfile installs `tesseract-ocr` via `apt-get`
When a smoke test (`tesseract --version`) is run inside the container in CI
Then the command succeeds
And the OCR fallback path is validated as callable

---

### Requirement: Alembic migrations run before API deployment

`alembic upgrade head` SHALL be executed as an ECS one-off run-task against the production RDS instance before the API service rolls over to the new image.

#### Scenario: Migrations complete before rolling deploy

Given the `build` job has pushed a new image
When the `migrate` step runs `aws ecs run-task` with the migration command override
Then the ECS task runs `alembic upgrade head` against the RDS endpoint
And the `deploy` step does not start until the migration task exits with code 0

#### Scenario: Migration failure halts the deploy

Given a schema migration fails mid-run (e.g. constraint violation)
When the ECS run-task exits with a non-zero code
Then the `deploy` step is skipped
And the pipeline is marked failed
And the existing API version continues serving traffic uninterrupted

---

### Requirement: ECS service is updated via rolling deployment

The `api-service` and `scheduler-service` ECS services SHALL be updated to the new task definition revision using a rolling deployment with a minimum healthy percent of 100%.

#### Scenario: Rolling deploy completes without downtime

Given a new image has been pushed and migrations have succeeded
When `aws ecs update-service --force-new-deployment` is called for `api-service`
Then ECS launches replacement tasks using the new task definition revision
And waits for new tasks to reach `RUNNING` before draining old tasks
And the ALB never routes traffic to a task that has not passed its health check

#### Scenario: Deploys trigger alerts if rollout exceeds timeout

Given ECS is rolling out new `api-service` tasks
When the rollout does not complete within 10 minutes
Then the `aws ecs wait services-stable` command times out
And the GitHub Actions step fails
And the on-call SNS notification is triggered

---

### Requirement: Frontend static assets deployed to S3 + CloudFront cache invalidated

The `npm run build` output SHALL be synced to the frontend S3 bucket and a CloudFront invalidation created on every successful main-branch push.

#### Scenario: Vite build synced to S3

Given the `deploy` job runs
When `aws s3 sync dist/ s3://medi-nudge-frontend-<env>/ --delete` executes
Then all new and changed files are uploaded
And files not present in the new build are removed from S3

#### Scenario: CloudFront cache is invalidated after S3 sync

Given S3 sync has completed
When `aws cloudfront create-invalidation --paths "/*"` runs
Then CloudFront edge caches are flushed
And users receive the new SPA within 1 minute

