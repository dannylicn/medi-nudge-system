"""Escalation case routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import EscalationCase, User, ESCALATION_PRIORITY_ORDER
from app.schemas.schemas import EscalationCaseOut, EscalationCaseUpdate
from app.services.escalation_service import update_escalation

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


@router.get("", response_model=list[EscalationCaseOut])
def list_escalations(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    patient_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(EscalationCase)
    if status:
        q = q.filter(EscalationCase.status == status)
    if priority:
        q = q.filter(EscalationCase.priority == priority)
    if patient_id:
        q = q.filter(EscalationCase.patient_id == patient_id)
    cases = q.all()
    # Sort: priority desc, then created_at asc
    cases.sort(
        key=lambda c: (-ESCALATION_PRIORITY_ORDER.get(c.priority, 0), c.created_at)
    )
    return cases


@router.get("/{case_id}", response_model=EscalationCaseOut)
def get_escalation(
    case_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    case = db.query(EscalationCase).filter(EscalationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Escalation case not found")
    return case


@router.patch("/{case_id}", response_model=EscalationCaseOut)
def update_escalation_case(
    case_id: int,
    payload: EscalationCaseUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    case = db.query(EscalationCase).filter(EscalationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Escalation case not found")
    return update_escalation(
        db=db,
        case=case,
        status=payload.status,
        assigned_to=payload.assigned_to,
        notes=payload.notes,
    )
