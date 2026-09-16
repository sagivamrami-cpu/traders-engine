# Task1 complete untracked additions

BASE=HEAD=c1b6071633c55376c64f0a98ece843706f420f49; no task commits. Five full additions, git diff --no-index NUL, not empty tracked diff.

warning: in the working copy of 'trading_system/tree_replay/_vendor/tree_core.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tree_core.py b/trading_system/tree_replay/_vendor/tree_core.py
new file mode 100644
index 0000000..788b47d
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tree_core.py
@@ -0,0 +1,328 @@
+"""The TR decision tree, executed — a range of readings, drawn where available.
+
+Sagiv built the tree and the feature spec in a separate session
+(`~/Desktop/md/TR-TREE-V2.md`, 444 lines; `TR-FEATURE-SPEC.md`, 171) and asked
+for strategies and trades built on them. This module is the runtime: it walks
+every stage in order against live data and reports what each one yielded.
+
+**A DOCUMENTED DISAGREEMENT, 2026-09-01, and he should settle it.** This
+docstring used to say "every stage a gate, every fall a NO TRADE", and cited
+his own document, which says exactly that: *"כל ענף שנופל = NO TRADE, לא
+'כניסה חלשה'"*. The code was faithful to what he had written.
+
+He then told me three times, in conversation, the opposite:
+
+    "לא בכל עסקה יהיה נר וקטור כאישור... אם אין נר וקטור אז ממשיכים לסעיפים
+     הבאים, איפה שאפשר לשאוב נתון שואבים ואז המערכת בונה עסקה... העץ הוא
+     מגוון רחב של נתונים שאפשר לשאוב ולבנות מזה עסקה, כל פעם יהיה משהו
+     אחר... זה לא צריך לפסול עסקה כי חסר נתון."
+
+The runtime now follows what he SAID, because it is the later instruction
+and he repeated it. TR-TREE-V2.md still says the older thing and has not
+been edited -- if that document is ever treated as the source of truth again,
+it will contradict this file. That is his to reconcile, not mine to quietly
+overwrite.
+
+**What that means here.** A stage that yields nothing appends to `w.missing`
+and the walk continues; the stage still joins `passed`, because it WAS
+consulted -- "walked" and "yielded something" are separate questions. Only
+the absence of something every later stage refines stops the walk: no data,
+an unverified tape, too few bars, an unusable news calendar, no level map,
+no directional read at all on the 4h, and no level ahead to serve as a
+target. Those are not refusals of a setup; there is simply nothing to build.
+
+**The stages, and where each already had an owner here:**
+
+    0  DATA GATE          corr.unverified on BOTH 15m and 4h + bar count
+                          (broker_shape_ok is NOT called here -- the doc and
+                          08-tree-coverage.md both claimed it was, and an
+                          audited table even ticked it. Corrected 2026-08-31.)
+    1  CONTEXT (4h)       matrix.read_tr + stretch (deviation, contraction)
+    2  LEVEL MAP          levelmap.build
+    3  SESSION STATE      sessions + brinks
+    4  PATTERN SCAN       wm.detect
+    5  LOCATION GATE      levelmap proximity  ← RANGE EXHAUSTION lives here
+    6  VECTOR GATE        tr.pvsra + stopping volume
+    7  MTF DECOMPOSITION  vectors inside the higher-TF candle
+    8  TRAP TEST          vector at the extreme ⇒ trade the OTHER way
+    9  VECTOR MEMORY      tr.vector_zones -- zones left by climax candles,
+                          open until price trades back through them. Liquidity
+                          pools (EQH/EQL) are reported ALONGSIDE, under their
+                          own name, because they are a different object.
+    10 TRIGGER            commitment of the last bar — a FACT (0.15 ATR
+                          classification, engineering heuristic)
+    11 TARGET ENGINE      scalp → next pivot · swing → AWR/RW. (The old
+                          parenthetical here — "AFTER target: the hybrid
+                          tree's order" — described TRIGGER's former slot
+                          and the reverse order; both are gone. Still true:
+                          AGGRESSIVE_ATR/BARS are defined and never read,
+                          whatever 09-engine-spec.md says.)
+    12 RISK               his own, no Tino version exists
+    13 INVALIDATION       pattern break / vector recovered against you
+
+    NOTE: STAGES has twelve entries and ends at TARGET — TRIGGER precedes
+    it since Sagiv's 2026-09-01 ruling, matching his document. RISK and
+    INVALIDATION are listed above because they are part of HIS tree, but
+    walk() does not run them; they are built afterwards, in
+    trade_from_walk() and the engine.
+
+**The nine open parameters are NOT guessed here.** The document lists them as
+places the source contradicts itself or is silent (vector base, recovery
+definition, "aggressive", "commitment", "at the highest point", level-zone
+width...). Each is a module constant with the document's own question in the
+comment, defaulted to the most conservative reading, and every plan reports
+which defaults it leaned on. A guess presented as a rule is exactly what the
+tree's provenance marks exist to prevent.
+
+**Nothing here is measured.** The document says so itself: *"העץ מתאר מה ידוע,
+לא מה עובד. אף אחד מהשלבים לא נמדד."* Firings log; the voice question is the
+setup-scientist's.
+"""
+from __future__ import annotations
+from dataclasses import dataclass, field
+import pandas as pd
+VECTOR_BASE = 'mean'
+RECOVERY = '50pct'
+MAX_MAGNET_ATR = 5.0
+AGGRESSIVE_ATR = 1.5
+AGGRESSIVE_BARS = 3
+EXTREME_LOOKBACK = 40
+BUY_SIDE, SELL_SIDE = ({'green', 'blue'}, {'red', 'violet'})
+EXTREME_PCT = 0.85
+MAX_DECISION_DRIFT_ATR = 0.33
+LEVEL_ZONE_ATR = 0.35
+STOP_CUSHION_ATR = 0.35
+TREE_STYLE = 'intraday'
+SV_BODY_MAX = 0.35
+SV_WICK_MIN = 0.5
+SV_VOLUME_MULT = 1.5
+
+class LevelsUnavailable(RuntimeError):
+    """The level universe could not be read; this is not an empty map."""
+FINAL_STAGE = None
+STAGES = ['DATA', 'CONTEXT', 'LEVELS', 'SESSION', 'PATTERN', 'LOCATION', 'VECTOR', 'MTF', 'TRAP', 'MEMORY', 'TRIGGER', 'TARGET']
+FINAL_STAGE = STAGES[-1]
+
+def _news_stop(events: list[dict], now_ts: float) -> str | None:
+    """A stop reason for the real ForexFactory cache shape, or ``None``.
+
+    A calendar with no future coverage is unusable, not a quiet calendar.
+    The caller deliberately lets that exception fail the tree closed.
+    """
+    from .revalidation import calendar_event_ts, calendar_high_impact_in_window
+    if not any(((calendar_event_ts(event) or 0) > now_ts for event in events)):
+        raise ValueError('calendar has no future events — stale')
+    event = calendar_high_impact_in_window(events, now_ts, 15 * 60)
+    if event is None:
+        return None
+    return f"חלון חדשות: {event.get('title', '?')} — רבע שעה לפני ואחרי לא סוחרים [07 @ 23m32s]"
+
+@dataclass
+class Walk:
+    """How far the tree got, and why it stopped."""
+    symbol: str
+    reached: str
+    variant: str = 'house'
+    passed: list = field(default_factory=list)
+    stopped_because: str | None = None
+    direction: str | None = None
+    facts: dict = field(default_factory=dict)
+    assumptions: list = field(default_factory=list)
+    zones: list = field(default_factory=list)
+    missing: list = field(default_factory=list)
+    decided_close: float | None = None
+    decided_bar: str | None = None
+    refused: object | None = None
+
+    @property
+    def complete(self) -> bool:
+        return self.stopped_because is None and self.reached == FINAL_STAGE
+
+    def render(self) -> str:
+        name = self.symbol.split(':')[-1]
+        head = f'🌳 {name} — עץ ההחלטות: ' + (f'עבר עד {self.reached}' if not self.complete else f'עבר את כל השלבים · כיוון {self.direction}')
+        lines = [head]
+        lines.append('  ' + ' → '.join(self.passed) if self.passed else '  נעצר בשלב הראשון')
+        if self.stopped_because:
+            lines.append(f'  ⛔ {self.reached}: {self.stopped_because} ⇒ NO TRADE')
+        for k, v in self.facts.items():
+            lines.append(f'  {k}: {v}')
+        if self.assumptions:
+            lines.append('  הנחות (פרמטרים פתוחים בעץ): ' + ' · '.join(self.assumptions))
+        return '\n'.join(lines)
+
+def _atr(df: pd.DataFrame, n: int=14) -> float:
+    prev = df['close'].shift(1)
+    rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
+    return float(rng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])
+
+def _stopping_volume(df: pd.DataFrame) -> bool:
+    """Stopping Volume: a rejection candle SHAPE that volume confirms.
+
+    THE NAME REQUIRED THE VOLUME, AND THE FUNCTION READ NONE.
+    2026-09-01, Codex: this measured body and wick geometry only -- no volume
+    column was touched anywhere in it -- while the fact printed to a
+    subscriber said "Stopping Volume — נר ההיפוך היחיד בשיטה". Gold's entire
+    STAGE 6 pass rested on it, and `sv_only` is allowed to INVERT a trade's
+    direction at an extreme. A pin bar on ordinary volume was being read as
+    the method's reversal signal and could turn a trade around.
+
+    Geometry is necessary and was never sufficient. Volume now has to agree,
+    at the method's OWN threshold -- PVSRA's 150% "above average", the same
+    number that separates a blue/violet rising vector from an ordinary
+    candle. No new constant is invented for this; the one that already
+    defines "unusual participation" here is the one used.
+    """
+    if len(df) < 12:
+        return False
+    bar = df.iloc[-2]
+    hi, lo = (float(bar['high']), float(bar['low']))
+    rng = hi - lo
+    if rng <= 0:
+        return False
+    body = abs(float(bar['close']) - float(bar['open'])) / rng
+    upper = (hi - max(float(bar['close']), float(bar['open']))) / rng
+    lower = (min(float(bar['close']), float(bar['open'])) - lo) / rng
+    if not (body <= SV_BODY_MAX and max(upper, lower) >= SV_WICK_MIN):
+        return False
+    try:
+        base = float(df['volume'].iloc[-12:-2].mean())
+        vol = float(bar['volume'])
+    except Exception:
+        return False
+    if base <= 0 or vol != vol or base != base:
+        return False
+    return vol >= SV_VOLUME_MULT * base
+
+def _levels_ahead(levels, close: float, short: bool, atr: float) -> list:
+    """Every DISTINCT level in the trade's direction, nearest first.
+
+    These are CANDIDATES, not the ladder. Which of them are targets and
+    which are obstacles is decided by tradeplan.resolve_ladder once the stop
+    is known -- until 2026-09-03 this helper returned the nearest two as the
+    ladder outright, so the tree's TP1 was routinely the level price was
+    standing on (0.01-0.06R) and every Nasdaq walk died on R:R.
+
+    2026-09-03 13:25: the tree sent XAUUSD BUY 4,425.10 with TP1 D4-LO
+    4,445.455 and TP2 LWEEK-LO 4,445.455 -- the same price under two names,
+    so the ladder had one rung and the client got "TP2" that could never pay
+    more than TP1. Sagiv: "הtp1 ו2 אותו יעד, תתקנו את זה". The engine path
+    already merges coincident names through tradeplan.distinct_targets; the
+    tree's three copies of nearest-ahead never called it. One helper now,
+    used by all three, so the tree cannot drift from the engine again.
+
+    The nearest name stays first inside a merged label ("D4-LO/LWEEK-LO"),
+    so the client reads the level that is actually nearest first. (Until
+    2026-09-03 the style check read that first name too; see TREE_STYLE.)
+    """
+    from .pricing import distinct_targets
+    cands = sorted([(n, p) for n, p in levels if (p < close if short else p > close)], key=lambda r: abs(r[1] - close))
+    return distinct_targets(cands, close, atr, limit=max(len(cands), 1))
+
+def _stamp_decision(w: Walk, d15: pd.DataFrame) -> bool:
+    """Anchor a decision to the exact price/bar it approved."""
+    try:
+        w.decided_close = float(d15['close'].iloc[-1])
+        w.decided_bar = str(d15.index[-1])
+    except Exception as exc:
+        w.stopped_because = f'החלטה ללא חותמת מחיר/נר ({type(exc).__name__}) — שומר הסחף לא זמין'
+        return False
+    return True
+
+def _levels_unavailable_reason(variant: str) -> str:
+    reason = 'מפת הרמות לא נקראה'
+    if variant == 'strict':
+        reason += ' במלואה — פיבוטים אינם תחליף למפת הבסיס'
+    return reason
+TREND_LADDER = ('4h', '1h', '30m', '15m', '5m')
+HI_FRAMES = ('4h', '1h')
+LO_FRAMES = ('30m', '15m', '5m')
+
+def _side(reads) -> str | None:
+    """The agreed side of several frames, or None when they disagree."""
+    dirs = {r.direction for r in reads if r.direction != 0}
+    if dirs == {1}:
+        return 'לונג'
+    if dirs == {-1}:
+        return 'שורט'
+    return None
+
+def _trend_from_ladder(ladder: dict) -> tuple:
+    """(higher-range side, shorter-range side, where the direction came from).
+
+    COMBINED, not "the first frame that has an opinion". Codex, auditing this
+    on 2026-09-01: the ladder read five frames and then let a single
+    directional 4h override four frames disagreeing with it, which is not the
+    combination Sagiv asked for.
+
+    Order of authority, and each step is a reading of a RANGE rather than of
+    one chart: the higher pair when they agree; else the shorter three when
+    they agree; else the whole stack when every frame leans one way. Only
+    then, nothing.
+    """
+    hi = _side([ladder[t] for t in HI_FRAMES if t in ladder])
+    lo = _side([ladder[t] for t in LO_FRAMES if t in ladder])
+
+    def _first(frames, side):
+        """The frame in `frames` carrying `side` — the read to build on.
+
+        The label names a RANGE, but every later stage needs an actual
+        ToolRead. Returning only the label left `ladder.get(label)` finding
+        nothing and silently keeping the 4h read: a direction from the short
+        range described by the 4h chart. Caught by the suite within a minute
+        of my writing it.
+        """
+        want = 1 if side == 'לונג' else -1
+        return next((t for t in frames if t in ladder and ladder[t].direction == want), None)
+    if hi:
+        return (hi, lo, 'טווח גבוה (4h+1h)', _first(HI_FRAMES, hi))
+    if lo:
+        return (hi, lo, 'טווח קצר (30m+15m+5m)', _first(LO_FRAMES, lo))
+    whole = _side(list(ladder.values()))
+    if whole:
+        return (hi, lo, 'כל המסגרות', _first(TREND_LADDER, whole))
+    return (hi, lo, None, None)
+
+def _ladder_text(ladder: dict, frames) -> str:
+    parts = []
+    for tf in frames:
+        r = ladder.get(tf)
+        if r is None:
+            parts.append(f'{tf} לא נקרא')
+        else:
+            parts.append(f'{tf} ' + ('לונג' if r.direction > 0 else 'שורט' if r.direction < 0 else 'דחוס'))
+    return ' · '.join(parts)
+
+def trap_direction(at_high: bool, at_low: bool, vec_kind: str | None, sv: bool, trend_dir: str | None) -> tuple[str | None, str]:
+    """Which way an extreme vector points: (direction, why).
+
+    Pure, so the decision can be DRIVEN by a test rather than reimplemented
+    beside one. Extracting it is what finally covered the wrong-direction bug
+    below: with the logic inline, reverting the fix left all 598 tests green.
+
+    Three readings, in order:
+
+    A TRAP inverts the vector's own side, because the vector is the side
+    caught out. Heavy buying into the high is longs walking into supply;
+    heavy selling into the low is shorts walking into demand.
+
+    NO TRAP, still at an extreme: the vector keeps its own side. It is
+    committing, not being trapped. 2026-09-01, live and confirmed: the
+    Nasdaq closed at 29,060.20, below the 15th percentile of 29,084.33, on a
+    GREEN candle -- heavy buying at the low. The branch said "not a trap",
+    correctly, and then handed the trade `trend_dir`, which was SHORT. The
+    desk sold heavy buying at the low.
+
+    MID-RANGE: the prevailing trend carries it. A vector between the
+    extremes is not making a stand anywhere.
+    """
+    at_edge = at_high or at_low
+    if at_high and (vec_kind in BUY_SIDE or (vec_kind is None and sv and (trend_dir == 'לונג'))):
+        return ('שורט', 'trap')
+    if at_low and (vec_kind in SELL_SIDE or (vec_kind is None and sv and (trend_dir == 'שורט'))):
+        return ('לונג', 'trap')
+    if at_edge and vec_kind in BUY_SIDE:
+        return ('לונג', 'committed')
+    if at_edge and vec_kind in SELL_SIDE:
+        return ('שורט', 'committed')
+    return (trend_dir, 'trend')

