## ABSOLUTE RULES (READ BEFORE EVERY ACTION)
- After /compact: STOP. Re-read this entire file and _state.md before doing anything.
- NEVER introduce tools, services, dependencies, or infrastructure that are not already in the repo.
- If you are unsure about something after /compact, SAY "I lost context, let me re-read the project files" instead of guessing.
- If you find yourself about to suggest something new (new API, new library, new service), CHECK the repo first. If it's not there, don't suggest it.
- When I say "deploy", follow the exact deploy steps in CLAUDE.md. Do not invent new steps.

# Medi-Nudge System

@.claude/memory/defects.md
@_state.md

Medication adherence system for chronic disease patients in Singapore.
Hackathon project, demo pitch on 25 May 2026. Mid-review bazaar on Friday 16 May.

## What it does

Helps care coordinators monitor and nudge patients to take their medication via a web portal, Telegram bot, and AI-powered voice messages. Targets elderly, chronic disease patients (diabetes, hypertension, cholesterol).

## User research insights (DO NOT IGNORE THESE)

We conducted user research interviews at Sengkang General Hospital and a National Health Centre. These findings MUST inform every feature we build:

- **Reminder fatigue**: Multiple patients mentioned ignoring app alerts over time. What works better are habit anchors (e.g. placing pills next to the bed, taking after dinner) and environmental cues rather than push notifications. One interviewee explicitly said mobile alerts cause fatigue and are ineffective.
- **Critical medications**: A nurse flagged Warfarin as a medication where missing even one day has real clinical consequences — blood becomes too thick or too thin. Some patients hide non-compliance or self-adjust. Critical meds need to be handled differently from low-stakes ones like cholesterol supplements.
- **"Playing doctor"**: Several patients self-adjust dosages or skip based on their own judgment. Observed across cholesterol, insulin, and Warfarin patients. This is a risk pattern healthcare professionals want to be alerted to.
- **Caregiver gaps**: Remote caregivers cannot verify if meds were actually taken. One caregiver counts pills manually. There is no reliable remote verification mechanism currently.
- **Human touch**: Patients and caregivers prefer human-feeling interactions. One caregiver said "talking to AI vs talking to a human is different." Elderly patients are more receptive to authority figures (nurses) than family reminders. ElevenLabs voice nudge should feel warm, not robotic.
- **Elderly patients**: Those who live alone are most at risk of missing doses. Pillboxes are still valued for physical, visual confirmation. Not all elderly use smartphones.
- **Teenagers**: Young patients miss doses due to low awareness of consequences and busy schedules, not traditional forgetfulness. They need different messaging.
- **Insulin patients**: Two diabetic patients struggled not with forgetting to inject, but with calculating correct dosage based on food intake. This is a decision-support problem, not a reminder problem.
- **Platform fragmentation**: Caregivers noted HealthHub and SingHealth apps don't show the same data. Our system should be a single source of truth for the patient's medication schedule.
- **Nurse's wishlist**: A dashboard showing missed doses and patient compliance patterns would be very useful. Educating patients on consequences of missing meds (especially critical ones) would help.

## Key design principles from research

- Voice nudges must feel warm and human, not robotic
- Critical medications (Warfarin, insulin, Rifaximin) need different handling than regular meds
- "Playing doctor" (self-adjustment) is a real risk pattern to detect
- Elderly patients value physical cues and human touch over app notifications
- Remote caregivers have no reliable verification mechanism
- Patients experience app fatigue from manual input

## Project goal and rules

Win or place as runner-up in the hackathon. This means:
- Prioritise features that are demo-impressive over features that are technically elegant
- Every feature must tie back to a real user research insight (we have the quotes to prove it)
- Do NOT try to build everything at 80%. Build fewer features at 100% polish.
  Example of what we DON'T want: all 4 feature prompts half-done with rough edges and sparse data.
  Example of what we DO want: 2-3 features fully working with realistic demo data, clean UI,
  and a live Telegram escalation that fires on stage. Judges should think "this feels like a real product",
  not "they built a lot but nothing works well."
- Seed realistic demo data so the dashboard looks convincing during the pitch
- Don't over-engineer -- this app only needs to survive a 5-10 min live demo
- Keep AWS costs low -- this is a hackathon on a test government account
- Demo impact matters more than code perfection

## Architecture

- **Backend**: Python FastAPI (port 8000), SQLAlchemy ORM, Alembic migrations, APScheduler
- **Frontend**: React + Vite (port 5173 local), Tailwind CSS
- **Database**: PostgreSQL 16 (RDS on AWS, SQLite locally)
- **Infra**: Terraform, ECS Fargate (public subnets, no NAT), ALB, CloudFront, S3
- **Integrations**: OpenAI (nudge message generation), ElevenLabs (voice nudges), Telegram Bot API
- **Region**: ap-southeast-1

## Local dev

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Deploy

Deploy commands reference Terraform outputs and AWS profile. See `infra/` for Terraform config.
Do NOT hardcode AWS account IDs, subnet IDs, security group IDs, or resource ARNs in committed files.

```bash
# Frontend: build, upload to S3 frontend bucket, invalidate CloudFront
cd frontend && npm run build
aws s3 sync dist s3://<frontend-bucket> --region ap-southeast-1
aws cloudfront create-invalidation --distribution-id <cf-dist-id> --paths "/*"

# Backend: build Docker, push to ECR, restart ECS
cd backend
docker build --platform linux/arm64 -t <ecr-repo-url>:latest .
docker push <ecr-repo-url>:latest
aws ecs update-service --cluster <ecs-cluster> --service api-service --force-new-deployment

# Migration: run as one-off ECS task
aws ecs run-task --cluster <ecs-cluster> --task-definition <migrate-task-def> --launch-type FARGATE ...
```

Resource names and IDs can be found via `terraform output` in the `infra/` directory.

## Conventions

- Commit messages: conventional commits (feat, fix, chore, docs, etc.)
- No Co-Authored-By lines in commits
- Explain code changes before making them
- Deploy in logical batches, not per-step
- Frontend env: .env.production has VITE_API_URL= (empty) for CloudFront; local dev defaults to localhost:8000

## Key files

- `backend/app/main.py` — FastAPI app entry point
- `backend/app/routers/webhook.py` — Telegram bot webhook handler
- `backend/app/services/agent_service.py` — Agentic message handler (LLM or rule-based)
- `backend/app/schemas/schemas.py` — All API request/response models
- `backend/app/models/models.py` — SQLAlchemy database models
- `frontend/src/lib/api.js` — API client (axios, auth token management)
- `frontend/src/hooks/useAuth.jsx` — Auth context (sessionStorage persistence)
- `frontend/src/pages/DashboardPage.jsx` — Main dashboard (patients + escalations)
- `infra/main.tf` — Terraform root module
- `infra/modules/` — VPC, ECS, RDS, S3, ALB, CloudFront, ECR, IAM modules
