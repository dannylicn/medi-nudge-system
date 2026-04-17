"""
Telegram long-polling script for local development.
Polls getUpdates and forwards each update to the local webhook endpoint.

Usage:
    cd backend && source venv/bin/activate
    python poll_telegram.py

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET in .env.
"""
import os
import sys
import time
import httpx

sys.path.insert(0, os.path.dirname(__file__))
from app.core.config import settings

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
WEBHOOK_SECRET = settings.TELEGRAM_WEBHOOK_SECRET
LOCAL_WEBHOOK = "http://localhost:8000/api/webhook/telegram"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def main():
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    # Delete any existing webhook so getUpdates works
    print("Removing existing webhook ...")
    httpx.post(f"{TELEGRAM_API}/deleteWebhook")

    print(f"Polling Telegram for updates (forwarding to {LOCAL_WEBHOOK}) ...")
    print("Press Ctrl+C to stop.\n")

    offset = 0
    while True:
        try:
            resp = httpx.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            )
            data = resp.json()
            if not data.get("ok"):
                print(f"Telegram API error: {data}")
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat = msg.get("chat", {})
                text = msg.get("text", "")
                print(f"[chat_id={chat.get('id')}] {text}")

                # Forward to local webhook
                try:
                    headers = {}
                    if WEBHOOK_SECRET:
                        headers["X-Telegram-Bot-Api-Secret-Token"] = WEBHOOK_SECRET
                    r = httpx.post(
                        LOCAL_WEBHOOK,
                        json=update,
                        headers=headers,
                        timeout=10,
                    )
                    print(f"  -> {r.status_code} {r.text[:100]}")
                except Exception as e:
                    print(f"  -> Forward failed: {e}")

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
