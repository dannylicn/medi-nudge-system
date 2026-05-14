# Mid-Review Bazaar Prep

## Elevator Pitch (30 seconds)
Medi-Nudge is a medication adherence system that uses AI to help care coordinators monitor chronic disease patients. We interviewed real patients, caregivers, and nurses at Sengkang General Hospital. We found that patients secretly self-adjust medication dosages, and remote caregivers have no way to verify if meds were actually taken. Our system detects these patterns and nudges patients via Telegram with warm, human-like voice messages.

## System Architecture (for technical questions)

### How it's deployed
- Backend: Python FastAPI running on AWS ECS Fargate (serverless containers)
- Frontend: React SPA on S3, served via CloudFront CDN
- Database: PostgreSQL on RDS
- Bot: Telegram Bot API with webhook to our backend
- Voice: ElevenLabs Text-to-Speech for voice nudges
- AI: OpenAI for generating personalised nudge messages and patient summaries
- Infra: Terraform (infrastructure as code), all in ap-southeast-1

### Why these choices?
- ECS Fargate over EC2: no servers to manage, pay per second, scales to zero
- CloudFront: single URL serves both frontend and proxies API calls (HTTPS included)
- Telegram over WhatsApp: free API, no business verification needed for hackathon, widely used in Singapore
- ElevenLabs: natural-sounding voices, free tier available, API is simple
- OpenAI: generates contextual nudge messages tailored to patient's language, condition, and adherence history

### Cost
- Hackathon budget: ~$30-40 for 16 days
- Biggest costs: ALB (~$9), RDS db.t4g.micro (~$11), Secrets Manager (~$1.90)
- CloudFront, S3, ECS: effectively $0 at hackathon scale
- OpenAI: ~$0.01 per AI summary (gpt-4o-mini)
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
A: We analyse dose timing patterns. If a patient's dose logs show highly irregular times (e.g., taking medication 4 hours late some days, on time others, or skipping every other day), we flag it as a possible self-adjustment pattern. This ties directly to our interview finding.

**Q: How do you handle patient privacy?**
A: NRICs are SHA-256 hashed before storage — never stored in plaintext. The system runs on a government AWS account with SCPs. All API endpoints require JWT authentication.

**Q: What happens if the patient doesn't use Telegram?**
A: The system is designed around Telegram because it's widely used in Singapore's elderly population. Future: could extend to SMS or WhatsApp. The web portal works independently for care coordinators.

**Q: How does voice nudge work?**
A: Text message → ElevenLabs API (text-to-speech) → .ogg audio file → sent via Telegram voice message. We selected voices that sound warm and caring. Patients can opt in to voice nudges.

**Q: What's the data model?**
A: Patient → PatientMedication (junction) → Medication. DoseLog tracks every taken/missed/skipped dose. NudgeCampaign tracks the nudge lifecycle (pending → sent → responded/escalated/resolved). EscalationCase flags issues for care coordinators.

**Q: How does the scheduler work?**
A: APScheduler running in a separate ECS container. Four jobs: daily refill gap detection (08:00 UTC), 48h no-reply retry (hourly), onboarding drop-off check (6h), medication reminders (every 30 min based on each patient's reminder_times in SGT).

**Q: Can it scale?**
A: ECS Fargate auto-scales. RDS can be upgraded. CloudFront handles CDN. But for the hackathon demo with 5 patients, we deliberately chose the smallest instances to minimise cost.

## Demo Script (5-10 min pitch)

1. **Open with research insight** (30s): "We interviewed patients, caregivers, and nurses. We found that 'playing doctor' — patients secretly self-adjusting their medication — is a hidden risk that no current system detects."

2. **Show dashboard** (1 min): Point out compliance scores, critical med badges, Siti Nurhaliza at 36% adherence with 55 critical med misses.

3. **Click into Siti's profile** (1 min): Show adherence circle, dose history, CRITICAL badges on Warfarin and Gliclazide. Click "Generate AI Summary" — show the AI insight.

4. **Show Telegram bot** (1 min): Open Telegram, show a medication reminder being received. Show the voice message if working.

5. **Show escalation flow** (30s): Point out how missed doses automatically escalate to the coordinator dashboard.

6. **Close with impact** (30s): "Our system catches what self-reporting misses. It's not just reminders — it's pattern detection powered by real user research."

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
