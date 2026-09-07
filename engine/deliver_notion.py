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
from datetime import date, datetime, timedelta, timezone

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


def _plain_title(title_prop: dict) -> str:
    """Flatten a Notion title property into a plain string."""
    parts = title_prop.get("title", []) if isinstance(title_prop, dict) else []
    out = []
    for p in parts:
        out.append(p.get("plain_text") or p.get("text", {}).get("content", ""))
    return "".join(out).strip()


def fetch_recent_titles(database_id: str, days: int = 30, max_items: int = 400) -> list[dict]:
    """Return recently-created ideas already in the DB, newest first.

    Each item is {"title", "pillar", "created"}. This is what stops the engine
    proposing the same idea day after day: the generator gets this list and is
    told not to repeat anything on it.

    Best-effort by design — on a missing token, HTTP error, or network failure
    it returns whatever it has (usually []), so a hiccup here can never break the
    daily run; the worst case is that one day generates without dedup.
    """
    token = os.getenv("NOTION_TOKEN")
    if not token or not database_id:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    out: list[dict] = []
    cursor = None
    try:
        while len(out) < max_items:
            body = {
                "sorts": [{"timestamp": "created_time", "direction": "descending"}],
                "page_size": 100,
            }
            if cursor:
                body["start_cursor"] = cursor
            r = requests.post(url, headers=_HEADERS, json=body, timeout=30)
            if r.status_code >= 300:
                break
            data = r.json()
            for page in data.get("results", []):
                created = page.get("created_time", "")
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    created_dt = None
                # results are newest-first, so once we pass the cutoff we're done
                if created_dt and created_dt < cutoff:
                    return out
                props = page.get("properties", {})
                title = _plain_title(props.get(TITLE_PROP, {}))
                pillar = (props.get(PILLAR_PROP, {}).get("select") or {}).get("name", "")
                if title:
                    out.append({"title": title, "pillar": pillar, "created": created})
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
    except requests.RequestException:
        return out
    return out
