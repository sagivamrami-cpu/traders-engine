"""Layer 2 — Generation.

Calls the Claude API with a profile and returns a list of structured content
ideas (Python dicts). This is the only place that talks to Anthropic.
"""

from __future__ import annotations  # allow `list | None` etc. on Python 3.9

import os
import re

from anthropic import Anthropic

from engine.prompts import build_messages

# Short, high-frequency words (Hebrew + English) that carry no topical meaning.
# Stripped before comparing two hooks so similarity is driven by real content words.
_STOPWORDS = {
    "של", "על", "עם", "או", "אם", "כי", "גם", "רק", "זה", "זו", "זאת", "מה",
    "למה", "איך", "את", "לא", "כן", "יש", "אין", "הוא", "היא", "הם", "אני",
    "אתה", "אבל", "כמו", "עוד", "כל", "כדי", "היה", "בין", "אחד", "יותר",
    "the", "and", "or", "you", "your", "this", "that", "for", "are", "was",
    "not", "but", "with", "have", "has", "why", "how", "what", "who",
}


_HE_PREFIXES = ("ש", "ו", "ה", "ב", "כ", "ל", "מ")
_HE_SUFFIXES = ("יים", "ים", "ות")

# Concept groups: surface forms (across scripts, transliterations and prefixes)
# that all mean the same recurring topic. Two hooks that touch the SAME group
# are treated as the same idea even when nothing else overlaps — this is what
# actually catches the reworded/transliterated repeats (drawdown/דראודאון,
# קסם/אינדיקטור/סיגנלים, VWAP every single day).
_CONCEPT_GROUPS = {
    "vwap":          {"vwap"},
    "regime":        {"regime", "רגים", "רג'ים"},
    "footprint":     {"footprint", "פוטפרינט"},
    "volume_profile": {"פרופיל"},
    "drawdown":      {"drawdown", "דראודאון", "דרואדאון"},
    "guru_myth":     {"קסם", "אינדיקטור", "סיגנלים", "signals", "גורו", "בטוחים"},
    "options_loss":  {"אופציות"},
    "buysell_quiz":  {"buy", "sell"},
    "backtest":      {"backtest", "בקטסט"},
}
_CONCEPT_OF = {form: g for g, forms in _CONCEPT_GROUPS.items() for form in forms}


def _strip_prefix(tok: str) -> str:
    """Strip one leading Hebrew particle (ש/ו/ה/ב/כ/ל/מ) if the rest is still a word."""
    if not tok.isascii() and len(tok) > 3 and tok[0] in _HE_PREFIXES:
        return tok[1:]
    return tok


def _stem(tok: str) -> str:
    """Crude Hebrew normalization so morphological variants collapse.

    Latin tokens are returned unchanged. For Hebrew we strip one leading particle
    and one common plural ending (ים/ות/יים) — enough to make מתעלם≈מתעלמים and
    מוסדות≈מוסדיים without a real morphological analyzer.
    """
    if tok.isascii():
        return tok
    tok = _strip_prefix(tok)
    for suf in _HE_SUFFIXES:
        if len(tok) > 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def _tokens(text: str) -> set:
    """Stemmed content-word set. `\\w+` under re.UNICODE covers Hebrew and Latin."""
    toks = re.findall(r"\w+", (text or "").lower(), re.UNICODE)
    return {_stem(t) for t in toks if len(t) > 2 and t not in _STOPWORDS}


def _concepts(text: str) -> set:
    """Which distinctive topic groups the text touches (prefix-aware)."""
    hits = set()
    for raw in re.findall(r"\w+", (text or "").lower(), re.UNICODE):
        for form in (raw, _strip_prefix(raw)):
            g = _CONCEPT_OF.get(form)
            if g:
                hits.add(g)
    return hits


def _too_similar(a: str, b: str, jaccard: float = 0.4, contain: float = 0.6) -> bool:
    """True if two hooks are the same underlying idea.

    Signals, any of which is enough:
      1. They touch the same distinctive concept group (VWAP, drawdown, guru-myth...).
         This is the one that catches heavily-reworded / transliterated repeats.
      2. Jaccard overlap of stemmed content words >= `jaccard`.
      3. Containment — a short hook that is essentially a subset of a longer one.
    """
    if _concepts(a) & _concepts(b):
        return True
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    if inter == 0:
        return False
    if inter / len(ta | tb) >= jaccard:
        return True
    return inter / min(len(ta), len(tb)) >= contain

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


def generate_ideas(profile: dict, count: int = 5, recent: list | None = None,
                   max_attempts: int = 3) -> list[dict]:
    """Return `count` fresh content-idea dicts for the given profile.

    `recent` is a list of {"title", ...} already published (read back from
    Notion). Those titles are used twice: injected into the prompt as an explicit
    do-not-repeat list, and as a post-generation guard that drops any idea whose
    hook is a near-duplicate of a recent title — or of an earlier idea in the
    same run. Together they stop the day-after-day recycling.

    Retries a couple of times if the model returns nothing usable or only
    duplicates. Runs unattended (cron), so on the final attempt it returns the
    best it has rather than failing the whole day's run.
    """
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    recent = recent or []
    recent_titles = [r.get("title", "") for r in recent if r.get("title")]
    system, user = build_messages(profile, count, recent)
    required = set(REQUIRED_FIELDS)

    accepted: list[dict] = []
    clean: list[dict] = []
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

        for idea in clean:
            hook = idea.get("hook", "")
            if any(_too_similar(hook, t) for t in recent_titles):
                continue  # repeats something already published
            if any(_too_similar(hook, a["hook"]) for a in accepted):
                continue  # duplicate within this same run
            accepted.append(idea)
            if len(accepted) >= count:
                return accepted[:count]

        last_error = ValueError("no fresh (non-duplicate) ideas")
        print(f"[generate] attempt {attempt}/{max_attempts}: "
              f"{len(accepted)}/{count} fresh ideas so far — retrying for more")

    if accepted:
        print(f"[generate] returning {len(accepted)} fresh idea(s) "
              f"(asked for {count}; model ran low on genuinely new angles)")
        return accepted[:count]
    if clean:
        print("[generate] warning: could not find non-duplicate ideas — returning latest batch as-is")
        return clean[:count]
    raise ValueError(f"Model failed to return usable ideas after {max_attempts} attempts: {last_error}")


if __name__ == "__main__":
    from brand import PROFILE
    for i, idea in enumerate(generate_ideas(PROFILE, 2), 1):
        print(f"\n=== idea {i} [{idea['pillar']}] ===")
        print(idea["hook"])
        print(idea["caption"][:200], "...")
