"""
T-50: Webhook security tests.
- Missing/invalid Telegram webhook secret → 403
- Valid secret → processes normally
"""
from unittest.mock import patch
import pytest
import json


WEBHOOK_URL = "/api/webhook/telegram"
DUMMY_SECRET = "test_telegram_webhook_secret"


def _telegram_update(chat_id: str = "123456789", text: str = "Yes"):
    """Build a minimal Telegram Update object."""
    return {
        "update_id": 100,
        "message": {
            "message_id": 1,
            "from": {"id": int(chat_id), "is_bot": False, "first_name": "Test"},
            "chat": {"id": int(chat_id), "type": "private"},
            "text": text,
        },
    }


class TestWebhookSecurity:
    def test_invalid_secret_returns_403(self, client):
        """Requests with an invalid Telegram webhook secret must be rejected with 403."""
        resp = client.post(
            WEBHOOK_URL,
            json=_telegram_update(),
            headers={"X-Telegram-Bot-Api-Secret-Token": "INVALID"},
        )
        assert resp.status_code == 403, (
            f"Expected 403 for invalid secret, got {resp.status_code}: {resp.text}"
        )

    def test_missing_secret_returns_403(self, client):
        """Requests without X-Telegram-Bot-Api-Secret-Token header must be rejected."""
        resp = client.post(
            WEBHOOK_URL,
            json=_telegram_update(),
        )
        assert resp.status_code in (403, 422), (
            f"Expected 403/422 for missing secret, got {resp.status_code}"
        )

    @patch("app.services.telegram_service.send_text")
    def test_valid_secret_processes(self, mock_send, client, db):
        """A request with a valid webhook secret (mocked validation) is processed."""
        from app.models.models import Patient

        chat_id = "123456789"
        existing = db.query(Patient).filter(
            Patient.phone_number == chat_id
        ).first()
        if not existing:
            p = Patient(
                full_name="Webhook Test Patient",
                phone_number=chat_id,
                language_preference="en",
                risk_level="low",
                is_active=True,
                onboarding_state="complete",
            )
            db.add(p)
            db.commit()

        with patch("app.routers.webhook.validate_telegram_token", return_value=True):
            resp = client.post(
                WEBHOOK_URL,
                json=_telegram_update(chat_id=chat_id),
                headers={"X-Telegram-Bot-Api-Secret-Token": "valid"},
            )

        assert resp.status_code in (200, 204), (
            f"Expected 200/204 for valid secret, got {resp.status_code}: {resp.text}"
        )


class TestWebhookNricNotLeaked:
    def test_nric_hash_not_in_patient_response(self, client, auth_headers, db):
        """Patient API response must not include nric_hash."""
        from app.models.models import Patient
        from app.core.config import hash_sha256

        p = Patient(
            full_name="NRIC Test",
            phone_number="+6591230600",
            language_preference="en",
            nric_hash=hash_sha256("S1234567D"),
            risk_level="low",
            is_active=True,
            onboarding_state="complete",
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        resp = client.get(f"/api/patients/{p.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        # nric_hash must never appear in response
        assert "nric_hash" not in data, "nric_hash must not be returned in API response"
        # The actual hash value also must not appear
        h = hash_sha256("S1234567D")
        assert h not in resp.text, "nric_hash value must not be present in serialized response"
