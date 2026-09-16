"""Private live-evidence helpers over explicit offline inputs only."""
import math

import pandas as pd


class LifecycleLiveEvidence:
    def __init__(self, source):
        self.source = source

    QUOTE_MAX_AGE_S = 420.0

    def _live_prices(self) -> dict:
        """Spot from HIS TradingView tap, only while genuinely fresh."""
        out = {}
        try:
            d = self.source.quote_payload()
        except Exception:
            return out
        now = self.source.now_epoch()
        for sym, q in d.items():
            try:
                price = float(q.get('lp', 0))
                age = now - float(q.get('ts', 0))
                if math.isfinite(price) and price > 0 and 0 <= age <= self.QUOTE_MAX_AGE_S:
                    out[sym] = price
            except Exception:
                continue
        return out

    def _historical_replay_safe(self, df, corr, t: dict) -> bool:
        """May an OPEN trade recover lifecycle facts from a stale exact tape?

        ``tv_stale`` means the tape cannot describe *now*.  It does not erase a
        timestamped bar that arrived after an already-known fill.  This narrow
        exception exists only for OPEN positions and only when the file contains
        a bar at/after the persisted fill stamp.  It is never used to fill a
        PENDING plan and never substitutes the stale close for a live quote.

        The distinction matters after a collector outage: once the missing bars
        are restored, a TP/stop wick is a historical fact even if the market has
        already moved away from it.  Before this gate the blanket ``tv_stale``
        check discarded those restored extremes, so quote_pump could report later
        progress while leaving an earlier TP absent forever.
        """
        if t.get("state") != "OPEN" or df is None or getattr(df, "empty", True):
            return False
        if corr is not None and getattr(corr, "unverified", False):
            return False
        try:
            latest = pd.to_datetime(df.index[-1], utc=True).timestamp()
            filled = float(t.get("filled_ts") or t["ts"])
            return latest >= filled
        except (IndexError, KeyError, TypeError, ValueError):
            return False

    FORCE_BAR_AGE_S = 120.0
