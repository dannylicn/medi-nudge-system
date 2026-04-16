"""
Agentic Telegram bot service.

Architecture:
- When OPENAI_API_KEY or LLM_BASE_URL is set: LLM tool-calling loop (max 3 iterations)
- Otherwise: rule-based fallback (existing classify_response logic — no behaviour change)

Entry point:
    agent_service.run(patient, text, db)  — called from webhook.py for all text messages
    agent_service.verify_and_confirm_medication(patient, name, db)  — called from onboarding
"""
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    NudgeCampaign, Patient, PatientMedication, OutboundMessage,
)
from app.services import escalation_service, medication_service
from app.services import nudge_campaign_service as _nudge_svc
from app.services import telegram_service
from app.services.nudge_generator import get_safety_ack, get_question_ack
from app.services.response_classifier import classify_response

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are a compassionate, multilingual medication adherence assistant for a Singapore clinic.
You help patients via Telegram to track their medications and stay healthy.

You MUST respond in the patient's preferred language (indicated in context).
You MUST NOT provide medical advice, dosage guidance, or drug interaction information.
You MUST NOT diagnose or interpret symptoms.
You MUST NOT reveal the patient's NRIC, clinical notes, or internal IDs.

Your job is to choose the single best tool call to handle the patient's message given the context.
Choose tools carefully:
- Use `confirm_adherence` when the patient clearly indicates they have taken or collected their medication.
- Use `escalate` with reason "side_effect" and priority "urgent" for ANY mention of symptoms, side effects, or feeling unwell.
- Use `send_reply` to answer factual questions about refill dates, medication names, or provide acknowledgements.
- Use `verify_medication` when the patient mentions a medicine name you need to match against the catalogue.
- Use `escalate` with reason "patient_question" when a question is outside your scope.
- Use `escalate` with reason "agent_limit_exceeded" only as an absolute last resort.

