"""Complete source EMA windows and reader over local inputs; not causal certification."""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from io import BytesIO
from pathlib import PurePosixPath
from . import indicators as I
MT5_SYMBOL_MAP = {'OANDA:XAUUSD': 'XAUUSD', 'OANDA:NAS100USD': 'NAS100', 'BINANCE:BTCUSDT': 'BTCUSD', 'TVC:VIX': 'VIX', 'TVC:DXY': 'DXY'}
LENGTHS = (5, 7, 13, 50, 200, 800)
FAST = (5, 7, 13)
SLOW = (50, 200, 800)
OPEN_ATR = 0.75
GLUED_ATR = 0.2
SLOPE_BARS = 3

@dataclass
class Window:
    length: int
    value: float
    distance: float
    atr: float
    slope_atr: float | None = None

    @property
    def atr_distance(self) -> float:
        return self.distance / self.atr if self.atr else 0.0

    @property
    def rising(self) -> bool | None:
        """Sign only, for callers that genuinely need a direction."""
        return None if self.slope_atr is None else self.slope_atr > 0

    @property
    def is_open(self) -> bool:
        return abs(self.atr_distance) >= OPEN_ATR

    @property
    def side(self) -> str:
        return 'מעל' if self.distance > 0 else 'מתחת'

    def render(self) -> str:
        state = 'פתוח' if self.is_open else 'סגור'
        return f'EMA{self.length}: {self.value:,.1f} · {abs(self.distance):,.1f} {self.side} ({abs(self.atr_distance):.1f} ATR) — חלון {state}'

