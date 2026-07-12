"""Builds the prompt sent to the Claude API from a profile dict.

The generation layer (engine/generate.py) calls build_messages() to get the
system prompt and user message for a given profile + number of ideas.
Keeping this separate means the brand file (brand.py) is the only thing that
changes the output — the engine itself stays generic.
"""

from __future__ import annotations  # allow `list | None` etc. on Python 3.9

import json


def _recent_block(recent: list) -> str:
    """Render the 'already published, do not repeat' section of the prompt."""
    lines = "\n".join(
        f'- [{r.get("pillar", "")}] {r.get("title", "")}'
        for r in recent if r.get("title")
    )
    if not lines:
        return ""
    return f"""

ALREADY PUBLISHED RECENTLY — DO NOT REPEAT ANY OF THESE. This is the single most important rule.
Treat a new idea as a repeat (and forbidden) if it teaches the same tool, busts the same myth,
tells the same personal story, or reuses the same hook/angle as any line below — even if the wording is different.
{lines}

Because of the list above:
- Do NOT make another VWAP explainer, another "magic indicator / 90% win-rate / safe signals" myth-bust,
  another generic BUY/SELL swipe quiz, another "this week was a drawdown" reality-check, or another
  "the options loss that changed me" story if a similar one already appears above.
- For a tool_explainer, choose a tool from SERVICES/TOPICS that is NOT already covered above
  (e.g. moving averages, sessions, order flow, footprint, volume profile, psychological targets) — never default to VWAP.
- Prefer pillars and angles that are under-represented in the list above. Aim for genuinely new ground each day."""


def build_messages(profile: dict, count: int, recent: list | None = None) -> tuple[str, str]:
    recent = recent or []
    pillars_txt = "\n".join(
        f'- {p["key"]}: {p["name"]} — {p["desc"]}' for p in profile["pillars"]
    )
    services_txt = ", ".join(profile.get("services", []))
    content_types_txt = ", ".join(profile.get("content_types", []))

    system = f"""You are a senior social-media content strategist for a specific business.
You write ONLY in {profile['language']} (Hebrew unless stated otherwise), in the brand's voice.

BUSINESS: {profile['display_name']}
SUMMARY: {profile['business_summary']}
AUDIENCE: {profile['audience']}
PLATFORMS: {", ".join(profile['platforms'])}
SERVICES / TOPICS: {services_txt}
VOICE & TONE: {profile['tone']}

CONTENT PILLARS (rotate across them, do not repeat the same pillar twice in one batch unless count > number of pillars):
{pillars_txt}

HARD RULES (never break):
{profile['guardrails']}

Every idea must be genuinely usable as-is: a real hook, a full ready-to-post caption,
and a short shootable video/reel script. No placeholders, no "insert X here"."""

    user = f"""Produce {count} distinct content ideas for today.
Content types available: {content_types_txt}.

Call the submit_content_ideas tool with exactly {count} ideas. For each idea:

- pillar: one of the pillar keys above.
- content_type: one of the content types above.
- hook: short scroll-stopping opening line, in {profile['language']}.
- caption: complete ready-to-post caption in {profile['language']}, including line breaks and emojis where natural.
- reel_script: a short 15-30s shot-by-shot script in {profile['language']}; use scene beats like [שוט 1] ...
- hashtags: 8-12 relevant hashtags.
- graphic_prompt: a detailed English image-generation prompt for a graphic/thumbnail that fits this post.
- cta: a clear call to action in {profile['language']}.

Every idea must be genuinely usable as-is — no placeholders, no "insert X here".
Make the {count} ideas feel varied in angle and format. Ground them in the real services/topics above."""

    user += _recent_block(recent)

    return system, user


if __name__ == "__main__":
    # quick smoke test of prompt shaping without calling the API
    from brand import PROFILE
    s, u = build_messages(PROFILE, 3)
    print(s)
    print("---")
    print(u)
