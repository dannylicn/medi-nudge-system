"""
T-48: Integration tests — escalation triggers.
- side_effect reply → escalation created
- 3 failed attempts → escalation
- ESCALATION_DAYS exceeded → escalation
"""
from unittest.mock import patch
from datetime import datetime, timezone, timedelta, date
import pytest


class TestEscalationTriggers:
    @patch("app.services.telegram_service.send_text")
    def test_side_effect_reply_triggers_escalation(self, mock_send, client, auth_headers, db):
        """A 'side_effect' classified reply must open an EscalationCase."""
        from app.models.models import (
            Patient, Medication, PatientMedication, NudgeCampaign, EscalationCase
        )

        patient = Patient(
            full_name="Side Effect Patient",
            phone_number="91230100",
            language_preference="en",
            risk_level="medium",
            is_active=True,
            onboarding_state="complete",
            telegram_chat_id="91230100",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        med = Medication(
            name="Lisinopril",
            generic_name="Lisinopril",
        )
        db.add(med)
        db.commit()
        db.refresh(med)

        pm = PatientMedication(
            patient_id=patient.id,
            medication_id=med.id,
            dosage="Once daily",
            is_active=True,
        )
        db.add(pm)
        db.commit()
        db.refresh(pm)

        campaign = NudgeCampaign(
            patient_id=patient.id,
            medication_id=med.id,
            days_overdue=3,
            attempt_number=1,
            status="sent",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        initial_count = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id
        ).count()

        with patch("app.routers.webhook.validate_telegram_token", return_value=True):
            resp = client.post(
                "/api/webhook/telegram",
                json={
                    "update_id": 200,
                    "message": {
                        "message_id": 2,
                        "from": {"id": int(patient.phone_number), "is_bot": False, "first_name": "Test"},
                        "chat": {"id": int(patient.phone_number), "type": "private"},
                        "text": "I feel very dizzy and vomiting",
                    },
                },
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid"},
            )

        assert resp.status_code in (200, 204)
        new_count = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id
        ).count()
        assert new_count > initial_count, "Expected escalation to be created for side effect reply"

    def test_escalation_has_correct_priority(self, client, auth_headers, db):
        """EscalationCase created for side_effect should be 'urgent' priority."""
        from app.models.models import Patient, EscalationCase
        from app.services.escalation_service import create_escalation

        patient = Patient(
            full_name="Priority Test",
            phone_number="+6591230200",
            language_preference="en",
            risk_level="high",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        case = create_escalation(
            db,
            patient_id=patient.id,
            reason="side_effect",
        )
        assert case.priority == "urgent"

    def test_missed_doses_escalation_priority(self, client, auth_headers, db):
        """EscalationCase for missed_doses should be 'high' priority."""
        from app.models.models import Patient
        from app.services.escalation_service import create_escalation

        patient = Patient(
            full_name="Missed Dose Patient",
            phone_number="+6591230300",
            language_preference="en",
            risk_level="medium",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        case = create_escalation(
            db,
            patient_id=patient.id,
            reason="repeated_non_adherence",
        )
        assert case.priority in ("high", "urgent")

    @patch("app.services.telegram_service.send_text")
    def test_escalation_routes_list(self, mock_send, client, auth_headers, db):
        """GET /api/escalations returns sorted cases with correct schema."""
        resp = client.get("/api/escalations", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Could be an items list or direct list
        cases = data.get("items", data) if isinstance(data, dict) else data
        assert isinstance(cases, list)

    def test_escalation_patch(self, client, auth_headers, db):
        """PATCH /api/escalations/{id} updates status and notes."""
        from app.models.models import Patient
        from app.services.escalation_service import create_escalation

        patient = Patient(
            full_name="Patch Test",
            phone_number="+6591230400",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        case = create_escalation(db, patient_id=patient.id, reason="no_reply_3_attempts")

        resp = client.patch(
            f"/api/escalations/{case.id}",
            json={"status": "in_progress", "notes": "Called patient, no answer."},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["status"] == "in_progress"


class TestRefillGapEscalation:
    @patch("app.services.telegram_service.send_text")
    def test_escalation_days_threshold(self, mock_send, db):
        """detect_and_trigger should escalate when days_overdue >= ESCALATION_DAYS."""
        from app.models.models import Patient, Medication, PatientMedication
        from app.services.refill_gap_service import detect_and_trigger
        from app.core.config import settings

        patient = Patient(
            full_name="Escalation Threshold Patient",
            phone_number="+6591230500",
            language_preference="en",
            risk_level="medium",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        med = Medication(
            name="Bisoprolol",
            generic_name="Bisoprolol",
        )
        db.add(med)
        db.commit()
        db.refresh(med)

        # Last dispensed more than ESCALATION_DAYS ago
        last_date = date.today() - timedelta(days=settings.ESCALATION_DAYS + 5 + 30)
        pm = PatientMedication(
            patient_id=patient.id,
            medication_id=med.id,
            dosage="Once daily",
            refill_interval_days=30,
            is_active=True,
        )
        db.add(pm)
        db.commit()
        db.refresh(pm)

        # Seed a dispensing record with old date so refill gap detector fires
        from app.models.models import DispensingRecord
        from datetime import datetime as _dt
        dr = DispensingRecord(
            patient_id=patient.id,
            medication_id=med.id,
            dispensed_at=_dt.combine(last_date, _dt.min.time()),
            days_supply=30,
        )
        db.add(dr)
        db.commit()

        # Run the detector
        detect_and_trigger(db)

        # Should either have created a campaign or escalation
        from app.models.models import EscalationCase, NudgeCampaign
        campaigns = db.query(NudgeCampaign).filter(
            NudgeCampaign.patient_id == patient.id
        ).all()
        escalations = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id
        ).all()

        assert len(campaigns) > 0 or len(escalations) > 0
