"""Pure pinned chart-desk pricing subset; commit 68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9.
Plan projects all original fields and only risk, rr, rr_far, tradeable;
not the full source class. See reversal-pricing-contracts.json and its AST auditor."""

from __future__ import annotations
from dataclasses import dataclass, field
from . import basis_symbols as basis


MIN_RR = 1.2


SWING_MULT = {"XAU": 4.5, "GOLD": 4.5, "NAS": 3.0, "US100": 3.0, "NQ": 3.0,
              "BTC": 5.0}


STYLE_MULT = {"scalp": 1.0, "intraday": 1.5}


INTRADAY_MULT = {"NAS": 1.0, "US100": 1.0, "NQ": 1.0}


INTRADAY_TARGET_COUNT = 3


FAR_TP1_R = 2.0


INSERT_TP1_R = 1.5


def _with_measured_rung(targets: list, entry: float, stop: float,
                        short: bool) -> list:
    """Prepend a measured first rung when the nearest level is far."""
    if not targets:
        return targets
    risk = abs(entry - stop) or 1e-9
    if abs(targets[0][1] - entry) <= FAR_TP1_R * risk:
        return targets
    px = entry - INSERT_TP1_R * risk if short else entry + INSERT_TP1_R * risk
    return [(f"{INSERT_TP1_R:g}R", round(px, 2))] + list(targets)


ENTRY_ZONE = {"XAU": 2.0, "NAS": 25.0, "US100": 25.0, "NQ": 25.0, "BTC": 60.0}


def entry_zone(symbol: str, entry: float) -> tuple[float, float]:
    """(low, high) of the band that counts as touching this entry."""
    u = basis.canonical_symbol(symbol).upper()
    half = next((v for k, v in ENTRY_ZONE.items() if k in u), 0.0)
    return (entry - half, entry + half)


STOP_BANDS = {"XAU": (5.0, 7.0), "GOLD": (5.0, 7.0), "NAS": (70.0, 120.0),
              "US100": (70.0, 120.0), "NQ": (70.0, 120.0),
              # His number, 2026-08-26: "ביט סטופ נע בין 200-500 דולר תנועה
              # לפי בחירה שלך לפי טיב העסקה". Replaces the ATR-derived guess
              # that stood in until he named it. Where inside the band a
              # given trade lands is manage.stop_for()'s quality call.
              # Sagiv, 2026-08-31, after the overnight scalp died on a 200$
              # stop: *"אי אפשר להחזיק עסקה עם 100-200 דולר סטופ בביטקוין...
              # לפחות 400-600 דולר"*. Supersedes his 2026-08-26 "200-500".
              # That night's low was 77,392 — a 400 floor (77,330) would have
              # HELD through it.
              "BTC": (400.0, 600.0)}


