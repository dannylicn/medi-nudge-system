"""
Mark critical medications and add Warfarin if not present.
Run after the is_critical migration.
"""
from app.core.database import SessionLocal
from app.models.models import Medication, PatientMedication, Patient, DoseLog
from datetime import datetime, timedelta
import random

CRITICAL_GENERICS = ["Gliclazide", "Warfarin"]


def run():
    db = SessionLocal()
    try:
        # Add Warfarin if not present
        warfarin = db.query(Medication).filter(Medication.generic_name == "Warfarin").first()
        if not warfarin:
            warfarin = Medication(
                name="Warfarin 5mg",
                generic_name="Warfarin",
                category="Anticoagulant",
                default_refill_days=30,
                is_critical=True,
            )
            db.add(warfarin)
            db.commit()
            db.refresh(warfarin)
            print(f"Created Warfarin (id={warfarin.id})")

            # Assign to Siti Nurhaliza (worst adherence, best demo story)
            siti = db.query(Patient).filter(Patient.full_name == "Siti Nurhaliza").first()
            if siti:
                pm = PatientMedication(
                    patient_id=siti.id,
                    medication_id=warfarin.id,
                    dosage="5mg once daily",
                    frequency="once_daily",
                    reminder_times=["08:00"],
                    is_active=True,
                )
                db.add(pm)
                db.commit()
                db.refresh(pm)
                print(f"Assigned Warfarin to Siti Nurhaliza (pm_id={pm.id})")

                # Seed 30 days of dose history for Warfarin (~35% adherence)
                now = datetime.utcnow()
                logs = []
                for day_offset in range(30, 0, -1):
                    day = now - timedelta(days=day_offset)
                    logged_at = day.replace(hour=8, minute=0, second=0, microsecond=0)
                    taken = random.random() < 0.35
                    logs.append(DoseLog(
                        patient_id=siti.id,
                        medication_id=warfarin.id,
                        patient_medication_id=pm.id,
                        status="taken" if taken else "missed",
                        source="seed_script" if not taken else "patient_reply",
                        logged_at=logged_at,
                    ))
                db.add_all(logs)
                db.commit()
                taken_count = sum(1 for l in logs if l.status == "taken")
                print(f"Seeded {len(logs)} Warfarin dose logs ({taken_count} taken, {len(logs)-taken_count} missed)")
        else:
            print(f"Warfarin already exists (id={warfarin.id})")

        # Mark critical meds
        for generic in CRITICAL_GENERICS:
            med = db.query(Medication).filter(Medication.generic_name == generic).first()
            if med:
                med.is_critical = True
                print(f"Marked {med.name} (generic={generic}) as critical")
        db.commit()

        # Show all meds with critical status
        all_meds = db.query(Medication).all()
        for m in all_meds:
            print(f"  {m.name}: is_critical={m.is_critical}")

    finally:
        db.close()


if __name__ == "__main__":
    run()
