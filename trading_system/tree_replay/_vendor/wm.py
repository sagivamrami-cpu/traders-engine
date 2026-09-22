"""W and M formations, mechanically — the shape half of Tino's entry.

The course's criteria (Tino1 DB §4, [04 @ 05m49s-07m18s] for the W,
[05 @ 00m09s] for the M): two lows (highs) with the second holding at or above
(below) the first, a meaningful push between them, and confirmation when the
neckline — the middle peak (trough) — gives way. The tattoo variant adds a
vector at the second leg; vector presence is REPORTED here, judged by the agent.

This is a STATE READER, like everything else in the desk (the round-1/2
research verdicts bind here too): it says "a W is forming / confirmed", it never
says "buy". The tr-agent applies the five-point checklist on top; the trade
engine cites the shape as one reason among several. Registered SILENT so the
firing log accumulates — the promotion question is the setup-scientist's.

Geometry notes that keep this honest:
- swings are CONFIRMED fractals (k bars both sides, same k as matrix) — the
  freshest candidate that could still be redefined by the next bar is never
  used, the same rule `zones._last_swing` enforces;
- tolerance is in ATR units, not percent, so gold and BTC read the same;
- "confirmed" needs a CLOSE through the neckline, not a wick."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from . import pattern_tr as tr
SWING_K = 3
LEG_TOLERANCE_ATR = 0.5
MIN_HEIGHT_ATR = 0.8
MAX_AGE_BARS = 40

@dataclass
class Formation:
    symbol: str
    kind: str
    leg1: float
    leg2: float
    neckline: float
    close: float
    confirmed: bool
    vector_at_leg2: bool
    bars_since_leg2: int

    @property
    def direction(self) -> str:
        return 'לונג' if self.kind == 'W' else 'שורט'

    def line(self) -> str:
        state = 'מאושרת (סגירה מעבר לצוואר)' if self.confirmed else 'מתגבשת'
        vec = ' · וקטור ברגל השנייה (קעקוע)' if self.vector_at_leg2 else ''
        return f"תבנית {self.kind} {state}: רגליים {self.leg1:,.2f}/{self.leg2:,.2f} · צוואר {self.neckline:,.2f}{vec} [0{(4 if self.kind == 'W' else 5)} @ Tino1 §4]"

def _swings(df: pd.DataFrame, k: int=SWING_K):
    hi, lo = (df['high'].values, df['low'].values)
    highs, lows = ([], [])
    n = len(df)
    for i in range(k, n - k):
        w = slice(i - k, i + k + 1)
        if lo[i] == min(lo[w]):
            lows.append((i, float(lo[i])))
        elif hi[i] == max(hi[w]):
            highs.append((i, float(hi[i])))
    return (_dedup_pivots(highs, k), _dedup_pivots(lows, k))

def _dedup_pivots(pivots: list, k: int) -> list:
    """Collapse a plateau into ONE pivot.

    A flat extreme — several adjacent bars sharing the same low — satisfies
    `lo[i] == min(window)` on EVERY bar of the plateau, so the same physical
    pivot was returned two and three times. detect() then took `lows[-2:]`,
    got the SAME leg twice, found no swing high strictly between two adjacent
    indices, and returned None: a clean double-bottom whose second leg had a
    flat tip was silently invisible, live. Caught 2026-08-31 by the very first
    wm fixture ever run (tr-tree-v4/tests/test_wm_fixtures.py) — the reason
    the dataset plan makes fixtures a P0 that blocks everything.

    Adjacent entries (gap <= k bars) at the same extreme are one pivot; the
    LAST bar of the plateau keeps it — policy, not accident: bars_since_leg2
    measures from the plateau's END (its true age), and the vector check
    window sits where the leg actually finished forming. (Codex review asked
    for the policy to be explicit and tested.)
    """
    out: list = []
    for i, v in pivots:
        if out and i - out[-1][0] <= k and (abs(v - out[-1][1]) < 1e-09):
            out[-1] = (i, v)
            continue
        out.append((i, v))
    return out

class WmReader:

    def __init__(self, source):
        self.source = source

    def detect(self, symbol: str, timeframe: str='15m') -> Formation | None:
        """The freshest W or M on the frame, or None."""
        try:
            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
            if corr and getattr(corr, 'unverified', False) or len(df) < 30:
                return None
        except Exception:
            return None
        prev = df['close'].shift(1)
        rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
        atr = float(rng.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1]) or 1e-09
        highs, lows = _swings(df)
        close = float(df['close'].iloc[-1])
        n = len(df)

        def vec_near(i: int) -> bool:
            try:
                seg = df.iloc[max(0, i - 2):i + 3]
                pv = tr.pvsra(seg)
                if pv is None:
                    return False
                if isinstance(pv, dict):
                    return bool(pv.get('climax') or pv.get('vector'))
                return bool(pv['kind'].isin(('green', 'red')).any())
            except Exception:
                return False
        best = None
        if len(lows) >= 2:
            (i1, l1), (i2, l2) = (lows[-2], lows[-1])
            between = [h for j, h in highs if i1 < j < i2]
            if between and n - 1 - i2 <= MAX_AGE_BARS and (l2 >= l1 - LEG_TOLERANCE_ATR * atr):
                neck = max(between)
                if neck - max(l1, l2) >= MIN_HEIGHT_ATR * atr:
                    best = Formation(symbol, 'W', l1, l2, neck, close, confirmed=close > neck, vector_at_leg2=vec_near(i2), bars_since_leg2=n - 1 - i2)
        if len(highs) >= 2:
            (i1, h1), (i2, h2) = (highs[-2], highs[-1])
            between = [l for j, l in lows if i1 < j < i2]
            if between and n - 1 - i2 <= MAX_AGE_BARS and (h2 <= h1 + LEG_TOLERANCE_ATR * atr):
                neck = min(between)
                if min(h1, h2) - neck >= MIN_HEIGHT_ATR * atr:
                    m = Formation(symbol, 'M', h1, h2, neck, close, confirmed=close < neck, vector_at_leg2=vec_near(i2), bars_since_leg2=n - 1 - i2)
                    if best is None or m.bars_since_leg2 < best.bars_since_leg2:
                        best = m
        return best

