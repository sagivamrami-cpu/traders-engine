# Task1 package

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49. Seven untracked full additions.

warning: in the working copy of 'trading_system/tree_replay/_vendor/wm.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/wm.py b/trading_system/tree_replay/_vendor/wm.py
new file mode 100644
index 0000000..536e655
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/wm.py
@@ -0,0 +1,138 @@
+"""W and M formations, mechanically — the shape half of Tino's entry.
+
+The course's criteria (Tino1 DB §4, [04 @ 05m49s-07m18s] for the W,
+[05 @ 00m09s] for the M): two lows (highs) with the second holding at or above
+(below) the first, a meaningful push between them, and confirmation when the
+neckline — the middle peak (trough) — gives way. The tattoo variant adds a
+vector at the second leg; vector presence is REPORTED here, judged by the agent.
+
+This is a STATE READER, like everything else in the desk (the round-1/2
+research verdicts bind here too): it says "a W is forming / confirmed", it never
+says "buy". The tr-agent applies the five-point checklist on top; the trade
+engine cites the shape as one reason among several. Registered SILENT so the
+firing log accumulates — the promotion question is the setup-scientist's.
+
+Geometry notes that keep this honest:
+- swings are CONFIRMED fractals (k bars both sides, same k as matrix) — the
+  freshest candidate that could still be redefined by the next bar is never
+  used, the same rule `zones._last_swing` enforces;
+- tolerance is in ATR units, not percent, so gold and BTC read the same;
+- "confirmed" needs a CLOSE through the neckline, not a wick."""
+from __future__ import annotations
+from dataclasses import dataclass
+import pandas as pd
+from . import pattern_tr as tr
+SWING_K = 3
+LEG_TOLERANCE_ATR = 0.5
+MIN_HEIGHT_ATR = 0.8
+MAX_AGE_BARS = 40
+
+@dataclass
+class Formation:
+    symbol: str
+    kind: str
+    leg1: float
+    leg2: float
+    neckline: float
+    close: float
+    confirmed: bool
+    vector_at_leg2: bool
+    bars_since_leg2: int
+
+    @property
+    def direction(self) -> str:
+        return 'לונג' if self.kind == 'W' else 'שורט'
+
+    def line(self) -> str:
+        state = 'מאושרת (סגירה מעבר לצוואר)' if self.confirmed else 'מתגבשת'
+        vec = ' · וקטור ברגל השנייה (קעקוע)' if self.vector_at_leg2 else ''
+        return f"תבנית {self.kind} {state}: רגליים {self.leg1:,.2f}/{self.leg2:,.2f} · צוואר {self.neckline:,.2f}{vec} [0{(4 if self.kind == 'W' else 5)} @ Tino1 §4]"
+
+def _swings(df: pd.DataFrame, k: int=SWING_K):
+    hi, lo = (df['high'].values, df['low'].values)
+    highs, lows = ([], [])
+    n = len(df)
+    for i in range(k, n - k):
+        w = slice(i - k, i + k + 1)
+        if lo[i] == min(lo[w]):
+            lows.append((i, float(lo[i])))
+        elif hi[i] == max(hi[w]):
+            highs.append((i, float(hi[i])))
+    return (_dedup_pivots(highs, k), _dedup_pivots(lows, k))
+
+def _dedup_pivots(pivots: list, k: int) -> list:
+    """Collapse a plateau into ONE pivot.
+
+    A flat extreme — several adjacent bars sharing the same low — satisfies
+    `lo[i] == min(window)` on EVERY bar of the plateau, so the same physical
+    pivot was returned two and three times. detect() then took `lows[-2:]`,
+    got the SAME leg twice, found no swing high strictly between two adjacent
+    indices, and returned None: a clean double-bottom whose second leg had a
+    flat tip was silently invisible, live. Caught 2026-08-31 by the very first
+    wm fixture ever run (tr-tree-v4/tests/test_wm_fixtures.py) — the reason
+    the dataset plan makes fixtures a P0 that blocks everything.
+
+    Adjacent entries (gap <= k bars) at the same extreme are one pivot; the
+    LAST bar of the plateau keeps it — policy, not accident: bars_since_leg2
+    measures from the plateau's END (its true age), and the vector check
+    window sits where the leg actually finished forming. (Codex review asked
+    for the policy to be explicit and tested.)
+    """
+    out: list = []
+    for i, v in pivots:
+        if out and i - out[-1][0] <= k and (abs(v - out[-1][1]) < 1e-09):
+            out[-1] = (i, v)
+            continue
+        out.append((i, v))
+    return out
+
+class WmReader:
+
+    def __init__(self, source):
+        self.source = source
+
+    def detect(self, symbol: str, timeframe: str='15m') -> Formation | None:
+        """The freshest W or M on the frame, or None."""
+        try:
+            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
+            if corr and getattr(corr, 'unverified', False) or len(df) < 30:
+                return None
+        except Exception:
+            return None
+        prev = df['close'].shift(1)
+        rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
+        atr = float(rng.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]) or 1e-09
+        highs, lows = _swings(df)
+        close = float(df['close'].iloc[-1])
+        n = len(df)
+
+        def vec_near(i: int) -> bool:
+            try:
+                seg = df.iloc[max(0, i - 2):i + 3]
+                pv = tr.pvsra(seg)
+                if pv is None:
+                    return False
+                if isinstance(pv, dict):
+                    return bool(pv.get('climax') or pv.get('vector'))
+                return bool(pv['kind'].isin(('green', 'red')).any())
+            except Exception:
+                return False
+        best = None
+        if len(lows) >= 2:
+            (i1, l1), (i2, l2) = (lows[-2], lows[-1])
+            between = [h for j, h in highs if i1 < j < i2]
+            if between and n - 1 - i2 <= MAX_AGE_BARS and (l2 >= l1 - LEG_TOLERANCE_ATR * atr):
+                neck = max(between)
+                if neck - max(l1, l2) >= MIN_HEIGHT_ATR * atr:
+                    best = Formation(symbol, 'W', l1, l2, neck, close, confirmed=close > neck, vector_at_leg2=vec_near(i2), bars_since_leg2=n - 1 - i2)
+        if len(highs) >= 2:
+            (i1, h1), (i2, h2) = (highs[-2], highs[-1])
+            between = [l for j, l in lows if i1 < j < i2]
+            if between and n - 1 - i2 <= MAX_AGE_BARS and (h2 <= h1 + LEG_TOLERANCE_ATR * atr):
+                neck = min(between)
+                if min(h1, h2) - neck >= MIN_HEIGHT_ATR * atr:
+                    m = Formation(symbol, 'M', h1, h2, neck, close, confirmed=close < neck, vector_at_leg2=vec_near(i2), bars_since_leg2=n - 1 - i2)
+                    if best is None or m.bars_since_leg2 < best.bars_since_leg2:
+                        best = m
+        return best
+

