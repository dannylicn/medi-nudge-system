# Medi-Nudge — WhatsApp Conversation Mockups

These are illustrative conversation flows for each patient interaction channel beyond the core medication nudge. Patient replies are in plain text; system messages are labelled **[Medi-Nudge]**. Quick-reply buttons are shown as `[Button]`.

---

## 0. Medication Adherence Nudge

### 0a. Friendly First Reminder (Attempt 1)

**Context:** Mr Rajan, 67, Type 2 diabetes. Metformin 500mg overdue by 3 days.

---

**[Medi-Nudge]**
Hi Mr Rajan 👋 This is a friendly reminder from your care team at SingHealth.

It looks like it may be time to collect your **Metformin 500mg**. Staying on track with your medication helps keep your blood sugar stable.

Have you collected your medication recently?

`[✅ Yes, already collected]`  `[❌ Not yet]`  `[❓ Need help]`

---

**Mr Rajan:** [taps ✅ Yes, already collected]

---

**[Medi-Nudge]**
Great, thank you for letting us know! 💊 Keep it up — your next check-in is in 30 days.

If you ever have questions about your medication, just reply `HELP`.

---

> **[System]** Campaign #1042 resolved — patient confirmed collection. Attempt 1. No escalation needed.

---

### 0b. Concern Follow-up (Attempt 2 — no reply after 48 hours)

**Context:** Same patient, Metformin overdue 5 days. No reply to attempt 1.

---

**[Medi-Nudge]**
Hi Mr Rajan, we noticed you haven't confirmed your **Metformin 500mg** yet.

Missing doses can affect your blood sugar control. We just want to make sure everything is okay.

`[✅ Collected it]`  `[⏳ Will collect today]`  `[🤒 Feeling unwell]`  `[❓ Have a question]`

---

**Mr Rajan:** Will collect today

---

**[Medi-Nudge]**
Understood, thank you! 🙏 We'll check back with you tomorrow.

Remember: collect your medication from the polyclinic pharmacy or your nearest CHAS GP. Let us know if you need any help.

---

> **[System]** Campaign #1042 attempt 2 — patient responded "will collect today". Status set to pending. Scheduler will re-check in 24h.

---

### 0c. Urgency Escalation (Attempt 3 — still no collection after 7 days)

**Context:** Same patient. 7 days overdue. Third and final automated attempt.

---

**[Medi-Nudge]**
Hi Mr Rajan, your care nurse is concerned. It has been a week since your **Metformin 500mg** was due for collection.

Missing this medication for over a week can raise your blood sugar to unsafe levels.

👩‍⚕️ Nurse Faridah will be in touch shortly. Or reply now:

`[✅ I've collected it]`  `[📞 Please call me]`  `[🚫 Stop reminders]`

---

> **[Care Coordinator Alert — internal]**
> 🔴 **URGENT** — Mr Rajan (Metformin 500mg) — 7 days overdue, 3 attempts exhausted. Escalation case #ESC-0318 opened. Assigned to Nurse Faridah. Priority: HIGH.

---

**Mr Rajan:** Please call me

---

**[Medi-Nudge]**
Thank you, Mr Rajan. Nurse Faridah will call you within 2 hours. 📞

If it is urgent, you can also call the polyclinic at 6355 3000.

---

> **[Care Coordinator Alert — internal]**
> Mr Rajan requested phone call. Escalation #ESC-0318 status → IN PROGRESS. Nurse Faridah notified via dashboard.

---

### 0d. Side Effect During Nudge Flow

**Context:** Mdm Siti, 54, hypertension. Amlodipine 5mg overdue 4 days. First nudge sent.

---

**[Medi-Nudge]**
Hi Mdm Siti, a gentle reminder from your care team 🌸

Your **Amlodipine 5mg** (blood pressure tablet) is due for collection. Have you been able to pick it up?

`[✅ Yes collected]`  `[❌ Not yet]`  `[🤒 Feeling unwell]`

---

**Mdm Siti:** I stopped taking it. Feeling dizzy and my legs are swollen

---