warning: in the working copy of 'trading_system/tree_replay/_vendor/tree_signals.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tree_signals.py b/trading_system/tree_replay/_vendor/tree_signals.py
new file mode 100644
index 0000000..0f2c61d
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tree_signals.py
@@ -0,0 +1,3 @@
+from .tr import emas, ema_cloud
+from .pvsra import pvsra
+from .tree_tr import vector_zones, daily_pivots

warning: in the working copy of 'trading_system/tree_replay/_vendor/tree_walk.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tree_walk.py b/trading_system/tree_replay/_vendor/tree_walk.py
new file mode 100644
index 0000000..c135752
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tree_walk.py
@@ -0,0 +1,566 @@
+from __future__ import annotations
+import pandas as pd
+from . import admission_matrix as matrix, map_sessions as sessions, watch_sessions
+from . import tree_signals as tr
+from .basis_operation import BasisOperation
+from .levelmap_operation import LevelmapOperation
+from .brinks import BrinksReader
+from .checklists import ChecklistReader
+from .wm import WmReader
+from .liquidity import LiquidityReader
+from .optionswall import OptionsWallReader
+from .stretch import StretchReader
+from .tree_core import VECTOR_BASE, RECOVERY, MAX_MAGNET_ATR, AGGRESSIVE_ATR, AGGRESSIVE_BARS, EXTREME_LOOKBACK, BUY_SIDE, SELL_SIDE, EXTREME_PCT, MAX_DECISION_DRIFT_ATR, LEVEL_ZONE_ATR, STOP_CUSHION_ATR, TREE_STYLE, SV_BODY_MAX, SV_WICK_MIN, SV_VOLUME_MULT, LevelsUnavailable, FINAL_STAGE, STAGES, _news_stop, Walk, _atr, _stopping_volume, _levels_ahead, _stamp_decision, _levels_unavailable_reason, TREND_LADDER, HI_FRAMES, LO_FRAMES, _side, _trend_from_ladder, _ladder_text, trap_direction
+
+class TreeReader:
+
+    def __init__(self, source):
+        self.source = source
+        self.basis = BasisOperation(source)
+        self.levelmap = LevelmapOperation(source)
+        self.brinks = BrinksReader(source)
+        self.checklists = ChecklistReader(source)
+        self.wm = WmReader(source)
+        self.liquidity = LiquidityReader(source)
+        self.optionswall = OptionsWallReader(source)
+        self.stretch = StretchReader(self.basis)
+
+    def _variant_levels(self, symbol: str, variant: str, missing: list | None=None) -> list | None:
+        """The level list a variant sees. This is the whole difference between them.
+
+    house  -- his toolkit: levelmap as-is, floor pivots EXCLUDED (his 2026-08-11
+              decision: "לא בערכת הכלים שלי").
+    strict -- the tree exactly as written: layer 4 demands PIVOTS (7) and
+              M LEVELS (6), so daily_pivots' 13 objects are added.
+
+    Sagiv, 2026-08-26: run both IN PARALLEL and measure which is more accurate,
+    rather than letting the authority order settle it untested. Neither variant
+    is "right" yet -- the tree_trade log, split by variant, is what will say.
+    """
+        basis = self.basis
+        levelmap = self.levelmap
+        try:
+            lv, _ = levelmap.build(symbol, missing)
+            out = [(l.name, float(l.price)) for l in lv]
+        except Exception:
+            return None
+        if variant == 'strict':
+            try:
+                d1, _ = basis.fetch_corrected(symbol, '1d', 30)
+                for name, px in tr.daily_pivots(d1).items():
+                    out.append((name, float(px)))
+            except Exception:
+                return None
+        return out
+
+    def _trend_ladder(self, symbol: str, d4h, r4) -> dict:
+        """read_tr on every frame in the stack. A frame that fails is absent."""
+        basis = self.basis
+        out = {'4h': r4}
+        for tf in TREND_LADDER[1:]:
+            try:
+                df, corr = basis.fetch_corrected(symbol, tf, 30)
+                if corr is not None and getattr(corr, 'unverified', False):
+                    continue
+                out[tf] = matrix.read_tr(df)
+            except Exception:
+                continue
+        return out
+
+    def walk(self, symbol: str, variant: str='house') -> Walk:
+        """Run the tree. `variant` picks the level universe -- see _variant_levels."""
+        basis = self.basis
+        brinks = self.brinks
+        checklists = self.checklists
+        wm = self.wm
+        stretch = self.stretch
+        w = Walk(symbol=symbol, reached='DATA', variant=variant)
+        w.assumptions = [f"מסלול={('עץ-מלא' if variant == 'strict' else 'בית')}", f'וקטור={VECTOR_BASE}', f'אישוש={RECOVERY}', f'קצה={int(EXTREME_PCT * 100)}% / {EXTREME_LOOKBACK} נרות', f'רוחב רמה={LEVEL_ZONE_ATR} ATR']
+        try:
+            d15, corr = basis.fetch_corrected(symbol, '15m', 10)
+            d4h, corr4 = basis.fetch_corrected(symbol, '4h', 60)
+        except Exception as e:
+            w.stopped_because = f'אין נתונים ({type(e).__name__})'
+            return w
+        for _frame, _c in (('15m', corr), ('4h', corr4)):
+            if _c is not None and getattr(_c, 'unverified', False):
+                w.stopped_because = f'מקור המחיר של {_frame} לא מאומת — הקריאה והרמות יהיו שגויות'
+                return w
+        if len(d15) < 5 or len(d4h) < 5:
+            w.stopped_because = f'אין מספיק נרות ({len(d15)}×15m, {len(d4h)}×4h) — העץ קורא עד שלושה נרות אחורה'
+            return w
+        _stale = [(f, c) for f, c in (('15m', corr), ('4h', corr4)) if c is not None and getattr(c, 'source', '').endswith('_stale')]
+        if _stale:
+            w.stopped_because = 'הטייפ מפגר: ' + ' · '.join((f'{f} — {c.note}' for f, c in _stale))
+            return w
+        atr = _atr(d15) or 1e-09
+        close = float(d15['close'].iloc[-1])
+        w.passed.append('DATA')
+        w.reached = 'CONTEXT'
+        try:
+            r4 = matrix.read_tr(d4h)
+        except Exception as exc:
+            from types import SimpleNamespace as _NS
+            r4 = _NS(direction=0, strength=0, note='לא נקרא')
+            w.missing.append(f'קריאת המגמה 4h לא נקראה ({type(exc).__name__})')
+        ladder = self._trend_ladder(symbol, d4h, r4)
+        hi_dir, lo_dir, dir_src, dir_tf = _trend_from_ladder(ladder)
+        w.facts['מגמה גבוהה'] = _ladder_text(ladder, ('4h', '1h'))
+        w.facts['מגמה קצרה'] = _ladder_text(ladder, ('30m', '15m', '5m'))
+        if dir_src is None:
+            w.missing.append('אין מגמה באף מסגרת — 4h/1h/30m/15m/5m כולן דחוסות')
+        else:
+            w.facts['מסגרת הכיוון'] = f'{dir_src} · נקרא מ-{dir_tf}'
+            if dir_src != 'טווח גבוה (4h+1h)':
+                w.facts['מגמה'] = f'הטווח הגבוה לא הכריע — הכיוון מ{dir_src}'
+        if hi_dir and lo_dir and (hi_dir != lo_dir):
+            w.facts['פער מגמות'] = f'הטווח הגבוה {hi_dir} מול הטווח הקצר {lo_dir} — לא מיושר'
+        r4 = ladder.get(dir_tf, r4) if dir_tf else r4
+        try:
+            optionswall = self.optionswall
+            _ow = optionswall.load(symbol, close)
+            if _ow is not None:
+                w.facts['אופציות'] = _ow.line()
+        except Exception:
+            pass
+        st = stretch.state(symbol)
+        if st is None:
+            regime = 'UNKNOWN'
+            dev = 0.0
+        else:
+            dev = st.max_dev
+            regime = 'DEVIATED' if abs(dev) >= 3.0 else 'CONSOLIDATING'
+        try:
+            struct = matrix.read_structure(d4h)
+        except Exception as exc:
+            from types import SimpleNamespace as _NS
+            struct = _NS(direction=0, note='מבנה לא נקרא')
+            w.missing.append(f'מבנה השוק לא נקרא ({type(exc).__name__})')
+        try:
+            e = tr.emas(d4h)
+            slopes = []
+            for n in (50, 200, 800):
+                col = e[f'ema{n}']
+                a, b = (float(col.iloc[-1]), float(col.iloc[-6]))
+                if a != a or b != b:
+                    slopes.append('?')
+                else:
+                    slopes.append('↑' if a > b else '↓')
+            slope_txt = '/'.join(slopes)
+        except Exception:
+            slope_txt = '?'
+        w.facts[f"הקשר {dir_tf or '4h'}"] = f'{r4.note} · {regime} · {struct.note} · שיפוע 4h 50/200/800: {slope_txt}'
+        if struct.direction != 0 and struct.direction != r4.direction:
+            w.facts['מבנה'] = 'המבנה נגד המניפה — סימן היפוך מוקדם'
+        w.passed.append('CONTEXT')
+        w.reached = 'LEVELS'
+        levels = self._variant_levels(symbol, variant, w.missing)
+        if levels is None:
+            w.stopped_because = _levels_unavailable_reason(variant)
+            return w
+        if not levels:
+            w.stopped_because = 'מפת הרמות לא נבנתה'
+            return w
+        if variant == 'strict':
+            w.facts['רמות'] = f'{len(levels)} כולל פיבוטים ו-M (העץ המלא)'
+        w.passed.append('LEVELS')
+        w.reached = 'SESSION'
+        try:
+            import json as _json
+            from datetime import datetime as _dt, timezone as _tz
+            from pathlib import PurePosixPath
+            cal = PurePosixPath('news-desk') / 'data' / 'ff_calendar.json'
+            now_ts = self.source.now_utc().timestamp()
+            reason = _news_stop(_json.loads(self.source.calendar_text(cal.as_posix())), now_ts)
+            if reason is not None:
+                w.stopped_because = reason
+                return w
+        except Exception as exc:
+            w.stopped_because = f'לוח החדשות לא שמיש ({exc}) — לא סוחרים עד שהלוח מתרענן'
+            return w
+        active = sorted(watch_sessions.current_session_at(decision_time=self.source.now_utc()))
+        box = None
+        try:
+            box = brinks.today_box(symbol)
+        except Exception:
+            pass
+        w.facts['סשן'] = '/'.join(active) if active else 'מחוץ לסשן'
+        try:
+            import pandas as _pd
+            mode = 'crypto' if 'BTC' in symbol.upper() else 'forex'
+            d15i = d15.copy()
+            d15i.index = _pd.to_datetime(d15i.index, utc=True)
+            psy = sessions.psy_levels(d15i, mode=mode)
+            if psy.get('available') and psy.get('window_end'):
+                now_utc = _pd.Timestamp(self.source.now_utc())
+                if now_utc < _pd.Timestamp(psy['window_end']):
+                    w.facts['PSY'] = 'בתוך חלון הגיבוש — הרמות זזות, provisional'
+        except Exception:
+            pass
+        if box:
+            w.facts['ברינקס'] = f'{box.lo:,.2f}–{box.hi:,.2f} ⇒ {box.side}'
+        w.passed.append('SESSION')
+        w.reached = 'PATTERN'
+        formation = None
+        formation_read = False
+        try:
+            formation = wm.detect(symbol, '1h') or wm.detect(symbol, '15m')
+            formation_read = True
+        except Exception as exc:
+            w.facts['W/M'] = f'לא נקרא ({type(exc).__name__})'
+        try:
+            fv = self.first_vector_above_50(symbol, '5m')
+            if fv is not None:
+                w.facts['First Vector'] = f"{fv['note']}  [{fv['source']}]"
+        except Exception:
+            pass
+        rvc_pattern = None
+        rvc_read = False
+        try:
+            rg = checklists.rvc_gvc(symbol, '15m')
+            rvc_read = True
+            if rg is not None:
+                w.facts['RVC/GVC'] = rg.line()
+                if formation is None and rg.recovered and rg.wick_ok:
+                    rvc_pattern = rg.name
+        except Exception as exc:
+            w.facts['RVC/GVC'] = f'לא נקרא ({type(exc).__name__})'
+        if formation is not None:
+            w.facts['תבנית'] = f"{formation.kind} {('מאושרת' if formation.confirmed else 'מתגבשת')}"
+        elif rvc_pattern:
+            w.facts['תבנית'] = f'{rvc_pattern} — התבנית היחידה כרגע'
+        elif not formation_read or not rvc_read:
+            w.facts['תבנית'] = 'לא נקראה — אין כאן ממצא שלילי'
+        else:
+            w.facts['תבנית'] = 'אין — דירוג נמוך'
+        w.passed.append('PATTERN')
+        w.reached = 'LOCATION'
+        near = [(n, p) for n, p in levels if abs(p - close) <= LEVEL_ZONE_ATR * atr]
+        if not near:
+            w.missing.append('המחיר לא על רמה מזוהה')
+        names = ' · '.join((n for n, _ in near[:3]))
+        w.facts['רמה'] = names or 'אין רמה קרובה — מיקום בין רמות'
+        exhaustion = any((n.startswith(('ADR', 'AWR', 'RD', 'RW')) for n, _ in near))
+        if exhaustion:
+            w.facts['מצב'] = 'RANGE EXHAUSTION — הטיה מוקדמת להיפוך'
+        w.passed.append('LOCATION')
+        w.reached = 'VECTOR'
+        VECTOR_KINDS = ('green', 'red', 'blue', 'violet')
+        has_vector = False
+        vec_kind = None
+        vector_read = True
+        try:
+            pv = tr.pvsra(d15)
+            if pv is not None and bool(pv['available'].iloc[-1]):
+                k = str(pv['kind'].iloc[-2])
+                if k in VECTOR_KINDS:
+                    has_vector, vec_kind = (True, k)
+        except Exception as exc:
+            w.missing.append(f'הווקטור לא נקרא ({type(exc).__name__})')
+            vector_read = False
+        sv = _stopping_volume(d15)
+        if vector_read and (not has_vector) and (not sv):
+            w.missing.append('אין וקטור ואין Stopping Volume באזור')
+        ctx = []
+        ema_context_read = False
+        try:
+            e15 = tr.emas(d15)
+            for n_ in (50, 200, 800):
+                if abs(close - float(e15[f'ema{n_}'].iloc[-1])) <= 1.0 * atr:
+                    ctx.append('ממוצע')
+                    break
+            ema_context_read = True
+        except Exception as exc:
+            w.facts['קרבה לממוצע'] = f'לא נקראה ({type(exc).__name__})'
+        if regime == 'CONSOLIDATING':
+            ctx.append('לא מתוח')
+        if formation is not None:
+            ctx.append('תבנית')
+        elif rvc_pattern:
+            ctx.append(f'תבנית ({rvc_pattern})')
+        if not ctx:
+            if not ema_context_read or not formation_read or (not rvc_read):
+                w.missing.append('הקשר הווקטור לא נקרא במלואו — לא ממירים unknown לאין-הקשר')
+            else:
+                w.missing.append('וקטור ללא הקשר — לא ליד ממוצע, לא בטווח, לא בתבנית')
+        where = f" · הקשר: {'/'.join(ctx)}" if ctx else ' · ללא הקשר'
+        if has_vector:
+            w.facts['וקטור'] = f'וקטור {vec_kind}{where}'
+        elif sv:
+            w.facts['וקטור'] = f'Stopping Volume — נר ההיפוך היחיד בשיטה{where}'
+        elif not vector_read:
+            w.facts['וקטור'] = 'לא נקרא — אין כאן ממצא שלילי'
+        else:
+            w.facts['וקטור'] = 'אין — העסקה נבנית משאר הפרמטרים'
+        w.passed.append('VECTOR')
+        w.reached = 'MTF'
+        nested = 0
+        one_hour_read = False
+        try:
+            d1h, corr1 = basis.fetch_corrected(symbol, '1h', 30)
+            if corr1 is not None and getattr(corr1, 'unverified', False):
+                raise ValueError('1h unverified')
+            pv1 = tr.pvsra(d1h)
+            if pv1 is not None and bool(pv1['available'].iloc[-1]):
+                nested = int(pv1['kind'].iloc[-7:-1].isin(VECTOR_KINDS).sum())
+                one_hour_read = True
+        except Exception:
+            pass
+        if not one_hour_read:
+            w.facts['צפיפות וקטורים (6×1h)'] = 'לא נקרא — אין נתוני 1h, לא קריאת שוק'
+        else:
+            w.facts['צפיפות וקטורים (6×1h)'] = f'{nested} נרות וקטור בשש השעות האחרונות' if nested else 'אין — שש שעות בלי נר וקטור'
+        w.passed.append('MTF')
+        w.reached = 'TRAP'
+        try:
+            br = checklists.brinks_read(symbol)
+            if br.formed:
+                w.facts['ברינקס'] = br.render().replace('\n', ' · ')
+                if br.swept_asia:
+                    w.facts['מלכודת ברינקס'] = 'הקופסה סחפה את קצה אסיה — היערך לצד הנגדי  [C8 pt4]'
+        except Exception:
+            pass
+        seg = d15.iloc[-(EXTREME_LOOKBACK + 1):-1]
+        hi_thresh = float(seg['high'].quantile(EXTREME_PCT))
+        lo_thresh = float(seg['low'].quantile(1 - EXTREME_PCT))
+        evidence_close = float(d15['close'].iloc[-2])
+        trend_dir = None if r4.direction == 0 else 'לונג' if r4.direction > 0 else 'שורט'
+        at_high = evidence_close >= hi_thresh
+        at_low = evidence_close <= lo_thresh
+        strength = 'שיא' if vec_kind in ('green', 'red') else 'מעל ממוצע'
+        w.direction, verdict = trap_direction(at_high, at_low, vec_kind, sv, trend_dir)
+        what = f'וקטור {vec_kind}' if vec_kind else 'Stopping Volume' if sv else 'המחיר'
+        if verdict == 'trap':
+            edge = 'העליון' if at_high else 'התחתון'
+            caught = 'לונגים' if at_high else 'שורטים'
+            w.facts['מלכודת'] = f'{what} ({strength}) בקצה {edge} — {caught} במלכודת, היערך ל{w.direction}'
+        elif verdict == 'committed':
+            edge = 'העליון' if at_high else 'התחתון'
+            act = 'קונה' if vec_kind in BUY_SIDE else 'מוכר'
+            w.facts['מלכודת'] = f'{what} בקצה {edge} — לא מלכודת, זה הצד ש{act} ומחויב ⇒ {w.direction}'
+        else:
+            w.facts['מלכודת'] = f'{what} לא בקצה — הכיוון מהמגמה'
+        if not _stamp_decision(w, d15):
+            return w
+        w.passed.append('TRAP')
+        w.reached = 'MEMORY'
+        magnet_txt = 'אין מגנט בטווח'
+        try:
+            _liq = self.liquidity
+            unswept = [p for p in _liq.pools(symbol) if not p.swept]
+            if unswept:
+                near = min(unswept, key=lambda p: abs(p.price - close))
+                dist = abs(near.price - close) / atr
+                if dist <= MAX_MAGNET_ATR:
+                    magnet_txt = f'{near.line()} · {dist:.1f} ATR מכאן'
+                else:
+                    magnet_txt = f'המגנט הקרוב {dist:.1f} ATR מכאן — מעבר לסף {MAX_MAGNET_ATR} , לא יעד'
+            r = _liq.run(symbol)
+            if r.detected:
+                w.facts['ריצת נזילות'] = r.line()
+        except Exception as exc:
+            magnet_txt = f'לא נקרא ({type(exc).__name__}) — אין ממצא שלילי'
+        w.facts['מגנט נזילות (EQH/EQL)'] = magnet_txt
+        try:
+            zones = tr.vector_zones(d15)
+            open_z = zones[zones['open']] if len(zones) else zones
+            if not len(open_z):
+                w.missing.append('אין אזורי וקטור פתוחים')
+                w.facts['זיכרון וקטור'] = 'אין אזור פתוח'
+            else:
+                mid = (open_z['top'] + open_z['bottom']) / 2.0
+                w.zones = [(float(m), str(k), int(tc)) for m, k, tc in zip(mid, open_z['kind'], open_z['touches'])]
+                d = (mid - close).abs()
+                i = d.idxmin()
+                z = open_z.loc[i]
+                side = 'מעל' if float(mid.loc[i]) > close else 'מתחת'
+                untested = 'לא נבחן' if int(z['touches']) == 0 else f"נבחן {int(z['touches'])}×"
+                above = int((mid > close).sum())
+                w.facts['זיכרון וקטור'] = f"{len(open_z)} אזורים פתוחים ({above} מעל · {len(open_z) - above} מתחת) · הקרוב {z['kind']} {float(z['bottom']):,.2f}-{float(z['top']):,.2f} {side}, {float(d.loc[i]) / atr:.1f} ATR, {untested}"
+        except Exception as exc:
+            w.facts['זיכרון וקטור'] = f'לא נקרא ({type(exc).__name__})'
+        w.passed.append('MEMORY')
+        if w.direction is None:
+            w.stopped_because = 'אין כיוון מאף מסגרת — אין צד למדוד טריגר או יעד מולו'
+            return w
+        w.reached = 'TRIGGER'
+        prev = float(d15['close'].iloc[-3])
+        last = float(d15['close'].iloc[-2])
+        moved = (last - prev if w.direction == 'לונג' else prev - last) / atr
+        w.facts.setdefault('commitment', f'הנר האחרון זז {moved:+.2f} ATR עם הכיוון')
+        if moved < 0.15:
+            why = 'הנר האחרון לא זז' if abs(moved) < 0.15 else f'הנר האחרון זז נגד הכיוון ({moved:+.2f} ATR)'
+            w.facts['commitment'] = f'אין ({why}) — סף 0.15 ATR, היוריסטיקה'
+        w.passed.append('TRIGGER')
+        w.reached = 'TARGET'
+        short = w.direction == 'שורט'
+        ahead = _levels_ahead(levels, close, short, atr)
+        if not ahead:
+            w.stopped_because = 'אין רמה בכיוון העסקה לשמש יעד'
+            return w
+        w.facts['רמות לפנים'] = ' · '.join((f'{n} {p:,.2f}' for n, p in ahead[:3]))
+        w.passed.append('TARGET')
+        return w
+
+    def first_vector_above_50(self, symbol: str, timeframe: str='5m'):
+        """The First Vector setup: the initial break of structure with a vector.
+
+    Source, fully specified for once:
+      "Initial break of THE STRUCTURE with a green vector"   [09 @ 02m11s]
+      fallback with no retrace -- a FULL CLOSE above the 50   [09 @ 07m31s]
+      requires a clean break of the CLOUD, not the line       [13 @ 21m01s]
+      read on 5m specifically -- the 1m manufactures shakeouts [13 @ 00m40s]
+
+    That last citation is why the default frame here is 5m and not the tree's
+    usual 15m: the source names the frame for THIS setup explicitly, and a
+    named frame outranks the layer-0 default.
+
+    "Clean break of the cloud" is the load-bearing clause. The 50 EMA in this
+    method is a BAND (`tr.ema_cloud`), not a line, so a close that pokes into
+    the cloud has not broken anything -- the bar must close beyond the far
+    edge. Reading it as a line would fire this setup on every touch.
+
+    Returns a dict or None. Reports; never trades on its own.
+    """
+        basis = self.basis
+        try:
+            df, corr = basis.fetch_corrected(symbol, timeframe, 5)
+            if corr and getattr(corr, 'unverified', False) or len(df) < 60:
+                return None
+            pv = tr.pvsra(df)
+            cloud = tr.ema_cloud(df)
+        except Exception:
+            return None
+        hi = cloud['upper'] if 'upper' in cloud else cloud.iloc[:, 0]
+        lo = cloud['lower'] if 'lower' in cloud else cloud.iloc[:, -1]
+        close = df['close']
+        n = len(df)
+        i = n - 2
+        kind = str(pv['kind'].iloc[i])
+        up = kind in ('green', 'blue')
+        dn = kind in ('red', 'violet')
+        if not (up or dn):
+            return None
+        c, edge_hi, edge_lo = (float(close.iloc[i]), float(hi.iloc[i]), float(lo.iloc[i]))
+        if up and c <= edge_hi:
+            return None
+        if dn and c >= edge_lo:
+            return None
+        look = df.iloc[max(0, i - 6):i]
+        prev_in_or_below = (look['close'] <= hi.iloc[max(0, i - 6):i]).all() if up else (look['close'] >= lo.iloc[max(0, i - 6):i]).all()
+        if not prev_in_or_below:
+            return None
+        return {'setup': 'First Vector above 50', 'direction': 'לונג' if up else 'שורט', 'timeframe': timeframe, 'vector': kind, 'close': c, 'cloud_edge': edge_hi if up else edge_lo, 'source': '09 @ 02m11s · 13 @ 21m01s · 13 @ 00m40s', 'note': f"וקטור {kind} שסוגר מלא {('מעל' if up else 'מתחת')} לענן ה-50 ב-{timeframe} — השבירה הראשונה"}
+
+    def levels_to_trade(self, symbol: str, close: float, direction: str, atr: float, variant: str='house'):
+        """(stop, targets) from the level map — HIS documented rule, one copy of it.
+
+    `00-method.md`: "יעדים — יעד פסיכולוגי / רמה נקובה מהמפה, לעולם לא מספר
+    עגול שרירותי". `08-tree-coverage.md`: "סטופ מאחורי הרמה שמאחור, יעדים =
+    הרמות שלפנים". The R gate itself is tradeplan.MIN_RR (1.2 since
+    2026-08-27), not the 1.5 that doc still names.
+    `05-risk-and-execution.md`: "targets are levels
+    that are actually in the way, not round-number wishes".
+
+    trade_from_walk has computed exactly this since the tree started building
+    trades. Extracted here because nine detectors fire without any numbers at
+    all -- 287 banked firings that no resolver can ever score -- and the answer
+    for them was never six new trading decisions. It is this rule, which is
+    already his, applied consistently.
+
+    Returns None when the map has no level ahead or none behind: a setup with
+    no obstacle in front has no target that pays, and the method says decline
+    rather than invent one.
+    """
+        short = direction in ('שורט', 'short', 'sell')
+        L = self._variant_levels(symbol, variant)
+        if L is None:
+            raise LevelsUnavailable('level universe could not be read')
+        ahead = _levels_ahead(L, close, short, atr)
+        behind = sorted([(n, p) for n, p in L if (p > close if short else p < close)], key=lambda r: abs(r[1] - close))[:1]
+        if not ahead or not behind:
+            return None
+        stop = behind[0][1] + (STOP_CUSHION_ATR * atr if short else -STOP_CUSHION_ATR * atr)
+        from .pricing import apply_stop_band, resolve_ladder
+        stop = apply_stop_band(symbol, close, stop, atr, [], style=TREE_STYLE)
+        if stop <= behind[0][1] if short else stop >= behind[0][1]:
+            return None
+        risk = abs(close - stop)
+        if risk <= 0:
+            return None
+        targets, _obstacles, refusal = resolve_ladder(ahead, symbol, close, stop, short, atr)
+        if refusal is not None:
+            return None
+        return (stop, targets)
+
+    def trade_from_walk(self, w: Walk):
+        """Build the actual trade a completed walk implies, or None.
+
+    This is what makes the tree a TRADING system rather than a commentary: a
+    walk that clears every gate turns into entry/stop/targets using the same
+    objects the walk already gathered. The final audit (2026-08-25) found the
+    tree annotated plans but nothing in the live pipeline ever BUILT a trade
+    from it -- the whole point, per Sagiv: "המערכת בונה עסקאות על בסיס עץ
+    ההחלטות".
+
+    Geometry follows STAGE 11-13: stop behind the nearest level BEHIND the
+    trade (+0.35 ATR buffer, his gold >=5pt floor via tradeplan's rules),
+    targets = the next named levels ahead, R:R gate MIN_RR (1.2 -- the 1.5
+    once written here described a gate the runtime never had) -- below it the walk
+    stays a walk.
+    """
+        basis = self.basis
+        from .pricing import MIN_RR, Plan
+        if not w.complete or not w.direction:
+            return None
+        try:
+            d15, _ = basis.fetch_corrected(w.symbol, '15m', 10)
+        except Exception:
+            w.facts['בניית עסקה'] = 'טייפ 15m לא נקרא מחדש — אין מסקנת R:R'
+            return None
+        close = float(d15['close'].iloc[-1])
+        atr = _atr(d15) or 1e-09
+        if w.decided_close is not None:
+            drift = abs(close - w.decided_close) / atr
+            if drift > MAX_DECISION_DRIFT_ATR:
+                w.facts['נדחה'] = f'המחיר זז {drift:.2f} ATR מאז שהעץ החליט ({w.decided_close:,.2f} → {close:,.2f})'
+                return None
+        short = w.direction == 'שורט'
+        L = self._variant_levels(w.symbol, w.variant)
+        if L is None:
+            w.facts['בניית עסקה'] = 'מפת הרמות לא נקראה מחדש — אין מסקנת R:R'
+            return None
+        for _mid, _kind, _tc in getattr(w, 'zones', []) or []:
+            if abs(_mid - close) <= MAX_MAGNET_ATR * atr:
+                _tag = 'לא נבחן' if _tc == 0 else f'{_tc}×'
+                L = list(L) + [(f'VZ50-{_kind} ({_tag})', float(_mid))]
+        ahead = _levels_ahead(L, close, short, atr)
+        behind = sorted([(n, p) for n, p in L if (p > close if short else p < close)], key=lambda r: abs(r[1] - close))[:1]
+        if not ahead or not behind:
+            w.facts['נדחה'] = 'אין רמה ' + ('לפנים' if not ahead else 'מאחור') + ' לבנות מולה — אין גיאומטריה'
+            return None
+        stop = behind[0][1] + (STOP_CUSHION_ATR * atr if short else -STOP_CUSHION_ATR * atr)
+        _warn: list = []
+        from .pricing import apply_stop_band, resolve_ladder
+        _style = TREE_STYLE
+        stop = apply_stop_band(w.symbol, close, stop, atr, _warn, style=_style)
+        targets, obstacles, refusal = resolve_ladder(ahead, w.symbol, close, stop, short, atr)
+        p = Plan(symbol=w.symbol, close=close, kind='trend', direction=w.direction, entry=close, stop=stop, targets=targets, atr=atr, style=_style, obstacles=obstacles, refusal=refusal)
+        p.warnings.extend(_warn)
+        p.not_drawn = list(w.missing)
+        p.reasons = [f"עץ ההחלטות ({('עץ-מלא' if w.variant == 'strict' else 'בית')}): כל {len(w.passed)} השלבים עברו", f"מסלול העץ: {' → '.join(w.passed)}", *(f'{k}: {v}' for k, v in w.facts.items()), *([f'נקודת החלטת העץ: {w.decided_close:,.2f} · {w.decided_bar}'] if w.decided_close is not None else []), f"הנחות העץ: {' · '.join(w.assumptions)}", f'ביטול: {behind[0][0]}']
+        if 'מלכודת' in w.facts and 'היערך' in str(w.facts.get('מלכודת', '')):
+            p.kind = 'reversal'
+            p.warnings.append('עסקת מלכודת — נגד הצד שנתפס. משפחת היפוך, לא נמדדה.')
+        anchor_px = behind[0][1]
+        stop_ok = p.stop > anchor_px if short else p.stop < anchor_px
+        if not stop_ok:
+            w.facts['נדחה'] = f'הרצועה הידקה את הסטופ ל-{p.stop:,.2f}, לפני נקודת הביטול {behind[0][0]} {anchor_px:,.2f} — העסקה לא נכנסת לרצועת הסיכון'
+            w.refused = p
+            return None
+        if not p.tradeable:
+            _tp1 = f' · TP1 {p.targets[0][0]} {p.targets[0][1]:,.2f}' if p.targets else ''
+            w.facts['נדחה'] = (p.refusal or f'R:R {p.rr:.2f} מתחת לסף {MIN_RR}') + f' — כניסה {p.entry:,.2f} · סטופ {p.stop:,.2f}{_tp1}'
+            w.refused = p
+            return None
+        return p

