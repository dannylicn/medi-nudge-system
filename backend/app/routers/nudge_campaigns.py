"""Nudge campaign management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import NudgeCampaign, User
from app.services.nudge_campaign_service import fire_campaign, fire_due_campaigns

router = APIRouter(prefix="/api/nudge-campaigns", tags=["nudge-campaigns"])


@router.post("/{campaign_id}/fire", status_code=200)
def fire_campaign_now(
    campaign_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Manually fire a pending campaign immediately, ignoring its scheduled fire_at.
    Useful for testing without waiting for the scheduler.
    """
    campaign = db.query(NudgeCampaign).filter(NudgeCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Campaign is already in status '{campaign.status}', only pending campaigns can be fired",
        )
    fire_campaign(db, campaign)
    return {"id": campaign.id, "status": campaign.status, "campaign_type": campaign.campaign_type}


@router.post("/fire-due", status_code=200)
def fire_all_due(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Fire all pending campaigns whose fire_at <= now.
    Equivalent to triggering the scheduler job manually.
    """
    results = fire_due_campaigns(db)
    return results
