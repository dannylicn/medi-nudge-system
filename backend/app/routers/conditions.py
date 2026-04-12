"""Condition catalog and condition-medication mapping routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Condition, ConditionMedication, Medication, User
from app.schemas.schemas import ConditionOut, ConditionCreate, ConditionMedicationAdd, MedicationOut

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


@router.get("", response_model=list[ConditionOut])
def list_conditions(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    conditions = (
        db.query(Condition)
        .options(joinedload(Condition.medications).joinedload(ConditionMedication.medication))
        .order_by(Condition.name)
        .all()
    )
    # Flatten the junction into a list of MedicationOut
    result = []
    for c in conditions:
        result.append(ConditionOut(
            id=c.id,
            name=c.name,
            medications=[
                MedicationOut.model_validate(cm.medication) for cm in c.medications
            ],
        ))
    return result


@router.post("", response_model=ConditionOut, status_code=201)
def create_condition(
    payload: ConditionCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if db.query(Condition).filter(Condition.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Condition already exists")
    cond = Condition(name=payload.name)
    db.add(cond)
    db.commit()
    db.refresh(cond)
    return ConditionOut(id=cond.id, name=cond.name, medications=[])


@router.post("/{condition_id}/medications", status_code=201)
def add_medication_to_condition(
    condition_id: int,
    payload: ConditionMedicationAdd,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cond = db.query(Condition).filter(Condition.id == condition_id).first()
    if not cond:
        raise HTTPException(status_code=404, detail="Condition not found")
    if not db.query(Medication).filter(Medication.id == payload.medication_id).first():
        raise HTTPException(status_code=404, detail="Medication not found")
    exists = db.query(ConditionMedication).filter(
        ConditionMedication.condition_id == condition_id,
        ConditionMedication.medication_id == payload.medication_id,
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Mapping already exists")
    cm = ConditionMedication(condition_id=condition_id, medication_id=payload.medication_id)
    db.add(cm)
    db.commit()
    return {"detail": "ok"}


@router.delete("/{condition_id}/medications/{medication_id}", status_code=204)
def remove_medication_from_condition(
    condition_id: int,
    medication_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cm = db.query(ConditionMedication).filter(
        ConditionMedication.condition_id == condition_id,
        ConditionMedication.medication_id == medication_id,
    ).first()
    if not cm:
        raise HTTPException(status_code=404, detail="Mapping not found")
    db.delete(cm)
    db.commit()
