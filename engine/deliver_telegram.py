"""Delivery — Telegram (Bot API).

Sends the daily ideas as a message, and optionally each idea's graphic as a
photo, straight to your own Telegram chat. Replaces the old WhatsApp/CallMeBot
delivery (Telegram is more reliable and can send images too).

One-time setup:
  1. In Telegram, @BotFather -> /newbot -> copy the bot token.
  2. Press Start / send any message to your new bot.
  3. Get your numeric chat id from @userinfobot.
  4. Put TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env.
"""

import html
import os

import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _creds():
    return os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a text message to the configured chat."""
    token, chat = _creds()
    if not token or not chat:
        print("[telegram] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing — skipping")
        return False
    r = requests.post(
        API.format(token=token, method="sendMessage"),
        data={
            "chat_id": chat,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    ok = r.ok and r.json().get("ok", False)
    if not ok:
        print(f"[telegram] sendMessage failed {r.status_code}: {r.text[:200]}")
    return ok


def send_photo(photo: str, caption: str = "") -> bool:
    """Send a photo. `photo` may be a public URL or a local file path."""
    token, chat = _creds()
    if not token or not chat:
        return False
    url = API.format(token=token, method="sendPhoto")
    data = {"chat_id": chat, "caption": caption[:1024], "parse_mode": "HTML"}
    try:
        if photo.startswith("http"):
            r = requests.post(url, data={**data, "photo": photo}, timeout=60)
        else:
            with open(photo, "rb") as f:
                r = requests.post(url, data=data, files={"photo": f}, timeout=120)
    except OSError as e:
        print(f"[telegram] cannot open photo {photo}: {e}")
        return False
    ok = r.ok and r.json().get("ok", False)
    if not ok:
        print(f"[telegram] sendPhoto failed {r.status_code}: {r.text[:200]}")
    return ok


def build_ping(display_name: str, count: int, sample_hooks: list, notion_url) -> str:
    """Build the daily HTML message body (hooks + Notion link)."""
    dn = html.escape(display_name)
    lines = [f"<b>✅ {count} רעיונות תוכן חדשים ל{dn}</b>", ""]
    for h in sample_hooks[:count]:
        lines.append(f"• {html.escape(h)}")
    if notion_url:
        lines += ["", f"פתח את כולם בנוטב'ן:", html.escape(notion_url)]
    return "\n".join(lines)
