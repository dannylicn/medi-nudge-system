"""
WhatsApp inbound/status webhook endpoints.
ALL inbound requests MUST have their X-Twilio-Signature validated before any processing.
"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Form, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import Patient, NudgeCampaign, OutboundMessage
from app.services.response_classifier import classify_response
from app.services import nudge_campaign_service, onboarding_service, ocr_service
from app.services.whatsapp_service import validate_twilio_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

ONBOARDING_STATES = {"invited", "consent_pending", "language_confirmed"}


def _validate_signature(request: Request, form_data: dict) -> None:
    """Reject requests with invalid Twilio signatures with 403."""
    signature = request.headers.get("X-Twilio-Signature", "")
    request_url = str(request.url)
    if not validate_twilio_signature(request_url, form_data, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


@router.post("/whatsapp")
async def inbound_whatsapp(
    request: Request,
    db: Session = Depends(get_db),
):
    """Main inbound WhatsApp message handler."""
    form_data = dict(await request.form())

    # SECURITY: Validate signature before any processing
    _validate_signature(request, form_data)

    from_number = form_data.get("From", "").replace("whatsapp:", "")
    body = form_data.get("Body", "").strip()
    num_media = int(form_data.get("NumMedia", 0))

    if not from_number:
        return Response(content="<Response/>", media_type="text/xml")

    # Look up patient
    patient = db.query(Patient).filter(Patient.phone_number == from_number).first()

    if not patient:
        logger.info("Inbound message from unknown number: %s", from_number)
        # Auto-reply, no patient data exposed
        return _twiml_response("We don't recognise this number. Please contact your clinic.")

    # WhatsApp Photo → OCR pipeline
    if num_media > 0:
        _handle_media(db, patient, form_data)
        return Response(content="<Response/>", media_type="text/xml")

    # Onboarding flow
    if patient.onboarding_state in ONBOARDING_STATES:
        onboarding_service.handle_onboarding_reply(db, patient, body)
        return Response(content="<Response/>", media_type="text/xml")

    # Active nudge campaign response
    open_campaign: NudgeCampaign | None = (
        db.query(NudgeCampaign)
        .filter(
            NudgeCampaign.patient_id == patient.id,
            NudgeCampaign.status == "sent",
        )
        .order_by(NudgeCampaign.created_at.desc())
        .first()
    )

    response_type = classify_response(body)

    if open_campaign:
        nudge_campaign_service.handle_response(
            db=db,
            campaign=open_campaign,
            response_text=body,
            response_type=response_type,
        )
    else:
        # No open campaign — still handle side effects and questions
        from app.services import escalation_service
        from app.services.nudge_generator import get_safety_ack, get_question_ack
        from app.services.whatsapp_service import send_text

        if response_type == "side_effect":
            escalation_service.create_escalation(
                db=db, patient_id=patient.id, reason="side_effect", priority="urgent"
            )
            send_text(db, patient.id, patient.phone_number, get_safety_ack(patient.language_preference))
        elif response_type in ("question", "opt_out"):
            escalation_service.create_escalation(
                db=db, patient_id=patient.id, reason="patient_question"
            )
            send_text(db, patient.id, patient.phone_number, get_question_ack(patient.language_preference))

    return Response(content="<Response/>", media_type="text/xml")


@router.post("/whatsapp/status")
async def whatsapp_status_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """Twilio delivery status callback."""
    form_data = dict(await request.form())
    _validate_signature(request, form_data)

    message_sid = form_data.get("MessageSid")
    message_status = form_data.get("MessageStatus")

    if not message_sid or not message_status:
        return Response(content="<Response/>", media_type="text/xml")

    msg = db.query(OutboundMessage).filter(
        OutboundMessage.whatsapp_message_id == message_sid
    ).first()

    if msg:
        status_map = {"delivered": "delivered", "read": "read", "failed": "failed", "undelivered": "failed"}
        if message_status in status_map:
            msg.status = status_map[message_status]
            if message_status == "delivered":
                from datetime import datetime
                msg.delivered_at = datetime.utcnow()
            db.commit()
    else:
        logger.info("Status callback for unknown message SID: %s", message_sid)
        # Return 200 to prevent Twilio retries

    return Response(content="<Response/>", media_type="text/xml")


def _handle_media(db: Session, patient: Patient, form_data: dict) -> None:
    """Download WhatsApp media and route to OCR pipeline."""
    import httpx
    media_url = form_data.get("MediaUrl0", "")
    if not media_url:
        return
    try:
        response = httpx.get(
            media_url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=30,
        )
        response.raise_for_status()
        ocr_service.ingest_image(
            db=db,
            patient_id=patient.id,
            image_bytes=response.content,
            source="whatsapp_photo",
        )
    except Exception as exc:
        logger.error("Failed to download/process WhatsApp media for patient %s: %s", patient.id, exc)


def _twiml_response(message: str) -> Response:
    twiml = f"<Response><Message>{message}</Message></Response>"
    return Response(content=twiml, media_type="text/xml")
