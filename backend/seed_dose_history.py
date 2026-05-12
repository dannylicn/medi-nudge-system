"""
Seed 30 days of backdated dose history for demo patients.
Run: python seed_dose_history.py

Idempotent — clears existing seeded DoseLog and DispensingRecord entries before inserting.
Also updates patients' onboarding_state to "complete" so they appear in dashboard analytics.
"""
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.models.models import (
    Patient, PatientMedication, Medication, DoseLog, DispensingRecord,
)

SGT = ZoneInfo("Asia/Singapore")
SEED_SOURCE = "seed_script"
DAYS = 30

PATIENT_PROFILES = {
    "Tan Ah Kow": {
        "overall_rate": 0.40,
        "weekday_penalty": 0.25,
        "weekend_rate": 0.65,
        "per_med_override": {"Metformin": 0.30},
    },
    "Lim Mei Hua": {
        "overall_rate": 0.92,
        "weekday_penalty": 0.0,
        "weekend_rate": 0.92,
        "per_med_override": {},
    },
    "Ahmad bin Hassan": {
        "overall_rate": 0.70,
        "weekday_penalty": 0.0,
        "weekend_rate": 0.60,
        "per_med_override": {},
    },
    "Siti Nurhaliza": {
        "overall_rate": 0.35,
        "weekday_penalty": 0.0,
        "weekend_rate": 0.35,
        "per_med_override": {},
    },
    "Raj Kumar": {
        "overall_rate": 0.88,
        "weekday_penalty": 0.0,
        "weekend_rate": 0.88,
        "per_med_override": {},
    },
}


def should_take(profile: dict, med_generic: str, day: datetime) -> bool:
    is_weekend = day.weekday() >= 5
    base_rate = profile.get("per_med_override", {}).get(
        med_generic, profile["weekend_rate" if is_weekend else "overall_rate"]
    )
    if not is_weekend and profile.get("weekday_penalty"):
        base_rate = max(0, base_rate - profile["weekday_penalty"])
    return random.random() < base_rate


def run():
    db = SessionLocal()
    try:
        now_utc = datetime.utcnow()
        patients = db.query(Patient).filter(Patient.full_name.in_(PATIENT_PROFILES.keys())).all()

        if not patients:
            print("No demo patients found. Run the API seed first.")
            return

        # Clear previous seed data
        db.query(DoseLog).filter(DoseLog.source == SEED_SOURCE).delete()
        db.query(DispensingRecord).filter(DispensingRecord.source == SEED_SOURCE).delete()
        db.commit()
        print(f"Cleared existing seed data.")

        dose_logs = []
        dispensing_records = []

        for patient in patients:
            profile = PATIENT_PROFILES[patient.full_name]
            patient_meds = (
                db.query(PatientMedication)
                .filter(PatientMedication.patient_id == patient.id, PatientMedication.is_active == True)
                .all()
            )

            if not patient_meds:
                print(f"  {patient.full_name}: no medications assigned, skipping")
                continue

            # Update onboarding state so dashboard includes this patient
            patient.onboarding_state = "complete"

            for pm in patient_meds:
                med = db.query(Medication).filter(Medication.id == pm.medication_id).first()
                if not med:
                    continue

                reminder_times = pm.reminder_times or ["08:00"]

                # Seed dispensing record (30 days ago)
                dispensing_records.append(DispensingRecord(
                    patient_id=patient.id,
                    medication_id=med.id,
                    dispensed_at=now_utc - timedelta(days=DAYS),
                    days_supply=DAYS,
                    quantity=DAYS * len(reminder_times),
                    source=SEED_SOURCE,
                ))

                # Generate dose logs for each day and reminder time
                for day_offset in range(DAYS, 0, -1):
                    day_date = now_utc - timedelta(days=day_offset)

                    for time_str in reminder_times:
                        hour, minute = map(int, time_str.split(":"))
                        logged_at = day_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                        taken = should_take(profile, med.generic_name, day_date)

                        # For Siti: add timing irregularity (self-adjustment pattern)
                        if patient.full_name == "Siti Nurhaliza" and taken:
                            offset_minutes = random.choice([-120, -60, 0, 60, 120, 180, 240])
                            logged_at = logged_at + timedelta(minutes=offset_minutes)

                        dose_logs.append(DoseLog(
                            patient_id=patient.id,
                            medication_id=med.id,
                            patient_medication_id=pm.id,
                            status="taken" if taken else "missed",
                            source=SEED_SOURCE if not taken else "patient_reply",
                            logged_at=logged_at,
                        ))

            taken_count = sum(1 for d in dose_logs if d.patient_id == patient.id and d.status == "taken")
            total_count = sum(1 for d in dose_logs if d.patient_id == patient.id)
            rate = round(taken_count / total_count * 100, 1) if total_count else 0
            print(f"  {patient.full_name}: {total_count} doses, {taken_count} taken ({rate}%)")

        db.add_all(dose_logs)
        db.add_all(dispensing_records)
        db.commit()

        print(f"\nSeeded {len(dose_logs)} dose logs and {len(dispensing_records)} dispensing records.")
        print("Updated patient onboarding states to 'complete'.")

    finally:
        db.close()


if __name__ == "__main__":
    run()
