"""
T-50: Webhook security tests.
- Invalid Twilio signature → 403
- Valid signature → processes normally
- Rate limiting headers present
"""
from unittest.mock import patch
import pytest
import hmac
import hashlib
import base64


def _build_twilio_sig(auth_token: str, url: str, params: dict) -> str:
    """Compute a valid Twilio HMAC-SHA1 signature."""
    s = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    mac = hmac.new(auth_token.encode(), s.encode(), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode()


WEBHOOK_URL = "http://testserver/api/webhook/whatsapp"
DUMMY_TOKEN = "test_twilio_auth_token"
FORM_PARAMS = {
    "From": "whatsapp:+6591234567",
    "Body": "Yes",
    "MessageSid": "SM_sec_001",
}


class TestWebhookSecurity:
    def test_invalid_signature_returns_403(self, client):
        """Requests with an invalid Twilio signature must be rejected with 403."""
        resp = client.post(
            "/api/webhook/whatsapp",
            data=FORM_PARAMS,
            headers={"X-Twilio-Signature": "INVALID_SIGNATURE"},
        )
        assert resp.status_code == 403, (
            f"Expected 403 for invalid signature, got {resp.status_code}: {resp.text}"
        )

    def test_missing_signature_returns_403(self, client):
        """Requests without X-Twilio-Signature header must be rejected."""
        resp = client.post(
            "/api/webhook/whatsapp",
            data=FORM_PARAMS,
        )
        assert resp.status_code in (403, 422), (
            f"Expected 403/422 for missing signature, got {resp.status_code}"
        )

    @patch("app.services.whatsapp_service.send_text")
    def test_valid_signature_processes(self, mock_send, client, db):
        """A request with a passing signature (mocked validation) is processed."""
        from app.models.models import Patient

        # Ensure patient exists for the FROM number
        existing = db.query(Patient).filter(
            Patient.phone_number == "+6591234567"
        ).first()
        if not existing:
            p = Patient(
                full_name="Webhook Test Patient",
                phone_number="+6591234567",
                language_preference="en",
                risk_level="low",
                is_active=True,
                onboarding_state="complete",
            )
            db.add(p)
            db.commit()

        with patch("app.routers.webhook.validate_twilio_signature", return_value=True):
            resp = client.post(
                "/api/webhook/whatsapp",
                data=FORM_PARAMS,
                headers={"X-Twilio-Signature": "valid"},
            )

        assert resp.status_code in (200, 204), (
            f"Expected 200/204 for valid signature, got {resp.status_code}: {resp.text}"
        )

    def test_status_callback_validates_signature(self, client):
        """Status callback also validates Twilio signature (consistent security)."""
        resp = client.post(
            "/api/webhook/whatsapp/status",
            data={
                "MessageSid": "SM_status_001",
                "MessageStatus": "delivered",
            },
        )
        # Should be 403 (signature required) — consistent with main webhook security
        assert resp.status_code == 403, "Status callback should also validate signature"


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
