"""
NudgeCampaign service.
Manages campaign lifecycle: create, send, handle responses, retry, escalate.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import (
    NudgeCampaign, Patient, Medication, CAMPAIGN_VALID_TRANSITIONS,
)
from app.services import nudge_generator, telegram_service, escalation_service, tts_service
from app.core.config import settings


def _transition(db: Session, campaign: NudgeCampaign, new_status: str) -> NudgeCampaign:
    allowed = CAMPAIGN_VALID_TRANSITIONS.get(campaign.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition NudgeCampaign from '{campaign.status}' to '{new_status}'"
        )
    campaign.status = new_status
    db.commit()
    db.refresh(campaign)
    return campaign


def create_and_send(
    db: Session,
    patient: Patient,
    medication: Medication,
    days_overdue: int,
    attempt: int = 1,
) -> NudgeCampaign:
    """Create a NudgeCampaign, generate message, send it, and advance state."""
    # Check for existing open campaign for this patient+medication
    existing = (
        db.query(NudgeCampaign)
        .filter(
            NudgeCampaign.patient_id == patient.id,
            NudgeCampaign.medication_id == medication.id,
            NudgeCampaign.status.in_(["pending", "sent"]),
        )
        .first()
    )
    if existing:
        existing.days_overdue = days_overdue
        db.commit()
        return existing

    condition = ", ".join(patient.conditions) if patient.conditions else ""
    message = nudge_generator.generate_nudge_message(
        name=patient.full_name,
        medication=medication.name,
        days_overdue=days_overdue,
        language=patient.language_preference,
        attempt=attempt,
        condition=condition,
    )

    campaign = NudgeCampaign(
        patient_id=patient.id,
        medication_id=medication.id,
        status="pending",
        days_overdue=days_overdue,
        attempt_number=attempt,
        message_content=message,
        language=patient.language_preference,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Send text (always for "text" and "both"; also the fallback for voice failures)
    chat_target = patient.telegram_chat_id or patient.phone_number
    send_text = patient.nudge_delivery_mode in ("text", "both")
    send_voice = patient.nudge_delivery_mode in ("voice", "both")

    out_msg = None
    if send_text or not send_voice:
        out_msg = telegram_service.send_text(
            db=db,
            patient_id=patient.id,
            to_phone=chat_target,
            body=message,
            campaign_id=campaign.id,
        )

    # Send voice if applicable
    if send_voice:
        ogg_path = tts_service.generate_voice_message(
            text=message,
            voice_id=patient.selected_voice_id,
            patient_id=patient.id,
            medication_id=medication.id,
            attempt=attempt,
        )
        if ogg_path:
            telegram_service.send_voice(
                db=db,
                patient_id=patient.id,
                to_phone=chat_target,
                ogg_path=ogg_path,
                campaign_id=campaign.id,
            )
        elif not out_msg:
            # Voice failed and no text was sent — fall back to text
            out_msg = telegram_service.send_text(
                db=db,
                patient_id=patient.id,
                to_phone=chat_target,
                body=message,
                campaign_id=campaign.id,
            )

    if out_msg is None:
        # Voice-only path succeeded; use a sentinel for status check
        _transition(db, campaign, "sent")
        campaign.last_sent_at = datetime.utcnow()
        db.commit()
    elif out_msg.status == "failed":
        _transition(db, campaign, "failed")
    else:
        _transition(db, campaign, "sent")
        campaign.last_sent_at = datetime.utcnow()
        db.commit()

    # Attempt-3 → escalate after sending
    if attempt >= settings.MAX_NUDGE_ATTEMPTS and campaign.status == "sent":
        escalation_service.create_escalation(
            db=db,
            patient_id=patient.id,
            reason="no_response",
            nudge_campaign_id=campaign.id,
            priority="high",
        )

    return campaign


def handle_response(
    db: Session,
    campaign: NudgeCampaign,
    response_text: str,
    response_type: str,
) -> NudgeCampaign:
    """Process a classified inbound response and update campaign state."""
    campaign.response = response_text
    campaign.response_type = response_type

    if response_type == "confirmed":
        _transition(db, campaign, "resolved")

    elif response_type == "side_effect":
        # MUST always escalate — never silently drop
        escalation_service.create_escalation(
            db=db,
            patient_id=campaign.patient_id,
            reason="side_effect",
            nudge_campaign_id=campaign.id,
            priority="urgent",
        )
        _transition(db, campaign, "escalated")
        # Send safety acknowledgement
        patient = db.query(Patient).filter(Patient.id == campaign.patient_id).first()
        if patient:
            ack = nudge_generator.get_safety_ack(patient.language_preference)
            telegram_service.send_text(
                db=db, patient_id=patient.id, to_phone=patient.telegram_chat_id or patient.phone_number, body=ack
            )

    elif response_type == "question":
        escalation_service.create_escalation(
            db=db,
            patient_id=campaign.patient_id,
            reason="patient_question",
            nudge_campaign_id=campaign.id,
        )
        _transition(db, campaign, "escalated")
        patient = db.query(Patient).filter(Patient.id == campaign.patient_id).first()
        if patient:
            ack = nudge_generator.get_question_ack(patient.language_preference)
            telegram_service.send_text(
                db=db, patient_id=patient.id, to_phone=patient.telegram_chat_id or patient.phone_number, body=ack
            )

    elif response_type in ("negative", "opt_out"):
        _transition(db, campaign, "responded")

    db.commit()
    db.refresh(campaign)
    return campaign


def retry_or_escalate(db: Session, campaign: NudgeCampaign) -> None:
    """Called by the 48h scheduler job for campaigns with no response."""
    if campaign.status != "sent":
        return

    if campaign.attempt_number < settings.MAX_NUDGE_ATTEMPTS:
        patient = db.query(Patient).filter(Patient.id == campaign.patient_id).first()
        medication = db.query(Medication).filter(Medication.id == campaign.medication_id).first()
        if not patient or not medication:
            return
        # Mark current as failed; create new attempt
        _transition(db, campaign, "failed")
        create_and_send(
            db=db,
            patient=patient,
            medication=medication,
            days_overdue=campaign.days_overdue,
            attempt=campaign.attempt_number + 1,
        )
    else:
        # Max attempts exhausted
        escalation_service.create_escalation(
            db=db,
            patient_id=campaign.patient_id,
            reason="no_response",
            nudge_campaign_id=campaign.id,
            priority="high",
        )
        _transition(db, campaign, "escalated")
