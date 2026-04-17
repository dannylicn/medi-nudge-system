"""
Tests for make-bot-agentic:
- medication_service.fuzzy_search
- agent_service tools (guard conditions)
- agent_service._build_context (PII stripping)
- Integration: fallback agent behaviour
- Integration: medicine verification gate
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.models import (
    Patient, Medication, PatientMedication, NudgeCampaign,
    EscalationCase, OutboundMessage,
)
from app.services import medication_service, agent_service


# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    Sess = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    s = Sess()
    try:
        yield s
    finally:
        s.close()


def _make_patient(db, phone="+6591000001", chat_id="1001", state="complete", is_active=True):
    p = Patient(
        full_name="Test Patient",
        phone_number=phone,
        language_preference="en",
        conditions=["Diabetes"],
        risk_level="normal",
        is_active=is_active,
        onboarding_state=state,
        telegram_chat_id=chat_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_medication(db, name="Metformin", generic="Metformin", category="Diabetes"):
    med = Medication(name=name, generic_name=generic, category=category, default_refill_days=30)
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


# ===========================================================================
# fuzzy_search tests
# ===========================================================================

class TestFuzzySearch:
    def test_exact_name_match_returns_confidence_1(self, db):
        _make_medication(db, name="Metformin", generic="Metformin")
        results = medication_service.fuzzy_search("Metformin", db)
        assert results, "Expected at least one result"
        assert results[0]["confidence"] == 1.0
        assert results[0]["medication"].name == "Metformin"

    def test_typo_metormin_matches_metformin(self, db):
        _make_medication(db, name="Metformin", generic="Metformin")
        results = medication_service.fuzzy_search("metormin", db, limit=5)
        names = [r["medication"].name for r in results]
        assert "Metformin" in names, f"Expected Metformin in results, got: {names}"
        top = next(r for r in results if r["medication"].name == "Metformin")
        assert top["confidence"] >= 0.75, f"Expected confidence ≥ 0.75, got {top['confidence']}"

    def test_no_match_returns_empty(self, db):
        _make_medication(db, name="Metformin", generic="Metformin")
        results = medication_service.fuzzy_search("zylomycin", db)
        assert results == [], f"Expected empty list, got: {results}"

    def test_fuzzy_search_never_modifies_table(self, db):
        _make_medication(db, name="Metformin", generic="Metformin")
        before = db.query(Medication).count()
        medication_service.fuzzy_search("anything", db)
        after = db.query(Medication).count()
        assert before == after, "fuzzy_search must not add rows to medications table"

    def test_generic_name_match(self, db):
        _make_medication(db, name="Lipitor", generic="Atorvastatin", category="Hyperlipidaemia")
        results = medication_service.fuzzy_search("atorvastatin", db)
        assert results, "Expected match on generic_name"
        assert results[0]["medication"].name == "Lipitor"

    def test_empty_query_returns_empty(self, db):
        _make_medication(db, name="Metformin", generic="Metformin")
        assert medication_service.fuzzy_search("", db) == []
        assert medication_service.fuzzy_search("  ", db) == []


# ===========================================================================
# agent_service._build_context PII stripping
# ===========================================================================

class TestBuildContext:
    def test_strips_nric_hash_and_phone(self, db):
        patient = _make_patient(db)
        patient.nric_hash = "abc123hash"
        db.commit()

        ctx = agent_service._build_context(patient, db)

        assert "nric_hash" not in ctx, "nric_hash must not appear in LLM context"
        assert "phone_number" not in ctx, "phone_number must not appear in LLM context"

    def test_includes_patient_name_and_language(self, db):
        patient = _make_patient(db)
        ctx = agent_service._build_context(patient, db)
        assert ctx["patient_name"] == "Test Patient"
        assert ctx["patient_language"] == "en"

    def test_active_campaign_included(self, db):
        patient = _make_patient(db)
        med = _make_medication(db)
        campaign = NudgeCampaign(
            patient_id=patient.id, medication_id=med.id,
            status="sent", days_overdue=5, attempt_number=1, language="en",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        ctx = agent_service._build_context(patient, db)
        assert ctx["active_campaign"] is not None
        assert ctx["active_campaign"]["days_overdue"] == 5
        assert ctx["active_campaign"]["medication"] == "Metformin"


# ===========================================================================
# Tool guard conditions
# ===========================================================================

class TestToolGuards:
    def test_confirm_adherence_no_open_campaign(self, db):
        patient = _make_patient(db)
        result = agent_service._tool_confirm_adherence(
            args={"campaign_id": 9999}, patient=patient, db=db
        )
        assert "error" in result
        assert result.get("terminal") is False

    def test_confirm_adherence_wrong_patient(self, db):
        p1 = _make_patient(db, phone="+6591000001", chat_id="1001")
        p2 = _make_patient(db, phone="+6591000002", chat_id="1002")
        med = _make_medication(db)
        campaign = NudgeCampaign(
            patient_id=p1.id, medication_id=med.id,
            status="sent", days_overdue=3, attempt_number=1, language="en",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        # p2 tries to confirm p1's campaign
        result = agent_service._tool_confirm_adherence(
            args={"campaign_id": campaign.id}, patient=p2, db=db
        )
        assert "error" in result

    def test_record_medication_rejects_nonexistent_id(self, db):
        patient = _make_patient(db)
        result = agent_service._tool_record_medication(
            args={"medication_id": 99999}, patient=patient, db=db
        )
        assert "error" in result
        assert result.get("terminal") is False

    def test_record_medication_valid_id_creates_record(self, db):
        patient = _make_patient(db)
        med = _make_medication(db)
        with patch("app.services.telegram_service.send_text"):
            result = agent_service._tool_record_medication(
                args={"medication_id": med.id}, patient=patient, db=db
            )
        assert result.get("recorded") is True
        assert result.get("terminal") is True
        pm = db.query(PatientMedication).filter(
            PatientMedication.patient_id == patient.id,
            PatientMedication.medication_id == med.id,
        ).first()
        assert pm is not None


# ===========================================================================
# Integration: rule-based fallback (LLM key absent)
# ===========================================================================

class TestFallbackAgent:
    def test_singlish_taken_resolves_campaign(self, db):
        patient = _make_patient(db)
        med = _make_medication(db)
        campaign = NudgeCampaign(
            patient_id=patient.id, medication_id=med.id,
            status="sent", days_overdue=3, attempt_number=1, language="en",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        with patch("app.services.telegram_service.send_text"), \
             patch.object(agent_service.settings, "OPENAI_API_KEY", ""), \
             patch.object(agent_service.settings, "LLM_BASE_URL", ""):
            agent_service._fallback_agent(patient, "yes I took it already", db)

        db.refresh(campaign)
        assert campaign.status == "resolved"

    def test_side_effect_message_escalates_urgently(self, db):
        patient = _make_patient(db)

        with patch("app.services.telegram_service.send_text"):
            agent_service._fallback_agent(patient, "I feel very unwell and have nausea after taking the pill", db)

        esc = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id,
            EscalationCase.reason == "side_effect",
        ).first()
        assert esc is not None
        assert esc.priority == "urgent"

    def test_question_creates_normal_escalation(self, db):
        patient = _make_patient(db)

        with patch("app.services.telegram_service.send_text"):
            agent_service._fallback_agent(patient, "what time should I take my medication?", db)

        esc = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id,
            EscalationCase.reason == "patient_question",
        ).first()
        assert esc is not None

    def test_llm_absent_uses_fallback(self, db):
        """When no LLM key, agent_service.run() must behave identically to fallback."""
        patient = _make_patient(db)
        med = _make_medication(db)
        campaign = NudgeCampaign(
            patient_id=patient.id, medication_id=med.id,
            status="sent", days_overdue=1, attempt_number=1, language="en",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        # Patch settings at the agent_service module level (where it's imported)
        with patch.object(agent_service.settings, "OPENAI_API_KEY", ""), \
             patch.object(agent_service.settings, "LLM_BASE_URL", ""), \
             patch("app.services.telegram_service.send_text"):
            agent_service.run(patient, "yes collected", db)

        db.refresh(campaign)
        assert campaign.status == "resolved"


# ===========================================================================
# Integration: medicine verification gate
# ===========================================================================

class TestMedicineVerificationGate:
    def test_typo_medicine_triggers_verify_flow(self, db):
        _make_medication(db, name="Metformin", generic="Metformin", category="Diabetes")
        patient = _make_patient(db, state="confirm")

        with patch("app.services.telegram_service.send_text") as mock_send:
            agent_service.verify_and_confirm_medication(patient, "metormin", db)

        db.refresh(patient)
        assert patient.onboarding_state == "medication_confirm_pending"
        assert mock_send.called
        # Message should mention "Metformin"
        sent_body = mock_send.call_args[1].get("body") or mock_send.call_args[0][3]
        assert "Metformin" in sent_body

    def test_patient_confirms_candidate_creates_patient_medication(self, db):
        import json
        med = _make_medication(db, name="Metformin", generic="Metformin", category="Diabetes")
        patient = _make_patient(db, state="medication_confirm_pending")
        patient.consent_channel = json.dumps({"pending_med_ids": [med.id]})
        db.commit()

        with patch("app.services.telegram_service.send_text"):
            agent_service.handle_medication_confirm_reply(patient, "yes", db)

        db.refresh(patient)
        assert patient.onboarding_state == "confirm"
        pm = db.query(PatientMedication).filter(
            PatientMedication.patient_id == patient.id,
            PatientMedication.medication_id == med.id,
        ).first()
        assert pm is not None

    def test_unknown_medicine_escalates_and_prompts_photo(self, db):
        # Catalogue has only Metformin — "zylomycin" won't match
        _make_medication(db, name="Metformin", generic="Metformin", category="Diabetes")
        patient = _make_patient(db, state="confirm")

        with patch("app.services.telegram_service.send_text") as mock_send:
            agent_service.verify_and_confirm_medication(patient, "zylomycin", db)

        esc = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id,
            EscalationCase.reason == "unknown_medication",
        ).first()
        assert esc is not None
        assert mock_send.called
