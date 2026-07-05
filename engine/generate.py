"""Layer 2 — Generation.

Calls the Claude API with a profile and returns a list of structured content
ideas (Python dicts). This is the only place that talks to Anthropic.
"""

import os

from anthropic import Anthropic

from engine.prompts import build_messages

# Sonnet gives the best quality/cost balance for content writing.
# Swap to "claude-haiku-4-5-20251001" to cut cost, or "claude-opus-4-8" for max quality.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

REQUIRED_FIELDS = ["pillar", "content_type", "hook", "caption", "reel_script",
                   "hashtags", "graphic_prompt", "cta"]

# Tool-use (forced function calling) instead of asking the model to hand-write
# a JSON blob: free-text JSON kept breaking on Hebrew captions (literal
# newlines, and invalid \' escapes around nested quotes) — the API enforces
# this schema server-side, so parsing can never fail on malformed text again.
IDEAS_TOOL = {
    "name": "submit_content_ideas",
    "description": "Submit the generated batch of content ideas.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ideas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pillar": {"type": "string"},
                        "content_type": {"type": "string"},
                        "hook": {"type": "string"},
                        "caption": {"type": "string"},
                        "reel_script": {"type": "string"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "graphic_prompt": {"type": "string"},
                        "cta": {"type": "string"},
                    },
                    "required": REQUIRED_FIELDS,
                },
            },
        },
        "required": ["ideas"],
    },
}


def generate_ideas(profile: dict, count: int = 5, max_attempts: int = 3) -> list[dict]:
    """Return `count` content-idea dicts for the given profile.

    Retries a couple of times if the model's tool call comes back empty or
    incomplete — this runs unattended (cron), so we don't want a single flaky
    response to fail the whole day's run.
    """
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    system, user = build_messages(profile, count)
    required = set(REQUIRED_FIELDS)

    last_error = None
    for attempt in range(1, max_attempts + 1):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[IDEAS_TOOL],
            tool_choice={"type": "tool", "name": "submit_content_ideas"},
        )
        tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
        ideas = (tool_use.input.get("ideas") if tool_use else None) or []

        clean = [idea for idea in ideas
                  if isinstance(idea, dict) and required.issubset(idea.keys())]
        if clean:
            return clean
        last_error = ValueError("Model returned no valid ideas.")
        print(f"[generate] attempt {attempt}/{max_attempts}: no valid ideas — retrying")

    raise ValueError(f"Model failed to return usable ideas after {max_attempts} attempts: {last_error}")


if __name__ == "__main__":
    from brand import PROFILE
    for i, idea in enumerate(generate_ideas(PROFILE, 2), 1):
        print(f"\n=== idea {i} [{idea['pillar']}] ===")
        print(idea["hook"])
        print(idea["caption"][:200], "...")
