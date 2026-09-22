"""Original stretch calculations over explicit local ports; not feed certification.

Actual dependency uses ADR14 and open +/- ADR/2; source prose is not the formula.
"""
from __future__ import annotations
from dataclasses import dataclass
from . import tr, ranges
BUDGET_MIN = 1.25
BEYOND_MIN = 0.0
BEYOND_EXTREME = 0.5
DEV_STRETCHED = 3.0

@dataclass
class Stretch:
    """How much of the day is already spent, measured from the open."""
    symbol: str
    close: float
    day_open: float
    adr: float
    budget_used: float
    rail_hi: float
    rail_lo: float
    beyond: float
    side: str | None
    devs: dict

    @property
    def is_extended(self) -> bool:
        """Budget spent AND price outside the open-anchored range."""
        return self.budget_used >= BUDGET_MIN and self.beyond > BEYOND_MIN

    @property
    def direction(self) -> str | None:
        """The direction the tape has overshot in, in Sagiv's vocabulary."""
        if not self.is_extended:
            return None
        return 'לונג' if self.side == 'up' else 'שורט'

    @property
    def max_dev(self) -> float:
        return max((abs(v) for v in self.devs.values()), default=0.0)

    def contradicts(self, direction: str) -> bool:
        """Does a call in `direction` mean 'keep going' on a tape already spent?

        Deliberately narrow. This is not "the trend is old" — it is the exact
        conjunction Sagiv named: the tools say continue, in the same direction
        the day has already overshot its own average range in.
        """
        return self.is_extended and direction == self.direction

    def line(self) -> str:
        """The one-line extension note that rides along with every alert."""
        word = 'מתיחה קיצונית' if self.beyond >= BEYOND_EXTREME else 'מתוח'
        rail = self.rail_hi if self.side == 'up' else self.rail_lo
        parts = [f"  ⚠ {word}: {self.budget_used:.0%} מ-ADR נוצל · {self.beyond:+.2f} ADR מעבר לפס {('העליון' if self.side == 'up' else 'התחתון')} ({rail:,.2f}, מפתיחת היום {self.day_open:,.2f})"]
        if self.max_dev >= DEV_STRETCHED:
            worst = max(self.devs.items(), key=lambda kv: abs(kv[1]))
            parts.append(f'     מרחק מהענן: {worst[1]:+.1f} ATR ({worst[0]}) — חלון פתוח, חוב שטרם נפרע')
        return '\n'.join(parts)

    def render(self) -> str:
        """Standalone block, for briefs that want the state on its own."""
        head = f"◈ {self.symbol.split(':')[-1]} — מצב מתיחה @ {self.close:,.2f}"
        if not self.is_extended:
            return f'{head}\n  תקציב יומי {self.budget_used:.0%} מ-ADR · בתוך הטווח מהפתיחה — אין מתיחה'
        return f'{head}\n{self.line()}'

def _atr(df, n: int=14) -> float:
    import pandas as pd
    prev = df['close'].shift(1)
    rng = pd.concat([df['high'] - df['low'], (df['high'] - prev).abs(), (df['low'] - prev).abs()], axis=1).max(axis=1)
    return float(rng.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])

class StretchReader:

    def __init__(self, source):
        self.source = source

    def _dev_from_cloud(self, symbol: str, tf: str, days: int) -> float | None:
        """Distance from the EMA50 cloud in ATRs — uncapped, unlike matrix's score."""
        try:
            df, _ = self.source.fetch_corrected(symbol, tf, days)
            if len(df) < 60:
                return None
            e = tr.emas(df)
            cloud = float(e['ema50'].iloc[-1])
            atr = _atr(df)
            if not atr:
                return None
            return (float(df['close'].iloc[-1]) - cloud) / atr
        except Exception:
            return None

    def state(self, symbol: str) -> Stretch | None:
        """Current extension state, or None when the inputs cannot support one."""
        try:
            daily, dcorr = self.source.fetch_corrected(symbol, '1d', 400)
            if daily.empty or not self.source.broker_shape_ok(dcorr, 20):
                return None
            lv = ranges.tr_levels(daily, ranges.weekly_from_daily(daily), broker_bars=True)
        except Exception:
            return None
        af = lv.get('adr_from_open') or {}
        if not (af.get('available') and af.get('verified')):
            return None
        adr = float(af.get('range') or 0)
        rail_hi, rail_lo = (af.get('high'), af.get('low'))
        if not adr or rail_hi is None or rail_lo is None:
            return None
        rail_hi, rail_lo = (float(rail_hi), float(rail_lo))
        today = daily.iloc[-1]
        day_open = float(today['open'])
        close = float(today['close'])
        budget = float(today['high'] - today['low']) / adr
        if close > rail_hi:
            beyond, side = ((close - rail_hi) / adr, 'up')
        elif close < rail_lo:
            beyond, side = ((rail_lo - close) / adr, 'down')
        else:
            beyond, side = (0.0, None)
        devs = {}
        for tf, days in (('15m', 20), ('1h', 60), ('4h', 240)):
            d = self._dev_from_cloud(symbol, tf, days)
            if d is not None:
                devs[tf] = d
        return Stretch(symbol=symbol, close=close, day_open=day_open, adr=adr, budget_used=budget, rail_hi=rail_hi, rail_lo=rail_lo, beyond=beyond, side=side, devs=devs)

