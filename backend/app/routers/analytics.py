"""Analytics and nudge campaign routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import NudgeCampaign, EscalationCase, User
from app.schemas.schemas import NudgeCampaignOut
from app.services import refill_gap_service
from app.services.daily_reminder_service import send_scheduled_reminders

router = APIRouter(tags=["campaigns & analytics"])


@router.get("/api/nudge-campaigns", response_model=list[NudgeCampaignOut])
def list_campaigns(
    patient_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(NudgeCampaign)
    if patient_id:
        q = q.filter(NudgeCampaign.patient_id == patient_id)
    if status:
        q = q.filter(NudgeCampaign.status == status)
    return q.order_by(NudgeCampaign.created_at.desc()).all()


@router.get("/api/analytics/adherence")
def adherence_analytics(
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Weekly adherence rate: % campaigns resolved with 'confirmed' response."""
    since = datetime.utcnow() - timedelta(days=days)
    campaigns = (
        db.query(NudgeCampaign)
        .filter(NudgeCampaign.created_at >= since)
        .all()
    )
    # Bucket by ISO week
    weekly: dict[str, dict] = {}
    for c in campaigns:
        week = c.created_at.strftime("%Y-W%W")
        if week not in weekly:
            weekly[week] = {"week": week, "total": 0, "confirmed": 0}
        weekly[week]["total"] += 1
        if c.response_type == "confirmed":
            weekly[week]["confirmed"] += 1
    result = []
    for w in sorted(weekly.keys()):
        d = weekly[w]
        rate = round(d["confirmed"] / d["total"] * 100, 1) if d["total"] else 0.0
        result.append({"week": w, "total": d["total"], "confirmed": d["confirmed"], "adherence_rate": rate})
    return result


@router.get("/api/analytics/escalations")
def escalation_analytics(
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Weekly escalation volume by priority."""
    since = datetime.utcnow() - timedelta(days=days)
    cases = db.query(EscalationCase).filter(EscalationCase.created_at >= since).all()
    weekly: dict[str, dict] = {}
    for c in cases:
        week = c.created_at.strftime("%Y-W%W")
        if week not in weekly:
            weekly[week] = {"week": week, "total": 0, "urgent": 0, "high": 0, "normal": 0, "low": 0}
        weekly[week]["total"] += 1
        priority = c.priority if c.priority in ("urgent", "high", "normal", "low") else "normal"
        weekly[week][priority] += 1
    return [weekly[w] for w in sorted(weekly.keys())]


@router.post("/api/nudge-campaigns/trigger")
def trigger_nudge_campaigns(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Manually trigger refill gap detection and nudge campaign creation."""
    return refill_gap_service.detect_and_trigger(db)


@router.post("/api/reminders/trigger")
def trigger_daily_reminders(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Manually trigger daily medication reminders for all active patients."""
    return send_scheduled_reminders(db, skip_window=True)
