"""Create patient, caregiver, and nurse user accounts for demo."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import User, Patient

DEMO_PASSWORD = "Demo1234!"

ACCOUNTS = [
    # Nurse/Doctor accounts (web portal)
    {"email": "nurse.sarah@sgh.com.sg", "full_name": "Sarah Tan (Nurse)", "role": "admin"},
    {"email": "dr.lim@sgh.com.sg", "full_name": "Dr. Lim Wei Ming", "role": "admin"},

    # Patient accounts (iOS app) — linked by phone_number lookup
    {"email": "tanweiliang@patient.medinudge.sg", "full_name": "Tan Wei Liang", "role": "patient", "phone": "+6591234001"},
    {"email": "limahkow@patient.medinudge.sg", "full_name": "Lim Ah Kow", "role": "patient", "phone": "+6591234002"},
    {"email": "sitirahimah@patient.medinudge.sg", "full_name": "Siti Rahimah", "role": "patient", "phone": "+6591234003"},
    {"email": "rajan@patient.medinudge.sg", "full_name": "Rajan Krishnamurthy", "role": "patient", "phone": "+6591234004"},
    {"email": "chenmeifong@patient.medinudge.sg", "full_name": "Chen Mei Fong", "role": "patient", "phone": "+6591234005"},

    # Caregiver accounts (iOS app) — linked to same patient as their patient
    {"email": "tanmeiling@caregiver.medinudge.sg", "full_name": "Tan Mei Ling", "role": "caregiver", "phone": "+6591234001"},
    {"email": "ahmadrahimi@caregiver.medinudge.sg", "full_name": "Ahmad Rahimi", "role": "caregiver", "phone": "+6591234003"},
    {"email": "priyarajan@caregiver.medinudge.sg", "full_name": "Priya Rajan", "role": "caregiver", "phone": "+6591234004"},
]


def seed():
    db = SessionLocal()
    try:
        created = 0
        for acct in ACCOUNTS:
            existing = db.query(User).filter(User.email == acct["email"]).first()
            if existing:
                continue

            patient_id = None
            if acct.get("phone"):
                patient = db.query(Patient).filter(Patient.phone_number == acct["phone"]).first()
                if patient:
                    patient_id = patient.id
                else:
                    print(f"  WARNING: Patient with phone {acct['phone']} not found for {acct['email']}")

            user = User(
                email=acct["email"],
                full_name=acct["full_name"],
                hashed_password=hash_password(DEMO_PASSWORD),
                role=acct["role"],
                patient_id=patient_id,
            )
            db.add(user)
            created += 1

        db.commit()
        print(f"Created {created} user accounts (password for all: {DEMO_PASSWORD})")
        print("\nAccounts:")
        for acct in ACCOUNTS:
            print(f"  {acct['role']:10} | {acct['email']:45} | {acct['full_name']}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
