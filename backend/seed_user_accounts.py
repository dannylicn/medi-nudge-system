"""Create patient, caregiver, and nurse user accounts for demo."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import CaregiverPatientLink, User, Patient

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

CAREGIVER_LINKS = [
    {
        "caregiver_email": "tanmeiling@caregiver.medinudge.sg",
        "patient_name": "Tan Wei Liang",
        "relationship": "father",
    },
    {
        "caregiver_email": "tanmeiling@caregiver.medinudge.sg",
        "patient_name": "Chen Mei Fong",
        "relationship": "mother",
    },
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


def seed_caregiver_links():
    """Seed demo caregiver-to-patient relationships without hardcoded patient IDs."""
    db = SessionLocal()
    try:
        created = 0
        for link in CAREGIVER_LINKS:
            caregiver = db.query(User).filter(User.email == link["caregiver_email"]).first()
            if not caregiver:
                print(f"  WARNING: Caregiver user {link['caregiver_email']} not found, skipping link")
                continue

            patient = db.query(Patient).filter(Patient.full_name == link["patient_name"]).first()
            if not patient:
                print(f"  WARNING: Patient {link['patient_name']} not found, skipping link")
                continue

            existing = (
                db.query(CaregiverPatientLink)
                .filter(
                    CaregiverPatientLink.caregiver_user_id == caregiver.id,
                    CaregiverPatientLink.patient_id == patient.id,
                )
                .first()
            )
            if existing:
                if existing.link_relationship != link["relationship"]:
                    existing.link_relationship = link["relationship"]
                continue

            db.add(
                CaregiverPatientLink(
                    caregiver_user_id=caregiver.id,
                    patient_id=patient.id,
                    link_relationship=link["relationship"],
                )
            )
            created += 1

        db.commit()
        print(f"  Seeded {created} caregiver-patient links")
    finally:
        db.close()


def seed_demo_notes():
    """Seed realistic caregiver notes for Tan Wei Liang (demo patient)."""
    from app.models.models import CaregiverNote
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        tan = db.query(Patient).filter(Patient.full_name == "Tan Wei Liang").first()
        if not tan:
            print("  Tan Wei Liang not found, skipping demo notes")
            return

        existing = db.query(CaregiverNote).filter(CaregiverNote.patient_id == tan.id).count()
        if existing:
            print(f"  Demo notes already exist ({existing}), skipping")
            return

        now = datetime.utcnow()
        notes = [
            CaregiverNote(
                patient_id=tan.id,
                author_name="Tan Mei Ling",
                author_role="caregiver",
                category="behavior",
                content="Mum seemed confused about which pills to take after lunch. Had to remind her twice.",
                created_at=now - timedelta(days=2, hours=3),
            ),
            CaregiverNote(
                patient_id=tan.id,
                author_name="Tan Mei Ling",
                author_role="caregiver",
                category="side_effect",
                content="She said the new medication makes her dizzy in the morning. Lasted about 30 minutes.",
                created_at=now - timedelta(days=1, hours=8),
            ),
            CaregiverNote(
                patient_id=tan.id,
                author_name="Tan Mei Ling",
                author_role="caregiver",
                category="missed_dose",
                content="Checked the pillbox, she missed her afternoon Warfarin again. Says she forgot.",
                created_at=now - timedelta(hours=5),
            ),
            CaregiverNote(
                patient_id=tan.id,
                author_name="Sarah Tan (Nurse)",
                author_role="admin",
                category="general",
                content="Called patient — caregiver confirms patient has been skipping Warfarin on weekends. Will schedule home visit.",
                created_at=now - timedelta(hours=2),
            ),
        ]
        db.add_all(notes)
        db.commit()
        print(f"  Seeded {len(notes)} demo caregiver notes for Tan Wei Liang")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    seed_caregiver_links()
    seed_demo_notes()
