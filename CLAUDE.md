# Medi-Nudge System

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

Full interview transcripts: /Users/jolyn/Desktop/hackathon/hackathon_interviews.txt

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
- **Database**: PostgreSQL 16 (RDS db.t4g.micro on AWS, SQLite locally)
- **Infra**: Terraform, ECS Fargate (public subnets, no NAT), ALB, CloudFront, S3
- **Integrations**: OpenAI (nudge message generation), ElevenLabs (voice nudges), Telegram Bot API

## Live URLs

- Web portal: https://d2osdk2gdq7n3i.cloudfront.net
- API docs: https://d2osdk2gdq7n3i.cloudfront.net/docs
- API (ALB): http://medi-nudge-staging-905906235.ap-southeast-1.elb.amazonaws.com
- Telegram bot: @MediNudgeBot

## AWS

- Region: ap-southeast-1
- Profile: agency_admin-354918370110
- VPC: nova-vpc (172.16.1.0/24, public subnets only)
- ECS cluster: medi-nudge-staging (api-service + scheduler-service)
- ECR: medi-nudge-api
- CloudFront proxies both frontend (S3) and /api/* (ALB) from one URL

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

Login: admin@medinudge.sg / changeme123

## Deploy frontend

```bash
cd frontend && npm run build
AWS_PROFILE=agency_admin-354918370110 aws s3 sync dist s3://medi-nudge-frontend-staging --region ap-southeast-1
AWS_PROFILE=agency_admin-354918370110 aws cloudfront create-invalidation --distribution-id E1P4QR73CSXTYF --paths "/*" --region ap-southeast-1
```

## Deploy backend

```bash
cd backend
AWS_PROFILE=agency_admin-354918370110 aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin 354918370110.dkr.ecr.ap-southeast-1.amazonaws.com
docker build --platform linux/arm64 -t 354918370110.dkr.ecr.ap-southeast-1.amazonaws.com/medi-nudge-api:latest .
docker push 354918370110.dkr.ecr.ap-southeast-1.amazonaws.com/medi-nudge-api:latest
AWS_PROFILE=agency_admin-354918370110 aws ecs update-service --cluster medi-nudge-staging --service api-service --force-new-deployment --region ap-southeast-1
```

## Run database migration on AWS

```bash
AWS_PROFILE=agency_admin-354918370110 aws ecs run-task --cluster medi-nudge-staging --task-definition medi-nudge-migrate-staging --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-0b7b0c35dc2ec701b],securityGroups=[sg-06e149633730e3316],assignPublicIp=ENABLED}" --region ap-southeast-1
```

## Conventions

- Commit messages: conventional commits (feat, fix, chore, docs, etc.)
- No Co-Authored-By lines in commits
- Explain code changes before making them
- Frontend env: .env.production has VITE_API_URL= (empty) for CloudFront; local dev defaults to localhost:8000
- Terraform state: s3://medi-nudge-tfstate-gt with DynamoDB lock table medi-nudge-tfstate-lock

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
