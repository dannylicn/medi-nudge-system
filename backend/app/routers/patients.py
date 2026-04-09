"""Patient management routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import hash_sha256
from app.models.models import Patient, User
from app.schemas.schemas import PatientCreate, PatientOut, PatientUpdate, PatientListResponse
from app.services.onboarding_service import send_invite

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Duplicate phone check
    if db.query(Patient).filter(Patient.phone_number == payload.phone_number).first():
        raise HTTPException(status_code=409, detail="A patient with this phone number already exists")

    # NRIC: hash before storage, never persist plaintext
    nric_hash = hash_sha256(payload.nric) if payload.nric else None
    if nric_hash and db.query(Patient).filter(Patient.nric_hash == nric_hash).first():
        raise HTTPException(status_code=409, detail="A patient with this NRIC already exists")

    patient = Patient(
        nric_hash=nric_hash,
        full_name=payload.full_name,
        age=payload.age,
        phone_number=payload.phone_number,
        language_preference=payload.language_preference,
        conditions=payload.conditions,
        risk_level=payload.risk_level,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Trigger onboarding invite
    try:
        send_invite(db, patient)
    except Exception:
        pass  # Don't fail patient creation if WhatsApp is unavailable

    return patient


@router.get("", response_model=PatientListResponse)
def list_patients(
    is_active: bool | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(Patient)
    if is_active is not None:
        q = q.filter(Patient.is_active == is_active)
    if risk_level:
        q = q.filter(Patient.risk_level == risk_level)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return PatientListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
def deactivate_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.is_active = False
    db.commit()
