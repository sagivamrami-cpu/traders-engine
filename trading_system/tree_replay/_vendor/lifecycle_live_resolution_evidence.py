"""Private live-resolution evidence collection over supplied offline ports."""
import pandas as pd

from .lifecycle_live_evidence import LifecycleLiveEvidence


class LifecycleLiveResolutionEvidence:
    """Recover only prices and forming-bar extremes before resolver mutation."""

    FORCE_BAR_AGE_S = LifecycleLiveEvidence.FORCE_BAR_AGE_S

    def __init__(self, source):
        self.source = source

    def collect(self, state: dict) -> tuple[dict, dict]:
        """Return ``(prices, bar_extremes)`` for PENDING/OPEN supplied records."""
        prices = LifecycleLiveEvidence(self.source)._live_prices()
        bar_extremes = {}
        try:
            raw_quotes = self.source.quote_payload()
        except Exception:
            raw_quotes = {}
        now = self.source.now_epoch()
        symbols = {
            trade["symbol"]
            for trade in state.values()
            if trade.get("state") in ("PENDING", "OPEN")
        }
        for symbol in symbols:
            age = now - float((raw_quotes.get(symbol) or {}).get("ts", 0))
            if symbol in prices and age <= self.FORCE_BAR_AGE_S:
                continue
            try:
                bars, correction = self.source.fetch_corrected(symbol, "15m", 2)
                if correction is not None and (
                    getattr(correction, "unverified", False)
                    or getattr(correction, "source", "") == "tv_stale"
                ):
                    continue
                latest = pd.to_datetime(bars.index[-1], utc=True).timestamp()
                if symbol not in prices or latest > now - age:
                    bar_extremes[symbol] = (
                        float(bars["low"].iloc[-1]),
                        float(bars["high"].iloc[-1]),
                    )
                    prices[symbol] = float(bars["close"].iloc[-1])
            except Exception:
                continue
        return prices, bar_extremes