def apply_stop_band(symbol: str, entry: float, stop: float, atr: float,
                    warnings: list, style: str = "intraday") -> float:
    """Clamp the stop into HIS band. Too tight widens; too wide TIGHTENS.

    The overnight 3.84pt gold stop (against his 5-7) filled at 02:27 and died
    at 02:48 -- a stop tighter than the instrument's noise floor is a fee, not
    protection. And his wording makes the band a band: past the cap the stop
    is pulled back to it, with the warning naming what was done.
    """
    u = basis.canonical_symbol(symbol).upper()
    band = next((b for k, b in STOP_BANDS.items() if k in u), None)
    derived = ""
    if band is None:
        return stop
    lo, hi = band
    if style == "swing":
        m = next((v for k, v in SWING_MULT.items() if k in u), 3.0)
        lo, hi = lo * m, hi * m
        derived = f" (סווינג ×{m:g})"
    elif style in STYLE_MULT:
        m = STYLE_MULT[style]
        if style == "intraday":
            m = next((v for k, v in INTRADAY_MULT.items() if k in u), m)
        if m != 1.0:
            lo, hi = lo * m, hi * m
            derived = f" ({style} ×{m:g})"
    # MEASURED FROM THE EDGE OF THE ZONE, NOT ITS MIDPOINT.
    #
    # Sagiv, 2026-08-31, on the gold short published minutes earlier: *"הסטופ
    # צמוד מידי, מהנקודה העליונה של הטווח זה 3 נקודות, זה ממש מעט. תרחיב
    # ל-5-7."* Entry 4,445.45 with the zone 4,443.45-4,447.45 and the stop at
    # 4,450.45 measures 5.00 from the midpoint and clears his band -- but a
    # fill anywhere in the published zone is a real fill, and the one at the
    # top left only 3.00 points of room. The band is a promise about RISK, and
    # risk is measured from the WORST fill the desk told him to expect.
    zlo, zhi = entry_zone(symbol, entry)
    short = stop > entry
    worst = zhi if short else zlo
    dist = abs(worst - stop)
    if dist < lo:
        stop = worst + lo if short else worst - lo
        warnings.append(f"הסטופ הורחב ל-{lo:,.0f} מקצה טווח הכניסה — תחתית "
                        f"הרצועה שקבעת (היה {dist:,.1f}){derived}")
    elif dist > hi:
        stop = worst + hi if short else worst - hi
        warnings.append(f"הסטופ הודק ל-{hi:,.0f} מקצה טווח הכניסה — תקרת "
                        f"הרצועה שקבעת (היה {dist:,.1f}){derived}")

    # PSYCHOLOGICAL ANCHORING — Sagiv, 2026-08-31: *"סטופ צריך להיות מעל או
    # מתחת רמה פסיכולוגית או מעל/מתחת לתמיכה"*. A stop sitting just IN FRONT
    # of a quarter-grid level is resting exactly where the level's own
    # defenders will trade against you; if a Q-level lies between the stop
    # and the band's ceiling, the stop crosses to its far side (+0.15 ATR),
    # never past the ceiling.
    try:
        from . import quarters
        for lv in quarters.nearest(symbol, stop, count=1):
            beyond = (stop < lv.price <= entry + hi) if short else                      (entry - hi <= lv.price < stop)
            if beyond:
                buf = 0.15 * max(atr, 1e-9)
                snapped = lv.price + buf if short else lv.price - buf
                if abs(entry - snapped) <= hi:
                    warnings.append(
                        f"הסטופ הוצמד מעבר לרמה הפסיכולוגית "
                        f"{lv.price:,.0f} ({lv.kind}) — לא נשענים לפניה")
                    stop = snapped
                break
    except Exception as exc:
        # THE STOP IS STILL VALID, IT IS JUST NOT OPTIMISED. Sagiv's rule,
        # derived from his two rulings on 2026-09-01: what the trader can see
        # for himself gets a LABEL; only what he cannot see any other way
        # blocks. He sees the stop on his chart. So a failed psychological
        # snap says so and ships, where a calendar outage -- an NFP he cannot
        # see coming -- stops the trade.
        warnings.append(f"הסטופ לא נבדק מול רמה פסיכולוגית "
                        f"({type(exc).__name__}) — תקף, לא ממוטב")
    return stop


