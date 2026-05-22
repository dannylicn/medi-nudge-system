"""Populate missed_dose_info for the 16 medications used by demo patients."""
from app.core.database import SessionLocal
from app.models.models import Medication

MISSED_DOSE_INFO = {
    # Diabetes
    "Metformin": (
        "Missing a dose may cause your blood sugar to stay higher than it should. "
        "If missed, take it as soon as you remember with food. Do not double your dose."
    ),
    "Metformin XR": (
        "Missing a dose may cause your blood sugar to stay higher than it should. "
        "If missed, take it as soon as you remember with food. Do not double your dose."
    ),
    "Gliclazide": (
        "Missing a dose may cause your blood sugar to stay too high. "
        "If missed, skip it and take your next dose before your next meal as usual. Do not double your dose."
    ),
    "Empagliflozin": (
        "Missing a dose may cause your blood sugar to stay too high. "
        "If missed and more than 12 hours until your next dose, take it now. Otherwise skip it. Do not double up."
    ),
    "Dapagliflozin": (
        "Missing a dose may cause your blood sugar to stay too high. "
        "If missed and more than 12 hours until your next dose, take it now. Otherwise skip it. Do not double up."
    ),
    "Sitagliptin": (
        "Missing a dose may cause your blood sugar to stay higher than it should. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Glimepiride": (
        "Missing a dose may cause your blood sugar to stay too high. "
        "If missed, skip it and take your next dose before your next meal. Do not double your dose."
    ),
    "Insulin Glargine": (
        "Missing a dose may cause your blood sugar to rise dangerously high. "
        "If missed, contact your doctor or nurse for advice on when to take your next dose. Do not double up."
    ),
    "Insulin Aspart": (
        "Missing a dose may cause your blood sugar to spike after meals. "
        "If missed, check your blood sugar and contact your doctor for advice. Do not inject a double dose."
    ),
    # Hypertension
    "Amlodipine": (
        "Missing a dose may cause your blood pressure to rise. "
        "If missed, take it as soon as you remember. Do not take two doses to make up for it."
    ),
    "Amlodipine Besylate": (
        "Missing a dose may cause your blood pressure to rise. "
        "If missed, take it as soon as you remember. Do not take two doses to make up for it."
    ),
    "Losartan": (
        "Missing a dose may cause your blood pressure to rise. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Losartan Potassium": (
        "Missing a dose may cause your blood pressure to rise. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Lisinopril": (
        "Missing a dose may cause your blood pressure to rise. "
        "If missed, take it as soon as you remember. Do not take two doses to make up for it."
    ),
    "Atenolol": (
        "Missing doses can cause your heart rate or blood pressure to rise. Stopping suddenly may worsen your condition. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Bisoprolol": (
        "Missing doses can cause your heart rate or blood pressure to rise. Stopping suddenly may worsen your condition. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Hydrochlorothiazide": (
        "Missing a dose may cause your blood pressure to rise or fluid to build up. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Nifedipine": (
        "Missing a dose may cause your blood pressure to rise. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    # Hyperlipidaemia
    "Atorvastatin": (
        "Missing doses may cause your bad cholesterol to rise again. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Rosuvastatin": (
        "Missing doses may cause your cholesterol levels to rise again. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Simvastatin": (
        "Missing doses may cause your cholesterol levels to rise again. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Fenofibrate": (
        "Missing doses may cause your triglyceride levels to rise. "
        "If missed, take it as soon as you remember with food. Do not double up."
    ),
    "Ezetimibe": (
        "Missing doses may cause your cholesterol levels to rise. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    # Cardiovascular / Anticoagulants
    "Acetylsalicylic Acid": (
        "Missing a dose may reduce protection against blood clots. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Clopidogrel": (
        "Missing a dose may reduce protection against blood clots. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not take two doses."
    ),
    "Apixaban": (
        "Missing a dose may increase your risk of blood clots or stroke. "
        "If missed, take it as soon as you remember on the same day. Do not double the next dose."
    ),
    "Rivaroxaban": (
        "Missing a dose may increase your risk of blood clots or stroke. "
        "If missed, take it immediately with food. Do not take two doses at the same time."
    ),
    "Warfarin": (
        "Missing a dose may cause your blood to become too thick, increasing the risk of blood clots. "
        "If missed, take it as soon as you remember on the same day. Do not double your dose the next day."
    ),
    # Respiratory
    "Salbutamol": (
        "This is a rescue inhaler — use it only when you feel breathless or wheezy. "
        "You do not need to take it on a schedule. Always carry it with you."
    ),
    "Budesonide/Formoterol": (
        "Missing your preventer inhaler may increase airway inflammation, raising risk of an asthma attack. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Fluticasone/Salmeterol": (
        "Missing your preventer inhaler may increase airway inflammation, raising risk of an asthma attack. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Tiotropium": (
        "Missing a dose may cause your airways to narrow, making breathing harder. "
        "If missed, take it as soon as you remember. Do not take two doses in one day."
    ),
    "Montelukast": (
        "Missing a dose may cause your asthma or allergy symptoms to return. "
        "If missed, skip it and take your next dose at the usual time. Do not double up."
    ),
    # Thyroid
    "Levothyroxine": (
        "Missing doses may cause tiredness and low energy as your thyroid levels drop. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    # Mental health
    "Escitalopram": (
        "Missing doses may cause dizziness, headache, or irritability. "
        "If missed, take it as soon as you remember unless it's past the halfway point to your next dose. Do not double up."
    ),
    "Sertraline": (
        "Missing doses may cause dizziness, irritability, or flu-like symptoms. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    # Gout
    "Allopurinol": (
        "Missing doses may cause uric acid to build up, increasing risk of a gout attack. "
        "If missed, take it as soon as you remember unless it's almost time for your next dose. Do not double up."
    ),
    "Colchicine": (
        "Missing a dose during a gout attack may cause pain and swelling to return. "
        "If missed, take it as soon as you remember. Do not take extra doses to make up."
    ),
    # Osteoporosis
    "Alendronate": (
        "Missing doses may slow bone strengthening and increase fracture risk over time. "
        "If missed, take it the next morning. Do not take two doses on the same day. Take on an empty stomach with plain water."
    ),
    # Gastrointestinal
    "Omeprazole": (
        "Missing a dose may cause heartburn or acid reflux to return. "
        "If missed, take it as soon as you remember. Do not take two doses to make up for it."
    ),
    "Pantoprazole": (
        "Missing a dose may cause heartburn or acid reflux to return. "
        "If missed, take it as soon as you remember. Do not take two doses to make up for it."
    ),
}


def seed():
    db = SessionLocal()
    try:
        updated = 0
        for generic_name, info in MISSED_DOSE_INFO.items():
            med = db.query(Medication).filter(Medication.generic_name == generic_name).first()
            if med:
                med.missed_dose_info = info
                updated += 1
            else:
                print(f"  WARNING: Medication '{generic_name}' not found in database")
        db.commit()
        print(f"Updated missed_dose_info for {updated}/{len(MISSED_DOSE_INFO)} medications")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
