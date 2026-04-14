# Medi-Nudge System

A personalised medication adherence platform for chronic disease patients, using WhatsApp nudges, prescription OCR, escalation workflows, and a care coordinator dashboard.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for prescription scanning)

---

## Backend (FastAPI)

### 1. Set up a virtual environment

```bash
cd backend
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=sqlite:///./medi_nudge.db
JWT_SECRET_KEY=your-secret-key-here

# Optional — required for WhatsApp messaging
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Optional — required for AI nudge generation
OPENAI_API_KEY=

MEDIA_STORAGE_PATH=./media
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

### 6. (Optional) Run the Telegram long-poll bridge

For local development, use this script to poll Telegram updates and forward them to the local webhook endpoint. Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` in your `.env` file.

```bash
python poll_telegram.py
```

---

## Frontend (React + Vite)

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Start the development server

```bash
npm run dev
```

The app will be available at **http://localhost:5173**

---

## Running Tests

From the `backend/` directory (with the virtual environment activated):

```bash
pytest
```

To run with coverage:

```bash
pytest --cov=app
```

---

## Project Structure

```
medi-nudge-system/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── core/         # Config, database, scheduler, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── routers/      # API route handlers
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic (nudges, OCR, escalations, WhatsApp)
│   ├── migrations/       # Alembic DB migrations
│   ├── tests/            # Pytest test suite
│   └── requirements.txt
├── frontend/             # React + Vite frontend
│   └── src/
│       ├── components/   # Shared UI components
│       ├── pages/        # Route-level page components
│       ├── hooks/        # Custom React hooks
│       └── lib/          # API client
└── docs/                 # Additional documentation
```

---

## Key Features

- **WhatsApp nudges** — scheduled medication reminders via Twilio
- **Prescription OCR** — extract medication data from uploaded images
- **Escalation engine** — flags non-adherent patients for care coordinator follow-up
- **Analytics dashboard** — adherence trends and patient insights
- **Caregiver loop** — loop in caregivers when patient is unresponsive

---

## AWS Deployment

Infrastructure is defined with Terraform under `infra/`. Target region: `ap-southeast-1`.

### Prerequisites

- Terraform >= 1.7
- AWS CLI configured with permissions to create IAM, ECS, RDS, S3, CloudFront resources
- ACM certificates created manually in `ap-southeast-1` (ALB) and `us-east-1` (CloudFront)
- S3 state bucket and DynamoDB lock table bootstrapped (see comments in `infra/backend.tf`)

### Deploy (staging)

```bash
cd infra
terraform init \
  -backend-config="bucket=medi-nudge-tfstate-staging" \
  -backend-config="key=staging/terraform.tfstate" \
  -backend-config="region=ap-southeast-1" \
  -backend-config="dynamodb_table=medi-nudge-tfstate-lock"

terraform plan -var-file="environments/staging/terraform.tfvars"
terraform apply -var-file="environments/staging/terraform.tfvars"
```

Replace `staging` with `production` and use `environments/production/terraform.tfvars` for production.

### Required GitHub repository variables

Set these under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Description |
|---|---|
| `GH_DEPLOY_ROLE_ARN` | IAM role ARN output from `terraform output github_actions_role_arn` |
| `FRONTEND_BUCKET_NAME` | S3 frontend bucket name from `terraform output frontend_bucket_name` |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID from `terraform output cloudfront_domain_name` |
| `ECS_PRIVATE_SUBNET_IDS` | Comma-separated private subnet IDs (from VPC module outputs) |
| `ECS_SG_ID` | ECS security group ID (from ECS module outputs) |
| `VITE_API_BASE_URL` | API base URL for the SPA build (e.g. `https://api.medi-nudge.example.com`) |

### Scheduler vs API

The app uses two ECS services sharing the same Docker image:

| Service | `SCHEDULER_ENABLED` | Entry point |
|---|---|---|
| `api-service` | `false` | `uvicorn app.main:app` |
| `scheduler-service` | `true` | `python -m app.worker` |

This prevents APScheduler from firing duplicate jobs when the API scales horizontally.

### Pre-signed prescription images

Set `AWS_S3_BUCKET_NAME` in the ECS task environment to switch prescription image storage from local filesystem to S3. Images are served as 15-minute pre-signed URLs — no public S3 access is required or granted.