warning: in the working copy of 'tests/tree_replay/test_tree_walk.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_tree_walk.py b/tests/tree_replay/test_tree_walk.py
new file mode 100644
index 0000000..3eab594
--- /dev/null
+++ b/tests/tree_replay/test_tree_walk.py
@@ -0,0 +1,509 @@
+"""Actual original tree decisions from raw synthetic tapes, not final read mocks."""
+
+import importlib
+import importlib.util
+import json
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay._vendor.correction import Correction
+
+SYMBOL = 'OANDA:XAUUSD'
+NOW = pd.Timestamp('2026-09-09T14:00Z')
+STAGES = ['DATA', 'CONTEXT', 'LEVELS', 'SESSION', 'PATTERN', 'LOCATION',
+          'VECTOR', 'MTF', 'TRAP', 'MEMORY', 'TRIGGER', 'TARGET']
+
+
+def api(part='tree_walk'):
+    name = 'trading_system.tree_replay._vendor.' + part
+    assert importlib.util.find_spec(name) is not None, 'Missing complete tree reader: ' + part
+    return importlib.import_module(name)
+
+
+def correction(source='tv_daily', confidence='exact'):
+    return Correction(SYMBOL, 0, source, confidence, 'synthetic')
+
+
+def frame(count=1001, freq='15min', rising=True, close=128., width=2.):
+    prices = [100 + i / 100 for i in range(count)] if rising else [close] * count
+    return pd.DataFrame({'open': [p - .005 for p in prices], 'close': prices,
+                         'high': [p + width / 2 for p in prices], 'low': [p - width / 2 for p in prices],
+                         'volume': [100.] * count},
+                        index=pd.date_range(end=NOW, periods=count, freq=freq))
+
+
+class RawSource:
+    def __init__(self, frames=None):
+        self.frames = {} if frames is None else frames
+        self.calls = []
+        self.now = NOW
+        self.calendar = json.dumps([{'dateline': NOW.timestamp() + 86400, 'impact': 'Low', 'title': 'future'}])
+
+    def fetch_corrected(self, symbol, timeframe, lookback):
+        self.calls.append(('fetch', symbol, timeframe, lookback))
+        value = self.frames.get((timeframe, lookback), LookupError('raw tape unavailable'))
+        if isinstance(value, list):
+            value = value.pop(0)
+        if isinstance(value, Exception):
+            raise value
+        df, c = value
+        return df.copy(deep=True), c
+
+    def now_utc(self):
+        self.calls.append(('clock',))
+        return self.now
+
+    def calendar_text(self, path):
+        self.calls.append(('calendar', path))
+        assert path == 'news-desk/data/ff_calendar.json'
+        if isinstance(self.calendar, Exception):
+            raise self.calendar
+        return self.calendar
+
+    def list_reports(self):
+        self.calls.append(('options-list',))
+        return []
+
+    def read_report(self, path):
+        raise FileNotFoundError(path)
+
+    def read_tv_csv(self, filename):
+        raise FileNotFoundError(filename)
+
+
+def full_source():
+    c = correction()
+    frames = {('15m', 10): (frame(), c), ('4h', 60): (frame(freq='4h'), c)}
+    for tf in ('1h', '30m', '15m', '5m'):
+        frames[(tf, 30)] = (frame(freq={'1h': '1h', '30m': '30min', '15m': '15min', '5m': '5min'}[tf]), c)
+    daily = frame(220, '1D', False, close=100, width=20)
+    daily.index = pd.date_range(end='2026-09-09T00:00Z', periods=220, freq='1D')
+    daily['open'] = 100.
+    daily.iloc[-1, daily.columns.get_loc('high')] = 115.
+    daily.iloc[-1, daily.columns.get_loc('low')] = 95.
+    daily.iloc[-1, daily.columns.get_loc('close')] = 110.
+    frames[('1d', 400)] = (daily, c)
+    frames[('1d', 30)] = (daily, c)
+    opening = frame(2, rising=False)
+    opening.index = pd.to_datetime(['2026-09-09T07:00Z', '2026-09-09T13:30Z'])
+    opening['open'] = [103., 107.]
+    frames[('5m', 3)] = (opening, c)
+    frames[('1h', 240)] = (frame(1600, '1h', False, close=100), c)
+    frames[('4h', 240)] = (frame(400, '4h', False, close=100), c)
+    return RawSource(frames)
+
+
+def test_data_fetch_failure_is_structured_stop_without_downstream_reads():
+    source = RawSource()
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.reached == 'DATA' and not w.complete
+    assert w.stopped_because == 'אין נתונים (LookupError)'
+    assert w.passed == []
+    assert source.calls == [('fetch', SYMBOL, '15m', 10)]
+
+
+@pytest.mark.parametrize('key', [('15m', 10), ('4h', 60)])
+@pytest.mark.parametrize('fault', ['unverified', 'stale', 'short'])
+def test_both_initial_frames_are_gated(key, fault):
+    source = full_source()
+    df, c = source.frames[key]
+    if fault == 'unverified':
+        c = correction('none', 'unknown')
+    elif fault == 'stale':
+        c = correction('tv_stale')
+    else:
+        df = df.iloc[-4:]
+    source.frames[key] = (df, c)
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert not w.complete and w.reached == 'DATA' and w.stopped_because
+    assert source.calls == [('fetch', SYMBOL, '15m', 10), ('fetch', SYMBOL, '4h', 60)]
+
+
+@pytest.mark.parametrize('high,low,kind,sv,trend,want,verdict', [
+    (True, False, 'green', False, None, 'שורט', 'trap'),
+    (True, False, 'blue', False, 'שורט', 'שורט', 'trap'),
+    (False, True, 'red', False, None, 'לונג', 'trap'),
+    (False, True, 'violet', False, 'לונג', 'לונג', 'trap'),
+    (False, True, 'green', False, 'שורט', 'לונג', 'committed'),
+    (True, False, 'red', False, 'לונג', 'שורט', 'committed'),
+    (True, False, None, True, 'לונג', 'שורט', 'trap'),
+    (False, True, None, True, 'שורט', 'לונג', 'trap'),
+    (False, False, 'green', True, 'שורט', 'שורט', 'trend'),
+    (False, False, None, False, None, None, 'trend'),
+])
+def test_trap_follows_vector_side_and_completed_edge(high, low, kind, sv, trend, want, verdict):
+    assert api('tree_core').trap_direction(high, low, kind, sv, trend) == (want, verdict)
+
+
+@pytest.mark.parametrize('row,vol,want', [
+    ((123, 140, 120, 130), 150, True),
+    ((123, 140, 120, 130.001), 150, False),
+    ((124, 139, 120, 130), 150, False),
+    ((123, 140, 120, 130), 149.999, False),
+    ((123, 140, 120, 130), 100, False),
+])
+def test_stopping_volume_requires_body_wick_and_volume(row, vol, want):
+    df = frame(12, rising=False)
+    for name, value in zip(('open', 'high', 'low', 'close'), row):
+        df.iloc[-2, df.columns.get_loc(name)] = value
+    df.iloc[-2, df.columns.get_loc('volume')] = vol
+    df.iloc[-1, df.columns.get_loc('volume')] = 1000000.
+    assert api('tree_core')._stopping_volume(df) is want
+
+
+@pytest.mark.parametrize('variant', ['house', 'strict'])
+def test_real_full_tree_visits_all_stages_and_builds_a_source_plan(variant):
+    source = full_source()
+    reader = api().TreeReader(source)
+    w = reader.walk(SYMBOL, variant)
+    assert w.complete and w.stopped_because is None and w.direction == 'לונג'
+    assert w.passed == STAGES and w.reached == 'TARGET'
+    assert w.decided_close == 110.
+    assert w.decided_bar == str(source.frames[('15m', 10)][0].index[-1])
+    assert w.facts['commitment'].startswith('אין (')
+    assert 'Stopping Volume' not in w.facts['וקטור']
+    assert source.calls.count(('fetch', SYMBOL, '1h', 30)) == 2
+    news = source.calls.index(('calendar', 'news-desk/data/ff_calendar.json'))
+    assert source.calls[news - 1] == ('clock',) and source.calls[news + 1] == ('clock',)
+    if variant == 'strict':
+        assert 'כולל פיבוטים ו-M' in w.facts['רמות']
+    plan = reader.trade_from_walk(w)
+    from trading_system.tree_replay._vendor.pricing import Plan
+    assert isinstance(plan, Plan) and plan.tradeable
+    assert plan.entry == 110. and plan.direction == 'לונג' and plan.style == 'intraday'
+    assert plan.stop == pytest.approx(99.7)
+    assert plan.targets[0][1] == 125.
+    assert plan.not_drawn == w.missing and plan.not_drawn is not w.missing
+    assert w.refused is None
+
+
+@pytest.mark.parametrize('calendar', [[], '{', OSError('missing'),
+    [{'dateline': NOW.timestamp() - 86400, 'impact': 'Low'}]])
+def test_unusable_calendar_stops_at_session(calendar):
+    source = full_source()
+    source.calendar = json.dumps(calendar) if isinstance(calendar, list) else calendar
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert not w.complete and w.reached == 'SESSION'
+    assert w.passed == ['DATA', 'CONTEXT', 'LEVELS']
+    assert w.stopped_because.startswith('לוח החדשות לא שמיש')
+    assert ('fetch', SYMBOL, '5m', 5) not in source.calls
+
+
+@pytest.mark.parametrize('offset,want_stop', [(-901, False), (-900, True), (900, True), (901, False)])
+def test_calendar_blackout_inclusive_fifteen_minutes(offset, want_stop):
+    events = [{'dateline': NOW.timestamp() + offset, 'impact': 'High', 'title': 'event'},
+              {'dateline': NOW.timestamp() + 86400, 'impact': 'Low'}]
+    result = api('tree_core')._news_stop(events, NOW.timestamp())
+    assert (result is not None) is want_stop
+    if want_stop:
+        assert result.startswith('חלון חדשות: event')
+
+
+def test_calendar_missing_impact_inside_window_is_error():
+    with pytest.raises(ValueError, match='has no impact'):
+        api('tree_core')._news_stop([{'dateline': NOW.timestamp() + 10}], NOW.timestamp())
+
+
+@pytest.mark.parametrize('short', [False, True])
+def test_first_vector_reads_completed_break_not_forming_noise(short):
+    df = frame(120, '5min', False)
+    df['open'] = 128.
+    df['high'] = 129.
+    df['low'] = 127.
+    df.iloc[-2, df.columns.get_loc('close')] = 116. if short else 140.
+    df.iloc[-2, df.columns.get_loc('high')] = 129. if short else 141.
+    df.iloc[-2, df.columns.get_loc('low')] = 115. if short else 127.
+    df.iloc[-2, df.columns.get_loc('volume')] = 250.
+    source = RawSource({('5m', 5): (df, correction())})
+    result = api().TreeReader(source).first_vector_above_50(SYMBOL)
+    assert result['direction'] == ('שורט' if short else 'לונג')
+    assert result['vector'] == ('red' if short else 'green')
+    assert result['close'] == (116. if short else 140.)
+    df.iloc[-1, df.columns.get_loc('close')] = 10000.
+    assert api().TreeReader(source).first_vector_above_50(SYMBOL) == result
+
+
+def test_strict_pivots_do_not_replace_failed_base_map():
+    source = full_source()
+    del source.frames[('1d', 400)]
+    reader = api().TreeReader(source)
+    # Source map returns empty on daily fetch failure; strict still adds pivots.
+    # A thrown malformed daily frame invalidates the whole universe instead.
+    source.frames[('1d', 400)] = (frame(0), correction())
+    assert reader._variant_levels(SYMBOL, 'strict') is None
+    assert ('fetch', SYMBOL, '1d', 30) not in source.calls
+
+
+def test_builder_stops_on_drift_before_map_rebuild():
+    source = full_source()
+    core = api('tree_core')
+    w = core.Walk(SYMBOL, 'TARGET', direction='לונג', passed=list(STAGES), decided_close=100.)
+    assert api().TreeReader(source).trade_from_walk(w) is None
+    assert w.facts['נדחה'].startswith('המחיר זז')
+    assert source.calls == [('fetch', SYMBOL, '15m', 10)]
+
+
+def test_builder_keeps_refused_plan_when_band_crosses_invalidation():
+    source = RawSource({
+        ('15m', 10): (frame(100, rising=False, close=110, width=10), correction()),
+        ('1d', 400): (frame(220, '1D', False, close=1000, width=20), correction()),
+    })
+    core = api('tree_core')
+    w = core.Walk(SYMBOL, 'TARGET', direction='לונג', passed=list(STAGES), zones=[(80., 'green', 0)])
+    assert api().TreeReader(source).trade_from_walk(w) is None
+    assert w.refused is not None and w.refused.entry == 110.
+    assert w.refused.stop > 80.
+    assert 'לפני נקודת הביטול' in w.facts['נדחה']
+
+
+def falling(df):
+    out = df.copy()
+    out['open'], out['close'] = 220 - df['open'], 220 - df['close']
+    out['high'], out['low'] = 220 - df['low'], 220 - df['high']
+    return out
+
+
+@pytest.mark.parametrize('conflicting_high_pair,want,tf', [(False, 'שורט', '4h'), (True, 'לונג', '30m')])
+def test_real_ladder_uses_combined_ranges_and_selected_read(conflicting_high_pair, want, tf):
+    source = full_source()
+    for key in [('4h', 60)] + ([] if conflicting_high_pair else [('1h', 30)]):
+        df, c = source.frames[key]
+        source.frames[key] = (falling(df), c)
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.complete and w.direction == want
+    assert w.facts['מסגרת הכיוון'].endswith('נקרא מ-' + tf)
+    assert 'הקשר ' + tf in w.facts
+    assert ('פער מגמות' in w.facts) is (not conflicting_high_pair)
+
+
+def test_all_neutral_reads_stop_after_memory_without_directional_geometry():
+    source = full_source()
+    for key in [('4h', 60), ('1h', 30), ('30m', 30), ('15m', 30), ('5m', 30)]:
+        source.frames[key] = (frame(rising=False), correction())
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert not w.complete and w.direction is None and w.reached == 'MEMORY'
+    assert w.passed == STAGES[:10]
+    assert 'אין כיוון' in w.stopped_because
+    assert 'commitment' not in w.facts and 'רמות לפנים' not in w.facts
+
+
+def test_missing_stretch_is_unknown_not_a_positive_regime():
+    source = full_source()
+    # Stretch's first daily read fails; the later map read still succeeds.
+    daily = source.frames[('1d', 400)]
+    source.frames[('1d', 400)] = [LookupError('stretch daily unavailable'), daily]
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.complete and 'UNKNOWN' in w.facts['הקשר 4h']
+    assert 'לא מתוח' not in w.facts['וקטור']
+    assert source.calls.count(('fetch', SYMBOL, '1d', 400)) == 2
+
+
+def test_none_initial_corrections_are_not_an_invented_veto():
+    source = full_source()
+    for key in [('15m', 10), ('4h', 60)]:
+        source.frames[key] = (source.frames[key][0], None)
+    assert api().TreeReader(source).walk(SYMBOL).complete
+
+
+def test_news_gate_uses_clock_before_calendar_read_not_after():
+    class AdvancingCalendar(RawSource):
+        def calendar_text(self, path):
+            result = super().calendar_text(path)
+            self.now = NOW + pd.Timedelta(seconds=2)
+            return result
+    source = AdvancingCalendar(full_source().frames)
+    source.calendar = json.dumps([{'dateline': NOW.timestamp() + 901, 'impact': 'High'},
+                                  {'dateline': NOW.timestamp() + 86400, 'impact': 'Low'}])
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.complete  # 901 seconds at the captured clock; 899 only after IO.
+    at = source.calls.index(('calendar', 'news-desk/data/ff_calendar.json'))
+    assert source.calls[at - 1] == ('clock',) and source.calls[at + 1] == ('clock',)
+
+
+def test_actual_hourly_w_pattern_is_consumed_without_secondary_scan():
+    anchors = {0: 100., 5: 103., 10: 90., 17: 110., 25: 91., 35: 115., 39: 115.}
+    closes = pd.Series(anchors).reindex(range(40)).interpolate()
+    df = frame(40, '1h', False)
+    df['close'], df['open'] = closes.to_numpy(), closes.to_numpy()
+    df['high'], df['low'] = closes.to_numpy() + 1, closes.to_numpy() - 1
+    source = full_source()
+    source.frames[('1h', 10)] = (df, correction())
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.complete and w.facts['תבנית'] == 'W מאושרת'
+    # DATA, pools and run: three reads. The slow run stops before its own
+    # pool reread; a redundant WM fallback would introduce a fourth read.
+    assert source.calls.count(('fetch', SYMBOL, '15m', 10)) == 3
+
+
+@pytest.mark.parametrize('fault', ['short', 'missing_volume', 'zero_volume'])
+def test_stopping_volume_missing_or_short_tape_is_not_confirmation(fault):
+    df = frame(11 if fault == 'short' else 12, rising=False)
+    if fault == 'missing_volume':
+        df = df.drop(columns='volume')
+    elif fault == 'zero_volume':
+        df['volume'] = 0.
+    assert api('tree_core')._stopping_volume(df) is False
+
+
+@pytest.mark.parametrize('fault', ['short', 'no_cloud_history', 'ordinary', 'unverified', 'prior_break', 'missing_volume'])
+def test_first_vector_absence_is_not_fabricated(fault):
+    df = frame(59 if fault == 'short' else 60 if fault == 'no_cloud_history' else 120, '5min', False)
+    df['open'] = 128.
+    if fault != 'ordinary':
+        df.iloc[-2, df.columns.get_loc('close')] = 140.
+        df.iloc[-2, df.columns.get_loc('high')] = 141.
+        df.iloc[-2, df.columns.get_loc('volume')] = 250.
+    if fault == 'prior_break':
+        df.iloc[-3, df.columns.get_loc('close')] = 150.
+        df.iloc[-3, df.columns.get_loc('high')] = 151.
+    if fault == 'missing_volume':
+        df = df.drop(columns='volume')
+    c = correction('none', 'unknown') if fault == 'unverified' else correction()
+    assert api().TreeReader(RawSource({('5m', 5): (df, c)})).first_vector_above_50(SYMBOL) is None
+
+
+@pytest.mark.parametrize('short,stop,first', [(False, 99.7, 125.), (True, 119.5, 95.)])
+def test_both_geometry_consumers_use_original_prices(short, stop, first):
+    source = full_source()
+    core = api('tree_core')
+    side = 'שורט' if short else 'לונג'
+    w = core.Walk(SYMBOL, 'TARGET', direction=side, passed=list(STAGES), decided_close=110.,
+                  missing=['missing observation'], facts={'fixture': 'literal'})
+    reader = api().TreeReader(source)
+    plan = reader.trade_from_walk(w)
+    assert plan is not None and plan.tradeable and plan.stop == pytest.approx(stop)
+    assert plan.targets[0][1] == first and plan.not_drawn == ['missing observation']
+    geometry = reader.levels_to_trade(SYMBOL, 110., side, 2.)
+    assert geometry is not None and geometry[0] == pytest.approx(stop)
+    assert geometry[1][0][1] == first
+
+
+@pytest.mark.parametrize('decided,present', [(109.34, True), (109.33999, False)])
+def test_builder_drift_boundary_is_strict_greater_than(decided, present):
+    source = full_source()
+    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג', decided_close=decided, passed=list(STAGES))
+    result = api().TreeReader(source).trade_from_walk(w)
+    assert (result is not None) is present
+    assert (('fetch', SYMBOL, '1d', 400) in source.calls) is present
+
+
+def test_builder_and_geometry_classify_map_outage_without_economic_verdict():
+    source = full_source()
+    source.frames[('1d', 400)] = (frame(0), correction())
+    core = api('tree_core')
+    w = core.Walk(SYMBOL, 'TARGET', direction='לונג')
+    reader = api().TreeReader(source)
+    assert reader.trade_from_walk(w) is None and w.refused is None
+    assert w.facts['בניית עסקה'] == 'מפת הרמות לא נקראה מחדש — אין מסקנת R:R'
+    with pytest.raises(core.LevelsUnavailable):
+        reader.levels_to_trade(SYMBOL, 110., 'לונג', 2.)
+
+
+def test_trap_reason_changes_plan_family_and_is_retained():
+    source = full_source()
+    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג', passed=list(STAGES),
+                              facts={'מלכודת': 'היערך ללונג'})
+    plan = api().TreeReader(source).trade_from_walk(w)
+    assert plan is not None and plan.kind == 'reversal'
+    assert 'עסקת מלכודת' in plan.warnings[-1]
+    assert any('היערך ללונג' in reason for reason in plan.reasons)
+
+
+def test_strict_appends_all_thirteen_previous_day_pivots_in_source_order():
+    reader = api().TreeReader(full_source())
+    house = reader._variant_levels(SYMBOL, 'house')
+    strict = reader._variant_levels(SYMBOL, 'strict')
+    # Previous H/L/C = 110/90/100; forming day 115/95/110 must not enter pivots.
+    assert strict == house + [('PP', 100.), ('R1', 110.), ('R2', 120.),
+        ('R3', 130.), ('S1', 90.), ('S2', 80.), ('S3', 70.),
+        ('M0', 75.), ('M1', 85.), ('M2', 95.), ('M3', 105.),
+        ('M4', 115.), ('M5', 125.)]
+
+
+def test_strict_pivot_read_failure_invalidates_successful_base_universe():
+    source = full_source()
+    source.frames[('1d', 30)] = OSError('daily pivot read unavailable')
+    w = api().TreeReader(source).walk(SYMBOL, 'strict')
+    assert not w.complete and w.reached == 'LEVELS'
+    assert 'פיבוט' in w.stopped_because
+    assert ('calendar', 'news-desk/data/ff_calendar.json') not in source.calls
+
+
+@pytest.mark.parametrize('inverse,name', [(False, 'RVC'), (True, 'GVC')])
+def test_actual_recovered_vector_pair_enters_pattern_and_context(inverse, name):
+    df = frame(33, rising=False, close=100.)
+    df['open'], df['volume'] = 100., 1.
+    for i, values in [(30, (102., 103., 99., 100., 3.)),
+                      (31, (100., 103., 99., 102., 10.)),
+                      (32, (102., 103., 99., 100., 100.))]:
+        for field, value in zip(('open', 'high', 'low', 'close', 'volume'), values):
+            df.iloc[i, df.columns.get_loc(field)] = value
+    if inverse:
+        df = falling(df)
+    source = full_source()
+    source.frames[('15m', 5)] = (df, correction())
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.complete and w.facts['תבנית'] == name + ' — התבנית היחידה כרגע'
+    assert name in w.facts['RVC/GVC']
+    assert 'תבנית (' + name + ')' in w.facts['וקטור']
+
+
+def test_actual_brinks_box_and_checklist_replace_the_first_box_annotation():
+    source = full_source()
+    source.now = pd.Timestamp('2026-09-09T15:00Z')
+    box = frame(12, '5min', False, close=100.)
+    box.index = pd.date_range('2026-09-09T14:00Z', periods=12, freq='5min')
+    source.frames[('5m', 2)] = (box, correction())
+    w = api().TreeReader(source).walk(SYMBOL)
+    assert w.complete and '99.00' in w.facts['ברינקס'] and '101.00' in w.facts['ברינקס']
+    # Two independent real consumers; second performs vector and Asia reads.
+    assert source.calls.count(('fetch', SYMBOL, '5m', 2)) == 2
+    assert ('fetch', SYMBOL, '5m', 10) in source.calls
+    assert ('fetch', SYMBOL, '15m', 3) in source.calls
+
+
+@pytest.mark.parametrize('mid,included', [(60., True), (59.999, False)])
+def test_vector_anchor_five_atr_boundary_changes_refusal_geometry(mid, included):
+    source = RawSource({
+        ('15m', 10): (frame(100, rising=False, close=110., width=10.), correction()),
+        ('1d', 400): (frame(220, '1D', False, close=1000., width=20.), correction()),
+    })
+    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג',
+                              zones=[(mid, 'green', 0)])
+    assert api().TreeReader(source).trade_from_walk(w) is None
+    if included:
+        assert w.refused is not None and w.refused.stop == pytest.approx(97.5)
+        assert 'VZ50-green' in w.facts['נדחה']
+    else:
+        assert w.refused is None and 'אין רמה מאחור' in w.facts['נדחה']
+
+
+def test_both_geometry_consumers_refuse_a_clamp_in_front_of_actual_map_anchor():
+    source = RawSource({
+        ('15m', 10): (frame(100, rising=False, close=110., width=10.), correction()),
+        ('1d', 400): (frame(220, '1D', False, close=1000., width=20.), correction()),
+        ('1h', 240): (frame(1600, '1h', False, close=80.), correction()),
+    })
+    reader = api().TreeReader(source)
+    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג')
+    assert reader.trade_from_walk(w) is None and w.refused is not None
+    assert w.refused.stop == pytest.approx(97.5)
+    assert 'לפני נקודת הביטול' in w.facts['נדחה']
+    assert reader.levels_to_trade(SYMBOL, 110., 'לונג', 10.) is None
+
+
+@pytest.mark.parametrize('reached,direction', [('MEMORY', 'לונג'), ('TARGET', None)])
+def test_builder_does_not_fetch_for_an_incomplete_or_directionless_walk(reached, direction):
+    source = RawSource()
+    w = api('tree_core').Walk(SYMBOL, reached, direction=direction)
+    assert api().TreeReader(source).trade_from_walk(w) is None
+    assert source.calls == [] and w.refused is None
+
+
+def test_builder_raw_price_reread_failure_is_not_an_economic_refusal():
+    w = api('tree_core').Walk(SYMBOL, 'TARGET', direction='לונג')
+    source = RawSource()
+    assert api().TreeReader(source).trade_from_walk(w) is None
+    assert w.refused is None
+    assert w.facts['בניית עסקה'] == 'טייפ 15m לא נקרא מחדש — אין מסקנת R:R'

