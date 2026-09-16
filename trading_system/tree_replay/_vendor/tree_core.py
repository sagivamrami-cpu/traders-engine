"""The TR decision tree, executed — a range of readings, drawn where available.

Sagiv built the tree and the feature spec in a separate session
(`~/Desktop/md/TR-TREE-V2.md`, 444 lines; `TR-FEATURE-SPEC.md`, 171) and asked
for strategies and trades built on them. This module is the runtime: it walks
every stage in order against live data and reports what each one yielded.

**A DOCUMENTED DISAGREEMENT, 2026-09-01, and he should settle it.** This
docstring used to say "every stage a gate, every fall a NO TRADE", and cited
his own document, which says exactly that: *"כל ענף שנופל = NO TRADE, לא
'כניסה חלשה'"*. The code was faithful to what he had written.

He then told me three times, in conversation, the opposite:

    "לא בכל עסקה יהיה נר וקטור כאישור... אם אין נר וקטור אז ממשיכים לסעיפים
     הבאים, איפה שאפשר לשאוב נתון שואבים ואז המערכת בונה עסקה... העץ הוא
     מגוון רחב של נתונים שאפשר לשאוב ולבנות מזה עסקה, כל פעם יהיה משהו
     אחר... זה לא צריך לפסול עסקה כי חסר נתון."

The runtime now follows what he SAID, because it is the later instruction
and he repeated it. TR-TREE-V2.md still says the older thing and has not
been edited -- if that document is ever treated as the source of truth again,
it will contradict this file. That is his to reconcile, not mine to quietly
overwrite.

**What that means here.** A stage that yields nothing appends to `w.missing`
and the walk continues; the stage still joins `passed`, because it WAS
consulted -- "walked" and "yielded something" are separate questions. Only
the absence of something every later stage refines stops the walk: no data,
an unverified tape, too few bars, an unusable news calendar, no level map,
no directional read at all on the 4h, and no level ahead to serve as a
target. Those are not refusals of a setup; there is simply nothing to build.

**The stages, and where each already had an owner here:**

    0  DATA GATE          corr.unverified on BOTH 15m and 4h + bar count
                          (broker_shape_ok is NOT called here -- the doc and
                          08-tree-coverage.md both claimed it was, and an
                          audited table even ticked it. Corrected 2026-08-31.)
    1  CONTEXT (4h)       matrix.read_tr + stretch (deviation, contraction)
    2  LEVEL MAP          levelmap.build
    3  SESSION STATE      sessions + brinks
    4  PATTERN SCAN       wm.detect
    5  LOCATION GATE      levelmap proximity  ← RANGE EXHAUSTION lives here
    6  VECTOR GATE        tr.pvsra + stopping volume
    7  MTF DECOMPOSITION  vectors inside the higher-TF candle
    8  TRAP TEST          vector at the extreme ⇒ trade the OTHER way
    9  VECTOR MEMORY      tr.vector_zones -- zones left by climax candles,
                          open until price trades back through them. Liquidity
                          pools (EQH/EQL) are reported ALONGSIDE, under their
                          own name, because they are a different object.
    10 TRIGGER            commitment of the last bar — a FACT (0.15 ATR
                          classification, engineering heuristic)
    11 TARGET ENGINE      scalp → next pivot · swing → AWR/RW. (The old
                          parenthetical here — "AFTER target: the hybrid
                          tree's order" — described TRIGGER's former slot
                          and the reverse order; both are gone. Still true:
                          AGGRESSIVE_ATR/BARS are defined and never read,
                          whatever 09-engine-spec.md says.)
    12 RISK               his own, no Tino version exists
    13 INVALIDATION       pattern break / vector recovered against you

    NOTE: STAGES has twelve entries and ends at TARGET — TRIGGER precedes
    it since Sagiv's 2026-09-01 ruling, matching his document. RISK and
    INVALIDATION are listed above because they are part of HIS tree, but
    walk() does not run them; they are built afterwards, in
    trade_from_walk() and the engine.

**The nine open parameters are NOT guessed here.** The document lists them as
places the source contradicts itself or is silent (vector base, recovery
definition, "aggressive", "commitment", "at the highest point", level-zone
width...). Each is a module constant with the document's own question in the
comment, defaulted to the most conservative reading, and every plan reports
which defaults it leaned on. A guess presented as a rule is exactly what the
tree's provenance marks exist to prevent.

**Nothing here is measured.** The document says so itself: *"העץ מתאר מה ידוע,
לא מה עובד. אף אחד מהשלבים לא נמדד."* Firings log; the voice question is the
setup-scientist's.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
VECTOR_BASE = 'mean'
RECOVERY = '50pct'
MAX_MAGNET_ATR = 5.0
AGGRESSIVE_ATR = 1.5
AGGRESSIVE_BARS = 3
EXTREME_LOOKBACK = 40
BUY_SIDE, SELL_SIDE = ({'green', 'blue'}, {'red', 'violet'})
EXTREME_PCT = 0.85
MAX_DECISION_DRIFT_ATR = 0.33
LEVEL_ZONE_ATR = 0.35
STOP_CUSHION_ATR = 0.35
TREE_STYLE = 'intraday'
SV_BODY_MAX = 0.35
SV_WICK_MIN = 0.5
SV_VOLUME_MULT = 1.5

class LevelsUnavailable(RuntimeError):
    """The level universe could not be read; this is not an empty map."""
FINAL_STAGE = None
STAGES = ['DATA', 'CONTEXT', 'LEVELS', 'SESSION', 'PATTERN', 'LOCATION', 'VECTOR', 'MTF', 'TRAP', 'MEMORY', 'TRIGGER', 'TARGET']
FINAL_STAGE = STAGES[-1]

def _news_stop(events: list[dict], now_ts: float) -> str | None:
    """A stop reason for the real ForexFactory cache shape, or ``None``.

    A calendar with no future coverage is unusable, not a quiet calendar.
    The caller deliberately lets that exception fail the tree closed.
    """
    from .revalidation import calendar_event_ts, calendar_high_impact_in_window
    if not any(((calendar_event_ts(event) or 0) > now_ts for event in events)):
        raise ValueError('calendar has no future events — stale')
    event = calendar_high_impact_in_window(events, now_ts, 15 * 60)
    if event is None:
        return None
    return f"חלון חדשות: {event.get('title', '?')} — רבע שעה לפני ואחרי לא סוחרים [07 @ 23m32s]"

@dataclass
class Walk:
    """How far the tree got, and why it stopped."""
    symbol: str
    reached: str
    variant: str = 'house'
    passed: list = field(default_factory=list)
    stopped_because: str | None = None
    direction: str | None = None
    facts: dict = field(default_factory=dict)
    assumptions: list = field(default_factory=list)
    zones: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    decided_close: float | None = None
    decided_bar: str | None = None
    refused: object | None = None

    @property
    def complete(self) -> bool:
        return self.stopped_because is None and self.reached == FINAL_STAGE

    def render(self) -> str:
        name = self.symbol.split(':')[-1]
        head = f'🌳 {name} — עץ ההחלטות: ' + (f'עבר עד {self.reached}' if not self.complete else f'עבר את כל השלבים · כיוון {self.direction}')
        lines = [head]
        lines.append('  ' + ' → '.join(self.passed) if self.passed else '  נעצר בשלב הראשון')
        if self.stopped_because:
            lines.append(f'  ⛔ {self.reached}: {self.stopped_because} ⇒ NO TRADE')
        for k, v in self.facts.items():
            lines.append(f'  {k}: {v}')
        if self.assumptions:
            lines.append('  הנחות (פרמטרים פתוחים בעץ): ' + ' · '.join(self.assumptions))
        return '\n'.join(lines)

def _atr(df: pd.DataFrame, n: int=14) -> float:
    prev = df['close'].shift(1)
    rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
    return float(rng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])

def _stopping_volume(df: pd.DataFrame) -> bool:
    """Stopping Volume: a rejection candle SHAPE that volume confirms.

    THE NAME REQUIRED THE VOLUME, AND THE FUNCTION READ NONE.
    2026-09-01, Codex: this measured body and wick geometry only -- no volume
    column was touched anywhere in it -- while the fact printed to a
    subscriber said "Stopping Volume — נר ההיפוך היחיד בשיטה". Gold's entire
    STAGE 6 pass rested on it, and `sv_only` is allowed to INVERT a trade's
    direction at an extreme. A pin bar on ordinary volume was being read as
    the method's reversal signal and could turn a trade around.

    Geometry is necessary and was never sufficient. Volume now has to agree,
    at the method's OWN threshold -- PVSRA's 150% "above average", the same
    number that separates a blue/violet rising vector from an ordinary
    candle. No new constant is invented for this; the one that already
    defines "unusual participation" here is the one used.
    """
    if len(df) < 12:
        return False
    bar = df.iloc[-2]
    hi, lo = (float(bar['high']), float(bar['low']))
    rng = hi - lo
    if rng <= 0:
        return False
    body = abs(float(bar['close']) - float(bar['open'])) / rng
    upper = (hi - max(float(bar['close']), float(bar['open']))) / rng
    lower = (min(float(bar['close']), float(bar['open'])) - lo) / rng
    if not (body <= SV_BODY_MAX and max(upper, lower) >= SV_WICK_MIN):
        return False
    try:
        base = float(df['volume'].iloc[-12:-2].mean())
        vol = float(bar['volume'])
    except Exception:
        return False
    if base <= 0 or vol != vol or base != base:
        return False
    return vol >= SV_VOLUME_MULT * base

def _levels_ahead(levels, close: float, short: bool, atr: float) -> list:
    """Every DISTINCT level in the trade's direction, nearest first.

    These are CANDIDATES, not the ladder. Which of them are targets and
    which are obstacles is decided by tradeplan.resolve_ladder once the stop
    is known -- until 2026-09-03 this helper returned the nearest two as the
    ladder outright, so the tree's TP1 was routinely the level price was
    standing on (0.01-0.06R) and every Nasdaq walk died on R:R.

    2026-09-03 13:25: the tree sent XAUUSD BUY 4,425.10 with TP1 D4-LO
    4,445.455 and TP2 LWEEK-LO 4,445.455 -- the same price under two names,
    so the ladder had one rung and the client got "TP2" that could never pay
    more than TP1. Sagiv: "הtp1 ו2 אותו יעד, תתקנו את זה". The engine path
    already merges coincident names through tradeplan.distinct_targets; the
    tree's three copies of nearest-ahead never called it. One helper now,
    used by all three, so the tree cannot drift from the engine again.

    The nearest name stays first inside a merged label ("D4-LO/LWEEK-LO"),
    so the client reads the level that is actually nearest first. (Until
    2026-09-03 the style check read that first name too; see TREE_STYLE.)
    """
    from .pricing import distinct_targets
    cands = sorted([(n, p) for n, p in levels if (p < close if short else p > close)], key=lambda r: abs(r[1] - close))
    return distinct_targets(cands, close, atr, limit=max(len(cands), 1))

def _stamp_decision(w: Walk, d15: pd.DataFrame) -> bool:
    """Anchor a decision to the exact price/bar it approved."""
    try:
        w.decided_close = float(d15['close'].iloc[-1])
        w.decided_bar = str(d15.index[-1])
    except Exception as exc:
        w.stopped_because = f'החלטה ללא חותמת מחיר/נר ({type(exc).__name__}) — שומר הסחף לא זמין'
        return False
    return True

def _levels_unavailable_reason(variant: str) -> str:
    reason = 'מפת הרמות לא נקראה'
    if variant == 'strict':
        reason += ' במלואה — פיבוטים אינם תחליף למפת הבסיס'
    return reason
TREND_LADDER = ('4h', '1h', '30m', '15m', '5m')
HI_FRAMES = ('4h', '1h')
LO_FRAMES = ('30m', '15m', '5m')

def _side(reads) -> str | None:
    """The agreed side of several frames, or None when they disagree."""
    dirs = {r.direction for r in reads if r.direction != 0}
    if dirs == {1}:
        return 'לונג'
    if dirs == {-1}:
        return 'שורט'
    return None

def _trend_from_ladder(ladder: dict) -> tuple:
    """(higher-range side, shorter-range side, where the direction came from).

    COMBINED, not "the first frame that has an opinion". Codex, auditing this
    on 2026-09-01: the ladder read five frames and then let a single
    directional 4h override four frames disagreeing with it, which is not the
    combination Sagiv asked for.

    Order of authority, and each step is a reading of a RANGE rather than of
    one chart: the higher pair when they agree; else the shorter three when
    they agree; else the whole stack when every frame leans one way. Only
    then, nothing.
    """
    hi = _side([ladder[t] for t in HI_FRAMES if t in ladder])
    lo = _side([ladder[t] for t in LO_FRAMES if t in ladder])

    def _first(frames, side):
        """The frame in `frames` carrying `side` — the read to build on.

        The label names a RANGE, but every later stage needs an actual
        ToolRead. Returning only the label left `ladder.get(label)` finding
        nothing and silently keeping the 4h read: a direction from the short
        range described by the 4h chart. Caught by the suite within a minute
        of my writing it.
        """
        want = 1 if side == 'לונג' else -1
        return next((t for t in frames if t in ladder and ladder[t].direction == want), None)
    if hi:
        return (hi, lo, 'טווח גבוה (4h+1h)', _first(HI_FRAMES, hi))
    if lo:
        return (hi, lo, 'טווח קצר (30m+15m+5m)', _first(LO_FRAMES, lo))
    whole = _side(list(ladder.values()))
    if whole:
        return (hi, lo, 'כל המסגרות', _first(TREND_LADDER, whole))
    return (hi, lo, None, None)

def _ladder_text(ladder: dict, frames) -> str:
    parts = []
    for tf in frames:
        r = ladder.get(tf)
        if r is None:
            parts.append(f'{tf} לא נקרא')
        else:
            parts.append(f'{tf} ' + ('לונג' if r.direction > 0 else 'שורט' if r.direction < 0 else 'דחוס'))
    return ' · '.join(parts)

def trap_direction(at_high: bool, at_low: bool, vec_kind: str | None, sv: bool, trend_dir: str | None) -> tuple[str | None, str]:
    """Which way an extreme vector points: (direction, why).

    Pure, so the decision can be DRIVEN by a test rather than reimplemented
    beside one. Extracting it is what finally covered the wrong-direction bug
    below: with the logic inline, reverting the fix left all 598 tests green.

    Three readings, in order:

    A TRAP inverts the vector's own side, because the vector is the side
    caught out. Heavy buying into the high is longs walking into supply;
    heavy selling into the low is shorts walking into demand.

    NO TRAP, still at an extreme: the vector keeps its own side. It is
    committing, not being trapped. 2026-09-01, live and confirmed: the
    Nasdaq closed at 29,060.20, below the 15th percentile of 29,084.33, on a
    GREEN candle -- heavy buying at the low. The branch said "not a trap",
    correctly, and then handed the trade `trend_dir`, which was SHORT. The
    desk sold heavy buying at the low.

    MID-RANGE: the prevailing trend carries it. A vector between the
    extremes is not making a stand anywhere.
    """
    at_edge = at_high or at_low
    if at_high and (vec_kind in BUY_SIDE or (vec_kind is None and sv and (trend_dir == 'לונג'))):
        return ('שורט', 'trap')
    if at_low and (vec_kind in SELL_SIDE or (vec_kind is None and sv and (trend_dir == 'שורט'))):
        return ('לונג', 'trap')
    if at_edge and vec_kind in BUY_SIDE:
        return ('לונג', 'committed')
    if at_edge and vec_kind in SELL_SIDE:
        return ('שורט', 'committed')
    return (trend_dir, 'trend')