warning: in the working copy of 'trading_system/tree_replay/_vendor/liquidity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/liquidity.py b/trading_system/tree_replay/_vendor/liquidity.py
new file mode 100644
index 0000000..f2e4349
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/liquidity.py
@@ -0,0 +1,150 @@
+"""Liquidity pools — equal highs/lows, and the run that takes them.
+
+TR-TREE-V2 layer 6 (STRUCTURE & LIQUIDITY) asks for three objects this desk did
+not have: **EQH/EQL**, **Stop Run**, and **Liquidity Run** — with an explicit
+`[WELD]` mark on the tree saying pools of liquidity are the union of
+liquidations AND unrecovered vectors, and that a Liquidity Run is *"מהלך מהיר
+שמאשש וקטור"* — speed plus recovery, not speed alone.
+
+**Why equal extremes are the object and not "a level".** A level is where price
+reacted once. An equal high is where price reacted TWICE at the same price,
+which means resting stops accumulated above it — the pool the method's whole
+market-maker premise is about (*"what is the market maker trying to make the
+retail trader think?"* `[01 @ 00m51s]`). The tree puts it under liquidity for
+that reason, not under levels.
+
+**Tolerance is in ATR, not ticks or percent**, so gold at 4,600 and BTC at
+80,000 mean the same thing by "equal". Two highs within `EQ_TOL_ATR` of each
+other count as equal; more than two is a stronger pool and is reported as such.
+
+**A run is speed AND recovery.** `Run.detected` requires both: the move covers
+`RUN_ATR` inside `RUN_BARS`, and it takes out a pool on the way. A fast move
+that takes nothing is expansion, not a liquidity run, and calling it one would
+manufacture the method's most important signal out of ordinary momentum.
+
+Nothing here is measured. It reports structure; the tree decides.
+"""
+from __future__ import annotations
+from dataclasses import dataclass, field
+import pandas as pd
+EQ_TOL_ATR = 0.25
+LOOKBACK = 120
+SWING_K = 3
+RUN_ATR = 1.5
+RUN_BARS = 4
+
+@dataclass
+class Pool:
+    """Equal highs or lows — resting stops, in the method's reading."""
+    side: str
+    price: float
+    touches: int
+    bars_ago: int
+    swept: bool
+
+    @property
+    def strength(self) -> str:
+        return 'חזק' if self.touches >= 3 else 'רגיל'
+
+    def line(self) -> str:
+        what = 'שיאים שווים' if self.side == 'high' else 'שפלים שווים'
+        state = 'נסחף' if self.swept else 'לא נסחף'
+        return f'{what} @ {self.price:,.2f} · {self.touches} נגיעות ({self.strength}) · {state}'
+
+@dataclass
+class Run:
+    """A liquidity run: speed AND a pool taken."""
+    detected: bool
+    direction: str | None = None
+    pool: Pool | None = None
+    atr_covered: float = 0.0
+    bars: int = 0
+
+    def line(self) -> str:
+        if not self.detected:
+            return 'אין ריצת נזילות'
+        return f"ריצת נזילות {self.direction} — {self.atr_covered:.1f} ATR ב-{self.bars} נרות, לקחה {(self.pool.line() if self.pool else '?')}"
+
+def _atr(df: pd.DataFrame, n: int=14) -> float:
+    prev = df['close'].shift(1)
+    rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
+    return float(rng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])
+
+def _swings(df: pd.DataFrame, k: int=SWING_K):
+    hi, lo = (df['high'].values, df['low'].values)
+    highs, lows = ([], [])
+    for i in range(k, len(df) - k):
+        w = slice(i - k, i + k + 1)
+        if hi[i] == max(hi[w]):
+            highs.append((i, float(hi[i])))
+        elif lo[i] == min(lo[w]):
+            lows.append((i, float(lo[i])))
+    return (highs, lows)
+
+class LiquidityReader:
+
+    def __init__(self, source):
+        self.source = source
+
+    def pools(self, symbol: str, timeframe: str='15m') -> list[Pool]:
+        """Equal-extreme pools on the frame, newest first."""
+        try:
+            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
+            if corr and getattr(corr, 'unverified', False) or len(df) < 40:
+                return []
+        except Exception:
+            return []
+        df = df.iloc[-LOOKBACK:]
+        atr = _atr(df) or 1e-09
+        tol = EQ_TOL_ATR * atr
+        n = len(df)
+        highs, lows = _swings(df)
+        out: list[Pool] = []
+        for side, pts in (('high', highs), ('low', lows)):
+            used = set()
+            for i, (idx, px) in enumerate(pts):
+                if idx in used:
+                    continue
+                group = [(idx, px)]
+                for jdx, jpx in pts[i + 1:]:
+                    if abs(jpx - px) <= tol:
+                        group.append((jdx, jpx))
+                        used.add(jdx)
+                if len(group) < 2:
+                    continue
+                level = sum((p for _, p in group)) / len(group)
+                newest = max((g for g, _ in group))
+                after = df.iloc[newest + 1:]
+                swept = bool(len(after) and ((after['high'] > level + tol).any() if side == 'high' else (after['low'] < level - tol).any()))
+                out.append(Pool(side=side, price=level, touches=len(group), bars_ago=n - 1 - newest, swept=swept))
+        out.sort(key=lambda p: p.bars_ago)
+        return out
+
+    def run(self, symbol: str, timeframe: str='15m') -> Run:
+        """Was there a liquidity run — speed AND a pool taken — just now?"""
+        try:
+            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
+            if corr and getattr(corr, 'unverified', False) or len(df) < 40:
+                return Run(detected=False)
+        except Exception:
+            return Run(detected=False)
+        atr = _atr(df) or 1e-09
+        seg = df.iloc[-(RUN_BARS + 1):-1]
+        if len(seg) < 2:
+            return Run(detected=False)
+        covered = (float(seg['high'].max()) - float(seg['low'].min())) / atr
+        if covered < RUN_ATR:
+            return Run(detected=False)
+        direction = 'לונג' if float(seg['close'].iloc[-1]) > float(seg['open'].iloc[0]) else 'שורט'
+        taken = None
+        for p in self.pools(symbol, timeframe):
+            if not p.swept:
+                continue
+            lo, hi = (float(seg['low'].min()), float(seg['high'].max()))
+            if lo <= p.price <= hi:
+                taken = p
+                break
+        if taken is None:
+            return Run(detected=False)
+        return Run(detected=True, direction=direction, pool=taken, atr_covered=covered, bars=len(seg))
+

