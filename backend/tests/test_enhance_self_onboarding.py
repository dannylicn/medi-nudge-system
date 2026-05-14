"""
Tests for enhance-smart-self-onboarding.

Tasks 18-24:
  18. _is_high_confidence() boundary cases
  19. OCR fast-path state transition: patient_pending → patient_confirmed → medication records
  20. OCR edit path: patient_pending → review
  21. _parse_frequency_to_times() coverage
  22. generate_info_card() — LLM path, fallback, safety filter
  23. Side-effect check-in job: creates campaign 3 days post-activation, no duplicates
  24. Check-in response routing: OK → resolved + DoseLog; SIDE EFFECT → escalation
"""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

WEBHOOK_URL = "/api/webhook/telegram"
DUMMY_SECRET = "test_telegram_webhook_secret"


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    import app.services.telegram_service as _ts
    monkeypatch.setattr(_ts.settings, "TELEGRAM_WEBHOOK_SECRET", DUMMY_SECRET)


def _make_patient(db, phone, state="complete", chat_id=None, lang="en"):
    from app.models.models import Patient
    p = Patient(
        full_name="Test Patient",
        phone_number=phone,
        telegram_chat_id=chat_id,
        language_preference=lang,
        risk_level="low",
        is_active=True,
        onboarding_state=state,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_scan(db, patient_id, fields_map, status="pending"):
    """Create a PrescriptionScan with ExtractedMedicationField rows."""
    from app.models.models import PrescriptionScan, ExtractedMedicationField
    scan = PrescriptionScan(
        patient_id=patient_id,
        image_path="/tmp/test.jpg",
        image_hash="abc123",
        source="telegram_photo",
        status=status,
    )
    db.add(scan)
    db.flush()
    for field_name, (value, confidence) in fields_map.items():
        db.add(ExtractedMedicationField(
            scan_id=scan.id,
            field_name=field_name,
            extracted_value=value,
            confidence=confidence,
        ))
    db.commit()
    db.refresh(scan)
    return scan


# ---------------------------------------------------------------------------
# Task 18: _is_high_confidence boundary cases
# ---------------------------------------------------------------------------

class TestIsHighConfidence:
    def _high_fields(self):
        return {
            "medication_name": ("Metformin", 0.92),
            "dosage": ("500mg", 0.88),
            "frequency": ("twice daily", 0.90),
            "dispense_date": ("2026-04-01", 0.80),
        }

    def test_all_above_threshold_returns_true(self, db):
        from app.services.ocr_service import _is_high_confidence
        p = _make_patient(db, "+6590001001")
        scan = _make_scan(db, p.id, self._high_fields())
        assert _is_high_confidence(scan) is True

    def test_required_field_at_boundary_085_returns_true(self, db):
        from app.services.ocr_service import _is_high_confidence
        fields = self._high_fields()
        fields["dosage"] = ("500mg", 0.85)  # exactly at threshold
        p = _make_patient(db, "+6590001002")
        scan = _make_scan(db, p.id, fields)
        assert _is_high_confidence(scan) is True

    def test_required_field_below_085_returns_false(self, db):
        from app.services.ocr_service import _is_high_confidence
        fields = self._high_fields()
        fields["dosage"] = ("500mg", 0.84)  # just below threshold
        p = _make_patient(db, "+6590001003")
        scan = _make_scan(db, p.id, fields)
        assert _is_high_confidence(scan) is False

    def test_missing_required_field_returns_false(self, db):
        from app.services.ocr_service import _is_high_confidence
        fields = self._high_fields()
        del fields["frequency"]
        p = _make_patient(db, "+6590001004")
        scan = _make_scan(db, p.id, fields)
        assert _is_high_confidence(scan) is False

    def test_no_date_field_returns_false(self, db):
        from app.services.ocr_service import _is_high_confidence
        fields = {
            "medication_name": ("Metformin", 0.92),
            "dosage": ("500mg", 0.88),
            "frequency": ("twice daily", 0.90),
            # no dispense_date or expiry_date
        }
        p = _make_patient(db, "+6590001005")
        scan = _make_scan(db, p.id, fields)
        assert _is_high_confidence(scan) is False


# ---------------------------------------------------------------------------
# Task 19: OCR fast-path state transition (patient_pending → patient_confirmed)
# ---------------------------------------------------------------------------

class TestOcrFastPath:
    def _high_scan_fields(self):
        return {
            "medication_name": ("Metformin 500mg", 0.92),
            "generic_name": ("Metformin", 0.90),
            "dosage": ("500mg", 0.88),
            "frequency": ("twice daily", 0.90),
            "dispense_date": ("2026-04-01", 0.80),
            "refill_days": ("30", 0.85),
        }

    def test_confirm_transitions_scan_and_creates_escalation(self, db):
        """CONFIRM reply: scan → patient_confirmed, low-priority escalation created."""
        from app.models.models import PrescriptionScan, EscalationCase
        import json

        p = _make_patient(db, "+6590002001", state="patient_pending_ocr_confirmation",
                          chat_id="200001")
        scan = _make_scan(db, p.id, self._high_scan_fields(), status="patient_pending")
        p.consent_channel = json.dumps({"pending_scan_id": scan.id})
        db.commit()

        with patch("app.routers.webhook.answer_callback_query"), \
             patch("app.services.telegram_service.send_text"), \
             patch("app.services.telegram_service.send_keyboard"), \
             patch("app.services.medication_info_service.generate_info_card", return_value="Info card"):
            from app.routers.webhook import _handle_ocr_confirm
            _handle_ocr_confirm(db, p)

        db.refresh(scan)
        db.refresh(p)
        assert scan.status == "patient_confirmed"
        assert p.onboarding_state == "confirm"
        # consent_channel may be set to schedule-confirm state; pending_scan_id should be cleared
        if p.consent_channel:
            import json as _j
            ch = _j.loads(p.consent_channel)
            assert "pending_scan_id" not in ch

        esc = db.query(EscalationCase).filter(
            EscalationCase.patient_id == p.id,
            EscalationCase.reason == "ocr_patient_confirmed",
        ).first()
        assert esc is not None
        assert esc.priority == "low"

    def test_confirm_creates_patient_medication(self, db):
        """CONFIRM reply: PatientMedication record is auto-populated from scan fields."""
        from app.models.models import PatientMedication
        import json

        p = _make_patient(db, "+6590002002", state="patient_pending_ocr_confirmation",
                          chat_id="200002")
        scan = _make_scan(db, p.id, self._high_scan_fields(), status="patient_pending")
        p.consent_channel = json.dumps({"pending_scan_id": scan.id})
        db.commit()

        with patch("app.services.telegram_service.send_text"), \
             patch("app.services.telegram_service.send_keyboard"), \
             patch("app.services.medication_info_service.generate_info_card", return_value="Info card"):
            from app.routers.webhook import _handle_ocr_confirm
            _handle_ocr_confirm(db, p)

        pm = db.query(PatientMedication).filter(PatientMedication.patient_id == p.id).first()
        assert pm is not None
        assert pm.is_active is True


# ---------------------------------------------------------------------------
# Task 20: OCR edit path
# ---------------------------------------------------------------------------

class TestOcrEditPath:
    def test_edit_transitions_scan_to_review(self, db):
        """EDIT reply: scan → review, patient state → medication_capture."""
        from app.models.models import PrescriptionScan
        import json

        p = _make_patient(db, "+6590003001", state="patient_pending_ocr_confirmation",
                          chat_id="300001")
        scan = _make_scan(db, p.id, {
            "medication_name": ("Metformin", 0.92),
            "dosage": ("500mg", 0.88),
        }, status="patient_pending")
        p.consent_channel = json.dumps({"pending_scan_id": scan.id})
        db.commit()

        with patch("app.services.telegram_service.send_text"), \
             patch("app.services.telegram_service.send_keyboard"):
            from app.routers.webhook import _handle_ocr_edit
            _handle_ocr_edit(db, p)

        db.refresh(scan)
        db.refresh(p)
        assert scan.status == "review"
        assert p.onboarding_state == "medication_capture"
        assert p.consent_channel is None


# ---------------------------------------------------------------------------
# Task 21: _parse_frequency_to_times
# ---------------------------------------------------------------------------

class TestParseFrequencyToTimes:
    def _parse(self, text):
        from app.services.ocr_service import _parse_frequency_to_times
        return _parse_frequency_to_times(text)

    def test_twice_daily(self):
        assert self._parse("twice daily") == ["08:00", "20:00"]

    def test_bd_abbreviation(self):
        assert self._parse("bd") == ["08:00", "20:00"]

    def test_once_daily(self):
        assert self._parse("once daily") == ["08:00"]

    def test_od_abbreviation(self):
        assert self._parse("Take 1 tablet od") == ["08:00"]

    def test_three_times_daily(self):
        assert self._parse("three times daily") == ["08:00", "14:00", "20:00"]

    def test_tds(self):
        assert self._parse("TDS") == ["08:00", "14:00", "20:00"]

    def test_four_times(self):
        assert self._parse("four times daily") == ["08:00", "12:00", "16:00", "20:00"]

    def test_with_meals(self):
        assert self._parse("with meals") == ["07:30", "12:30", "18:30"]

    def test_nocte(self):
        assert self._parse("nocte") == ["21:00"]

    def test_at_night(self):
        assert self._parse("at night") == ["21:00"]

    def test_unknown_returns_empty(self):
        assert self._parse("as required") == []

    def test_none_returns_empty(self):
        assert self._parse(None) == []


# ---------------------------------------------------------------------------
# Task 22: generate_info_card
# ---------------------------------------------------------------------------

class TestGenerateInfoCard:
    def test_returns_llm_content_when_available(self):
        from app.services.medication_info_service import generate_info_card

        with patch("app.services.medication_info_service.settings") as mock_settings, \
             patch("app.services.medication_info_service._llm_info_card") as mock_llm:
            mock_settings.OPENAI_API_KEY = "fake_key"
            mock_settings.LLM_BASE_URL = ""
            mock_llm.return_value = "Metformin helps manage diabetes. Watch for nausea. Reply SIDE EFFECT if unwell."
            result = generate_info_card("Metformin", "en")

        assert "Metformin" in result
        assert "SIDE EFFECT" in result

    def test_falls_back_to_template_when_llm_unavailable(self):
        from app.services.medication_info_service import generate_info_card

        with patch("app.services.medication_info_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.LLM_BASE_URL = ""
            result = generate_info_card("Amlodipine", "en")

        assert "Amlodipine" in result
        assert "SIDE EFFECT" in result

    def test_safety_filter_discards_dosage_word(self):
        from app.services.medication_info_service import generate_info_card

        with patch("app.services.medication_info_service.settings") as mock_settings, \
             patch("app.services.medication_info_service._llm_info_card") as mock_llm:
            mock_settings.OPENAI_API_KEY = "fake_key"
            mock_settings.LLM_BASE_URL = ""
            # LLM returns unsafe content containing "dosage"
            mock_llm.return_value = "Take the correct dosage every morning. Reply SIDE EFFECT if unwell."
            result = generate_info_card("Metformin", "en")

        # Should use fallback template, not the LLM output with "dosage"
        assert "dosage" not in result.lower() or "chronic condition" in result

    def test_fallback_works_for_all_languages(self):
        from app.services.medication_info_service import generate_info_card

        with patch("app.services.medication_info_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.LLM_BASE_URL = ""
            for lang in ("en", "zh", "ms", "ta"):
                result = generate_info_card("Metformin", lang)
                assert "Metformin" in result
                assert len(result) > 20


# ---------------------------------------------------------------------------
# Task 23: Side-effect check-in job
# ---------------------------------------------------------------------------

class TestSideEffectCheckinJob:
    def _make_medication(self, db, name="Metformin", generic="metformin_test_checkin"):
        from app.models.models import Medication
        med = Medication(name=name, generic_name=generic, default_refill_days=30)
        db.add(med)
        db.commit()
        db.refresh(med)
        return med

    def _make_pm(self, db, patient_id, med_id, days_ago=3):
        from app.models.models import PatientMedication
        created = datetime.utcnow() - timedelta(days=days_ago, hours=1)
        pm = PatientMedication(
            patient_id=patient_id,
            medication_id=med_id,
            is_active=True,
            created_at=created,
        )
        db.add(pm)
        db.commit()
        db.refresh(pm)
        return pm

    def test_creates_campaign_3_days_post_activation(self, db):
        from app.models.models import NudgeCampaign
        from app.services.side_effect_checkin_service import run_side_effect_checkin_check

        p = _make_patient(db, "+6590004001", state="complete", chat_id="400001")
        med = self._make_medication(db)
        self._make_pm(db, p.id, med.id, days_ago=3)

        with patch("app.services.telegram_service.send_keyboard") as mock_kbd:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_kbd.return_value = mock_msg
            results = run_side_effect_checkin_check(db)

        assert results["sent"] >= 1
        campaign = db.query(NudgeCampaign).filter(
            NudgeCampaign.patient_id == p.id,
            NudgeCampaign.campaign_type == "side_effect_checkin",
        ).first()
        assert campaign is not None
        # Campaign is created in "pending" state — scheduler fires it at fire_at
        assert campaign.status == "pending"
        assert campaign.fire_at is not None

    def test_does_not_duplicate(self, db):
        from app.models.models import NudgeCampaign
        from app.services.side_effect_checkin_service import run_side_effect_checkin_check

        p = _make_patient(db, "+6590004002", state="complete", chat_id="400002")
        med = self._make_medication(db, name="Amlodipine", generic="amlodipine_checkin_dup")
        self._make_pm(db, p.id, med.id, days_ago=3)

        with patch("app.services.telegram_service.send_keyboard") as mock_kbd:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_kbd.return_value = mock_msg
            run_side_effect_checkin_check(db)
            run_side_effect_checkin_check(db)  # second run should not duplicate

        count = db.query(NudgeCampaign).filter(
            NudgeCampaign.patient_id == p.id,
            NudgeCampaign.campaign_type == "side_effect_checkin",
        ).count()
        assert count == 1

    def test_skips_patient_still_in_onboarding(self, db):
        from app.models.models import NudgeCampaign
        from app.services.side_effect_checkin_service import run_side_effect_checkin_check

        p = _make_patient(db, "+6590004003", state="medication_capture", chat_id="400003")
        med = self._make_medication(db, name="Losartan", generic="losartan_checkin_skip")
        self._make_pm(db, p.id, med.id, days_ago=3)

        with patch("app.services.telegram_service.send_keyboard"):
            results = run_side_effect_checkin_check(db)

        campaign = db.query(NudgeCampaign).filter(
            NudgeCampaign.patient_id == p.id,
            NudgeCampaign.campaign_type == "side_effect_checkin",
        ).first()
        assert campaign is None
        assert results["skipped"] >= 1


# ---------------------------------------------------------------------------
# Task 24: Check-in response routing
# ---------------------------------------------------------------------------

class TestCheckinResponseRouting:
    def _make_checkin_campaign(self, db, patient_id, med_id, status="sent"):
        from app.models.models import NudgeCampaign
        c = NudgeCampaign(
            patient_id=patient_id,
            medication_id=med_id,
            status=status,
            campaign_type="side_effect_checkin",
            days_overdue=0,
            attempt_number=1,
            language="en",
            last_sent_at=datetime.utcnow(),
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    def test_ok_reply_resolves_campaign_and_logs_no_issue(self, db):
        from app.models.models import NudgeCampaign, Medication, DoseLog
        from app.services.nudge_campaign_service import handle_response

        p = _make_patient(db, "+6590005001", state="complete", chat_id="500001")
        med = Medication(name="Metformin", generic_name="metformin_routing_ok", default_refill_days=30)
        db.add(med)
        db.commit()
        campaign = self._make_checkin_campaign(db, p.id, med.id)

        with patch("app.services.telegram_service.send_text"):
            handle_response(db, campaign, "YES", "confirmed")

        db.refresh(campaign)
        assert campaign.status == "resolved"

        dose_log = db.query(DoseLog).filter(
            DoseLog.patient_id == p.id,
            DoseLog.medication_id == med.id,
            DoseLog.status == "no_issue",
            DoseLog.source == "checkin_ok",
        ).first()
        assert dose_log is not None

    def test_side_effect_reply_creates_urgent_escalation(self, db):
        from app.models.models import NudgeCampaign, Medication, EscalationCase
        from app.services.nudge_campaign_service import handle_response

        p = _make_patient(db, "+6590005002", state="complete", chat_id="500002")
        med = Medication(name="Amlodipine", generic_name="amlodipine_routing_se", default_refill_days=30)
        db.add(med)
        db.commit()
        campaign = self._make_checkin_campaign(db, p.id, med.id)

        with patch("app.services.telegram_service.send_text"):
            handle_response(db, campaign, "SIDE EFFECT", "side_effect")

        db.refresh(campaign)
        assert campaign.status == "escalated"

        esc = db.query(EscalationCase).filter(
            EscalationCase.patient_id == p.id,
            EscalationCase.reason == "side_effect",
            EscalationCase.priority == "urgent",
        ).first()
        assert esc is not None
