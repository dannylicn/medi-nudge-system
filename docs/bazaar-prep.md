# Mid-Review Bazaar Prep

## Elevator Pitch (30 seconds)
Medi-Nudge is a medication adherence system that uses AI to help care coordinators monitor chronic disease patients. We interviewed real patients, caregivers, and nurses at Sengkang General Hospital. We found that patients secretly self-adjust medication dosages, and remote caregivers have no way to verify if meds were actually taken. Our system detects these patterns and nudges patients via Telegram with warm, human-like voice messages.

## System Architecture (for technical questions)

### How it's deployed (verified from Terraform + code)

**Backend:**
- Python 3.12 + FastAPI, running on AWS ECS Fargate (serverless containers, ARM64)
- 2 ECS services: api-service (512 CPU / 1024MB memory) and scheduler-service (256 CPU / 512MB memory)
- Docker image stored in ECR, built from python:3.12-slim with Tesseract OCR + OpenCV
- All secrets (API keys, DB password, JWT secret) stored in AWS Secrets Manager and injected at runtime — nothing hardcoded

**Frontend:**
- React 19 + Vite + Tailwind CSS, built as static files
- Hosted on S3 bucket, served via CloudFront CDN
- CloudFront serves both frontend AND proxies /api/* requests to the backend ALB — so one single URL for everything with HTTPS

**Database:**
- PostgreSQL 16 on RDS (db.t4g.micro — 2 vCPU, 1GB RAM, 20GB gp3 storage)
- Encrypted at rest, single AZ (no multi-AZ for hackathon)
- Migrations managed by Alembic

**Networking:**
- VPC (nova-vpc, /24 CIDR) with 2 public subnets in ap-southeast-1a and 1b
- No NAT gateways — ECS tasks run in public subnets with auto-assigned public IPs (cost saving)
- Application Load Balancer routes traffic to ECS tasks
- Infrastructure as code using Terraform

**Integrations:**
- OpenAI (GPT-4): AI patient summaries, nudge message generation, OCR prescription extraction
- ElevenLabs: text-to-speech voice nudges
- Telegram Bot API: patient communication via webhook
- No Twilio — WhatsApp/SMS not live (difficult to register for hackathon)

### Why these choices?
- ECS Fargate over EC2: no servers to manage, pay per second, no patching
- CloudFront: single URL for frontend + API, free HTTPS, free tier covers our usage
- Public subnets (no NAT): saves ~$65-130/month — NAT gateways are the biggest unnecessary cost for a hackathon
- Telegram over WhatsApp: free API, no business verification needed, widely used by elderly in Singapore
- ARM64 containers: cheaper than x86 on Fargate, Mac M-series builds natively
- Secrets Manager over .env files: secrets never touch the codebase or Docker image

### Cost (verified)
- Total estimated for 16 days: ~$30-40
- ALB: ~$9 (biggest cost — needed for stable DNS in front of ECS tasks)
- RDS db.t4g.micro: ~$11
- Secrets Manager: ~$3.60 (9 secrets × $0.40/month)
- ECS Fargate: ~$3-5 (2 small tasks, ARM64)
- CloudFront: $0 (free tier — 1M requests/month, 100GB transfer)
- S3: $0 (negligible storage)
- OpenAI: ~$0.01 per AI summary call
- ElevenLabs: free tier

## Features and the Research Behind Them

### 1. Compliance Score + Critical Medication Flag
- **What it does**: Dashboard shows per-patient adherence % and flags missed critical medications (Warfarin, Gliclazide) with a red badge
- **Research insight**: Nurse said "a dashboard showing missed doses and patient compliance patterns would be very useful." She flagged Warfarin as a medication where "missing even one day has real consequences — blood becomes too thick or too thin."
- **Quote to use**: "The nurse we interviewed said she wants to see compliance patterns at a glance. So we built exactly that."

### 2. AI-Generated Patient Summary
- **What it does**: OpenAI generates a 2-3 sentence plain-English summary of each patient's adherence behaviour. Example: "Siti has missed 65% of her Warfarin doses. Her timing is irregular, suggesting possible self-adjustment."
- **Research insight**: Nurse wants to understand patterns quickly. "Playing doctor" (self-adjustment) was observed across multiple patients.
- **Quote to use**: "Several patients we interviewed admitted to self-adjusting their dosages. Our AI detects irregular patterns and alerts the care team."

### 3. Telegram Bot + Voice Nudges
- **What it does**: Sends medication reminders via Telegram. Supports text and voice messages (ElevenLabs). Multilingual (English, Chinese, Malay, Tamil).
- **Research insight**: "Talking to AI vs talking to a human is different." Elderly patients are more receptive to authority figures (nurses). Our voice nudges sound warm and human, not robotic.
- **Quote to use**: "Caregivers told us patients respond better to a nurse's voice than a family member's nagging. So we built voice nudges that feel like a care team check-in."

### 4. Automated Escalation
- **What it does**: If a patient doesn't respond to 3 nudge attempts, the system automatically escalates to the care coordinator dashboard. Side effects trigger urgent escalation immediately.
- **Research insight**: Nurse said patients sometimes hide non-compliance. System catches what self-reporting misses.

## Anticipated Technical Questions

**Q: How does the AI generate personalised messages?**
A: We send the patient's medication history, adherence patterns, language preference, and conditions to OpenAI. The prompt asks for a warm, actionable summary. Each summary costs <$0.01 and is cached for 24 hours.

**Q: How do you detect self-adjustment ("playing doctor")?**
A: Currently, the AI Insights feature asks OpenAI to look for irregular dose timing patterns (e.g., taking medication at very different times each day, or skipping every other day) when generating a patient summary. If the data shows a self-adjustment pattern, the AI summary will flag it. We're planning to build a dedicated detection alert for the final pitch — a separate system-level flag, not just the AI mentioning it.

**Q: How do you handle patient privacy?**
A: NRICs are SHA-256 hashed before storage — never stored in plaintext. The system runs on a government AWS account with SCPs. All API endpoints require JWT authentication.

**Q: What happens if the patient doesn't use Telegram?**
A: The system is designed around Telegram because it's widely used in Singapore's elderly population. Future: could extend to SMS or WhatsApp. The web portal works independently for care coordinators.

**Q: How does voice nudge work?**
A: Text message → ElevenLabs API (text-to-speech) → .ogg audio file → sent via Telegram voice message. We selected voices that sound warm and caring. Patients can opt in to voice nudges.

**Q: What's the data model?**
A: Patient → PatientMedication (junction) → Medication. DoseLog tracks every taken/missed/skipped dose. NudgeCampaign tracks the nudge lifecycle (pending → sent → responded/escalated/resolved). EscalationCase flags issues for care coordinators.

**Q: How does the scheduler work?**
A: APScheduler running in a separate ECS container. Six jobs: daily refill gap detection (08:00 SGT), 48h no-reply retry (hourly), onboarding drop-off check (6h), fire pending nudge campaigns (every 30 min), medication reminders (every 30 min based on each patient's reminder_times in SGT), and side-effect check-in (daily 09:05 SGT for medications started 3 days ago).

**Q: Can it scale?**
A: ECS Fargate auto-scales. RDS can be upgraded. CloudFront handles CDN. But for the hackathon demo with 5 patients, we deliberately chose the smallest instances to minimise cost.

## Feedback Bazaar Walkthrough Script

### Opening (10 seconds)
"Hi! This is Medi-Nudge — a medication adherence system for chronic disease patients in Singapore. We interviewed real patients, caregivers, and a nurse at Sengkang General Hospital, and built this based on what they told us."

### 1. Dashboard (30-45 seconds)
Open the web portal.

"This is the care coordinator dashboard. Each patient shows their Doses Taken percentage — colour-coded so the nurse immediately knows who needs attention. Red means below 50%. The ⚠️ icon means they've missed critical medications — a nurse we interviewed told us that for medications like Warfarin, missing even one day has real consequences."

Point to the right sidebar: "Pending escalations are flagged here — these 4 are because high-risk patients have consecutive missed doses. Below that, the High Risk Patients count and Pending Refills give a quick summary."

### 2. Patient Detail (45-60 seconds)
Click on Tan Wei Liang (high risk, low adherence, has ⚠️).

"When the nurse clicks into a patient, they get the full picture."

Point to adherence circle: "62% overall adherence in the last 30 days."

Point to AI Insights: "This AI Insights section is generated automatically — it analyses 30 days of dose history and gives a plain English summary with a recommendation. Powered by OpenAI. The nurse doesn't need to read through hundreds of dose records."

Read the AI summary out loud.

Point to Active Medications: "Each medication shows whether it's critical — like Gliclazide MR here which is flagged as CRITICAL."

Point to Doses by Medication: "This breaks down adherence per medication with progress bars. The nurse can see exactly which medication this patient is struggling with — Jardiance is at 42%, that's the worst one."

Point to Recent Activity: "Recent activity shows what happened in the last few days, scrollable."

### 3. Medications Tab (15 seconds)
Click on Medications tab.

"This is the medication catalog — 41 medications commonly prescribed for chronic conditions in Singapore. Nurses can add new medications here as needed."

### 4. Escalations Tab (20 seconds)
Click on Escalations tab.

"This is the full escalation queue — same data as the dashboard sidebar but in a dedicated view. Nurses can manage cases here — assign them, add notes, or resolve them. Right now we have 4 open urgent cases, all from high-risk patients with consecutive missed doses."

### 5. OCR Review Tab (20 seconds)
Click on OCR Review tab.

"This is for prescription scanning. A patient takes a photo of their prescription label, and OCR — Optical Character Recognition — automatically extracts the details using GPT-4 Vision. It pulls out the medication name, dosage, frequency, prescriber, clinic, dispense and expiry dates, instructions, and warnings — each with a confidence score. The nurse reviews it here and confirms or corrects it, instead of typing everything manually. If GPT-4 Vision is unavailable, it falls back to Tesseract for basic text extraction. We haven't populated demo data for this yet, but the feature is built."

### 6. Analytics Tab (30-45 seconds)
Click on Analytics tab.

"The analytics page shows trends over time."

Point to Dose Adherence Rate chart: "This chart shows the overall dose adherence rate across all patients by week — what percentage of all scheduled doses were taken."

Point to Adherence by Medication table: "This table breaks it down by medication, sorted worst-first. Plavix is at 58.6% — the worst adherence. Omeprazole is at 86.4% — the best. This tells the nurse which medications patients are struggling with most across the whole patient population."

Point to Escalation Volume by Week chart: "This shows how many escalation cases were created each week, broken down by priority — urgent, high, normal, low. Right now all 4 are urgent."

### Closing (10 seconds)
"Everything we built ties back to what patients, caregivers, and the nurse told us during our research. Any feedback on what you've seen? What would make this more useful for a nurse or doctor?"

### If asked about the research
"We interviewed 8 patients, 2 caregivers, and a nurse. The biggest insights were: patients secretly self-adjust their dosages — we call it 'playing doctor'. Remote caregivers have no way to verify if meds were actually taken. And for critical medications like Warfarin, missing even one day has real clinical consequences. Everything we built addresses one of these findings."

### If asked what's next
"For the final pitch, we're adding analytics charts that show critical vs non-critical medication adherence trends, and a heatmap showing when patients miss doses most — which day and time of day. We're also working on Telegram bot integration for medication reminders and caregiver notifications."

### Tips for the bazaar
- Don't read from notes — click through the portal naturally, talk about what you see
- Lead with the research — "a nurse told us..." is more powerful than "we built a feature that..."
- Ask for feedback — "What would you change?" gets better responses than "what do you think?"
- If something breaks — say "let me show you this other part" and move on
- You have 2-3 minutes per person — don't try to show everything, focus on Dashboard → Patient Detail → Analytics as the core flow, mention the other tabs briefly

## Analytics Charts — What Each Chart Shows

### Dose Adherence Rate (line chart)
- **Data source:** DoseLog table — every time a patient takes or misses a scheduled dose, a record is created
- **How it works:** Groups all dose records by week across ALL patients, then counts:
  - **Taken:** number of doses with status "taken" (e.g. 531 doses taken in week 16)
  - **Missed:** number of doses with status "missed" (e.g. 216 doses missed in week 16)
  - **Adherence %:** taken / (taken + missed) × 100 (e.g. 531/747 = 71.1%)
- **What it tells a nurse:** "Are patients overall getting better or worse at taking their meds week over week?"
- **Known issue:** Currently shows Taken and Missed raw counts on the same axis as Adherence %, which makes the chart confusing (shows "531%" which is not a real percentage — it's a count). Fix planned: remove Taken/Missed lines, keep only Adherence %.

### Adherence by Medication (table)
- **Data source:** Same DoseLog table, grouped by medication instead of by week
- **What it shows:** For each medication: total doses scheduled, how many taken, how many missed, adherence %
- **What it tells a nurse:** "Which medications are patients struggling with most?" Sorted worst-first.

### Escalation Volume by Week (bar chart)
- **Data source:** EscalationCase table — created when patients don't respond to nudges, report side effects, or miss doses repeatedly
- **What it shows:** Number of escalation cases per week, colour-coded by priority (urgent, high, normal, low)
- **What it tells a nurse:** "Are escalations increasing or decreasing? What severity?"

### Doses Taken (dashboard column)
- **Data source:** Same DoseLog table, filtered per patient for the last 30 days
- **How it works:** (doses taken / total doses) × 100 per patient
- **What the ⚠️ icon means:** This patient has missed doses of a critical medication (e.g. Warfarin, Gliclazide) — hover to see how many

### AI Insights (patient detail page)
- **Data source:** Patient's 30-day dose history, medications, conditions — sent to OpenAI
- **What it generates:** A 2-3 sentence plain English summary of the patient's adherence pattern with an actionable recommendation
- **Example:** "Siti is frequently missing doses of Gliclazide and Warfarin, particularly on weekends. Recommend a check-in call to explore barriers."
- **Auto-generates** when nurse clicks into a patient. Refresh button to regenerate. Cached for 24 hours.