warning: in the working copy of 'trading_system/tree_replay/_vendor/brinks.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/brinks.py b/trading_system/tree_replay/_vendor/brinks.py
new file mode 100644
index 0000000..d050141
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/brinks.py
@@ -0,0 +1,101 @@
+"""The Brinks Box — the strategy Tino ranks above everything else.
+
+> "If I were to pick one strategy from the Hybrid system, not use anything else
+> and not trade any other time… it would be the Brinks Box Strategy."
+> [Checklist-8 @ p1]
+
+Until 2026-08-26 this existed on the floor only as text in the PDF database —
+the corpus's own headline, uncoded. This is the mechanical core:
+
+**The box** forms **14:00–15:00 GMT** (banks open 09:00 ET; the bell 09:30) —
+always one hour wide, variable height, same start for all common assets
+[Checklist-8 @ p2]. High and low of the completed hour, body AND wick.
+
+**The read, after completion** [Checklist-8 @ p14-p15]:
+- unrecovered vectors INSIDE the box are the strategy's core — what the MM
+  printed and still owes a recovery;
+- the MIDPOINT is the gate: a long needs price holding above it, a short below;
+- external vectors away from the box are the destinations.
+
+**What is deliberately left to the human/agent:** which vector to lean on and
+the entry itself. Tino calls the whole method discretionary [17 @ 00m50s]; this
+module reports the box's facts so the trade engine and the tr-agent can cite
+them, and logs a SILENT firing so the family accumulates a sample — his own
+build-don't-send rule from 2026-08-13 applies to his favourite strategy too."""
+from __future__ import annotations
+from dataclasses import dataclass, field
+from datetime import datetime, timedelta, timezone
+import pandas as pd
+from . import pattern_tr as tr
+BOX_START_H, BOX_END_H = (14, 15)
+RELEVANT_UNTIL_H = 20
+
+@dataclass
+class Box:
+    symbol: str
+    hi: float
+    lo: float
+    close: float
+    open_vectors_inside: int | None
+    formed_at: str
+
+    @property
+    def mid(self) -> float:
+        return (self.hi + self.lo) / 2.0
+
+    @property
+    def side(self) -> str:
+        """Which side of the midpoint price holds — the checklist's gate."""
+        if self.close > self.mid:
+            return 'לונג'
+        if self.close < self.mid:
+            return 'שורט'
+        return 'על האמצע'
+
+    def line(self) -> str:
+        if self.open_vectors_inside is None:
+            vec = ' · הווקטורים בתוכה לא נקראו'
+        elif self.open_vectors_inside:
+            vec = f' · {self.open_vectors_inside} וקטורים לא-משוחזרים בתוכה'
+        else:
+            vec = ''
+        return f"קופסת ברינקס {self.lo:,.2f}–{self.hi:,.2f} · המחיר {('מעל' if self.close > self.mid else 'מתחת ל')}אמצע ({self.mid:,.2f}) ⇒ נטיית {self.side}{vec} [Checklist-8]"
+
+class BrinksReader:
+
+    def __init__(self, source):
+        self.source = source
+
+    def today_box(self, symbol: str, now: datetime | None=None) -> Box | None:
+        """Today's completed Brinks box, while it is still the session's context.
+
+    None before 15:00 GMT (the box is still forming — rule 1: wait), and after
+    20:00 GMT (the session it set up is over)."""
+        now = now or self.source.now_utc()
+        if not BOX_END_H <= now.hour < RELEVANT_UNTIL_H or now.weekday() >= 5:
+            return None
+        try:
+            df, corr = self.source.fetch_corrected(symbol, '5m', 2)
+            if corr and getattr(corr, 'unverified', False):
+                return None
+        except Exception:
+            return None
+        if df.empty:
+            return None
+        idx = pd.to_datetime(df.index, utc=True)
+        day = now.date()
+        start = pd.Timestamp(datetime(day.year, day.month, day.day, BOX_START_H, tzinfo=timezone.utc))
+        end = start + timedelta(hours=1)
+        seg = df[(idx >= start) & (idx < end)]
+        if len(seg) < 8:
+            return None
+        hi, lo = (float(seg['high'].max()), float(seg['low'].min()))
+        open_inside = None
+        try:
+            pv = tr.pvsra(seg)
+            zones_ = tr.vector_zones(seg, pv)
+            open_inside = int(zones_['open'].sum()) if len(zones_) else 0
+        except Exception:
+            open_inside = None
+        return Box(symbol=symbol, hi=hi, lo=lo, close=float(df['close'].iloc[-1]), open_vectors_inside=open_inside, formed_at=f'{day} {BOX_START_H:02d}:00-{BOX_END_H:02d}:00 GMT')
+