warning: in the working copy of 'docs/architecture/TREE-WALK-READER-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/TREE-WALK-READER-USAGE.md b/docs/architecture/TREE-WALK-READER-USAGE.md
new file mode 100644
index 0000000..b69a3cf
--- /dev/null
+++ b/docs/architecture/TREE-WALK-READER-USAGE.md
@@ -0,0 +1,58 @@
+# Original tree walk over raw offline ports
+
+Status: runtime implemented; source audit and independent acceptance pending.
+Authority: TREE-WALK-READER-CONTRACT.md, pinned chartdesk/tree.py. This is a
+private offline composition, not a public causal replay or trained model.
+
+`TreeReader(source).walk(symbol, variant='house')` runs all twelve original
+visited stages. `strict` additionally appends the thirteen previous-day pivots.
+`walk.complete` means TARGET with no stop reason, not that every observation
+was positive. Missing observations and negative findings remain distinct.
+
+The reader constructs actual basis/map/stretch/pattern/liquidity/options readers
+and uses the actual matrix, EMA/cloud, PVSRA, vector-memory and calendar logic.
+No final Walk, map, pattern, matrix or Plan verdict is supplied by the provider.
+
+Required raw ports:
+
+- `fetch_corrected(symbol, timeframe, lookback)` returns a pandas OHLCV frame
+  and the source-compatible correction object (or raises the actual read error).
+- `now_utc()` returns an aware UTC operation time, separately on each call.
+- `calendar_text('news-desk/data/ff_calendar.json')` returns raw calendar JSON.
+- `list_reports()`, `read_report(logical_id)`, `read_tv_csv(filename)` supply
+  the original options-reader raw artifacts. Failures retain original catches.
+
+Repeated keys can return different available snapshots. Do not cache all reads
+under one pass timestamp: news captures time before reading its calendar; session,
+Brinks and provisional PSY have separate clocks. Construction performs no IO.
+The original requested lookback is not permission to trim all delivered history.
+Original forming/completed-row conventions are retained, not normalized away.
+
+`first_vector_above_50(symbol, timeframe='5m')` returns the source setup dict
+or None. It reads the completed candle and the preceding six closes against
+the actual EMA50 cloud; a setup is not an order.
+
+`trade_from_walk(w)` rereads current 15m prices and the map, applies strict
+greater-than .33 ATR decision drift, incorporates vector midpoints within
+5 ATR, and uses original intraday stop bands and named distinct targets.
+It returns the original pricing Plan or None. Some geometry/R:R refusals keep
+the actual rejected Plan in `w.refused`; unavailable inputs are not economic
+loss labels. `levels_to_trade(symbol, close, direction, atr, variant='house')`
+is the separate original geometry consumer: returns `(stop, targets)` or None,
+and raises LevelsUnavailable for an unreadable universe.
+
+Plan.tradeable is internal source pricing acceptance only: outer admission,
+cross-producer arbitration, fills, costs, exits and measured outcomes are still
+separate. No new win rate, outcome-learning dataset or model is produced here.
+
+Runtime verification:
+
+```powershell
+python -B -m pytest tests/tree_replay/test_tree_walk.py tests/tree_replay/test_levelmap_operation.py tests/tree_replay/test_pattern_readers.py tests/tree_replay/test_optionswall.py tests/tree_replay/test_tree_tr.py -q --tb=short -p no:cacheprovider
+```
+
+Fixtures supply raw synthetic tapes and hand-derived expected decisions/prices.
+They are not historical feed/publication certification. Full source projection
+audit, review gates, causal providers and the market-watch caller remain before
+real replay. After acceptance the actual reader must bind Revalidation.tree_walk;
+that existing raw port is not currently a complete tree integration.