**[Medi-Nudge]**
Thank you for telling us, Mdm Siti. Dizziness and swollen legs can be side effects of Amlodipine and should be checked by a doctor.

Please **do not abruptly stop** your blood pressure medication without consulting a doctor first — this can be dangerous.

👩‍⚕️ Your care coordinator has been alerted and will contact you shortly.

`[📞 Call me now]`  `[🏥 I'll visit the clinic]`

---

> **[Care Coordinator Alert — internal]**
> 🔴 **SIDE EFFECT REPORTED** — Mdm Siti — Amlodipine 5mg — symptoms: dizziness, leg swelling. Patient self-discontinued. Escalation case #ESC-0319 opened. Priority: URGENT. Immediate nurse outreach required.

---

### 0e. Multilingual Nudge — Chinese (普通话)

**Context:** Mr Chen Da Ming, 72, cannot read English. Language preference: Simplified Chinese.

---

**[Medi-Nudge]**
陈先生，您好 👋 这是来自您的医疗团队的温馨提醒。

您的 **二甲双胍 500mg**（糖尿病药物）已到了领药时间。请问您最近有去领药吗？

`[✅ 已领取]`  `[❌ 还没领]`  `[❓ 需要帮助]`

---

**Mr Chen:** 已经拿了，谢谢

---

**[Medi-Nudge]**
太好了，陈先生！💊 感谢您告知我们。请继续按时服药，保持血糖稳定。

如有任何问题，请随时回复 `帮助`。

---

> **[System]** Campaign #1044 resolved — Chinese-language patient confirmed collection. No escalation.

---

### 0f. Multilingual Nudge — Malay (Bahasa Melayu)

**Context:** Puan Aishah, 60, hypertension + high cholesterol. Simvastatin overdue 3 days.

---

**[Medi-Nudge]**
Selamat sejahtera Puan Aishah 👋 Ini adalah peringatan mesra daripada pasukan jagaan anda.

Ubat **Simvastatin 20mg** (ubat kolesterol) anda sudah perlu diambil. Adakah anda sudah mengambilnya?

`[✅ Sudah ambil]`  `[❌ Belum]`  `[❓ Perlukan bantuan]`

---

**Puan Aishah:** Belum. Nak tanya boleh makan sama masa dengan ubat darah tinggi?

---

**[Medi-Nudge]**
Soalan yang bagus, Puan Aishah! 👍 Ya, Simvastatin boleh diambil bersama ubat darah tinggi anda. Ia lebih baik dimakan pada waktu malam.

Sila ambil ubat anda hari ini dan hubungi kami jika ada kekeliruan lagi.

`[✅ Faham, akan ambil]`  `[📞 Hubungi saya]`

---

> **[System]** Campaign #1045 — patient had question, auto-answered by LLM. Status → pending confirmation. Follow-up scheduled in 24h.

---



**Context:** Mr Tan, 63, hypertension. System sends a scheduled weekly BP check-in.

---

**[Medi-Nudge]**
Hi Mr Tan 👋 It's your weekly blood pressure check-in.

Please reply with your BP reading in this format:
**SYS/DIA** — e.g. `130/85`

If you haven't taken it yet, reply `SKIP` and we'll remind you tomorrow.

---

**Mr Tan:** 138/88

---

**[Medi-Nudge]**
Thank you, Mr Tan. Your reading today: **138/88 mmHg** — recorded ✅

This is slightly above your target of 135/85. No immediate action needed, but do try to reduce salt intake and rest well.

Your care team can see this reading. See you next week! 💊

---

> **[Care Coordinator Alert — internal]**
> Mr Tan's BP: 138/88. Slightly elevated. No escalation needed. Logged to patient record.

---

## 2. Symptom & Wellbeing Check-in

**Context:** Mdm Lim, 58, diabetes + hypertension. Weekly wellbeing pulse.

---

**[Medi-Nudge]**
Hi Mdm Lim, how are you feeling this week?

`[😊 Good]`  `[😐 Okay]`  `[😔 Not great]`

---

**Mdm Lim:** [taps 😔 Not great]

