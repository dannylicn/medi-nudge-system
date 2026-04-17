"""Seed demo patients, medications assignments, and dose logs for staging."""
import sys, os, random
from datetime import datetime, timedelta, UTC

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, engine, Base
from app.core.config import hash_sha256
from app.models.models import (
    Patient, Medication, PatientMedication, DoseLog, User,
    NudgeCampaign, Escalation,
)
from app.core.security import get_password_hash

PATIENTS = [
    dict(full_name="Tan Wei Liang", phone_number="+6591234001", nric="S7012345A",
         language_preference="en", risk_level="high", conditions=["Hypertension", "Diabetes Mellitus Type 2"],
         onboarding_state="complete", is_active=True, caregiver_name="Tan Mei Ling", caregiver_phone_number="+6598765001"),
    dict(full_name="Lim Ah Kow", phone_number="+6591234002", nric="S6523456B",
         language_preference="en", risk_level="normal", conditions=["Hypertension", "Hyperlipidaemia"],
         onboarding_state="complete", is_active=True, caregiver_name=None, caregiver_phone_number=None),
    dict(full_name="Siti Rahimah", phone_number="+6591234003", nric="S8034567C",
         language_preference="ms", risk_level="low", conditions=["Diabetes Mellitus Type 2"],
         onboarding_state="complete", is_active=True, caregiver_name="Ahmad Rahimi", caregiver_phone_number="+6598765003"),
    dict(full_name="Rajan Krishnamurthy", phone_number="+6591234004", nric="S7545678D",
         language_preference="en", risk_level="high", conditions=["Coronary Artery Disease", "Hypertension", "Hyperlipidaemia"],
         onboarding_state="complete", is_active=True, caregiver_name="Priya Rajan", caregiver_phone_number="+6598765004"),
    dict(full_name="Chen Mei Fong", phone_number="+6591234005", nric="S8056789E",
         language_preference="zh", risk_level="normal", conditions=["Hypothyroidism", "Hypertension"],
         onboarding_state="complete", is_active=True, caregiver_name=None, caregiver_phone_number=None),
    dict(full_name="Ahmad Zulkifli", phone_number="+6591234006", nric="S6567890F",
         language_preference="ms", risk_level="high", conditions=["Heart Failure", "Hypertension"],
         onboarding_state="complete", is_active=True, caregiver_name="Fatimah Zulkifli", caregiver_phone_number="+6598765006"),
    dict(full_name="Wong Beng Huat", phone_number="+6591234007", nric="S7078901G",
         language_preference="zh", risk_level="low", conditions=["Hyperlipidaemia", "GERD"],
         onboarding_state="complete", is_active=True, caregiver_name=None, caregiver_phone_number=None),
    dict(full_name="Kavitha Subramaniam", phone_number="+6591234008", nric="S8089012H",
         language_preference="en", risk_level="normal", conditions=["Asthma", "Anxiety Disorder"],
         onboarding_state="complete", is_active=True, caregiver_name=None, caregiver_phone_number=None),
    dict(full_name="Lee Chong Meng", phone_number="+6591234009", nric="S6590123I",
         language_preference="zh", risk_level="high", conditions=["Diabetes Mellitus Type 2", "Chronic Kidney Disease"],
         onboarding_state="complete", is_active=True, caregiver_name="Lee Sok Hua", caregiver_phone_number="+6598765009"),
    dict(full_name="Nurul Huda Binte Ismail", phone_number="+6591234010", nric="S9001234J",
         language_preference="ms", risk_level="low", conditions=["Hypertension"],
         onboarding_state="complete", is_active=True, caregiver_name=None, caregiver_phone_number=None),
]

# condition name → preferred medication generic names
CONDITION_MED_MAP = {
    "Hypertension":               ["Amlodipine", "Losartan", "Bisoprolol"],
    "Diabetes Mellitus Type 2":   ["Metformin", "Empagliflozin", "Gliclazide"],
    "Hyperlipidaemia":            ["Atorvastatin", "Rosuvastatin"],
    "Coronary Artery Disease":    ["Acetylsalicylic Acid", "Clopidogrel", "Atorvastatin", "Bisoprolol"],
    "Heart Failure":              ["Bisoprolol", "Lisinopril", "Empagliflozin"],
    "Hypothyroidism":             ["Levothyroxine"],
    "Asthma":                     ["Salbutamol", "Budesonide/Formoterol"],
    "Anxiety Disorder":           ["Escitalopram"],
    "Chronic Kidney Disease":     ["Losartan", "Amlodipine"],
    "GERD":                       ["Omeprazole"],
}

