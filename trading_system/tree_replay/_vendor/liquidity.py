"""Liquidity pools — equal highs/lows, and the run that takes them.

TR-TREE-V2 layer 6 (STRUCTURE & LIQUIDITY) asks for three objects this desk did
not have: **EQH/EQL**, **Stop Run**, and **Liquidity Run** — with an explicit
`[WELD]` mark on the tree saying pools of liquidity are the union of
liquidations AND unrecovered vectors, and that a Liquidity Run is *"מהלך מהיר
שמאשש וקטור"* — speed plus recovery, not speed alone.

**Why equal extremes are the object and not "a level".** A level is where price
reacted once. An equal high is where price reacted TWICE at the same price,
which means resting stops accumulated above it — the pool the method's whole
market-maker premise is about (*"what is the market maker trying to make the
retail trader think?"* `[01 @ 00m51s]`). The tree puts it under liquidity for
that reason, not under levels.

**Tolerance is in ATR, not ticks or percent**, so gold at 4,600 and BTC at
80,000 mean the same thing by "equal". Two highs within `EQ_TOL_ATR` of each
other count as equal; more than two is a stronger pool and is reported as such.

**A run is speed AND recovery.** `Run.detected` requires both: the move covers
`RUN_ATR` inside `RUN_BARS`, and it takes out a pool on the way. A fast move
that takes nothing is expansion, not a liquidity run, and calling it one would
manufacture the method's most important signal out of ordinary momentum.

Nothing here is measured. It reports structure; the tree decides.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
EQ_TOL_ATR = 0.25
LOOKBACK = 120
SWING_K = 3
RUN_ATR = 1.5
RUN_BARS = 4

@dataclass
class Pool:
    """Equal highs or lows — resting stops, in the method's reading."""
    side: str
    price: float
    touches: int
    bars_ago: int
    swept: bool

    @property
    def strength(self) -> str:
        return 'חזק' if self.touches >= 3 else 'רגיל'

    def line(self) -> str:
        what = 'שיאים שווים' if self.side == 'high' else 'שפלים שווים'
        state = 'נסחף' if self.swept else 'לא נסחף'
        return f'{what} @ {self.price:,.2f} · {self.touches} נגיעות ({self.strength}) · {state}'

@dataclass
class Run:
    """A liquidity run: speed AND a pool taken."""
    detected: bool
    direction: str | None = None
    pool: Pool | None = None
    atr_covered: float = 0.0
    bars: int = 0

    def line(self) -> str:
        if not self.detected:
            return 'אין ריצת נזילות'
        return f"ריצת נזילות {self.direction} — {self.atr_covered:.1f} ATR ב-{self.bars} נרות, לקחה {(self.pool.line() if self.pool else '?')}"

def _atr(df: pd.DataFrame, n: int=14) -> float:
    prev = df['close'].shift(1)
    rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
    return float(rng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])

def _swings(df: pd.DataFrame, k: int=SWING_K):
    hi, lo = (df['high'].values, df['low'].values)
    highs, lows = ([], [])
    for i in range(k, len(df) - k):
        w = slice(i - k, i + k + 1)
        if hi[i] == max(hi[w]):
            highs.append((i, float(hi[i])))
        elif lo[i] == min(lo[w]):
            lows.append((i, float(lo[i])))
    return (highs, lows)

class LiquidityReader:

    def __init__(self, source):
        self.source = source

    def pools(self, symbol: str, timeframe: str='15m') -> list[Pool]:
        """Equal-extreme pools on the frame, newest first."""
        try:
            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
            if corr and getattr(corr, 'unverified', False) or len(df) < 40:
                return []
        except Exception:
            return []
        df = df.iloc[-LOOKBACK:]
        atr = _atr(df) or 1e-09
        tol = EQ_TOL_ATR * atr
        n = len(df)
        highs, lows = _swings(df)
        out: list[Pool] = []
        for side, pts in (('high', highs), ('low', lows)):
            used = set()
            for i, (idx, px) in enumerate(pts):
                if idx in used:
                    continue
                group = [(idx, px)]
                for jdx, jpx in pts[i + 1:]:
                    if abs(jpx - px) <= tol:
                        group.append((jdx, jpx))
                        used.add(jdx)
                if len(group) < 2:
                    continue
                level = sum((p for _, p in group)) / len(group)
                newest = max((g for g, _ in group))
                after = df.iloc[newest + 1:]
                swept = bool(len(after) and ((after['high'] > level + tol).any() if side == 'high' else (after['low'] < level - tol).any()))
                out.append(Pool(side=side, price=level, touches=len(group), bars_ago=n - 1 - newest, swept=swept))
        out.sort(key=lambda p: p.bars_ago)
        return out

    def run(self, symbol: str, timeframe: str='15m') -> Run:
        """Was there a liquidity run — speed AND a pool taken — just now?"""
        try:
            df, corr = self.source.fetch_corrected(symbol, timeframe, 10)
            if corr and getattr(corr, 'unverified', False) or len(df) < 40:
                return Run(detected=False)
        except Exception:
            return Run(detected=False)
        atr = _atr(df) or 1e-09
        seg = df.iloc[-(RUN_BARS + 1):-1]
        if len(seg) < 2:
            return Run(detected=False)
        covered = (float(seg['high'].max()) - float(seg['low'].min())) / atr
        if covered < RUN_ATR:
            return Run(detected=False)
        direction = 'לונג' if float(seg['close'].iloc[-1]) > float(seg['open'].iloc[0]) else 'שורט'
        taken = None
        for p in self.pools(symbol, timeframe):
            if not p.swept:
                continue
            lo, hi = (float(seg['low'].min()), float(seg['high'].max()))
            if lo <= p.price <= hi:
                taken = p
                break
        if taken is None:
            return Run(detected=False)
        return Run(detected=True, direction=direction, pool=taken, atr_covered=covered, bars=len(seg))