---

**[Medi-Nudge]**
I'm sorry to hear that, Mdm Lim. Can you tell me a bit more?

`[Feeling tired]`  `[Feeling dizzy]`  `[Pain or discomfort]`  `[Feeling down / sad]`  `[Something else]`

---

**Mdm Lim:** [taps Feeling dizzy]

---

**[Medi-Nudge]**
Thank you for letting us know. Dizziness can sometimes be related to blood pressure medication.

A few quick questions:
1️⃣ How long have you been feeling dizzy? (e.g. "since yesterday", "a few hours")
2️⃣ Does it happen when you stand up quickly?

---

**Mdm Lim:** Since yesterday morning. Yes when I stand up

---

**[Medi-Nudge]**
Noted. This sounds like it could be postural hypotension — a known side effect. Please:
- Stand up slowly from a seated or lying position
- Stay hydrated

I'm flagging this to your care coordinator to follow up with you today. If you feel faint or fall, call **995** immediately.

`[OK, understood]`  `[I need help now]`

---

> **[Care Coordinator Alert — MEDIUM priority]**
> Mdm Lim reports dizziness since yesterday, worse on standing. Possible postural hypotension. Please follow up today.

---

## 3. Structured Side Effect Reporting

**Context:** Mr Rajan, 55, newly started on Metformin. Replies `SIDE EFFECT`.

---

**Mr Rajan:** SIDE EFFECT

---

**[Medi-Nudge]**
Hi Mr Rajan, thank you for letting us know. I'll help you log this.

Which medication do you think is causing the issue?

`[Metformin]`  `[Amlodipine]`  `[Not sure]`

---

**Mr Rajan:** [taps Metformin]

---

**[Medi-Nudge]**
What symptom are you experiencing?

`[Nausea / vomiting]`  `[Diarrhoea]`  `[Stomach pain]`  `[Dizziness]`  `[Rash / itching]`  `[Other]`

---

**Mr Rajan:** [taps Nausea / vomiting]

---

**[Medi-Nudge]**
How severe is the nausea, on a scale of 1–5?
(1 = mild discomfort, 5 = unable to eat or drink)

---

**Mr Rajan:** 3

---

**[Medi-Nudge]**
Understood. Nausea is a common side effect when starting Metformin — it usually improves after 1–2 weeks.

💡 Tips: Take Metformin with food, start with a small meal.

I've logged this for your care team. If it gets worse (score 4–5), please reply `SIDE EFFECT` again or call your clinic.

`[OK, will try that]`  `[It's getting worse]`

---

> **[Side Effect Log]** Mr Rajan | Metformin | Nausea | Severity 3 | Status: Logged, monitoring

---

## 4. Appointment Reminder & Preparation

**Context:** Mdm Fatimah, 67, upcoming polyclinic appointment in 2 days.

---

**[Medi-Nudge]**
Hi Mdm Fatimah, a reminder that you have a polyclinic appointment in **2 days**:

📅 **Wednesday, 1 April 2026**
🕙 **10:00 AM**
📍 **Queenstown Polyclinic**

To prepare:
✅ Bring all your medication bottles or blister packs
✅ Fast for **8 hours** if you have a blood test scheduled
✅ Bring your NRIC or Healthhub app

See you there! Reply `CONFIRM` to acknowledge.

---

**Mdm Fatimah:** CONFIRM

---

**[Medi-Nudge]**
Great, see you Wednesday! 😊

If you need to reschedule, visit HealthHub or call your polyclinic directly.

---

**[Day of appointment — post-visit follow-up, sent 3 hours after scheduled time]**

**[Medi-Nudge]**
Hi Mdm Fatimah, hope your appointment went well today!

Were there any changes to your medications?

`[Yes, new medications]`  `[No changes]`  `[I didn't go — reschedule]`

---

**Mdm Fatimah:** [taps Yes, new medications]

---

**[Medi-Nudge]**
Got it! Please take a photo of your new prescription or medication bag and send it here — our team will update your medication list.

📸 *Send photo now or reply `LATER` to do this another time.*

