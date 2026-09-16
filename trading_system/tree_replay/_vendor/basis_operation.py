import pandas as pd
from .correction import EXCHANGE_NATIVE


class BasisOperation:
    def __init__(self, source):
        self.source = source

    def fetch_corrected(self, symbol, timeframe, lookback):
        return self.source.fetch_corrected(symbol, timeframe, lookback)

    def now_utc(self):
        return self.source.now_utc()

    def broker_shape_ok(self, corr, days: float) -> bool:
        "May a RANGE object looking `days` back trust this frame's shape?\n\n    A constant offset shifts a level but never fixes a range, so range-shaped\n    objects (ADR, RD, psy levels, session ranges, yesterday's extremes) need\n    bars that are genuinely his. Pure broker sources qualify outright; a\n    spliced frame qualifies only when its genuine-TV span reaches back at\n    least `days` -- the window being measured must lie entirely on the TV side\n    of the seam.\n    "
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
            age_days = (pd.Timestamp(self.source.now_utc()) - corr.tv_from).total_seconds() / 86400.0
            return age_days >= days
        return False