@dataclass
class Plan:
    symbol: str
    close: float
    kind: str                    # "trend" | "reversal" | "none"
    direction: str | None        # "לונג" | "שורט"
    entry: float | None = None
    stop: float | None = None
    targets: list = field(default_factory=list)   # [(name, price)]
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    wait_for: str | None = None
    atr: float = 0.0
    style: str = "intraday"      # "scalp" | "intraday" | "swing"
    playbook: object | None = None   # chartdesk.playbook.Playbook, when matched
    scale_in: str | None = None  # the PDF protocol, when the style carries it
    # PARAMETERS THE TREE COULD NOT DRAW HERE. Not warnings about the trade --
    # a record of which readings this location happened to offer, which is
    # exactly what Sagiv asked the tree to report rather than refuse on.
    not_drawn: list = field(default_factory=list)
    # LEVELS IN THE WAY: named levels ahead of the entry, outside its zone,
    # nearer than TP1. Disclosed on the signal as "בדרך: …", never targets,
    # never profit events, never management triggers (see resolve_ladder).
    obstacles: list = field(default_factory=list)   # [(name, price)]
    # Why the resolver drew no ladder here, or None. A refused plan keeps
    # its geometry so the refusal can be scored like any other blocked plan.
    refusal: str | None = None
    # THE TRACKER'S VERDICT on whether the trade is active from the send,
    # stamped by tracker.record() (build close inside the band AND the live
    # tap agreeing). None until recorded; then the signal line follows it,
    # so the text and the recorded state come from one decision.
    born_open: bool | None = None
    # STAMPED BY tracker.blocked_after_stop when the post-stop cooldown let
    # this plan through because its entry lies beyond the stop that rejected
    # the last one. Positive information, not a warning: it goes on the
    # checklist as a ✅ and into watch_events as its own event kind, so the
    # exception can be scored separately from the trades it releases.
    cooldown_release: dict | None = None
    # WHAT THIS ENTRY IS ANCHORED TO, AND WHAT ARGUES AGAINST IT.
    # chartdesk.entry_quality classifies every plan; the labels ship on the
    # checklist and the full verdict goes to watch_events as a shadow record.
    # It changes no decision — turning the shadow into a block is Sagiv's
    # call. See entry_quality's docstring for the 04.09 trades behind it.
    entry_labels: list = field(default_factory=list)
    entry_quality: dict | None = None
    # Immutable receipt for the exact input ledger captured during this build.
    input_state_id: str | None = None

    @property
    def risk(self) -> float:
        if self.entry is None or self.stop is None:
            return 0.0
        return abs(self.entry - self.stop)

    @property
    def rr(self) -> float:
        """Reward-to-risk on the FIRST target — the one actually taken.

        This read `targets[-1]` (the FARTHEST target) until 2026-08-27, when
        Sagiv caught a gold short shipping "R:R 1.7" whose first target was
        4.36 points against a 5.76-point stop: **0.76R**. The 1.5 gate was
        being cleared by a target the trade might never reach, while the first
        partial -- the one the management engine takes at TP1 -- was booked at
        less than the risk.

        His own rule says exactly this (knowledge/05-risk-and-execution.md):
        "minimum 1.5R to the first target… if no level is far enough to pay
        for the risk, the correct output is 'price is pinned between its stop
        and its first obstacle — stand aside'."

        Since 2026-09-03 the first target is the first level that PAYS, and
        the nearer levels are disclosed as obstacles instead of gating the
        trade -- see resolve_ladder for the rule and why it overrides 05.
        """
        if not self.targets or not self.risk:
            return 0.0
        return abs(self.entry - self.targets[0][1]) / self.risk

    @property
    def rr_far(self) -> float:
        """Reward-to-risk on the farthest target — reported, never gated."""
        if not self.targets or not self.risk:
            return 0.0
        return abs(self.entry - self.targets[-1][1]) / self.risk

    @property
    def tradeable(self) -> bool:
        return (self.kind != "none" and self.refusal is None
                and self.rr >= MIN_RR)

    # Warnings a subscriber can act on, as opposed to desk-internal notes.
    # A caveat earns its line only if it changes how the trade should be read.
    CLIENT_CAVEATS = ("לא מאומת", "לא ממוטב", "לא נבדק", "מחוץ לחלונות",
                      "רחב מהתקרה", "הורחב")

    # The undrawn parameters, as tags. The tree writes full sentences because
    # they are read in the walk and in the log; a subscriber line has room for
    # a word. Explicit mapping rather than truncation, because "אין וקטור ואין
    # Stopping Volume" truncated to its first words says "אין וקטור ואין",
    # which is worse than saying nothing.
    NOT_DRAWN_TAGS = (
        ("Stopping Volume", "וקטור"),
        ("לא על רמה", "רמה"),
        ("commitment", "טריגר"),
        ("ללא הקשר", "הקשר וקטור"),
        ("לא נקרא במלואו", "הקשר וקטור"),
        ("הווקטור לא נקרא", "וקטור (לא נקרא)"),
        ("אין מגמה באף מסגרת", "מגמה"),
    )


MIN_TARGET_SEP_ATR = 0.5


