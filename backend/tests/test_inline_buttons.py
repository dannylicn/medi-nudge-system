"""
Tests for Telegram inline keyboard button support (add-telegram-inline-buttons).

Covers:
  - send_keyboard() includes reply_markup in the HTTP payload
  - answer_callback_query() posts to the correct endpoint
  - _handle_callback_query() routes callback_data to handle_onboarding_reply
  - Callback from unknown chat_id triggers self-onboarding
  - Text input ("1", "English") still works as fallback alongside buttons
"""
from unittest.mock import patch, MagicMock
import pytest

WEBHOOK_URL = "/api/webhook/telegram"
DUMMY_SECRET = "test_telegram_webhook_secret"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_patient(db, phone, name="Button Test", state="invited", chat_id=None):
    from app.models.models import Patient
    p = Patient(
        full_name=name,
        phone_number=phone,
        telegram_chat_id=chat_id,
        language_preference="en",
        risk_level="low",
        is_active=True,
        onboarding_state=state,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _callback_update(chat_id: str, data: str):
    """Build a minimal Telegram callback_query Update object."""
    return {
        "update_id": 200,
        "callback_query": {
            "id": "cq_test_123",
            "from": {"id": int(chat_id), "is_bot": False, "first_name": "Test"},
            "message": {
                "message_id": 42,
                "chat": {"id": int(chat_id), "type": "private"},
                "text": "Please select your preferred language",
            },
            "data": data,
        },
    }


def _text_update(chat_id: str, text: str):
    """Build a minimal Telegram text message Update."""
    return {
        "update_id": 201,
        "message": {
            "message_id": 43,
            "from": {"id": int(chat_id), "is_bot": False, "first_name": "Test"},
            "chat": {"id": int(chat_id), "type": "private"},
            "text": text,
        },
    }


@pytest.fixture(autouse=True)
def _set_webhook_secret(monkeypatch):
    import app.services.telegram_service as _ts
    monkeypatch.setattr(_ts.settings, "TELEGRAM_WEBHOOK_SECRET", DUMMY_SECRET)


# ---------------------------------------------------------------------------
# Unit tests: send_keyboard
# ---------------------------------------------------------------------------

class TestSendKeyboard:
    def test_reply_markup_included_in_payload(self, db):
        """send_keyboard must include reply_markup.inline_keyboard in the HTTP POST."""
        from app.services.telegram_service import send_keyboard
        from app.models.models import Patient
        patient = _make_patient(db, "+6591110001", chat_id="111000001")

        buttons = [[{"text": "Option A", "callback_data": "1"}, {"text": "Option B", "callback_data": "2"}]]

        captured = {}

        def _fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"ok": True, "result": {"message_id": 99}}
            return resp

        with patch("app.services.telegram_service.httpx.post", side_effect=_fake_post):
            with patch("app.services.telegram_service.settings") as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = "fake_token"
                send_keyboard(db, patient.id, "111000001", "Choose:", buttons)

        assert "reply_markup" in captured["json"]
        assert captured["json"]["reply_markup"] == {"inline_keyboard": buttons}

    def test_simulated_when_no_token(self, db):
        """send_keyboard records OutboundMessage with status=simulated when token not set."""
        from app.services.telegram_service import send_keyboard
        from app.models.models import OutboundMessage
        patient = _make_patient(db, "+6591110002", chat_id="111000002")

        buttons = [[{"text": "Yes", "callback_data": "1"}]]

        with patch("app.services.telegram_service.settings") as mock_settings:
            mock_settings.TELEGRAM_BOT_TOKEN = None
            msg = send_keyboard(db, patient.id, "111000002", "Choose:", buttons)

        assert msg.status == "simulated"


# ---------------------------------------------------------------------------
# Unit tests: answer_callback_query
# ---------------------------------------------------------------------------

class TestAnswerCallbackQuery:
    def test_posts_to_answer_callback_query_endpoint(self):
        """answer_callback_query must POST to answerCallbackQuery with the correct id."""
        from app.services.telegram_service import answer_callback_query

        captured = {}

        def _fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"ok": True}
            return resp

        with patch("app.services.telegram_service.httpx.post", side_effect=_fake_post):
            with patch("app.services.telegram_service.settings") as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = "fake_token"
                answer_callback_query("cq_abc123")

        assert "answerCallbackQuery" in captured["url"]
        assert captured["json"]["callback_query_id"] == "cq_abc123"

    def test_no_op_when_no_token(self):
        """answer_callback_query must not make any HTTP calls when token is not set."""
        from app.services.telegram_service import answer_callback_query

        with patch("app.services.telegram_service.httpx.post") as mock_post:
            with patch("app.services.telegram_service.settings") as mock_settings:
                mock_settings.TELEGRAM_BOT_TOKEN = None
                answer_callback_query("cq_noop")

        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# Integration tests: webhook callback_query routing
