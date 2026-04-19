# Change: add-telegram-inline-buttons

## Why

Every multi-choice prompt during onboarding asks patients to type a number ("Reply 1, 2, or 3"). Non-technical or elderly patients frequently type free text, send the wrong number, or abandon the flow entirely — causing unnecessary escalations and care-coordinator callbacks.

Telegram supports inline keyboard buttons (`InlineKeyboardMarkup`) that appear directly under a message. Tapping a button requires no typing and cannot produce an invalid response. The bot becomes immediately more usable with no changes to the patient-facing conversation content or the existing response-parsing logic.

## What Changes

1. **Transport layer** (`telegram_service.py`): New `send_keyboard()` function sends `sendMessage` with an `inline_keyboard` reply_markup. New `answer_callback_query()` function acknowledges button taps (required by the Telegram API to dismiss the loading spinner on the button).

2. **Webhook** (`webhook.py`): The current webhook silently ignores any Telegram update that lacks a `message` key — meaning all button taps are dropped today. A new `callback_query` handler is added before the early-return guard. It extracts `chat_id` and `callback_data`, acknowledges the query, looks up the patient, and routes `callback_data` through the same `onboarding_service.handle_onboarding_reply()` path — exactly as if the patient had typed that text. Text fallback is fully preserved.

3. **Onboarding prompts** (`onboarding_service.py`): All five numbered menus are updated to call `send_keyboard()` instead of `send_text()`. Button labels are human-readable (e.g., "English", "Morning (8am–12pm)", "Text only"). `callback_data` values match what the existing parser already handles ("1", "2", "3", etc.). No parser logic changes required.

## Affected menus

| Menu | Buttons |
|---|---|
| Language selection | English / 中文 / Melayu / தமிழ் |
| Medication capture method | Confirm on file / Send a photo / Enter manually |
| Contact time preference | Morning / Afternoon / Evening / No preference |
| Delivery mode | Text only / Voice only / Both |
| Voice selection | Female / Male / Record my own |

## Out of scope

YES/NO consent prompts and nudge campaign reply keywords (YES, SIDE EFFECT, HELP) — these are free-text responses handled by the response classifier and are not numbered option lists.

## Impact

- Affected specs: `patient-onboarding` (modified)
- Affected code:
  - `app/services/telegram_service.py` — add `send_keyboard()`, `answer_callback_query()`
  - `app/routers/webhook.py` — add `_handle_callback_query()` before `message` guard
  - `app/services/onboarding_service.py` — swap five numbered text menus for `send_keyboard()` calls (5 menus × up to 4 languages)