warning: in the working copy of 'trading_system/tree_replay/_vendor/checklists.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/checklists.py b/trading_system/tree_replay/_vendor/checklists.py
new file mode 100644
index 0000000..3b8ee27
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/checklists.py
@@ -0,0 +1,212 @@
+"""RVC/GVC, Block Trade and Brinks — from Tino's own checklist PDFs.
+
+These three sat marked ❌ in the tree-coverage audit with the verdict "no
+source defines them". **That verdict was wrong, and Sagiv was right to push
+back.** I had searched the extracted markdown corpus and stopped there. The
+definitions were in the PDF library all along, each with a DEDICATED
+checklist:
+
+    Checklist-6-RVC-GVC-Strategy.pdf          (14p)
+    Checklist-7-The-Block-Trade-Principle.pdf (11p)
+    Checklist-8-The-Brinks-Box-Strategy.pdf   (15p)
+
+The lesson is written into the coverage doc: "not in the corpus" is a claim
+about a SEARCH, and a search that covered one of two archives has not earned
+that claim.
+
+Citations here are `[C6 p]`, `[C7 p]`, `[C8 p]` — the checklist and its point.
+"""
+from __future__ import annotations
+from dataclasses import dataclass
+import pandas as pd
+from . import map_sessions as sessions, pattern_tr as tr
+from .brinks import BrinksReader
+WICK_SYMMETRY_MAX = 2.0
+BLOCK_BODY_MIN = 0.6
+BLOCK_RANGE_MIN_ATR = 1.0
+
+@dataclass
+class RvcGvc:
+    """A red-then-green (long) or green-then-red (short) vector formation."""
+    direction: str
+    name: str
+    first_kind: str
+    second_kind: str
+    recovered: bool
+    wick_ok: bool
+    bars_ago: int
+    price: float
+
+    def line(self) -> str:
+        s = f'{self.name} — {self.first_kind}→{self.second_kind} ⇒ {self.direction}'
+        if not self.recovered:
+            s += ' · השני לא כיסה את הראשון'
+        if not self.wick_ok:
+            s += ' · פתילים לא סימטריים'
+        return s + f'  [C6]'
+
+@dataclass
+class Block:
+    """A candle whose body says commitment — market memory to retrigger."""
+    direction: str
+    price_hi: float
+    price_lo: float
+    body_pct: float
+    range_atr: float
+    quality: str
+    bars_ago: int
+
+    def line(self) -> str:
+        return f'בלוק {self.direction} {self.price_lo:,.2f}-{self.price_hi:,.2f} · גוף {self.body_pct * 100:.0f}% · {self.range_atr:.1f} ATR · איכות {self.quality}  [C7]'
+
+def block_quality(df, i: int, atr: float) -> tuple[str, float, float]:
+    """Grade one candle as a block. [C7 pt1] big candle, small wicks."""
+    h, l = (float(df['high'].iloc[i]), float(df['low'].iloc[i]))
+    o, c = (float(df['open'].iloc[i]), float(df['close'].iloc[i]))
+    rng = max(h - l, 1e-09)
+    body_pct = abs(c - o) / rng
+    range_atr = rng / max(atr, 1e-09)
+    if body_pct >= BLOCK_BODY_MIN and range_atr >= BLOCK_RANGE_MIN_ATR:
+        q = 'טוב'
+    elif body_pct >= 0.45:
+        q = 'גבולי'
+    else:
+        q = 'גרוע'
+    return (q, body_pct, range_atr)
+
+@dataclass
+class BrinksRead:
+    """The Brinks Box strategy checklist, walked. [C8]"""
+    formed: bool
+    box_hi: float | None
+    box_lo: float | None
+    internal_vectors: list | None
+    external_vectors: list | None
+    swept_asia: bool | None
+    note: str = ''
+
+    def render(self) -> str:
+        if not self.formed:
+            return f'קופסת ברינקס — {self.note}  [C8 pt1]'
+        L = [f'קופסת ברינקס {self.box_lo:,.2f}-{self.box_hi:,.2f}  [C8]']
+        if self.internal_vectors is None or self.external_vectors is None:
+            L.append('  וקטורים בתוך/מחוץ לקופסה: לא נקראו  [C8 pt2-3]')
+        else:
+            L.append(f'  וקטורים לא מכוסים בתוך הקופסה: {len(self.internal_vectors)}  [C8 pt2]')
+            L.append(f'  וקטורים לא מכוסים מחוץ לקופסה: {len(self.external_vectors)}  [C8 pt3]')
+        if self.swept_asia is None:
+            L.append('  סחיפת אסיה: לא נקראה  [C8 pt4]')
+        elif self.swept_asia:
+            L.append('  ⚠ הקופסה סחפה את קצה אסיה — מלכודת נזילות  [C8 pt4]')
+        return '\n'.join(L)
+
+class ChecklistReader:
+
+    def __init__(self, source):
+        self.source = source
+        self.brinks = BrinksReader(source)
+
+    def rvc_gvc(self, symbol: str, timeframe: str='15m') -> RvcGvc | None:
+        """The formation on the last two COMPLETED candles, or None.
+
+    Only the last two: [C6 pt6] makes this a same-moment setup — the candle
+    after the vector must itself close as a vector. Scanning further back
+    would report formations whose trade is long gone.
+    """
+        try:
+            df, corr = self.source.fetch_corrected(symbol, timeframe, 5)
+            if corr and getattr(corr, 'unverified', False) or len(df) < 30:
+                return None
+            pv = tr.pvsra(df)
+        except Exception:
+            return None
+        i = len(df) - 2
+        j = i - 1
+        if j < 0:
+            return None
+        a, b = (str(pv['kind'].iloc[j]), str(pv['kind'].iloc[i]))
+        reds, greens = (('red', 'violet'), ('green', 'blue'))
+        if a in reds and b in greens:
+            direction, name = ('לונג', 'RVC')
+        elif a in greens and b in reds:
+            direction, name = ('שורט', 'GVC')
+        else:
+            return None
+        o1, c1 = (float(df['open'].iloc[j]), float(df['close'].iloc[j]))
+        c2 = float(df['close'].iloc[i])
+        recovered = c2 >= max(o1, c1) if direction == 'לונג' else c2 <= min(o1, c1)
+        h, l = (float(df['high'].iloc[i]), float(df['low'].iloc[i]))
+        o2 = float(df['open'].iloc[i])
+        up_w, dn_w = (h - max(o2, c2), min(o2, c2) - l)
+        lo_w, hi_w = (min(up_w, dn_w), max(up_w, dn_w))
+        wick_ok = hi_w <= WICK_SYMMETRY_MAX * lo_w if lo_w > 1e-09 else False
+        return RvcGvc(direction, name, a, b, recovered, wick_ok, 1, c2)
+
+    def blocks(self, symbol: str, timeframe: str='15m', lookback: int=60) -> list[Block]:
+        """Vector candles that qualify as blocks, newest first. [C7]"""
+        try:
+            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
+            if corr and getattr(corr, 'unverified', False) or len(df) < 40:
+                return []
+            pv = tr.pvsra(df)
+        except Exception:
+            return []
+        prev = df['close'].shift(1)
+        trng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
+        atr = float(trng.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]) or 1e-09
+        out: list[Block] = []
+        n = len(df)
+        for i in range(max(1, n - lookback), n - 1):
+            kind = str(pv['kind'].iloc[i])
+            if kind not in ('green', 'red', 'blue', 'violet'):
+                continue
+            q, body, ratr = block_quality(df, i, atr)
+            if q == 'גרוע':
+                continue
+            out.append(Block('לונג' if kind in ('green', 'blue') else 'שורט', float(df['high'].iloc[i]), float(df['low'].iloc[i]), body, ratr, q, n - 1 - i))
+        out.sort(key=lambda b: b.bars_ago)
+        return out
+
+    def brinks_read(self, symbol: str, timeframe: str='5m') -> BrinksRead:
+        """Walk Tino's four Brinks checklist points.
+
+    [C8 pt1] wait until the box is FORMED (14:00-15:00 GMT). He allows an
+             exception for traders who know their asset's box behaviour; we
+             do not take it -- an exception granted to experience is not one
+             a detector gets to grant itself.
+    [C8 pt2] unrecovered vectors INSIDE the box, on 1m/5m/15m.
+    [C8 pt3] unrecovered vectors OUTSIDE it -- the targets beyond.
+    [C8 pt4] did the box sweep the Asia extreme? Then it is a trap, and the
+             read inverts.
+    """
+        try:
+            box = self.brinks.today_box(symbol)
+        except Exception:
+            return BrinksRead(False, None, None, [], [], False, 'לא ניתן לחשב')
+        if box is None:
+            return BrinksRead(False, None, None, [], [], False, 'טרם נסגרה — ממתינים (14:00-15:00 GMT)')
+        hi, lo = (float(box.hi), float(box.lo))
+        inside = outside = None
+        try:
+            df, _c = self.source.fetch_corrected(symbol, timeframe, 10)
+            zones = tr.vector_zones(df)
+            inside, outside = ([], [])
+            for t, z in zones[zones['open']].iterrows():
+                mid = (float(z['top']) + float(z['bottom'])) / 2.0
+                rec = {'price': mid, 'kind': str(z['kind']), 'top': float(z['top']), 'bottom': float(z['bottom'])}
+                (inside if lo <= mid <= hi else outside).append(rec)
+        except Exception:
+            inside = outside = None
+        swept = None
+        try:
+            d15, _c = self.source.fetch_corrected(symbol, '15m', 3)
+            idx = pd.to_datetime(d15.index, utc=True)
+            day = pd.Timestamp(box.formed_at).tz_convert('UTC').date()
+            m = [t.date() == day and 0 <= t.hour < 7 for t in idx]
+            asia = d15[m]
+            if len(asia):
+                swept = hi > float(asia['high'].max()) or lo < float(asia['low'].min())
+        except Exception:
+            swept = None
+        return BrinksRead(True, hi, lo, inside, outside, swept)
+

