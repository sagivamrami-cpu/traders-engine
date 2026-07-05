"""Delivery — Notion.

Writes each generated idea as a new page (row) in a Notion database.
Short fields go into database properties; long text (caption, script) goes
into the page body so it's easy to read and edit on mobile.

Your Notion database must have these properties (rename via the constants below
if yours differ):
    - a Title property named  "Name"
    - a Select property named "Status"   (add an option "Draft")
    - a Select property named "Pillar"
    - a Date property named   "Date"
"""

import os
from datetime import date

import requests

NOTION_VERSION = "2022-06-28"
TITLE_PROP = "Name"
STATUS_PROP = "Status"
PILLAR_PROP = "Pillar"
DATE_PROP = "Date"

_HEADERS = {
    "Authorization": f"Bearer {os.getenv('NOTION_TOKEN', '')}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def _chunks(text: str, size: int = 1900):
    text = text or ""
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _para(text: str) -> list[dict]:
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": c}}]},
        }
        for c in _chunks(text)
    ]


def _heading(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _build_children(idea: dict) -> list[dict]:
    children = [_heading("📝 קופי לפוסט")]
    children += _para(idea["caption"])
    children.append(_heading("🎬 תסריט לריל"))
    children += _para(idea["reel_script"])
    children.append(_heading("🏷️ האשטגים"))
    children += _para(" ".join(idea.get("hashtags", [])))
    children.append(_heading("🎨 פרומפט לגרפיקה"))
    children += _para(idea["graphic_prompt"])
    children.append(_heading("👉 קריאה לפעולה"))
    children += _para(idea["cta"])
    return children


def push_ideas(ideas: list[dict], database_id: str) -> list[str]:
    """Create one Notion page per idea. Returns the list of page URLs."""
    if not os.getenv("NOTION_TOKEN"):
        raise RuntimeError("NOTION_TOKEN is not set.")

    today = date.today().isoformat()
    urls = []
    for idea in ideas:
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                TITLE_PROP: {"title": [{"text": {"content": idea["hook"][:200]}}]},
                STATUS_PROP: {"select": {"name": "Draft"}},
                PILLAR_PROP: {"select": {"name": idea["pillar"]}},
                DATE_PROP: {"date": {"start": today}},
            },
            "children": _build_children(idea),
        }
        r = requests.post(
            "https://api.notion.com/v1/pages", headers=_HEADERS, json=payload, timeout=30
        )
        if r.status_code >= 300:
            raise RuntimeError(f"Notion error {r.status_code}: {r.text[:300]}")
        urls.append(r.json().get("url", ""))
    return urls