---

## 5. Refill Coordination

**Context:** Mr Wong, 70, approaching refill due date for Atorvastatin.

---

**[Medi-Nudge]**
Hi Mr Wong 👋 Your **Atorvastatin 20mg** refill is due in **5 days** (est. 4 April).

Do you have enough tablets to last until then?

`[Yes, I'm fine]`  `[Running low — need refill]`  `[Already collected]`

---

**Mr Wong:** [taps Running low — need refill]

---

**[Medi-Nudge]**
No problem! 

To request a refill at your polyclinic, you can:
1️⃣ Book via **HealthHub app** → Appointments → Medication Refill
2️⃣ Call **Queenstown Polyclinic**: 6100 1234

Would you like us to notify your care coordinator to prepare your refill?

`[Yes please]`  `[I'll do it myself]`

---

**Mr Wong:** Yes please

---

**[Medi-Nudge]**
Done! ✅ Your care coordinator has been notified. You'll receive a message when your medications are ready for collection.

---

> **[Care Coordinator Task]** Mr Wong — Atorvastatin refill requested. Prepare for collection. Notify patient when ready.

---

## 6. Lab Result Notification

**Context:** Mdm Chen, 61, HbA1c result just uploaded to system.

---

**[Medi-Nudge]**
Hi Mdm Chen, your latest lab results are in! 🧪

📋 **HbA1c**: 7.6% *(Target: below 7.0%)*
📋 **Fasting Glucose**: 8.2 mmol/L *(Target: 4.0–7.0)*
📋 **Total Cholesterol**: 4.8 mmol/L ✅ *(within range)*

Your HbA1c and glucose are slightly above target. This means your blood sugar has been a little high over the past 2–3 months.

Your doctor will review this at your next appointment on **15 April**. No urgent action needed.

`[What can I do to improve?]`  `[I have a question]`  `[OK, understood]`

---

**Mdm Chen:** What can I do to improve?

---

**[Medi-Nudge]**
Great question! Here are 3 things that can help lower HbA1c:

🥗 **Diet**: Reduce white rice, sugary drinks, and sweet snacks. Try brown rice or replace half your rice with vegetables.

🚶 **Exercise**: A 20-min walk after meals helps lower blood glucose.

💊 **Medication**: Make sure you take your Metformin and Gliclazide every day, even when you feel fine.

Small changes add up. We're cheering you on! 💪

---

## 7. Health Education (Micro-learning)

**Context:** Scheduled Tuesday tip for Mr Kumar, 59, hypertension patient.

---

**[Medi-Nudge]**
💡 **Health Tip Tuesday** — for you, Mr Kumar

**Did you know?** High blood pressure often has no symptoms — that's why it's called the "silent killer".

Taking your Amlodipine daily, even when you feel perfectly fine, protects your heart and brain from damage over time.

🎯 Today's goal: Take your evening tablet with dinner.

Reply `DONE` when you've taken it!

---

**Mr Kumar:** DONE

---

**[Medi-Nudge]**
Well done, Mr Kumar! 🎉 Keep it up — consistent medication is the #1 thing you can do for your heart health.

---

## 8. Lifestyle Nudge

**Context:** Ramadan period — Mr Hafiz, 52, diabetes, currently fasting.

---

**[Medi-Nudge]**
Ramadan Mubarak, Mr Hafiz 🌙

A reminder that **fasting can affect your blood sugar** and how your diabetes medications work.

Important adjustments:
⚠️ **Do not take Metformin at Sahur on an empty stomach** — take it with your Iftar meal instead
⚠️ **Gliclazide dose may need to be halved** — please confirm with your doctor or pharmacist

Experiencing dizziness or sweating during the day? Break your fast immediately and check your sugar.

If you need guidance, reply `HELP` and we'll connect you to your care team.

`[OK, noted]`  `[I have a question]`

---

## 9. Two-Way Conversational Q&A

**Context:** Mrs Ng, 66, messages outside of any scheduled campaign.

---

**Mrs Ng:** Can I take my blood pressure medicine with grapefruit juice?