warning: in the working copy of 'trading_system/tree_replay/_vendor/pattern_tr.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/pattern_tr.py b/trading_system/tree_replay/_vendor/pattern_tr.py
new file mode 100644
index 0000000..ded4bae
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/pattern_tr.py
@@ -0,0 +1,2 @@
+from .pvsra import pvsra
+from .tree_tr import vector_zones

warning: in the working copy of 'tests/tree_replay/test_pattern_readers.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_pattern_readers.py b/tests/tree_replay/test_pattern_readers.py
new file mode 100644
index 0000000..ec3af58
--- /dev/null
+++ b/tests/tree_replay/test_pattern_readers.py
@@ -0,0 +1,301 @@
+"""Literal OHLCV fixtures exercise original readers, not final verdict doubles."""
+import importlib
+import importlib.util
+from types import SimpleNamespace
+
+import numpy as np
+import pandas as pd
+import pytest
+
+
+def api(module):
+    name='trading_system.tree_replay._vendor.'+module
+    assert importlib.util.find_spec(name) is not None, 'pattern reader missing: '+module
+    return importlib.import_module(name)
+
+
+def frame(anchors=None,n=40,start='2026-09-09 10:00Z'):
+    anchors=anchors or {0:100.,n-1:100.}
+    c=np.interp(np.arange(n),list(anchors),list(anchors.values()))
+    return pd.DataFrame(dict(open=c,high=c+1,low=c-1,close=c,volume=1.),
+        index=pd.date_range(start,periods=n,freq='5min'))
+
+
+class Frames:
+    def __init__(self,mapping,now='2026-09-09 15:00Z',corr=None):
+        self.mapping=mapping
+        self.now=pd.Timestamp(now).to_pydatetime()
+        self.corr=corr
+        self.calls=[]
+    def fetch_corrected(self,*key):
+        self.calls.append(key)
+        value=self.mapping[key]
+        if isinstance(value,list): value=value.pop(0)
+        if isinstance(value,Exception): raise value
+        return value.copy(),self.corr
+    def now_utc(self):
+        self.calls.append(('clock',))
+        return self.now
+
+
+def w_frame():
+    return frame({0:100.,5:103.,10:90.,17:110.,25:91.,35:115.,39:115.})
+
+
+def mirror(f):
+    result=f.copy()
+    for col in ['open','close']: result[col]=200-f[col]
+    result['high'],result['low']=200-f['low'],200-f['high']
+    return result
+
+
+@pytest.mark.parametrize('inverse,kind,legs,neck,direction',[
+    (False,'W',(89.,90.),111.,'לונג'),(True,'M',(111.,110.),89.,'שורט')])
+def test_wm_geometry_and_actual_local_vector_warmup(inverse,kind,legs,neck,direction):
+    f=mirror(w_frame()) if inverse else w_frame()
+    f.loc[f.index[25],'volume']=1000
+    p=Frames({('X','1h',10):f})
+    got=api('wm').WmReader(p).detect('X','1h')
+    assert (got.kind,got.leg1,got.leg2,got.neckline)==(kind,*legs,neck)
+    assert got.confirmed and got.direction==direction and got.bars_since_leg2==14
+    assert not got.vector_at_leg2  # original five-row PVSRA has no baseline
+    assert p.calls==[('X','1h',10)]
+
+
+@pytest.mark.parametrize('close,confirmed',[(111.,False),(111.01,True),(110.99,False)])
+def test_wm_neckline_needs_strict_close(close,confirmed):
+    f=w_frame(); f.iloc[-1,f.columns.get_loc('close')]=close
+    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
+    assert got.kind=='W' and got.confirmed==confirmed
+
+
+def test_swing_priority_and_plateau_policy_are_not_interchangeable():
+    f=frame(n=10)
+    assert api('wm')._swings(f)==([],[(6,99.)])
+    assert api('liquidity')._swings(f)==([(3,101.),(4,101.),(5,101.),(6,101.)],[])
+    assert api('wm')._dedup_pivots([(1,10.),(4,10.),(8,10.),(9,11.)],3)==[(4,10.),(8,10.),(9,11.)]
+
+
+@pytest.mark.parametrize('n,present',[(66,True),(67,False)])
+def test_wm_age_boundary_without_new_pivots(n,present):
+    f=frame({0:100.,5:103.,10:90.,17:110.,25:91.,n-1:115.},n)
+    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
+    assert (got is not None)==present
+    if present: assert got.bars_since_leg2==40
+
+
+@pytest.mark.parametrize('leg,present',[(89.5,True),(80.,False)])
+def test_wm_second_leg_undercut_tolerance(leg,present):
+    f=frame({0:100.,10:90.,17:110.,25:leg,39:115.})
+    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
+    assert (got is not None)==present
+
+
+def test_wm_newer_m_takes_precedence_over_valid_w():
+    f=frame({0:100.,5:90.,10:110.,18:91.,25:109.,39:95.})
+    got=api('wm').WmReader(Frames({('X','15m',10):f})).detect('X')
+    assert (got.kind,got.leg1,got.leg2,got.neckline,got.bars_since_leg2)==('M',111.,110.,90.,14)
+
+
+@pytest.mark.parametrize('module,method,lookback,minimum,empty',[
+    ('wm','detect',10,30,None),('liquidity','pools',10,40,[]),
+    ('liquidity','run',10,40,False),('checklists','rvc_gvc',5,30,None),
+    ('checklists','blocks',10,40,[])])
+@pytest.mark.parametrize('fault',['short','correction','error'])
+def test_reader_initial_unavailability_preserves_original_result(module,method,lookback,minimum,empty,fault):
+    f=OSError('missing') if fault=='error' else frame(n=minimum-1 if fault=='short' else 60)
+    p=Frames({('X','15m',lookback):f},corr=SimpleNamespace(unverified=True) if fault=='correction' else None)
+    cls={'wm':'WmReader','liquidity':'LiquidityReader','checklists':'ChecklistReader'}[module]
+    got=getattr(getattr(api(module),cls)(p),method)('X')
+    assert (got.detected if method=='run' else got)==empty
+    assert p.calls==[('X','15m',lookback)]
+
+
+def pool_frame(sweep=False):
+    f=frame({0:100.,10:110.,17:100.,25:110.,35:100.,39:101.})
+    if sweep: f.iloc[-1,f.columns.get_loc('high')]=115.
+    return f
+
+
+@pytest.mark.parametrize('sweep',[False,True])
+def test_equal_highs_pool_geometry_and_newest_touch(sweep):
+    p=Frames({('X','15m',10):pool_frame(sweep)})
+    pools=api('liquidity').LiquidityReader(p).pools('X')
+    highs=[x for x in pools if x.side=='high']
+    assert len(highs)==1
+    h=highs[0]
+    assert (h.price,h.touches,h.bars_ago,h.swept)==(111.,2,14,sweep)
+
+
+def test_pool_groups_against_first_price_not_chained_centroid():
+    f=frame(n=60)
+    f['high']=np.linspace(101.,102.,60); f['low']=np.linspace(90.,91.,60)
+    f.iloc[10,f.columns.get_loc('high')]=110.
+    f.iloc[25,f.columns.get_loc('high')]=112.
+    f.iloc[40,f.columns.get_loc('high')]=114.
+    got=api('liquidity').LiquidityReader(Frames({('X','15m',10):f})).pools('X')
+    assert [(p.side,p.price,p.touches,p.bars_ago,p.swept) for p in got]==[('high',111.,2,34,True)]
+
+
+def test_pool_lookback_excludes_old_extremes():
+    f=frame({0:100.,10:150.,20:100.,30:150.,40:100.,159:110.},160)
+    assert api('liquidity').LiquidityReader(Frames({('X','15m',10):f})).pools('X')==[]
+
+
+@pytest.mark.parametrize('swept,direction',[(True,'לונג'),(False,None)])
+def test_run_needs_actual_swept_pool_from_second_read(swept,direction):
+    speed=frame()
+    speed.iloc[35:39,speed.columns.get_loc('low')]=95.
+    speed.iloc[35:39,speed.columns.get_loc('high')]=115.
+    speed.iloc[38,speed.columns.get_loc('close')]=112.
+    p=Frames({('X','15m',10):[speed,pool_frame(swept)]})
+    got=api('liquidity').LiquidityReader(p).run('X')
+    assert got.detected==swept and got.direction==direction
+    if swept: assert got.pool.price==111. and got.bars==4
+    assert p.calls==[('X','15m',10),('X','15m',10)]
+
+
+def test_slow_run_does_not_request_pool_and_forming_spike_is_not_completed_speed():
+    f=frame(); f.iloc[-1,f.columns.get_loc('high')]=1000.
+    p=Frames({('X','15m',10):f})
+    assert not api('liquidity').LiquidityReader(p).run('X').detected
+    assert p.calls==[('X','15m',10)]
+
+
+@pytest.mark.parametrize('close',[99.,100.])
+def test_run_equal_or_lower_close_is_short_even_with_high_side_pool(close):
+    f=frame(); f.loc[f.index[35:39],'high']=115.; f.loc[f.index[35:39],'low']=95.
+    f.iloc[38,f.columns.get_loc('close')]=close
+    p=Frames({('X','15m',10):[f,pool_frame(True)]})
+    r=api('liquidity').LiquidityReader(p).run('X')
+    assert r.detected and r.direction=='שורט' and r.pool.side=='high'
+
+
+@pytest.mark.parametrize('now,formed',[
+    ('2026-09-09 14:59:59Z',False),('2026-09-09 15:00Z',True),
+    ('2026-09-09 19:59:59Z',True),('2026-09-09 20:00Z',False),
+    ('2026-09-12 15:00Z',False)])
+def test_brinks_utc_window_and_clock_order(now,formed):
+    p=Frames({('X','5m',2):frame(n=8,start='2026-09-09 14:00Z')},now)
+    got=api('brinks').BrinksReader(p).today_box('X')
+    assert (got is not None)==formed
+    assert p.calls==[('clock',)]+([('X','5m',2)] if formed else [])
+    if formed:
+        assert (got.hi,got.lo,got.mid,got.side)==(101.,99.,100.,'על האמצע')
+        assert got.formed_at=='2026-09-09 14:00-15:00 GMT'
+
+
+@pytest.mark.parametrize('count',[7,8])
+def test_brinks_minimum_and_explicit_clock(count):
+    f=frame(n=count,start='2026-09-09 14:00Z')
+    f.loc[pd.Timestamp('2026-09-09 15:00Z')]=[120.,130.,110.,125.,1.]
+    p=Frames({('X','5m',2):f})
+    b=api('brinks').BrinksReader(p).today_box('X',now=p.now)
+    assert p.calls==[('X','5m',2)]
+    if count==7: assert b is None
+    else: assert (b.hi,b.lo,b.close,b.open_vectors_inside)==(101.,99.,125.,0)
+
+
+def test_brinks_counts_actual_unrecovered_vector_inside_hour():
+    f=frame(n=12,start='2026-09-09 14:00Z')
+    f.iloc[10]=[100.,103.,99.,102.,3.]
+    p=Frames({('X','5m',2):f})
+    assert api('brinks').BrinksReader(p).today_box('X').open_vectors_inside==1
+
+
+def rvc_frame(inverse=False,close=102.,upper=1.,lower=1.):
+    f=frame(n=33)
+    f.iloc[30]=[102.,103.,99.,100.,3.]
+    f.iloc[31]=[100.,max(100.,close)+upper,100.-lower,close,10.]
+    f.iloc[32]=[102.,103.,99.,100.,100.]  # opposite forming vector is ignored
+    return mirror(f) if inverse else f
+
+
+@pytest.mark.parametrize('inverse,name,direction',[(False,'RVC','לונג'),(True,'GVC','שורט')])
+@pytest.mark.parametrize('close,upper,lower,recovered,wick_ok',[
+    (102.,1.,1.,True,True),(101.9,1.,1.,False,True),
+    (102.,2.,1.,True,True),(102.,2.1,1.,True,False),(102.,0.,1.,True,False)])
+def test_rvc_completed_real_vectors_recovery_and_wicks(inverse,name,direction,close,upper,lower,recovered,wick_ok):
+    p=Frames({('X','15m',5):rvc_frame(inverse,close,upper,lower)})
+    r=api('checklists').ChecklistReader(p).rvc_gvc('X')
+    assert r is not None
+    assert (r.name,r.direction,r.recovered,r.wick_ok,r.bars_ago)==(name,direction,recovered,wick_ok,1)
+    assert (r.first_kind,r.second_kind)==(('green','red') if inverse else ('red','green'))
+
+
+def test_rvc_requires_second_completed_vector_not_just_opposite_color():
+    f=rvc_frame(); f.iloc[31,f.columns.get_loc('volume')]=0.1
+    assert api('checklists').ChecklistReader(Frames({('X','15m',5):f})).rvc_gvc('X') is None
+
+
+@pytest.mark.parametrize('inverse',[False,True])
+def test_rvc_accepts_real_rising_tier_vectors(inverse):
+    f=rvc_frame()
+    # A prior wide candle keeps spread-volume below climax while volumes rise.
+    f.iloc[25]=[100.,120.,80.,100.,1.]
+    f.iloc[30,f.columns.get_loc('volume')]=1.6
+    f.iloc[31,f.columns.get_loc('volume')]=1.7
+    if inverse: f=mirror(f)
+    r=api('checklists').ChecklistReader(Frames({('X','15m',5):f})).rvc_gvc('X')
+    assert (r.first_kind,r.second_kind)==(('blue','violet') if inverse else ('violet','blue'))
+    assert r.recovered and r.wick_ok
+
+
+@pytest.mark.parametrize('body,atr,quality',[(6.,10.,'טוב'),(6.,10.1,'גבולי'),(4.5,10.,'גבולי'),(4.49,10.,'גרוע')])
+def test_block_literal_quality_boundaries(body,atr,quality):
+    f=pd.DataFrame([dict(open=0.,close=body,low=0.,high=10.)])
+    q,pct,ratio=api('checklists').block_quality(f,0,atr)
+    assert q==quality and pct==body/10. and ratio==10./atr
+
+
+def test_blocks_actual_vectors_newest_order_and_forming_exclusion():
+    f=frame(n=43)
+    f.iloc[40]=[100.,110.,100.,108.,3.]
+    f.iloc[41]=[108.,110.,100.,100.,10.]
+    f.iloc[42]=[100.,110.,100.,110.,100.]
+    p=Frames({('X','15m',10):f})
+    got=api('checklists').ChecklistReader(p).blocks('X')
+    assert [(b.direction,b.price_hi,b.price_lo,b.quality,b.bars_ago) for b in got]==[
+        ('שורט',110.,100.,'טוב',1),('לונג',110.,100.,'טוב',2)]
+
+
+def test_blocks_suppress_poor_vector_body_and_apply_lookback():
+    f=frame(n=43)
+    f.iloc[40]=[100.,110.,100.,108.,3.]
+    f.iloc[41]=[100.,110.,100.,102.,10.]
+    reader=api('checklists').ChecklistReader(Frames({('X','15m',10):f}))
+    assert [b.bars_ago for b in reader.blocks('X')]==[2]
+    assert reader.blocks('X',lookback=2)==[]
+
+
+@pytest.mark.parametrize('inverse',[False,True])
+def test_blocks_accept_actual_rising_tier_and_full_frame_atr(inverse):
+    f=frame(n=42)
+    f.iloc[35]=[100.,120.,80.,100.,1.]
+    f.iloc[40]=[100.,110.,100.,108.,1.6]
+    if inverse: f=mirror(f)
+    p=Frames({('X','15m',10):f})
+    got=api('checklists').ChecklistReader(p).blocks('X',lookback=2)
+    assert len(got)==1 and got[0].direction==('שורט' if inverse else 'לונג')
+    assert got[0].quality=='טוב'
+    # The forming row cannot be emitted but does contribute to original ATR.
+    f.iloc[-1,f.columns.get_loc('high')]=1000.
+    got=api('checklists').ChecklistReader(Frames({('X','15m',10):f})).blocks('X',lookback=2)
+    assert len(got)==1 and got[0].quality=='גבולי'
+
+
+@pytest.mark.parametrize('broken',[False,True])
+def test_brinks_checklist_composes_real_box_and_raw_timestamp_failure(broken):
+    box=frame(n=12,start='2026-09-09 14:00Z')
+    zones=frame(n=12)
+    zones.iloc[10]=[100.,102.,99.,102.,3.]
+    zones.iloc[11]=[102.,103.,99.,101.,1.]
+    p=Frames({('X','5m',2):box,('X','5m',10):OSError('missing zones') if broken else zones,
+        ('X','15m',3):frame(n=10,start='2026-09-09 00:00Z')})
+    got=api('checklists').ChecklistReader(p).brinks_read('X')
+    assert got.formed and (got.box_hi,got.box_lo)==(101.,99.) and got.swept_asia is None
+    if broken: assert got.internal_vectors is None and got.external_vectors is None
+    else:
+        assert got.internal_vectors==[dict(price=101.,kind='green',top=102.,bottom=100.)]
+        assert got.external_vectors==[]
+    assert p.calls==[('clock',),('X','5m',2),('X','5m',10),('X','15m',3)]