def ladder_ready(cands: list, symbol: str, entry: float, atr: float,
                 short: bool) -> list:
    """Candidates that may legally be a target, nearest first.

    2026-09-01. A shipped NAS100 long carried TP3 at 29,499.10 against an entry
    of 29,492.60 -- 6.5 points out, 0.05R, and INSIDE the published entry zone
    29,467.60-29,517.60. It printed "TP3 הושג — היעד האחרון" while TP1 at
    29,687.60 had never been approached. A price you are still ENTERING at
    cannot also be where you take profit.

    Three rules, each reusing a constant that already exists:
      - it must be genuinely ahead (a "target" behind entry is not a target)
      - it must be outside the entry zone
      - it must be at least MIN_TARGET_SEP_ATR away, the same separation the
        ladder already demands BETWEEN rungs. If two targets that close count
        as one place, a target that close to entry is the entry.
    """
    lo, hi = entry_zone(symbol, entry)
    out = []
    for nm, px in cands:
        # SIGNED, deliberately. A candidate behind the entry comes out
        # negative and is therefore already below the separation floor -- a
        # separate `if d <= 0` guard was written here first and could never
        # fire on its own, which is the shape this repo keeps producing. One
        # comparison does both jobs.
        d = (entry - px) if short else (px - entry)
        if lo <= px <= hi:
            continue
        if d < MIN_TARGET_SEP_ATR * atr:
            continue
        out.append((d, nm, px))
    out.sort(key=lambda r: r[0])
    return [(nm, px) for _, nm, px in out]


def ordered_ladder(targets: list, entry: float, short: bool) -> list:
    """The ladder in the only order a ladder can have: nearest rung first.

    The numbering IS the promise -- TP1 is what price meets first, TP3 is the
    far one, and "היעד האחרון" means the trade has run its course. Intraday
    built `early[:1] + ahead` and never re-sorted, so a confluence zone farther
    out could be pushed to the front and the nearest level fell to the end.
    A sort here cannot be bypassed by any future candidate source, which is
    why it sits at the end rather than only tightening the filter upstream.
    """
    return sorted(targets,
                  key=lambda t: (entry - t[1]) if short else (t[1] - entry))


def distinct_targets(cands: list, entry: float, atr: float,
                     limit: int = 2) -> list:
    """Pick targets that are genuinely apart, merging coincident level names."""
    out: list = []
    for nm, px in cands:
        if not out:
            out.append([nm, px])
            continue
        if abs(px - out[-1][1]) < MIN_TARGET_SEP_ATR * atr:
            # Same place, two names: keep the nearer price, name both once.
            if nm not in out[-1][0]:
                out[-1][0] = f"{out[-1][0]}/{nm}"
            continue
        if len(out) >= limit:
            break
        out.append([nm, px])
    return [(nm, px) for nm, px in out[:limit]]


def _n_levels(n: int) -> str:
    return "רמה אחת" if n == 1 else f"{n} רמות"


def resolve_ladder(cands: list, symbol: str, entry: float, stop: float,
                   short: bool, atr: float,
                   limit: int = INTRADAY_TARGET_COUNT) -> tuple:
    """(targets, obstacles, refusal) for candidate levels against a FINAL stop.

    One resolver for every builder -- the engine's intraday build, both of
    the tree's geometry copies, the conditional preview and trade_admin's
    rebuild -- so a ladder cannot mean different things on different paths.
    `targets` is nearest-first and capped at `limit`; `obstacles` are the
    distinct levels nearer than TP1; `refusal` says why no ladder was drawn,
    or is None. A refusal still returns the paying levels it found, so the
    refused geometry can be logged and scored.
    """
    ready = ladder_ready(cands, symbol, entry, atr, short)
    merged = distinct_targets(ready, entry, atr, limit=max(len(ready), 1))
    risk = abs(entry - stop) or 1e-9
    obstacles = [(nm, px) for nm, px in merged
                 if abs(px - entry) / risk < MIN_RR]
    paying = [(nm, px) for nm, px in merged
              if abs(px - entry) / risk >= MIN_RR]
    road = " · ".join(f"{nm} {px:,.2f}" for nm, px in obstacles[:3])
    if not paying:
        why = "אין רמה שמשלמת על הסטופ"
        if obstacles:
            why += f": {_n_levels(len(obstacles))} בדרך ({road})"
        return [], obstacles, why
    first_r = abs(paying[0][1] - entry) / risk
    if first_r > FAR_TP1_R and obstacles:
        return (ordered_ladder(paying[:limit], entry, short), obstacles,
                f"יעד ראשון רחוק: {first_r:.2f}R מעבר ל-{FAR_TP1_R:g}R, "
                f"{_n_levels(len(obstacles))} בדרך ({road})")
    targets = _with_measured_rung(paying, entry, stop, short)
    return ordered_ladder(targets[:limit], entry, short), obstacles, None