---

**[Medi-Nudge]**
Great question, Mrs Ng! 🍊

**No — grapefruit juice should be avoided** with your medication **Amlodipine**.

Grapefruit can increase the amount of this drug in your bloodstream, which may cause your blood pressure to drop too low, leading to dizziness or fainting.

Stick to water, plain juice, or other drinks. This applies to grapefruit and pomelo.

Is there anything else you'd like to know?

`[Yes, I have another question]`  `[No, thanks!]`

---

**Mrs Ng:** What if I accidentally took double dose this morning?

---

**[Medi-Nudge]**
Don't panic — one accidental double dose of Amlodipine is usually not dangerous, but you should:

1️⃣ **Skip your next dose** (take the one after that as normal)
2️⃣ **Monitor for symptoms** — dizziness, flushing, faster heartbeat
3️⃣ **Sit or lie down** if you feel lightheaded
4️⃣ **Call 995** if you feel chest pain or faint

I'm flagging this to your care coordinator to check in with you today.

`[OK, I feel fine]`  `[I feel unwell — need help]`

---

> **[Care Coordinator Alert — MEDIUM]** Mrs Ng reports accidental double dose of Amlodipine. Please follow up within 2 hours.

---

## 10. Caregiver Loop

**Context:** Mr Tan's daughter, Sarah, is linked as his caregiver.

---

**[Medi-Nudge → Sarah (caregiver)]**
Hi Sarah, I'm reaching out on behalf of **Mr Tan (your father)**.

He has not confirmed his **Lisinopril** dose for the past **2 days**. He may have forgotten or be unwell.

Could you check in on him when you get a chance? 🙏

`[I'll check on him]`  `[He already took it]`  `[He is unwell — escalate]`

---

**Sarah:** He already took it — I gave it to him this morning

---

**[Medi-Nudge → Sarah]**
Thank you, Sarah! ✅ I've marked it as taken for today.

You're doing a great job looking out for him. 💛

---

> **[Patient Record]** Mr Tan — Lisinopril Day 2 confirmed via caregiver (Sarah). Logged.

---

## 11. Post-Discharge Follow-up

**Context:** Mr Lim, 71, discharged from SGH 1 day ago after a cardiac event. Day 1 check-in.

---

**[Medi-Nudge]**
Hi Mr Lim, welcome home! 🏠

We'll be checking in with you daily for the next 7 days to make sure you're recovering well.

**Day 1 check-in:**

Are you experiencing any of the following?

`[Chest pain]`  `[Breathlessness]`  `[Swollen legs/feet]`  `[Dizziness]`  `[None of these]`

---

**Mr Lim:** [taps None of these]

---

**[Medi-Nudge]**
Glad to hear that! 😊

A reminder to take your **discharge medications** as prescribed — all 4 of them, every day, even if you feel fine. They protect your heart during recovery.

💊 Aspirin · Bisoprolol · Ramipril · Atorvastatin

Reply `DONE` when you've taken today's medications.

---

**Mr Lim:** DONE

---

**[Medi-Nudge]**
Well done, Mr Lim. Rest well and see you tomorrow. 🌟

If anything changes, reply `HELP` at any time.

---

## 12. Mental Health & Motivation Check-in

**Context:** Mdm Wong, 60, has had low adherence for 3 weeks. System triggers a gentler check-in.

---

**[Medi-Nudge]**
Hi Mdm Wong, we noticed you've had a tough few weeks with your medications. That's okay — managing a chronic condition is hard.

How are you feeling in general lately?

`[Fine, just busy]`  `[Feeling tired / unmotivated]`  `[Feeling worried or stressed]`  `[Feeling sad or low]`

---

**Mdm Wong:** [taps Feeling sad or low]

---

**[Medi-Nudge]**
Thank you for sharing that with us, Mdm Wong. 💛

Feeling low is very common for people managing long-term health conditions — you are not alone.

I'd like to connect you with someone who can help. Your care coordinator will reach out to you today for a private chat.

