"""
Onboarding flow tests.
- Patient creation triggers invite
- YES reply → consent_pending, language prompt sent
- Language reply → complete, welcome message sent
- NO reply → patient deactivated
- Drop-off recovery after retries → escalation
- Full webhook integration: invite → YES → language → complete
"""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytest


class TestOnboardingService:
    def test_send_invite_sets_state(self, db):
        """send_invite should set onboarding_state to 'invited' and send message."""
        from app.models.models import Patient
        from app.services.onboarding_service import send_invite

        patient = Patient(
            full_name="Invite Test",
            phone_number="100001",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with patch("app.services.telegram_service.send_text") as mock_send:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_send.return_value = mock_msg
            send_invite(db, patient)

        db.refresh(patient)
        assert patient.onboarding_state == "invited"
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert "Medi-Nudge" in call_kwargs.kwargs.get("body", call_kwargs[1].get("body", ""))

    def test_invite_reply_yes_transitions_to_consent_pending(self, db):
        """Replying YES to invite should set consent and move to consent_pending."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_onboarding_reply

        patient = Patient(
            full_name="Yes Reply",
            phone_number="100002",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="invited",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with patch("app.services.telegram_service.send_text") as mock_send:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_send.return_value = mock_msg
            handle_onboarding_reply(db, patient, "Yes")

        db.refresh(patient)
        assert patient.onboarding_state == "consent_pending"
        assert patient.consent_obtained_at is not None
        assert patient.consent_channel == "telegram"
        # Should send language selection prompt
        mock_send.assert_called_once()

    def test_invite_reply_no_deactivates_patient(self, db):
        """Replying NO to invite should deactivate the patient."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_onboarding_reply

        patient = Patient(
            full_name="No Reply",
            phone_number="100003",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="invited",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        handle_onboarding_reply(db, patient, "No")

        db.refresh(patient)
        assert patient.is_active is False

    def test_language_reply_completes_onboarding(self, db):
        """Selecting a language after consent should complete onboarding."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_onboarding_reply

        patient = Patient(
            full_name="Lang Select",
            phone_number="100004",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="consent_pending",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with patch("app.services.telegram_service.send_text") as mock_send:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_send.return_value = mock_msg
            handle_onboarding_reply(db, patient, "2")  # Chinese

        db.refresh(patient)
        assert patient.onboarding_state == "complete"
        assert patient.language_preference == "zh"
        # Should send welcome message
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        body = call_kwargs.kwargs.get("body", call_kwargs[1].get("body", ""))
        assert "Medi-Nudge" in body

    def test_language_reply_english(self, db):
        """Selecting English should set language to 'en' and complete."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_onboarding_reply

        patient = Patient(
            full_name="English Select",
            phone_number="100005",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="consent_pending",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with patch("app.services.telegram_service.send_text") as mock_send:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_send.return_value = mock_msg
            handle_onboarding_reply(db, patient, "1")

        db.refresh(patient)
        assert patient.onboarding_state == "complete"
        assert patient.language_preference == "en"

    def test_language_reply_malay(self, db):
        """Selecting Malay should set language to 'ms' and complete."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_onboarding_reply

        patient = Patient(
            full_name="Malay Select",
            phone_number="100006",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="consent_pending",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with patch("app.services.telegram_service.send_text") as mock_send:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_send.return_value = mock_msg
            handle_onboarding_reply(db, patient, "3")

        db.refresh(patient)
        assert patient.onboarding_state == "complete"
        assert patient.language_preference == "ms"

    def test_invalid_language_stays_in_consent_pending(self, db):
        """Invalid language reply should keep state as consent_pending."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_onboarding_reply

        patient = Patient(
            full_name="Bad Lang",
            phone_number="100007",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="consent_pending",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        handle_onboarding_reply(db, patient, "hello world")

        db.refresh(patient)
        assert patient.onboarding_state == "consent_pending"

    def test_drop_off_retries_then_escalates(self, db):
        """Drop-off with retry_count >= 2 should create an escalation."""
        from app.models.models import Patient, EscalationCase
        from app.services.onboarding_service import handle_drop_off

        patient = Patient(
            full_name="Drop Off Patient",
            phone_number="100008",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="invited",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        handle_drop_off(db, patient, retry_count=2)

        db.refresh(patient)
        assert patient.onboarding_state == "drop_off_recovery"
        esc = db.query(EscalationCase).filter(
            EscalationCase.patient_id == patient.id
        ).first()
        assert esc is not None
        assert esc.reason == "onboarding_drop_off"

    def test_drop_off_retry_resends_invite(self, db):
        """Drop-off with retry_count < 2 should re-send invite."""
        from app.models.models import Patient
        from app.services.onboarding_service import handle_drop_off

        patient = Patient(
            full_name="Retry Patient",
            phone_number="100009",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="invited",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with patch("app.services.telegram_service.send_text") as mock_send:
            mock_msg = MagicMock()
            mock_msg.status = "sent"
            mock_send.return_value = mock_msg
            handle_drop_off(db, patient, retry_count=1)

        mock_send.assert_called_once()
        db.refresh(patient)
        assert patient.onboarding_state == "invited"


class TestOnboardingWebhookIntegration:
    @patch("app.services.telegram_service.send_text")
    def test_full_onboarding_via_webhook(self, mock_send, client, db):
        """End-to-end: patient created → invite → YES → language → complete."""
        from app.models.models import Patient

        mock_msg = MagicMock()
        mock_msg.status = "sent"
        mock_send.return_value = mock_msg

        # Create a patient in invited state
        patient = Patient(
            full_name="E2E Onboarding",
            phone_number="200001",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="invited",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        # Step 1: Patient replies YES
        with patch("app.routers.webhook.validate_telegram_token", return_value=True):
            resp = client.post(
                "/api/webhook/telegram",
                json={
                    "update_id": 301,
                    "message": {
                        "message_id": 1,
                        "from": {"id": 200001, "is_bot": False, "first_name": "E2E"},
                        "chat": {"id": 200001, "type": "private"},
                        "text": "Yes",
                    },
                },
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid"},
            )
        assert resp.status_code == 200
        db.refresh(patient)
        assert patient.onboarding_state == "consent_pending"
        assert patient.consent_channel == "telegram"

        # Step 2: Patient picks language (Chinese)
        with patch("app.routers.webhook.validate_telegram_token", return_value=True):
            resp = client.post(
                "/api/webhook/telegram",
                json={
                    "update_id": 302,
                    "message": {
                        "message_id": 2,
                        "from": {"id": 200001, "is_bot": False, "first_name": "E2E"},
                        "chat": {"id": 200001, "type": "private"},
                        "text": "2",
                    },
                },
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid"},
            )
        assert resp.status_code == 200
        db.refresh(patient)
        assert patient.onboarding_state == "complete"
        assert patient.language_preference == "zh"

    @patch("app.services.telegram_service.send_text")
    def test_completed_patient_not_routed_to_onboarding(self, mock_send, client, db):
        """A patient with onboarding_state='complete' should go through nudge path."""
        from app.models.models import Patient

        patient = Patient(
            full_name="Completed Patient",
            phone_number="200002",
            language_preference="en",
            risk_level="low",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(patient)
        db.commit()

        with patch("app.routers.webhook.validate_telegram_token", return_value=True):
            resp = client.post(
                "/api/webhook/telegram",
                json={
                    "update_id": 303,
                    "message": {
                        "message_id": 3,
                        "from": {"id": 200002, "is_bot": False, "first_name": "Done"},
                        "chat": {"id": 200002, "type": "private"},
                        "text": "Yes",
                    },
                },
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid"},
            )
        assert resp.status_code == 200
        # Should NOT have changed onboarding state
        db.refresh(patient)
        assert patient.onboarding_state == "complete"