@dataclass
class EmaState:
    symbol: str
    timeframe: str
    close: float
    atr: float
    windows: list[Window]
    unconverged: list[int] = field(default_factory=list)
    source: str = ''

    def window(self, length: int) -> Window | None:
        return next((w for w in self.windows if w.length == length), None)

    @property
    def trend_strict(self) -> str:
        """Price above 50 AND 200 AND 800 (his long test, stated with AND)."""
        need = [self.window(n) for n in SLOW]
        if any((w is None for w in need)):
            return 'לא ידוע'
        if all((w.distance > 0 for w in need)):
            return 'עולה'
        if all((w.distance < 0 for w in need)):
            return 'יורד'
        return 'מעורב'

    @property
    def trend_loose(self) -> str:
        """His short test as spoken: below the 50, the 200 OR the 800."""
        need = [self.window(n) for n in SLOW]
        if any((w is None for w in need)):
            return 'לא ידוע'
        if any((w.distance < 0 for w in need)):
            return 'יורד (מבחן רופף)'
        return 'עולה'

    @property
    def lost(self) -> list[int]:
        """Slow averages price is currently below — the cascade map (F-S08)."""
        return [n for n in SLOW if (w := self.window(n)) is not None and w.distance < 0]

    @property
    def cascade_next(self) -> int | None:
        """The next average DOWN the ladder after the ones already lost.

        Furman's rule (F-S08) is that losing an average hands price to the NEXT
        one, and the 800's reaction is the strong one. So the destination is
        the first slow EMA below everything already lost -- not the lost one
        itself, which is where a naive min() over `lost` lands and reads as
        "you lost the 50, so the target is the 50".
        """
        if not self.lost:
            return None
        deepest = max(self.lost)
        remaining = [n for n in SLOW if n > deepest]
        return remaining[0] if remaining else None

    @property
    def next_magnet(self) -> Window | None:
        """The nearest OPEN window — where the unfinished business sits."""
        opens = [w for w in self.windows if w.is_open]
        return min(opens, key=lambda w: abs(w.atr_distance)) if opens else None

    @property
    def slope_agreement(self) -> float | None:
        """How much of the fan is sloping the SAME way, from -1 to +1.

        Sagiv, 2026-08-31, reading BTC: *"הממוצעים עם שיפוע אגרסיבי למטה ויש
        גם סדר של 4 ממוצעים לשורט."* Order and slope are two different facts —
        a fan can be stacked for a short while every average is turning up
        under it — and the desk only ever had the order. null when no average
        could be measured, never 0.0, which would read as "perfectly split".

        MAGNITUDE-WEIGHTED, on GPT's finding: counting signs let slopes of
        [+10.0, -0.01, -0.01] report -0.33 while `slope_strength` reported
        0.01, so between them neither output mentioned the +10 that was
        actually driving the fan. Weighting by size makes one decisive average
        outweigh two that have barely moved, and a genuinely flat average
        contributes nothing instead of counting as a vote against.
        """
        vals = [w.slope_atr for w in self.windows if w.slope_atr is not None]
        if not vals:
            return None
        total = sum((abs(v) for v in vals))
        return sum(vals) / total if total else 0.0

    @property
    def slope_coverage(self) -> float:
        """Share of the fan whose slope could actually be measured.

        Without it an agreement of -1.0 read the same whether six averages
        agreed or one was measured and five were unconverged -- and 4h/1h are
        exactly where the 800 goes missing. The reading and its confidence
        travel together.
        """
        return len([w for w in self.windows if w.slope_atr is not None]) / len(LENGTHS)

    @property
    def slope_strength(self) -> float | None:
        """Median absolute slope across the fan, in ATRs.

        The magnitude half of the same reading: `slope_agreement` says whether
        the averages point one way, this says how hard. Kept continuous — ?4
        forbids freezing a threshold for "aggressive" before it is calibrated
        walk-forward, so nothing here labels the number.
        """
        vals = sorted((abs(w.slope_atr) for w in self.windows if w.slope_atr is not None))
        if not vals:
            return None
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    @property
    def cascade_gap(self) -> tuple[int, float] | None:
        """(length, ATRs) of the gap to the cascade's next average.

        His thesis on BTC: four averages stacked for a short, only the 800
        below, so price goes and closes the distance to it. `cascade_next`
        already named that destination; nothing measured how far away it was,
        which is the number that decides whether the move is worth a trade.
        """
        n = self.cascade_next
        if n is None:
            return None
        w = self.window(n)
        if w is None or not self.atr or self.atr <= 0:
            return None
        return (n, w.atr_distance)

    def glued(self, fast_length: int=5) -> tuple[bool, float]:
        """Are the fast EMAs stacked on top of each other? (F-S12)

        `fast_length` is 5 for Tino's set, 7 for Furman's -- the answer can
        legitimately differ between them, which is why the caller chooses.
        """
        a, b = (self.window(fast_length), self.window(13))
        if a is None or b is None or (not self.atr):
            return (False, 0.0)
        gap = abs(a.value - b.value) / self.atr
        return (gap <= GLUED_ATR, gap)

    @property
    def stack_order(self) -> str:
        """Are the slow averages themselves in trend order?

        This is YS2's state variable: 50 above 200 above 800 means every
        horizon agrees, and the last crossing completing that order is the
        regime flip itself.

        The label names the EMAs that were ACTUALLY compared. Caught 2026-08-13
        on gold 4h: EMA800 sat in `unconverged`, only 50 and 200 were compared,
        and the string still read "(50>200>800)" -- a two-EMA fact printed as a
        three-EMA claim. Any bias taken from that string rested on an average
        that does not exist yet. `trend_strict` had the gap right all along;
        only this label lied.
        """
        vals = [(n, w.value) for n in SLOW if (w := self.window(n)) is not None]
        if len(vals) < 2:
            return 'לא ידוע'
        names = [n for n, _ in vals]
        order = [v for _, v in vals]
        partial = '' if len(vals) == len(SLOW) else ' — חלקית'
        if all((order[i] > order[i + 1] for i in range(len(order) - 1))):
            return f"מסודרת שורית ({'>'.join((str(n) for n in names))}){partial}"
        if all((order[i] < order[i + 1] for i in range(len(order) - 1))):
            return f"מסודרת דובית ({'<'.join((str(n) for n in names))}){partial}"
        return 'לא מסודרת — הערימה מעורבבת'

    def render(self) -> str:
        lines = [f"◈ {self.symbol.split(':')[-1]} {self.timeframe} @ {self.close:,.1f}"]
        lines.append(f'  מגמה (מבחן קפדני): {self.trend_strict} · ערימה: {self.stack_order}')
        for w in self.windows:
            lines.append('  ' + w.render())
        if self.unconverged:
            lines.append(f"  ⚠ לא התכנסו (אין מספיק היסטוריה): {', '.join((f'EMA{n}' for n in self.unconverged))}")
        return '\n'.join(lines)

