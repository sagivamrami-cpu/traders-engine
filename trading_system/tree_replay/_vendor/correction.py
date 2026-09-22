from __future__ import annotations
from dataclasses import dataclass
import pandas as pd


@dataclass
class Correction:
    symbol: str
    offset: float                  # add to every OHLC value of the proxy feed
    source: str                    # tv_live | cash_hours | cached_stale | none
    confidence: str                # high | medium | low | unknown
    note: str
    # When source == "tv_spliced": the timestamp where genuine TV bars begin.
    # Bars at/after it are his chart's, exactly; bars before it are corrected
    # proxy, right in LEVEL but not guaranteed right in SHAPE.
    tv_from: "pd.Timestamp | None" = None

    def render(self) -> str:
        if self.source == "none":
            return f"⚠ {self.symbol}: {self.note}"
        if self.source == "mt5_broker":
            return f"✅ {self.symbol}: {self.note}"
        sign = "+" if self.offset >= 0 else ""
        return f"{self.symbol}: תוקן {sign}{self.offset:.1f} ({self.note})"

    @property
    def show(self) -> bool:
        """Whether a caller should print this line at all -- true for every
        correction that isn't a silent, nothing-to-report zero."""
        return bool(self.offset) or self.source in ("none", "mt5_broker")

    @property
    def unverified(self) -> bool:
        """True when a correction was NEEDED but none could be applied --
        the raw proxy price can be materially wrong (found live 2026-08-12:
        gold's no-correction fallback, taken when the TV tap isn't reachable,
        showed 4,468.7 against a real chart at ~4,407 -- a $61 gap, not the
        cents-level noise the rest of this module treats as negligible).
        Callers MUST NOT present this price as a plain, trustworthy headline,
        and must not compute derived precision (distances, levels) from it
        as if it were solid ground.

        Deliberately narrower than `source == "none"`: that value is also
        used for the benign case (crypto, spot-vs-spot, confidence "n/a") --
        correctly a zero offset because none is needed, not a failed lookup.
        Only confidence "unknown" means "a correction was needed and we
        couldn't get one" -- checking source alone flagged BTC as unverified
        too, a false positive caught in the same live test that found the
        gold bug.
        """
        return self.source == "none" and self.confidence == "unknown"


EXCHANGE_NATIVE = {"BINANCE:BTCUSDT"}


def broker_shape_ok_at(corr, days: float, *, decision_time) -> bool:
    """May a RANGE object looking `days` back trust this frame's shape?

    A constant offset shifts a level but never fixes a range, so range-shaped
    objects (ADR, RD, psy levels, session ranges, yesterday's extremes) need
    bars that are genuinely his. Pure broker sources qualify outright; a
    spliced frame qualifies only when its genuine-TV span reaches back at
    least `days` -- the window being measured must lie entirely on the TV side
    of the seam.
    """
    if corr is None:
        return False
    if corr.source in ("tv_daily", "mt5_broker"):
        return True
    # Exchange-native instruments are exempt, and this is not a loosening.
    #
    # The guard exists because gold and the Nasdaq are traded here as OTC CFDs
    # while their fallback bars come from COMEX/CME futures -- a genuinely
    # different instrument, measured at ~75% of spot's daily range, which no
    # constant offset repairs. BTC has no such gap: Binance IS the venue, its
    # bars ARE the tape, and there is no "his broker" version to prefer.
    #
    # Found 2026-08-24: with the MT5 export 90h stale, this returned False for
    # BTC and silently disabled `stretch.state()` and `rails.check()` on the one
    # instrument whose data is authoritative -- so the over-extension detector
    # Sagiv asked for could not speak about BTC at all.
    if corr.symbol in EXCHANGE_NATIVE:
        return True
    if corr.source == "tv_spliced" and corr.tv_from is not None:
        age_days = (pd.Timestamp(decision_time) - corr.tv_from).total_seconds() / 86400.0
        return age_days >= days
    return False