warning: in the working copy of 'docs/architecture/TREE-PATTERN-READERS-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/TREE-PATTERN-READERS-USAGE.md b/docs/architecture/TREE-PATTERN-READERS-USAGE.md
new file mode 100644
index 0000000..c166a59
--- /dev/null
+++ b/docs/architecture/TREE-PATTERN-READERS-USAGE.md
@@ -0,0 +1,40 @@
+# Original pattern readers (private offline interfaces)
+
+Spec: TREE-PATTERN-READERS-SOURCE-CONTRACT.md. Four instance readers under
+trading_system/tree_replay/_vendor preserve the pinned chart-desk calculations:
+
+- WmReader(source).detect(symbol,timeframe='15m') -> Formation or None.
+- LiquidityReader(source).pools(symbol,timeframe='15m') -> list[Pool];
+  run with the same arguments -> Run.
+- BrinksReader(source).today_box(symbol,now=None) -> Box or None.
+- ChecklistReader(source).rvc_gvc(symbol,timeframe='15m') -> RvcGvc or None;
+  blocks(symbol,timeframe='15m',lookback=60) -> list[Block];
+  brinks_read(symbol,timeframe='5m') -> BrinksRead.
+
+Supply fetch_corrected(symbol,timeframe,lookback)->(pandasFrame,correction)
+and now_utc()->aware UTC datetime. No production defaults exist. Each call gets
+its original request, including LiquidityReader.run's second fetch through
+the actual pools reader. ChecklistReader composes the actual BrinksReader;
+all vector calculations use real local PVSRA and vector memory, not final
+verdicts supplied by a provider. Lookback is a request, not proof of coverage.
+
+These raw ports do not validate causal market history. The caller must supply
+what the original reader could observe at the operation time, including its
+forming row. RVC and blocks exclude that row as a candidate; ATR/current close
+may still consume it. Source catches preserve None/empty results, which must
+not be mistaken for proven absence when building features later.
+
+Preserved source quirks: WM and liquidity use different swing priorities and
+plateau policies; WM's five-row vector window cannot warm up the ten-row PVSRA
+baseline. Brinks uses fixed UTC hours, accepts eight bars, and includes whole-
+frame current close. Its formatted range string is not an ISO timestamp;
+the actual composed checklist can fail parsing it and report swept_asia=None.
+This is documented baseline behavior, not a silently repaired trading rule.
+Original numerical thresholds, even those called open parameters by source
+comments, remain unchanged. Custom auction behavior is not implemented.
+
+Source/runtime reviews and component acceptance are required; read the latest
+exchange status. Implementation existence is not acceptance. No whole tree,
+causal replay, entry fill, economic label, dataset, model or live readiness is
+implied. Next work remains the options reader, full walk/builder/caller binding,
+remaining producers and economic simulation.

