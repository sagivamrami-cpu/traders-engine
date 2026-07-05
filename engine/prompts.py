"""Builds the prompt sent to the Claude API from a profile dict.

The generation layer (engine/generate.py) calls build_messages() to get the
system prompt and user message for a given profile + number of ideas.
Keeping this separate means the brand file (brand.py) is the only thing that
changes the output — the engine itself stays generic.
"""

import json


def build_messages(profile: dict, count: int) -> tuple[str, str]:
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

    return system, user


if __name__ == "__main__":
    # quick smoke test of prompt shaping without calling the API
    from brand import PROFILE
    s, u = build_messages(PROFILE, 3)
    print(s)
    print("---")
    print(u)