FREQUENCIES = ["once_daily", "twice_daily", "once_daily", "once_daily"]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ── Care coordinator user ─────────────────────────────────────────
        if not db.query(User).filter(User.email == "coordinator@medi-nudge.demo").first():
            db.add(User(
                email="coordinator@medi-nudge.demo",
                hashed_password=get_password_hash("Demo1234!"),
                full_name="Demo Coordinator",
            ))
            db.commit()
            print("Created coordinator: coordinator@medi-nudge.demo / Demo1234!")

        # ── Patients ──────────────────────────────────────────────────────
        now = datetime.now(UTC).replace(tzinfo=None)
        created_patients = []

        for pd in PATIENTS:
            existing = db.query(Patient).filter(Patient.phone_number == pd["phone_number"]).first()
            if existing:
                created_patients.append(existing)
                continue

            p = Patient(
                full_name=pd["full_name"],
                phone_number=pd["phone_number"],
                nric_hash=hash_sha256(pd["nric"]),
                language_preference=pd["language_preference"],
                risk_level=pd["risk_level"],
                conditions=pd["conditions"],
                onboarding_state=pd["onboarding_state"],
                is_active=pd["is_active"],
                caregiver_name=pd.get("caregiver_name"),
                caregiver_phone_number=pd.get("caregiver_phone_number"),
                consent_obtained_at=now - timedelta(days=random.randint(10, 60)),
            )
            db.add(p)
            db.commit()
            db.refresh(p)
            created_patients.append(p)

        print(f"Patients ready: {len(created_patients)}")

        # ── Assign medications ────────────────────────────────────────────
        pm_count = 0
        for p, pd in zip(created_patients, PATIENTS):
            assigned_generics = set()
            for cond in pd["conditions"]:
                for generic in CONDITION_MED_MAP.get(cond, []):
                    if generic in assigned_generics:
                        continue
                    med = db.query(Medication).filter(Medication.generic_name == generic).first()
                    if not med:
                        continue
                    exists = db.query(PatientMedication).filter(
                        PatientMedication.patient_id == p.id,
                        PatientMedication.medication_id == med.id,
                    ).first()
                    if not exists:
                        freq = random.choice(FREQUENCIES)
                        times = ["08:00"] if freq == "once_daily" else ["08:00", "20:00"]
                        pm = PatientMedication(
                            patient_id=p.id,
                            medication_id=med.id,
                            dosage=f"{random.choice([5,10,25,50,100,500])}mg",
                            frequency=freq,
                            reminder_times=times,
                            refill_interval_days=30,
                            start_date=(now - timedelta(days=random.randint(30, 180))).date(),
                            is_active=True,
                            last_reminded_at=now - timedelta(hours=random.randint(1, 48)),
                        )
                        db.add(pm)
                        pm_count += 1
                    assigned_generics.add(generic)
        db.commit()
        print(f"Patient medications assigned: {pm_count}")

        # ── Dose logs (90 days history) ───────────────────────────────────
        dose_count = 0
        all_pms = db.query(PatientMedication).all()
        for pm in all_pms:
            daily = 2 if pm.frequency == "twice_daily" else 1
            for day_offset in range(90, 0, -1):
                day = now - timedelta(days=day_offset)
                # High-risk patients miss more doses
                adherence_rate = 0.65 if pm.patient.risk_level == "high" else (
                    0.80 if pm.patient.risk_level == "normal" else 0.92
                )
                for dose_num in range(daily):
                    hour = 8 if dose_num == 0 else 20
                    scheduled = day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    taken = random.random() < adherence_rate
                    existing = db.query(DoseLog).filter(
                        DoseLog.patient_medication_id == pm.id,
                        DoseLog.scheduled_at == scheduled,
                    ).first()
                    if not existing:
                        db.add(DoseLog(
                            patient_id=pm.patient_id,
                            patient_medication_id=pm.id,
                            status="taken" if taken else "missed",
                            scheduled_at=scheduled,
                            logged_at=scheduled + timedelta(minutes=random.randint(0, 30)) if taken else None,
                        ))
                        dose_count += 1
                        if pm.patient.last_taken_at is None and taken:
                            pm.patient.last_taken_at = scheduled
        db.commit()
        print(f"Dose logs created: {dose_count}")

        # ── Escalations for high-risk patients ───────────────────────────
        esc_count = 0
        for p in created_patients:
            if p.risk_level == "high":
                if not db.query(Escalation).filter(Escalation.patient_id == p.id).first():
                    db.add(Escalation(
                        patient_id=p.id,
                        reason="Consecutive missed doses — high risk patient",
                        status="open",
                        priority="urgent",
                        created_at=now - timedelta(days=random.randint(1, 5)),
                    ))
                    esc_count += 1
        db.commit()
        print(f"Escalations created: {esc_count}")

        print("\nDone! Login: coordinator@medi-nudge.demo / Demo1234!")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
