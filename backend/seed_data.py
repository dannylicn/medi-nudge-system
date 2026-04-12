"""Seed the database with common chronic-disease medications for Singapore."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, engine, Base
from app.models.models import Medication, Condition, ConditionMedication

MEDICATIONS = [
    # Diabetes
    ("Metformin", "Metformin", "Diabetes", 30),
    ("Glucophage XR", "Metformin XR", "Diabetes", 30),
    ("Gliclazide MR", "Gliclazide", "Diabetes", 30),
    ("Jardiance", "Empagliflozin", "Diabetes", 30),
    ("Forxiga", "Dapagliflozin", "Diabetes", 30),
    ("Januvia", "Sitagliptin", "Diabetes", 30),
    ("Amaryl", "Glimepiride", "Diabetes", 30),
    ("Lantus", "Insulin Glargine", "Diabetes", 30),
    ("NovoRapid", "Insulin Aspart", "Diabetes", 30),
    # Hypertension
    ("Amlodipine", "Amlodipine", "Hypertension", 30),
    ("Norvasc", "Amlodipine Besylate", "Hypertension", 30),
    ("Losartan", "Losartan", "Hypertension", 30),
    ("Cozaar", "Losartan Potassium", "Hypertension", 30),
    ("Lisinopril", "Lisinopril", "Hypertension", 30),
    ("Atenolol", "Atenolol", "Hypertension", 30),
    ("Bisoprolol", "Bisoprolol", "Hypertension", 30),
    ("Hydrochlorothiazide", "Hydrochlorothiazide", "Hypertension", 30),
    ("Nifedipine LA", "Nifedipine", "Hypertension", 30),
    # Hyperlipidaemia
    ("Lipitor", "Atorvastatin", "Hyperlipidaemia", 30),
    ("Crestor", "Rosuvastatin", "Hyperlipidaemia", 30),
    ("Zocor", "Simvastatin", "Hyperlipidaemia", 30),
    ("Fenofibrate", "Fenofibrate", "Hyperlipidaemia", 30),
    ("Ezetimibe", "Ezetimibe", "Hyperlipidaemia", 30),
    # Cardiovascular / Anticoagulants
    ("Aspirin", "Acetylsalicylic Acid", "Cardiovascular", 30),
    ("Plavix", "Clopidogrel", "Cardiovascular", 30),
    ("Eliquis", "Apixaban", "Anticoagulant", 30),
    ("Xarelto", "Rivaroxaban", "Anticoagulant", 30),
    ("Warfarin", "Warfarin", "Anticoagulant", 30),
    # Respiratory / Asthma / COPD
    ("Ventolin", "Salbutamol", "Respiratory", 30),
    ("Symbicort", "Budesonide/Formoterol", "Respiratory", 30),
    ("Seretide", "Fluticasone/Salmeterol", "Respiratory", 60),
    ("Spiriva", "Tiotropium", "Respiratory", 30),
    ("Montelukast", "Montelukast", "Respiratory", 30),
    # Thyroid
    ("Eltroxin", "Levothyroxine", "Thyroid", 30),
    # Mental health
    ("Escitalopram", "Escitalopram", "Mental Health", 30),
    ("Sertraline", "Sertraline", "Mental Health", 30),
    # Gout
    ("Allopurinol", "Allopurinol", "Gout", 30),
    ("Colchicine", "Colchicine", "Gout", 30),
    # Osteoporosis
    ("Alendronate", "Alendronate", "Osteoporosis", 30),
    # GI / Acid reflux
    ("Omeprazole", "Omeprazole", "Gastrointestinal", 30),
    ("Pantoprazole", "Pantoprazole", "Gastrointestinal", 30),
]

# Condition name → list of generic_names of related medications
CONDITION_MEDICATIONS = {
    "Diabetes Mellitus Type 2": [
        "Metformin", "Metformin XR", "Gliclazide", "Empagliflozin",
        "Dapagliflozin", "Sitagliptin", "Glimepiride",
        "Insulin Glargine", "Insulin Aspart",
    ],
    "Diabetes Mellitus Type 1": [
        "Insulin Glargine", "Insulin Aspart", "Metformin",
    ],
    "Hypertension": [
        "Amlodipine", "Amlodipine Besylate", "Losartan", "Losartan Potassium",
        "Lisinopril", "Atenolol", "Bisoprolol", "Hydrochlorothiazide", "Nifedipine",
    ],
    "Hyperlipidaemia": [
        "Atorvastatin", "Rosuvastatin", "Simvastatin", "Fenofibrate", "Ezetimibe",
    ],
    "Coronary Artery Disease": [
        "Acetylsalicylic Acid", "Clopidogrel", "Atorvastatin", "Rosuvastatin",
        "Bisoprolol", "Atenolol", "Amlodipine",
    ],
    "Heart Failure": [
        "Bisoprolol", "Lisinopril", "Losartan", "Losartan Potassium",
        "Empagliflozin", "Dapagliflozin", "Hydrochlorothiazide",
    ],
    "Atrial Fibrillation": [
        "Apixaban", "Rivaroxaban", "Warfarin", "Bisoprolol", "Atenolol",
    ],
    "Stroke": [
        "Acetylsalicylic Acid", "Clopidogrel", "Apixaban", "Rivaroxaban",
        "Warfarin", "Atorvastatin", "Rosuvastatin",
    ],
    "Chronic Kidney Disease": [
        "Losartan", "Losartan Potassium", "Lisinopril", "Amlodipine",
    ],
    "Asthma": [
        "Salbutamol", "Budesonide/Formoterol", "Fluticasone/Salmeterol", "Montelukast",
    ],
    "COPD": [
        "Salbutamol", "Tiotropium", "Budesonide/Formoterol", "Fluticasone/Salmeterol",
    ],
    "Osteoarthritis": [],
    "Osteoporosis": ["Alendronate"],
    "Gout": ["Allopurinol", "Colchicine"],
    "Hypothyroidism": ["Levothyroxine"],
    "Hyperthyroidism": [],
    "Depression": ["Escitalopram", "Sertraline"],
    "Anxiety Disorder": ["Escitalopram", "Sertraline"],
    "Dementia": [],
    "Obesity": ["Metformin"],
    "GERD": ["Omeprazole", "Pantoprazole"],
    "Fatty Liver Disease": [],
    "Chronic Hepatitis B": [],
    "Anaemia": [],
    "Benign Prostatic Hyperplasia": [],
    "Glaucoma": [],
    "Epilepsy": [],
    "Parkinson's Disease": [],
    "Rheumatoid Arthritis": [],
    "Psoriasis": [],
}


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added_meds = 0
    added_conds = 0
    added_maps = 0
    try:
        # Seed medications
        for name, generic, category, refill in MEDICATIONS:
            exists = db.query(Medication).filter(Medication.generic_name == generic).first()
            if not exists:
                db.add(Medication(name=name, generic_name=generic, category=category, default_refill_days=refill))
                added_meds += 1
        db.commit()

        # Seed conditions and mappings
        for cond_name, med_generics in CONDITION_MEDICATIONS.items():
            cond = db.query(Condition).filter(Condition.name == cond_name).first()
            if not cond:
                cond = Condition(name=cond_name)
                db.add(cond)
                db.commit()
                db.refresh(cond)
                added_conds += 1
            for generic in med_generics:
                med = db.query(Medication).filter(Medication.generic_name == generic).first()
                if not med:
                    continue
                exists = db.query(ConditionMedication).filter(
                    ConditionMedication.condition_id == cond.id,
                    ConditionMedication.medication_id == med.id,
                ).first()
                if not exists:
                    db.add(ConditionMedication(condition_id=cond.id, medication_id=med.id))
                    added_maps += 1
        db.commit()
        print(f"Seeded {added_meds} medications, {added_conds} conditions, {added_maps} mappings")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