def _atr(df: pd.DataFrame, n: int=14) -> float:
    prev = df['close'].shift(1)
    trng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
    return float(trng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])

def _read_with_deep(df, deep, symbol: str, timeframe: str, source: str='') -> EmaState:
    """Build the state from bars already in hand — the testable half.

    Split out of read() so the window and slope arithmetic can be driven with
    constructed frames. Every other test injects a finished Window, so before
    this existed the whole slope block could have been deleted and the suite
    would still have reported OK (GPT, reviewing a1fa0c8).
    """
    close = float(df['close'].iloc[-1])
    atr = _atr(df)
    windows, unconverged = ([], [])
    for n in LENGTHS:
        src = df
        if len(df) < 2 * n and deep is not None:
            head = deep[deep.index < df.index[0]]
            if len(head):
                src = pd.concat([head, df])
                src = src[~src.index.duplicated(keep='last')].sort_index()
        if len(src) < 2 * n:
            unconverged.append(n)
            continue
        series = I.ema(src['close'], n)
        val = float(series.iloc[-1])
        if val != val:
            unconverged.append(n)
            continue
        slope = None
        if len(series) > SLOPE_BARS:
            prev = float(series.iloc[-1 - SLOPE_BARS])
            span_atr = _atr(src.tail(2 * SLOPE_BARS + 14)) if len(src) > 20 else atr
            if prev == prev and span_atr and (span_atr > 0):
                slope = (val - prev) / span_atr
        windows.append(Window(n, val, close - val, atr, slope_atr=slope))
    return EmaState(symbol=symbol, timeframe=timeframe, close=close, atr=atr, windows=windows, unconverged=unconverged, source=source)

class EmaReader:

    def __init__(self, source):
        self.source = source

    def read(self, symbol: str, timeframe: str, lookback: int | None=None) -> EmaState:
        """Mechanical EMA state for one symbol on one timeframe."""
        lookback = lookback or {'1d': 2200, '4h': 2000, '1h': 2000, '15m': 2000, '5m': 2000}.get(timeframe, 2000)
        df, corr = self.source.fetch_corrected(symbol, timeframe, lookback)
        deep = None
        try:
            _dp = PurePosixPath('.') / 'deep' / f"{MT5_SYMBOL_MAP.get(symbol, '')}_{ {'4h': 'H4', '1h': 'H1', '15m': 'M15'}.get(timeframe, '')}.csv"
            if _dp.name.startswith('_') is False and self.source.deep_exists(_dp.as_posix()):
                _d = pd.read_csv(BytesIO(self.source.deep_bytes(_dp.as_posix())))
                _d['time'] = pd.to_datetime(_d['time'], utc=True)
                deep = _d.set_index('time').sort_index()
        except Exception:
            deep = None
        return _read_with_deep(df, deep, symbol, timeframe, source=corr.source if corr else '')

    def read_stack(self, symbol: str, timeframes=('4h', '1h', '15m', '5m')) -> dict[str, EmaState]:
        out = {}
        for tf in timeframes:
            try:
                out[tf] = self.read(symbol, tf)
            except Exception:
                continue
        return out
