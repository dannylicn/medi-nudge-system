"""Auth router — login and token refresh."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, hash_password
from app.models.models import CaregiverPatientLink, Patient, User
from app.schemas.schemas import AccessiblePatient, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _accessible_patients_for_user(db: Session, user: User) -> list[AccessiblePatient]:
    accessible: list[AccessiblePatient] = []
    seen_patient_ids: set[int] = set()

    if user.own_patient_id is not None:
        own_patient = db.query(Patient).filter(Patient.id == user.own_patient_id).first()
        if own_patient:
            accessible.append(
                AccessiblePatient(
                    patient_id=own_patient.id,
                    name=own_patient.full_name,
                    relationship="self",
                )
            )
            seen_patient_ids.add(own_patient.id)

    links = (
        db.query(CaregiverPatientLink)
        .join(Patient, CaregiverPatientLink.patient_id == Patient.id)
        .filter(CaregiverPatientLink.caregiver_user_id == user.id)
        .order_by(CaregiverPatientLink.id.asc())
        .all()
    )
    for link in links:
        if link.patient_id in seen_patient_ids:
            continue
        accessible.append(
            AccessiblePatient(
                patient_id=link.patient.id,
                name=link.patient.full_name,
                relationship=link.link_relationship or "caregiver",
            )
        )
        seen_patient_ids.add(link.patient_id)

    if accessible:
        return accessible

    if user.patient_id is None:
        return accessible
    patient = db.query(Patient).filter(Patient.id == user.patient_id).first()
    if not patient:
        return accessible

    return [
        AccessiblePatient(
            patient_id=patient.id,
            name=patient.full_name,
            relationship="self" if user.role == "patient" else "default",
        )
    ]


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        patient_id=user.patient_id,
        own_patient_id=user.own_patient_id,
        full_name=user.full_name,
        accessible_patients=_accessible_patients_for_user(db, user),
    )


@router.post("/register", response_model=TokenResponse, include_in_schema=False)
def register(payload: LoginRequest, full_name: str = "Coordinator", db: Session = Depends(get_db)):
    """Dev-only: create a user for testing."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, full_name=full_name, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, user_id=user.id)
