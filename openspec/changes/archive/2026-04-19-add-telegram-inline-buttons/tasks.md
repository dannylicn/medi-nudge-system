# Tasks: add-telegram-inline-buttons

## Phase 1: Transport layer
- [x] 1. Add `send_keyboard(db, patient_id, to_phone, body, buttons, *, campaign_id=None, chat_id=None)` to `telegram_service.py`
  - `buttons` type: `list[list[dict]]` where each dict is `{"text": str, "callback_data": str}`
  - POST to `sendMessage` with `reply_markup: {"inline_keyboard": buttons}`
  - Record OutboundMessage the same way as `send_text()`
  - No-op simulation path when `TELEGRAM_BOT_TOKEN` is not set (sets `msg.status = "simulated"`)
- [x] 2. Add `answer_callback_query(callback_query_id: str)` to `telegram_service.py`
  - POST to `answerCallbackQuery` with `callback_query_id`
  - Silently no-ops if `TELEGRAM_BOT_TOKEN` is not set

## Phase 2: Webhook callback_query handler
- [x] 3. In `webhook.py`, check for `update.get("callback_query")` BEFORE the `if not message: return` guard
- [x] 4. Implement `_handle_callback_query(db: Session, callback_query: dict) -> None`:
  - Call `telegram_service.answer_callback_query(callback_query["id"])`
  - Extract `chat_id` from `callback_query["message"]["chat"]["id"]`
  - Extract `data` from `callback_query.get("data", "")`
  - Lookup patient by `telegram_chat_id`; if not found, route to `onboarding_service.handle_start_command(db, chat_id, None)`
  - If patient is in an onboarding state: call `onboarding_service.handle_onboarding_reply(db, patient, data)`
  - If patient is active (onboarding complete): call `agent_service.run(patient, data, db)`

## Phase 3: Onboarding prompts
- [x] 5. Replace language selection `LANG_QUICK_REPLIES` send with `send_keyboard()` call
  - Single row of 4 buttons: `[{"text": "English", "callback_data": "1"}, {"text": "中文", "callback_data": "2"}, {"text": "Melayu", "callback_data": "3"}, {"text": "தமிழ்", "callback_data": "4"}]`
  - Remove "Reply 1, 2, 3 or 4" instruction from message text
- [x] 6. Replace `MEDICATION_PROMPT` (4 languages) with `send_keyboard()` calls
  - 3 buttons (one per row): "✅ Confirm on file" (cb: "1"), "📷 Send a photo" (cb: "2"), "✏️ Enter manually" (cb: "3")
  - Remove "Reply 1, 2, or 3" from message text
- [x] 7. Replace `PREFERENCES_PROMPT` (4 languages) with `send_keyboard()` calls
  - 4 buttons: "☀️ Morning" (cb: "1"), "🌤 Afternoon" (cb: "2"), "🌆 Evening" (cb: "3"), "🔕 No preference" (cb: "4")
  - Remove "Reply 1–4" from message text
- [x] 8. Replace `VOICE_PREFERENCE_PROMPT` (4 languages) with `send_keyboard()` calls
  - 3 buttons: "💬 Text only" (cb: "1"), "🔊 Voice only" (cb: "2"), "💬🔊 Both" (cb: "3")
  - Remove "Reply 1-3" from message text
- [x] 9. Replace `VOICE_SELECTION_PROMPT` (4 languages) with `send_keyboard()` calls
  - 3 buttons: "👩 Female" (cb: "1"), "👨 Male" (cb: "2"), "🎙 Record my own" (cb: "3")
  - Remove "Reply 1, 2 or 3" from message text

## Phase 4: Tests
- [x] 10. Unit test `send_keyboard()` — verify `reply_markup.inline_keyboard` is included in the HTTP request body
- [x] 11. Unit test `answer_callback_query()` — verify correct endpoint and payload
- [x] 12. Integration test `_handle_callback_query()` — callback from known patient in onboarding routes to `handle_onboarding_reply()`
- [x] 13. Integration test — callback from unknown `chat_id` routes to self-onboarding
- [x] 14. Regression test — text message "1" / "English" still works alongside buttons (fallback preserved)

## Dependencies
- Phase 1 must complete before Phases 2 and 3
- Phases 2 and 3 are independent of each other after Phase 1
- Phase 4 tests may be written alongside implementation (TDD preferred)