# ---------------------------------------------------------------------------

class TestCallbackQueryWebhook:
    def test_callback_routes_to_onboarding(self, client, db):
        """Button tap on a patient in onboarding state routes callback_data to handle_onboarding_reply."""
        patient = _make_patient(db, "+6591120001", state="consent_pending", chat_id="112000001")

        # Patch the name as imported in webhook.py (not the telegram_service module attribute)
        with patch("app.routers.webhook.answer_callback_query") as mock_ack, \
             patch("app.services.onboarding_service.handle_onboarding_reply") as mock_handler, \
             patch("app.services.telegram_service.send_keyboard"):
            resp = client.post(
                WEBHOOK_URL,
                json=_callback_update("112000001", "1"),
                headers={"X-Telegram-Bot-Api-Secret-Token": DUMMY_SECRET},
            )

        assert resp.status_code == 200
        mock_ack.assert_called_once_with("cq_test_123")
        mock_handler.assert_called_once()
        # The third positional arg to handle_onboarding_reply is the data string
        call_args = mock_handler.call_args
        assert call_args[0][2] == "1"

    def test_callback_unknown_chat_triggers_self_onboarding(self, client, db):
        """Button tap from an unknown chat_id triggers self-onboarding flow."""
        with patch("app.routers.webhook.answer_callback_query"), \
             patch("app.services.onboarding_service.handle_start_command") as mock_start, \
             patch("app.services.onboarding_service._send_raw"):
            resp = client.post(
                WEBHOOK_URL,
                json=_callback_update("999999999", "1"),
                headers={"X-Telegram-Bot-Api-Secret-Token": DUMMY_SECRET},
            )

        assert resp.status_code == 200
        mock_start.assert_called_once()
        assert mock_start.call_args[0][1] == "999999999"

    def test_callback_ack_called_before_routing(self, client, db):
        """answer_callback_query must be called even if routing fails."""
        patient = _make_patient(db, "+6591120002", state="complete", chat_id="112000002",
                                name="Active Patient")
        db.query(type(patient)).filter_by(id=patient.id).update({"is_active": True})
        db.commit()

        with patch("app.routers.webhook.answer_callback_query") as mock_ack, \
             patch("app.services.agent_service.run"), \
             patch("app.services.telegram_service.send_keyboard"):
            resp = client.post(
                WEBHOOK_URL,
                json=_callback_update("112000002", "some_data"),
                headers={"X-Telegram-Bot-Api-Secret-Token": DUMMY_SECRET},
            )

        assert resp.status_code == 200
        mock_ack.assert_called_once()


# ---------------------------------------------------------------------------
# Regression test: text input fallback
# ---------------------------------------------------------------------------

class TestTextFallback:
    def test_typing_number_still_routes_to_onboarding(self, client, db):
        """Patients who type '2' instead of tapping a button still advance the onboarding state."""
        patient = _make_patient(db, "+6591130001", state="consent_pending", chat_id="113000001")

        with patch("app.services.onboarding_service.handle_onboarding_reply") as mock_handler, \
             patch("app.services.telegram_service.send_keyboard"), \
             patch("app.services.telegram_service.send_text"):
            resp = client.post(
                WEBHOOK_URL,
                json=_text_update("113000001", "2"),
                headers={"X-Telegram-Bot-Api-Secret-Token": DUMMY_SECRET},
            )

        assert resp.status_code == 200
        mock_handler.assert_called_once()
        # data passed is the typed text "2"
        assert mock_handler.call_args[0][2] == "2"

    def test_typing_language_name_still_works(self, client, db):
        """Patients who type 'English' in full still have their language recognised."""
        patient = _make_patient(db, "+6591130002", state="consent_pending", chat_id="113000002")

        with patch("app.services.onboarding_service.handle_onboarding_reply") as mock_handler, \
             patch("app.services.telegram_service.send_keyboard"), \
             patch("app.services.telegram_service.send_text"):
            resp = client.post(
                WEBHOOK_URL,
                json=_text_update("113000002", "English"),
                headers={"X-Telegram-Bot-Api-Secret-Token": DUMMY_SECRET},
            )

        assert resp.status_code == 200
        mock_handler.assert_called_once()
        # webhook passes text as-is; handle_onboarding_reply lowercases internally
        assert mock_handler.call_args[0][2] == "English"
