"""
Sends the 5-slide "screen time myth" TikTok carousel (10 images = 5 slides x 2
A/B variants) to Telegram as one album via sendMediaGroup, with a per-photo
sendPhoto fallback if the album call fails.

Run from the traders-engine repo (needs TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
in .env there, same as send_volume_profile.py):

    cd ~/traders-engine && .venv/bin/python send_myth_bust_carousel.py

The Cowork sandbox cannot reach api.telegram.org, so this must run on your Mac.
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Minimal fallback .env parser if python-dotenv isn't installed
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    sys.exit("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env")

# Ordered 1A,1B,2A,2B,3A,3B,4A,4B,5A,5B
IMAGES = [
    ("1/5 A", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085358_38d8b8a2-4a87-49dd-bb2f-d8cb64880fd3.png"),
    ("1/5 B", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085358_189926de-2d48-454d-b7cd-c22608e1624d.png"),
    ("2/5 A", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085400_06863e41-7a5b-4443-b54b-fae02de8ad9a.png"),
    ("2/5 B", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085400_c2895d11-1b9a-4968-a457-4ac43aa86173.png"),
    ("3/5 A", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085404_096f8aa0-457c-4f69-b063-d22bf2922a13.png"),
    ("3/5 B", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085403_b94ab8a7-58f7-4f3b-9c69-602d35bc3b51.png"),
    ("4/5 A", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085407_bc48b21a-47e3-4521-814a-6f4603601bb2.png"),
    ("4/5 B", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085407_59811b8f-ee2b-47c1-aaa1-b05606bfce6a.png"),
    ("5/5 A", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085410_c87d8b0c-c73f-4263-bef1-ce04f9ec7168.png"),
    ("5/5 B", "https://d8j0ntlcm91z4.cloudfront.net/user_3FtSoJESMaqcMakFT3nbzLgpg8T/hf_20260714_085410_2a6b72c2-3df7-46b4-b851-1ca1f00ba5b1.png"),
]

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_album():
    media = [
        {"type": "photo", "media": url, "caption": label if i == 0 else None}
        for i, (label, url) in enumerate(IMAGES)
    ]
    # Telegram doesn't like null captions in the payload; drop them
    for m in media:
        if m["caption"] is None:
            m.pop("caption")
    resp = requests.post(f"{API}/sendMediaGroup", json={"chat_id": CHAT_ID, "media": media}, timeout=30)
    return resp


def send_per_photo():
    ok, failed = 0, []
    for label, url in IMAGES:
        r = requests.post(
            f"{API}/sendPhoto",
            data={"chat_id": CHAT_ID, "photo": url, "caption": label},
            timeout=30,
        )
        if r.ok and r.json().get("ok"):
            ok += 1
        else:
            failed.append((label, r.text))
    return ok, failed


if __name__ == "__main__":
    print(f"Sending {len(IMAGES)} images as one album...")
    r = send_album()
    if r.ok and r.json().get("ok"):
        print("Album sent successfully.")
    else:
        print(f"Album send failed ({r.status_code}): {r.text}")
        print("Falling back to per-photo sendPhoto...")
        ok, failed = send_per_photo()
        print(f"Sent {ok}/{len(IMAGES)} photos.")
        if failed:
            print("Failed:")
            for label, err in failed:
                print(f"  {label}: {err}")
