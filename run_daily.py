#!/usr/bin/env python3
"""Daily runner (cron entrypoint) — standalone, one business only.

This folder is fully self-contained: its own brand.py, its own .env, its own
Notion database and its own Telegram chat. Nothing here is shared with any
other business.

Flow:
    1. load this folder's brand
    2. generate ideas (Claude API)
    3. push them to this brand's Notion database
    4. send a Telegram message (ideas + Notion link) to your chat

Usage:
    python run_daily.py
    python run_daily.py --count 4
    python run_daily.py --dry-run          # print only, no delivery
    python run_daily.py --no-telegram
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from engine.generate import generate_ideas
from engine.deliver_notion import push_ideas
from engine.deliver_telegram import send_message, build_ping
from brand import PROFILE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args()

    tag = PROFILE["key"]
    print(f"[{tag}] generating {args.count} ideas ...")
    ideas = generate_ideas(PROFILE, args.count)
    print(f"[{tag}] got {len(ideas)} ideas")

    if args.dry_run:
        for i, idea in enumerate(ideas, 1):
            print(f"\n=== {i} [{idea['pillar']} / {idea['content_type']}] ===")
            print("HOOK:", idea["hook"])
            print("CAPTION:", idea["caption"])
            print("SCRIPT:", idea["reel_script"])
            print("HASHTAGS:", " ".join(idea["hashtags"]))
            print("GRAPHIC:", idea["graphic_prompt"])
            print("CTA:", idea["cta"])
        return

    db_id = os.getenv("NOTION_DB")
    if not db_id:
        sys.exit("Missing NOTION_DB in .env")
    urls = push_ideas(ideas, db_id)
    print(f"[{tag}] pushed {len(urls)} pages to Notion")

    if not args.no_telegram:
        text = build_ping(
            PROFILE["display_name"], len(ideas),
            [idea["hook"] for idea in ideas],
            urls[0] if urls else None,
        )
        sent = send_message(text)
        print(f"[{tag}] telegram: {'sent' if sent else 'skipped/failed'}")


if __name__ == "__main__":
    main()