Context fields provided:
- patient_name, patient_language, patient_conditions, onboarding_state, is_active
- active_campaign: {medication, days_overdue, attempt_number, campaign_id} or null
- recent_messages: last 5 outbound message bodies (for context)
- refill_info: next refill due date (if available)
"""

# ---------------------------------------------------------------------------
# Tool schemas for OpenAI function calling
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "classify_intent",
            "description": "Classify the patient's intent from their message. Returns intent and confidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The patient's message text"},
                    "language": {"type": "string", "description": "Patient's language code (en/zh/ms/ta)"},
                },
                "required": ["text", "language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_medication",
            "description": "Fuzzy-search the medication catalogue for a given name. Returns ranked matches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Medicine name typed by the patient"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_reply",
            "description": "Send a text message to the patient. This is terminal — the loop ends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Message to send to the patient"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate",
            "description": "Create an escalation case for a care coordinator. This is terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": ["side_effect", "patient_question", "agent_limit_exceeded", "unknown_medication"],
                        "description": "Reason for escalation",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["urgent", "high", "normal", "low"],
                        "description": "Priority level",
                    },
                    "send_ack": {
                        "type": "boolean",
                        "description": "Whether to send an acknowledgement message to the patient",
                    },
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_adherence",
            "description": "Mark the patient's open nudge campaign as resolved (medication taken/collected). Terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "integer", "description": "ID of the open NudgeCampaign to resolve"},
                },
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_medication",
            "description": "Create a PatientMedication for a confirmed catalogue entry. Terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_id": {"type": "integer", "description": "ID of the medication in the catalogue"},
                },
                "required": ["medication_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Context builder (strips PII)
# ---------------------------------------------------------------------------

def _build_context(patient: Patient, db: Session) -> dict:
    """Build a compact context dict for the LLM. Strips NRIC hash and raw phone_number."""
    active_campaign = (
        db.query(NudgeCampaign)
        .filter(NudgeCampaign.patient_id == patient.id, NudgeCampaign.status == "sent")
        .order_by(NudgeCampaign.created_at.desc())
        .first()
    )
    campaign_ctx = None
    if active_campaign:
        from app.models.models import Medication as MedModel
        med = db.query(MedModel).filter(MedModel.id == active_campaign.medication_id).first()
        campaign_ctx = {
            "campaign_id": active_campaign.id,
            "medication": med.name if med else "unknown",
            "days_overdue": active_campaign.days_overdue,
            "attempt_number": active_campaign.attempt_number,
        }

    recent_msgs = (
        db.query(OutboundMessage)
        .filter(OutboundMessage.patient_id == patient.id)
        .order_by(OutboundMessage.sent_at.desc())
        .limit(5)
        .all()
    )

    # Compute refill info if available
    refill_info = None
    try:
        from app.models.models import DispensingRecord, PatientMedication as PM
        latest_pm = (
            db.query(PM)
            .filter(PM.patient_id == patient.id, PM.is_active == True)  # noqa: E712
            .order_by(PM.created_at.desc())
            .first()
        )
        if latest_pm:
            from app.models.models import DispensingRecord as DR
            latest_dr = (
                db.query(DR)
                .filter(DR.patient_id == patient.id, DR.medication_id == latest_pm.medication_id)
                .order_by(DR.dispensed_at.desc())
                .first()
            )
            if latest_dr:
                from datetime import timedelta
                due = latest_dr.dispensed_at + timedelta(days=latest_dr.days_supply)
                refill_info = due.strftime("%d %b %Y")
    except Exception:
        pass

    return {
        "patient_name": patient.full_name,
        "patient_language": patient.language_preference or "en",
        "patient_conditions": patient.conditions or [],
        "onboarding_state": patient.onboarding_state,
        "is_active": patient.is_active,
        "active_campaign": campaign_ctx,
        "recent_messages": [m.content for m in reversed(recent_msgs) if m.content],
        "refill_info": refill_info,
        # nric_hash and phone_number intentionally excluded
    }


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _run_llm(messages: list[dict], tools: list[dict]) -> Optional[dict]:
    """Call OpenAI (or compatible) and return the first tool call dict, or None."""
    try:
        import openai
        client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY or None,
            base_url=settings.LLM_BASE_URL or None,
        )
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL or "gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="required",
            max_tokens=512,
            timeout=15,
        )
        choice = resp.choices[0]
        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            return {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Tool executors
# ---------------------------------------------------------------------------

def _tool_classify_intent(args: dict, **_) -> dict:
    """Pure function — no DB side effects."""
    text = args.get("text", "")
    language = args.get("language", "en")
    intent = classify_response(text)
    return {"intent": intent, "language": language}


def _tool_verify_medication(args: dict, db: Session, **_) -> dict:
    query = args.get("query", "")
    matches = medication_service.fuzzy_search(query, db, limit=5)
    return {
        "query": query,
        "matches": [
            {
                "medication_id": m["medication"].id,
                "name": m["medication"].name,
                "generic_name": m["medication"].generic_name,
                "category": m["medication"].category,
                "confidence": m["confidence"],
            }
            for m in matches
        ],
    }


def _tool_send_reply(args: dict, patient: Patient, db: Session, **_) -> dict:
    text = args.get("text", "")
    telegram_service.send_text(
        db=db,
        patient_id=patient.id,
        to_phone=patient.telegram_chat_id or patient.phone_number,
        body=text,
    )
    return {"sent": True, "terminal": True}


def _tool_escalate(args: dict, patient: Patient, db: Session, **_) -> dict:
    reason = args.get("reason", "patient_question")
    priority = args.get("priority") or ("urgent" if reason == "side_effect" else "normal")
    send_ack = args.get("send_ack", True)

    escalation_service.create_escalation(db=db, patient_id=patient.id, reason=reason, priority=priority)

    if send_ack:
        lang = patient.language_preference or "en"
        if reason == "side_effect":
            ack = get_safety_ack(lang)
        else:
            ack = get_question_ack(lang)
        telegram_service.send_text(
            db=db,
            patient_id=patient.id,
            to_phone=patient.telegram_chat_id or patient.phone_number,
            body=ack,
        )
    return {"escalated": True, "reason": reason, "terminal": True}


def _tool_confirm_adherence(args: dict, patient: Patient, db: Session, **_) -> dict:
    campaign_id = args.get("campaign_id")
    if not campaign_id:
        return {"error": "campaign_id required", "terminal": False}

    campaign = db.query(NudgeCampaign).filter(
        NudgeCampaign.id == campaign_id,
        NudgeCampaign.patient_id == patient.id,
        NudgeCampaign.status == "sent",
    ).first()
    if not campaign:
        return {"error": "No open campaign found for that ID", "terminal": False}

    _nudge_svc._transition(db, campaign, "resolved")

    lang = patient.language_preference or "en"
    TAKEN_ACK = {
        "en": "Great job! 👍 Your medication has been recorded as taken. Keep it up!",
        "zh": "做得好！👍 您的服药记录已更新。继续保持！",
        "ms": "Bagus sekali! 👍 Ubat anda telah direkodkan sebagai sudah diambil. Teruskan!",
        "ta": "சரிதான்! 👍 உங்கள் மருந்து எடுத்தது பதிவு செய்யப்பட்டது. தொடர்ந்து வாருங்கள்!",
    }
    telegram_service.send_text(
        db=db,
        patient_id=patient.id,
        to_phone=patient.telegram_chat_id or patient.phone_number,
        body=TAKEN_ACK.get(lang, TAKEN_ACK["en"]),
    )
    return {"resolved": True, "campaign_id": campaign_id, "terminal": True}


def _tool_record_medication(args: dict, patient: Patient, db: Session, **_) -> dict:
    medication_id = args.get("medication_id")
    if not medication_id:
        return {"error": "medication_id required", "terminal": False}

    from app.models.models import Medication as MedModel
    med = db.query(MedModel).filter(MedModel.id == medication_id).first()
    if not med:
        return {"error": f"medication_id {medication_id} not found in catalogue", "terminal": False}

    # Idempotent: skip if already exists
    existing = db.query(PatientMedication).filter(
        PatientMedication.patient_id == patient.id,
        PatientMedication.medication_id == medication_id,
        PatientMedication.is_active == True,  # noqa: E712
    ).first()
    if not existing:
        pm = PatientMedication(patient_id=patient.id, medication_id=medication_id, is_active=True)
        db.add(pm)
        db.commit()

    return {"recorded": True, "medication": med.name, "terminal": True}


TOOL_EXECUTORS = {
    "classify_intent": _tool_classify_intent,
    "verify_medication": _tool_verify_medication,
    "send_reply": _tool_send_reply,
    "escalate": _tool_escalate,
    "confirm_adherence": _tool_confirm_adherence,
    "record_medication": _tool_record_medication,
}


# ---------------------------------------------------------------------------
# Rule-based fallback (wraps existing classify_response logic)
# ---------------------------------------------------------------------------

def _fallback_agent(patient: Patient, text: str, db: Session) -> None:
    """
    Fallback when no LLM key is available.
    Replicates existing webhook logic exactly — no behaviour change.
    """
    response_type = classify_response(text)
    lang = patient.language_preference or "en"

    open_campaign = (
        db.query(NudgeCampaign)
        .filter(NudgeCampaign.patient_id == patient.id, NudgeCampaign.status == "sent")
        .order_by(NudgeCampaign.created_at.desc())
        .first()
    )

    if open_campaign:
        _nudge_svc.handle_response(
            db=db, campaign=open_campaign, response_text=text, response_type=response_type
        )
        return

    if response_type == "confirmed" or text.strip().upper() in ("TAKEN", "已服", "SUDAH"):
        from app.routers.webhook import _handle_taken
        _handle_taken(db, patient)
    elif response_type == "side_effect":
        escalation_service.create_escalation(db=db, patient_id=patient.id, reason="side_effect", priority="urgent")
        telegram_service.send_text(
            db=db,
            patient_id=patient.id,
            to_phone=patient.telegram_chat_id or patient.phone_number,
            body=get_safety_ack(lang),
        )
    elif response_type in ("question", "opt_out"):
        escalation_service.create_escalation(db=db, patient_id=patient.id, reason="patient_question")
        telegram_service.send_text(
            db=db,
            patient_id=patient.id,
            to_phone=patient.telegram_chat_id or patient.phone_number,
            body=get_question_ack(lang),
        )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(patient: Patient, text: str, db: Session) -> None:
    """
    Process an inbound text message for an active (non-onboarding) patient.
    Uses LLM agent when keys are configured; falls back to rule-based logic.
    """
    if not (settings.OPENAI_API_KEY or settings.LLM_BASE_URL):
        _fallback_agent(patient, text, db)
        return

    context = _build_context(patient, db)
    lang = context["patient_language"]

    system_msg = {"role": "system", "content": AGENT_SYSTEM_PROMPT}
    user_msg = {
        "role": "user",
        "content": (
            f"Patient context: {json.dumps(context)}\n\n"
            f"Patient message: {text}"
        ),
    }
    messages = [system_msg, user_msg]

    for iteration in range(MAX_ITERATIONS):
        tool_call = _run_llm(messages, TOOL_SCHEMAS)
        if not tool_call:
            # LLM unavailable or returned no tool call — use rule-based fallback
            _fallback_agent(patient, text, db)
            return

        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        executor = TOOL_EXECUTORS.get(tool_name)

        if not executor:
            logger.warning("Unknown tool requested by LLM: %s", tool_name)
            break

        result = executor(args=tool_args, patient=patient, db=db)
        logger.debug("Agent tool=%s args=%s result=%s", tool_name, tool_args, result)

        # Terminal tools end the loop
        if result.get("terminal"):
            return

        # Append tool result as observation for next iteration
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": f"call_{iteration}", "type": "function", "function": {"name": tool_name, "arguments": json.dumps(tool_args)}}
        ]})
        messages.append({"role": "tool", "tool_call_id": f"call_{iteration}", "content": json.dumps(result)})

    # Fallback: agent exhausted iterations without terminal action
    logger.warning("Agent loop exhausted for patient %s — escalating", patient.id)
    escalation_service.create_escalation(db=db, patient_id=patient.id, reason="agent_limit_exceeded")
    telegram_service.send_text(
        db=db,
        patient_id=patient.id,
        to_phone=patient.telegram_chat_id or patient.phone_number,
        body=get_question_ack(lang),
    )


# ---------------------------------------------------------------------------
# Medicine verification for onboarding manual-entry sub-flow
# ---------------------------------------------------------------------------

MED_VERIFY_PROMPT = {
    "en": (
        "I found a possible match: **{name}** ({category}).\n"
        "Reply YES to confirm, or type the full medication name to search again."
    ),
    "zh": (
        "找到可能的匹配：**{name}** ({category})。\n"
        "回复\"是\"确认，或重新输入完整药名。"
    ),
    "ms": (
        "Saya jumpa padanan: **{name}** ({category}).\n"
        "Balas YA untuk sahkan, atau taip nama ubat penuh."
    ),
    "ta": (
        "பொருந்திய மருந்து: **{name}** ({category}).\n"
        "YES என்று பதிலளிக்கவும், அல்லது மருந்தின் முழு பெயரை மீண்டும் தட்டச்சு செய்யவும்."
    ),
}

MED_MULTI_PROMPT = {
    "en": "I found several matches. Please reply with the number:\n{options}\n\nOr send a photo of the medicine label.",
    "zh": "找到多个匹配，请回复编号：\n{options}\n\n或发送药品标签的照片。",
    "ms": "Saya jumpa beberapa padanan. Balas dengan nombor:\n{options}\n\nAtau hantar foto label ubat.",
    "ta": "பல பொருத்தங்கள் கண்டறியப்பட்டன. எண்ணில் பதிலளிக்கவும்:\n{options}\n\nஅல்லது மருந்து லேபிள் புகைப்படம் அனுப்பவும்.",
}

MED_NO_MATCH_PROMPT = {
    "en": "I couldn't find that medication in our records. Please send a photo of the medicine label and our team will review it.",
    "zh": "在我们的记录中找不到该药物。请发送药品标签的照片，我们的团队将进行确认。",
    "ms": "Saya tidak jumpa ubat itu dalam rekod kami. Sila hantar foto label ubat dan pasukan kami akan menyemaknya.",
    "ta": "அந்த மருந்து எங்கள் பதிவுகளில் காணவில்லை. மருந்து லேபிள் புகைப்படம் அனுப்பவும், எங்கள் குழு சரிபார்க்கும்.",
}


def verify_and_confirm_medication(patient: Patient, med_name: str, db: Session) -> None:
    """
    Called from onboarding manual-entry sub-flow (option 3 / free-text in confirm state).
    Fuzzy-matches the name, presents candidates, sets state to `medication_confirm_pending`.
    """
    lang = patient.language_preference or "en"
    matches = medication_service.fuzzy_search(med_name, db, limit=5)
    high = [m for m in matches if m["confidence"] >= 0.85]
    low = [m for m in matches if 0.3 <= m["confidence"] < 0.85]

    from app.services.onboarding_service import ONBOARDING_STATES
    from app.services.telegram_service import send_text as _send

    def _send_p(body: str):
        _send(db=db, patient_id=patient.id, to_phone=patient.telegram_chat_id or patient.phone_number, body=body)

    if high:
        top = high[0]["medication"]
        # Store pending ID in a temporary escalation-safe way: persist in patient notes field
        # We reuse a lightweight approach: store JSON in a dedicated column-free way via EscalationCase notes
        # Actually: store the candidate IDs in patient.consent_channel as a transient JSON blob
        # (safe to overwrite; it's reset at onboarding complete)
        import json as _json
        patient.consent_channel = _json.dumps({"pending_med_ids": [m["medication"].id for m in high[:4]]})
        patient.onboarding_state = "medication_confirm_pending"
        db.commit()

        if len(high) == 1:
            cat = top.category or "medication"
            tmpl = MED_VERIFY_PROMPT.get(lang, MED_VERIFY_PROMPT["en"])
            _send_p(tmpl.format(name=top.name, category=cat))
        else:
            options = "\n".join(
                f"{i+1}. {m['medication'].name} ({m['medication'].category or 'medication'})"
                for i, m in enumerate(high[:4])
            )
            tmpl = MED_MULTI_PROMPT.get(lang, MED_MULTI_PROMPT["en"])
            _send_p(tmpl.format(options=options))

    elif low:
        # Moderate confidence — present as numbered list
        import json as _json
        patient.consent_channel = _json.dumps({"pending_med_ids": [m["medication"].id for m in low[:4]]})
        patient.onboarding_state = "medication_confirm_pending"
        db.commit()
        options = "\n".join(
            f"{i+1}. {m['medication'].name} ({m['medication'].category or 'medication'})"
            for i, m in enumerate(low[:4])
        )
        tmpl = MED_MULTI_PROMPT.get(lang, MED_MULTI_PROMPT["en"])
        _send_p(tmpl.format(options=options))

    else:
        # No match — prompt photo and escalate
        escalation_service.create_escalation(
            db=db, patient_id=patient.id, reason="unknown_medication", priority="normal"
        )
        _send_p(MED_NO_MATCH_PROMPT.get(lang, MED_NO_MATCH_PROMPT["en"]))


def handle_medication_confirm_reply(patient: Patient, text: str, db: Session) -> None:
    """
    Handles a reply while patient is in medication_confirm_pending state.
    YES/number → record_medication + advance to confirm, photo → OCR (handled in webhook).
    """
    import json as _json
    from app.services.onboarding_service import _send_patient, _handle_confirm_reply

    lang = patient.language_preference or "en"

    # Parse pending candidates from consent_channel
    pending_ids = []
    try:
        stored = _json.loads(patient.consent_channel or "{}")
        pending_ids = stored.get("pending_med_ids", [])
    except Exception:
        pass

    choice = text.strip().lower()

    # YES or "1" when only one candidate
    selected_id = None
    if choice in ("yes", "ya", "是", "iya"):
        selected_id = pending_ids[0] if pending_ids else None
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(pending_ids):
            selected_id = pending_ids[idx]

    if selected_id:
        from app.models.models import Medication as MedModel
        med = db.query(MedModel).filter(MedModel.id == selected_id).first()
        if med:
            existing = db.query(PatientMedication).filter(
                PatientMedication.patient_id == patient.id,
                PatientMedication.medication_id == selected_id,
            ).first()
            if not existing:
                pm = PatientMedication(patient_id=patient.id, medication_id=selected_id, is_active=False)
                db.add(pm)

            patient.onboarding_state = "confirm"
            patient.consent_channel = None
            db.commit()

            from app.services.telegram_service import send_text as _send
            _send(
                db=db,
                patient_id=patient.id,
                to_phone=patient.telegram_chat_id or patient.phone_number,
                body=f"Added: {med.name}. Enter another medication or reply *DONE* when finished.",
            )
            return

    # Not a valid selection — re-prompt with the list or treat as new med name
    if pending_ids and (choice.isdigit() or choice in ("yes", "ya", "是", "iya", "no", "tidak")):
        from app.services.telegram_service import send_text as _send
        _send(
            db=db,
            patient_id=patient.id,
            to_phone=patient.telegram_chat_id or patient.phone_number,
            body="Please reply with the number from the list, or type the medication name to search again.",
        )
    else:
        # Treat as a new medication name search
        patient.onboarding_state = "confirm"
        patient.consent_channel = None
        db.commit()
        verify_and_confirm_medication(patient, text, db)
