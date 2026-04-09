"""Medication catalog and patient prescription routes."""
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Medication, PatientMedication, Patient, DispensingRecord, User
from app.schemas.schemas import (
    MedicationCreate, MedicationOut,
    PatientMedicationCreate, PatientMedicationOut,
    DispensingRecordCreate, DispensingRecordOut,
)

router = APIRouter(tags=["medications"])


# ---------------------------------------------------------------------------
# Medication catalog
# ---------------------------------------------------------------------------

@router.post("/api/medications", response_model=MedicationOut, status_code=201)
def create_medication(
    payload: MedicationCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if db.query(Medication).filter(Medication.generic_name == payload.generic_name).first():
        raise HTTPException(status_code=409, detail="Medication with this generic name already exists")
    med = Medication(**payload.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


@router.get("/api/medications", response_model=list[MedicationOut])
def list_medications(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Medication).all()


@router.get("/api/medications/{med_id}", response_model=MedicationOut)
def get_medication(med_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    med = db.query(Medication).filter(Medication.id == med_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    return med


# ---------------------------------------------------------------------------
# Patient prescriptions (PatientMedication)
# ---------------------------------------------------------------------------

@router.post("/api/patients/{patient_id}/medications", response_model=PatientMedicationOut, status_code=201)
def assign_medication(
    patient_id: int,
    payload: PatientMedicationCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not db.query(Medication).filter(Medication.id == payload.medication_id).first():
        raise HTTPException(status_code=404, detail="Medication not found")
    pm = PatientMedication(patient_id=patient_id, **payload.model_dump())
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm


@router.get("/api/patients/{patient_id}/medications", response_model=list[PatientMedicationOut])
def list_patient_medications(
    patient_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return (
        db.query(PatientMedication)
        .filter(PatientMedication.patient_id == patient_id, PatientMedication.is_active == True)
        .all()
    )


@router.patch("/api/patients/{patient_id}/medications/{pm_id}", response_model=PatientMedicationOut)
def update_patient_medication(
    patient_id: int,
    pm_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    pm = db.query(PatientMedication).filter(
        PatientMedication.id == pm_id, PatientMedication.patient_id == patient_id
    ).first()
    if not pm:
        raise HTTPException(status_code=404, detail="PatientMedication not found")
    pm.is_active = is_active
    db.commit()
    db.refresh(pm)
    return pm


# ---------------------------------------------------------------------------
# Dispensing records
# ---------------------------------------------------------------------------

@router.post("/api/dispensing-records", response_model=DispensingRecordOut, status_code=201)
def create_dispensing_record(
    payload: DispensingRecordCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    record = DispensingRecord(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/api/patients/{patient_id}/dispensing-records", response_model=list[DispensingRecordOut])
def list_dispensing_records(
    patient_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return (
        db.query(DispensingRecord)
        .filter(DispensingRecord.patient_id == patient_id)
        .order_by(DispensingRecord.dispensed_at.desc())
        .all()
    )


@router.post("/api/dispensing-records/import", status_code=201)
def import_dispensing_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Bulk import dispensing records from a CSV.
    Expected columns: patient_id, medication_id, dispensed_at (ISO8601), days_supply, quantity, source
    """
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    created, skipped, errors = 0, 0, []

    for row in reader:
        try:
            dispensed_at = datetime.fromisoformat(row["dispensed_at"])
            # Dedup check
            exists = db.query(DispensingRecord).filter(
                DispensingRecord.patient_id == int(row["patient_id"]),
                DispensingRecord.medication_id == int(row["medication_id"]),
                DispensingRecord.dispensed_at == dispensed_at,
            ).first()
            if exists:
                skipped += 1
                continue
            record = DispensingRecord(
                patient_id=int(row["patient_id"]),
                medication_id=int(row["medication_id"]),
                dispensed_at=dispensed_at,
                days_supply=int(row["days_supply"]),
                quantity=int(row.get("quantity") or 0) or None,
                source=row.get("source", "pharmacy"),
            )
            db.add(record)
            created += 1
        except Exception as exc:
            errors.append({"row": row, "error": str(exc)})

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