In the meantime, if you need to talk to someone now:
📞 **Samaritans of Singapore (SOS)**: 1767 (24/7)

`[OK, please connect me]`  `[I'm ok, don't need to]`

---

> **[Care Coordinator Alert — HIGH]** Mdm Wong reports feeling sad/low. Low adherence for 3 weeks. Possible depression screening needed. Assign social worker or counsellor.

---

## 13. Vaccination Reminder

**Context:** Mr Ahmad, 64, diabetic. Annual flu season reminder.

---

**[Medi-Nudge]**
Hi Mr Ahmad, flu season is here 🍂

As someone with **diabetes**, you are at higher risk of serious complications from the flu. A flu vaccine is **strongly recommended** and **subsidised** for you under the National Adult Immunisation Schedule.

📍 You can get it at your nearest polyclinic — no appointment needed.

Have you had your flu jab this year?

`[Yes, already done ✅]`  `[Not yet — where can I go?]`  `[I don't want it]`

---

**Mr Ahmad:** Not yet — where can I go?

---

**[Medi-Nudge]**
Here are the polyclinics nearest to your registered address (Jurong West):

🏥 **Jurong Polyclinic** — 190 Jurong East Ave 1
🏥 **Bukit Batok Polyclinic** — 50 Bukit Batok West Ave 3
🏥 **Pioneer Polyclinic** — 1 stars Ave 4

Walk in during opening hours. Bring your NRIC. The vaccine costs **$0–$7** depending on your subsidy tier.

Let us know when you've done it! `[Done — I got vaccinated]`

---

## 14. Polypharmacy Safety Check

**Context:** System detects a new prescription for Ibuprofen added to Mdm Koh's record, who is already on Lisinopril.

---

**[Medi-Nudge]**
Hi Mdm Koh, we noticed a new medication — **Ibuprofen** — has been added to your record.

⚠️ **Important heads-up**: Ibuprofen (a painkiller) can **reduce the effectiveness** of your blood pressure medication **Lisinopril**, and may raise your blood pressure if taken regularly.

Please let your prescribing doctor know that you are on Lisinopril, if they don't already.

For mild pain, **Paracetamol** is a safer alternative. Ask your pharmacist about this.

Was Ibuprofen prescribed by your usual clinic?

`[Yes, my doctor knows]`  `[I bought it myself]`  `[I have a question]`

---

**Mdm Koh:** I bought it myself

---

**[Medi-Nudge]**
Thank you for letting us know. For your safety, please avoid taking Ibuprofen regularly with your current medications.

✅ **Safe alternative**: Paracetamol (up to 4 tablets of 500mg per day)

I've flagged this for your care team to review at your next visit. Is the pain under control?

`[Yes, it's ok]`  `[No, still in pain — need help]`

---

## 15. Preference & Consent Management

**Context:** Mdm Tan wants to change her contact hours.

---

**Mdm Tan:** Can you stop messaging me in the morning? I work night shift

---

**[Medi-Nudge]**
Of course, Mdm Tan! Let me update your preferences.

What is the best time to reach you?

`[12pm – 3pm]`  `[3pm – 6pm]`  `[6pm – 9pm]`  `[Custom time]`

---

**Mdm Tan:** [taps 3pm – 6pm]

---

**[Medi-Nudge]**
Done! ✅ We'll only contact you between **3:00 PM – 6:00 PM** from now on.

You can change this anytime by replying `SETTINGS`.

Is there anything else you'd like to update?

`[Change language]`  `[Update caregiver contact]`  `[Opt out of messages]`  `[No, I'm good]`

---

> **System note:** Patient quiet hours updated to 15:00–18:00. Scheduler will respect new window for all outbound messages.

---

## Legend

| Tag | Meaning |
|---|---|
| `[Button]` | WhatsApp quick-reply button |
| **[Medi-Nudge]** | Outbound system message |
| **[Care Coordinator Alert]** | Internal notification, not seen by patient |
| **[Side Effect Log]** | Internal structured record |
| `SIDE EFFECT`, `HELP`, `DONE` | Keyword triggers parsed by the system |
