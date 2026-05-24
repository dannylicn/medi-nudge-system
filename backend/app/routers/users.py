"""User-scoped app sync routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import CaregiverPatientLink, Patient, User, UserDeviceToken
from app.schemas.schemas import AckResponse, CaregiverLinkCreate, CaregiverLinkOut, DeviceTokenCreate


router = APIRouter(prefix="/api/users", tags=["users"])

IOS_BUNDLE_ID = "com.adheris.Adheris"


@router.post("/me/caregiver-links", response_model=CaregiverLinkOut, status_code=201)
def create_my_caregiver_link(
    payload: CaregiverLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    link = (
        db.query(CaregiverPatientLink)
        .filter(
            CaregiverPatientLink.caregiver_user_id == user.id,
            CaregiverPatientLink.patient_id == patient.id,
        )
        .first()
    )
    if link:
        link.link_relationship = payload.relationship
    else:
        link = CaregiverPatientLink(
            caregiver_user_id=user.id,
            patient_id=patient.id,
            link_relationship=payload.relationship,
        )
        db.add(link)

    db.commit()
    return CaregiverLinkOut(
        patient_id=patient.id,
        name=patient.full_name,
        relationship=link.link_relationship,
    )


@router.post("/me/device-tokens", response_model=AckResponse)
def register_my_device_token(
    payload: DeviceTokenCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(UserDeviceToken).filter(UserDeviceToken.token == payload.token).first()
    now = datetime.utcnow()
    if row:
        row.user_id = user.id
        row.platform = payload.platform
        row.bundle_id = IOS_BUNDLE_ID
        row.is_active = True
        row.updated_at = now
    else:
        row = UserDeviceToken(
            user_id=user.id,
            token=payload.token,
            platform=payload.platform,
            bundle_id=IOS_BUNDLE_ID,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)

    db.commit()
    return AckResponse(status="ok")
