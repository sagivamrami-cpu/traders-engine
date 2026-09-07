#!/usr/bin/env python3
"""One-off: push the Volume Profile carousel (7 slides) to Telegram.

Run this on your Mac — the Cowork sandbox can't reach api.telegram.org, but your
machine can (same path the daily engine uses). It reads TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID from .env and sends the 7 slides as one swipeable album.

    cd ~/traders-engine
    ./venv/bin/python send_volume_profile.py      # or: python3 send_volume_profile.py

To swap a slide to its B variant, just replace that URL below.
"""

import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
API = "https://api.telegram.org/bot{token}/{method}"

# Volume Profile — 7 slides, in order (variant A of each; slide 7 = fixed "מדריך").
SLIDES = [
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260712_205624_2931cbea-8aa8-4fb6-abac-971b0c1ca9e3.png",  # 1 כריכה — Volume Profile
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260712_205628_39031371-dad6-4b03-9214-2fd665a0feab.png",  # 2 POC
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260712_205630_1d1b1c88-0ced-4e22-9bbf-8375a2cd5927.png",  # 3 בניית הפרופיל
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260712_205634_e725c68d-c691-4818-82c6-92c93c82f5f0.png",  # 4 Value Area
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260712_205637_c842fb65-3bf3-4c1b-a297-a28ecb2e9deb.png",  # 5 רמות אמיתיות
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260712_205641_d3605a14-15ca-439b-b613-f60b44d29b39.png",  # 6 זה לא קסם
    "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260713_061908_81dde3bb-4fc5-4fd6-8157-e6c8e90d61b8.png",  # 7 סיום/CTA — "רוצה עוד תוכן כזה? תעשה עוקב"
]

CAPTION = (
    "\U0001F4CA Volume Profile — המדריך המלא (7 שקופיות)\n"
    "המקום שבו הכי הרבה כסף החליף ידיים.\n\n"
    "@Daytraderfx • TRADERS REALITY"
)


def main():
    if not TOKEN or not CHAT:
        sys.exit("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env")

    media = []
    for i, url in enumerate(SLIDES):
        item = {"type": "photo", "media": url}
        if i == 0:
            item["caption"] = CAPTION  # caption shows on the album
        media.append(item)

    r = requests.post(
        API.format(token=TOKEN, method="sendMediaGroup"),
        data={"chat_id": CHAT, "media": json.dumps(media)},
        timeout=120,
    )
    if r.ok and r.json().get("ok"):
        print(f"✅ Sent {len(SLIDES)} slides as an album to Telegram.")
        return

    print(f"⚠️ sendMediaGroup failed ({r.status_code}): {r.text[:300]}")
    print("Falling back to sending one photo at a time…")
    ok = 0
    for i, url in enumerate(SLIDES, 1):
        rr = requests.post(
            API.format(token=TOKEN, method="sendPhoto"),
            data={"chat_id": CHAT, "photo": url, "caption": CAPTION if i == 1 else ""},
            timeout=120,
        )
        if rr.ok and rr.json().get("ok"):
            ok += 1
        else:
            print(f"  slide {i} failed: {rr.status_code} {rr.text[:150]}")
    print(f"Sent {ok}/{len(SLIDES)} slides.")


if __name__ == "__main__":
    main()
