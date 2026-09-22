from __future__ import annotations
import re


MAX_REJECTION_AGE_S = 20 * 60


LABEL_NO_ANCHOR = "כניסה ללא עוגן"


LABEL_NO_TRIGGER = "טריגר כיווני חסר"


PREDICATE = "no_named_anchor_and_no_aligned_rejection_or_trigger"


_ANCHOR_PREFIXES = ("רמה:", "כניסה בריטסט ל", "כניסה:")


_PRICE_TAIL = re.compile(r"[\s,]*[\d,]+(?:\.\d+)?\s*$")


_NAME_SPLIT = re.compile(r"[·/]")


_COUNT_PREFIX = re.compile(r"^\d+\s+רמות\s*:\s*")


def anchor_names(reasons) -> set[str] | None:
    """The named levels a plan is ENTERED on, or None if it names none.

    Names only. Two plans on one cluster carry the same names at different
    prices, and comparing prices would call them different levels.

    The line often carries more than the entry: the engine writes
    `"כניסה: Q-WHOLE · ביטול: PSY-HI"` and the retest builder writes
    `"כניסה בריטסט ל-Q-QUARTER, לא במחיר השוק"`. A stop is not an anchor and
    a clause is not a level -- BTC's first live shadow row, 04.09 14:25,
    reported `["Q-WHOLE", "ביטול: PSY-HI"]` before this cut.
    """
    for r in (reasons or []):
        r = str(r).strip()
        for pre in _ANCHOR_PREFIXES:
            if not r.startswith(pre):
                continue
            body = r[len(pre):].lstrip("־- :")
            if not body or body.startswith("אין"):
                return None
            body = _COUNT_PREFIX.sub("", body.split(",")[0])
            names = set()
            for part in _NAME_SPLIT.split(body):
                part = _PRICE_TAIL.sub("", part).strip()
                if not part or ":" in part:
                    break          # a new labelled clause — the entry ended
                names.add(part.upper())
            return names or None
    return None


def aligned_trigger(reasons, direction: str | None) -> str | None:
    """The directional trigger this plan actually has, or None.

    Four readings count, and each is a fact a builder already wrote:
    a last bar that committed WITH the direction (0.15 ATR, tree stage 10),
    a trap or a committed extreme that resolves TO this direction, and a
    CONFIRMED W for a long or M for a short. A forming pattern and the bare
    presence of a vector do not: "there is a vector somewhere" is not a
    reason to be on this side of it.

    THE TREE AND THE ENGINE SAY THE SAME THINGS DIFFERENTLY. The tree writes
    its facts as `"<name>: <value>"`; the engine writes `wm.line()`
    ("תבנית W מאושרת (סגירה מעבר לצוואר): …") plus its own verdict line
    ("התבנית מאשרת את כיוון העסקה (לונג)"). Reading only the tree's shape
    put "טריגר כיווני חסר" on a BTC swing long that had a confirmed W --
    the first engine plan the shadow ever classified, 04.09 14:52.
    """
    if not direction:
        return None
    want = "W" if direction == "לונג" else "M"
    for r in (reasons or []):
        r = str(r).strip()
        if r.startswith("commitment:"):
            v = r.split(":", 1)[1].strip()
            if not v.startswith(("אין", "לא נקרא")):
                return "commitment"
        elif r.startswith("מלכודת:"):
            v = r.split(":", 1)[1].strip()
            if direction in v and ("היערך" in v or "⇒" in v):
                return "trap"
        elif r.startswith("התבנית מאשרת את כיוון העסקה"):
            # The engine has already checked confirmed AND same-direction.
            if direction in r:
                return f"confirmed_{want}"
        elif r.startswith("תבנית"):
            v = r[len("תבנית"):].lstrip(": ")
            if (v.startswith(want) and "מאושרת" in v
                    and "לא מאושרת" not in v and "מתגבשת" not in v):
                return f"confirmed_{want}"
    return None


def still_defending(rej: dict | None, direction: str | None, entry) -> bool:
    """Is this rejection still ARGUING against a trade in `direction`?

    A bullish rejection is support, and support only argues against a short
    while the short is still above it. Once price has broken below and the
    short is entered underneath, the same zone has FAILED -- it now agrees
    with the short, and calling it "against" would be the desk telling a
    client the opposite of what the chart says.
    """
    if not rej or entry is None or not direction:
        return False
    lo, hi = rej.get("zone_lo"), rej.get("zone_hi")
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        return False
    return (float(hi) <= float(entry) if direction == "שורט"
            else float(lo) >= float(entry))


def opposing_label(rej: dict | None) -> str | None:
    """`נגד דחייה טרייה מ־4,461.69–4,462.54 (EMA200-1h · D3-HI)`."""
    if not rej:
        return None
    lo, hi = rej.get("zone_lo"), rej.get("zone_hi")
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        return None
    out = f"נגד דחייה טרייה מ־{float(lo):,.2f}–{float(hi):,.2f}"
    names = [str(n) for n in (rej.get("levels") or []) if str(n).strip()]
    if names:
        out += f" ({' · '.join(names[:3])})"
    return out


def evaluate(*, direction: str | None, entry, atr: float, reasons,
             aligned_rejection: dict | None = None,
             opposing_rejection: dict | None = None) -> dict:
    """Classify one entry. Never decides anything.

    `shadow_block` is the predicate a stricter desk would refuse on: no named
    anchor, no aligned directional trigger, and no fresh rejection agreeing
    with the trade. An OPPOSING rejection adds its label but is deliberately
    not part of the predicate -- it is the loudest evidence on the 10:25
    short, and a predicate that needed it would miss the 11:05 long, which
    had nothing against it and nothing for it either.
    """
    names = anchor_names(reasons)
    trigger = aligned_trigger(reasons, direction)
    if not still_defending(opposing_rejection, direction, entry):
        opposing_rejection = None      # broken support is not opposition
    labels = []
    if not names:
        labels.append(LABEL_NO_ANCHOR)
    if trigger is None:
        labels.append(LABEL_NO_TRIGGER)
    against = opposing_label(opposing_rejection)
    if against:
        labels.append(against)
    return {
        "anchor_names": sorted(names) if names else [],
        "aligned_trigger": trigger,
        "aligned_rejection": _rej(aligned_rejection, entry, atr),
        "opposing_rejection": _rej(opposing_rejection, entry, atr),
        "labels": labels,
        "shadow_block": bool(not names and trigger is None
                             and not aligned_rejection),
        "predicate": PREDICATE,
    }


def _rej(rej: dict | None, entry, atr: float) -> dict | None:
    if not rej:
        return None
    out = {k: rej.get(k) for k in
           ("ts", "direction", "zone_lo", "zone_hi", "levels", "close",
            "wick_atr", "age_s")}
    gap = rej.get("gap")
    if isinstance(gap, (int, float)) and atr:
        out["distance_atr"] = round(float(gap) / float(atr), 2)
    else:
        out["distance_atr"] = None
    return out
