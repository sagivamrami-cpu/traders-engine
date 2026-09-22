"""Pinned live PENDING/OPEN resolver composition over supplied offline ports."""
from __future__ import annotations

import pandas as pd

from .lifecycle_live_evidence import LifecycleLiveEvidence
from .lifecycle_open_minimum_success import LifecycleOpenMinimumSuccess
from .lifecycle_open_ordinary_resolution import LifecycleOpenOrdinaryResolution
from .lifecycle_open_postfill_evidence import LifecycleOpenPostfillEvidence
from .lifecycle_open_protection import LifecycleOpenProtection
from .lifecycle_open_zone_return import LifecycleOpenZoneReturn
from .lifecycle_pending_resolution import LifecyclePendingResolution


class LifecycleLiveResolver:
    """Compose accepted live-resolution children in retained source order."""

    FORCE_BAR_AGE_S = LifecycleLiveEvidence.FORCE_BAR_AGE_S

    def __init__(self, source):
        self.source = source
        self.pending = LifecyclePendingResolution(source)
        self.postfill = LifecycleOpenPostfillEvidence(source)
        self.minimum = LifecycleOpenMinimumSuccess(source)
        self.protection = LifecycleOpenProtection(source)
        self.ordinary = LifecycleOpenOrdinaryResolution(source)
        self.zone_return = LifecycleOpenZoneReturn(source)

    def _observation(self, state: dict) -> tuple[dict, dict, dict]:
        """Return the source's two-read quote snapshot and corrected range facts."""
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
        return prices, bar_extremes, raw_quotes

    def resolve(self, state: dict) -> tuple[list[tuple[str, bool]], bool]:
        """Resolve supplied live records without persistence, delivery, or loading."""
        prices, bar_extremes, raw_quotes = self._observation(state)
        if not prices:
            return [], False

        messages: list[tuple[str, bool]] = []
        changed = False
        for _key, trade in list(state.items()):
            if trade.get("state") in ("STOPPED", "DONE", "CANCELLED"):
                continue
            symbol = trade["symbol"]
            if symbol not in prices:
                continue
            spot = prices[symbol]

            if trade.get("state") == "PENDING":
                child_messages, child_changed = self.pending.resolve(
                    trade, state=state, price=spot, bar_extremes=bar_extremes
                )
                messages.extend(child_messages)
                changed = changed or child_changed
                if trade.get("state") == "CANCELLED":
                    continue

            if trade.get("state") != "OPEN":
                continue
            low, high, provisional_minimum = self.postfill.collect(trade, spot)
            child_messages, child_changed, minimum_message = self.minimum.resolve(
                trade,
                low=low,
                high=high,
                spot=spot,
                quote=raw_quotes.get(symbol) or {},
                has_bar_extremes=symbol in bar_extremes,
                minimum_message=provisional_minimum,
            )
            messages.extend(child_messages)
            changed = changed or child_changed

            child_messages, child_changed = self.protection.resolve(trade, low=low, high=high)
            messages.extend(child_messages)
            changed = changed or child_changed
            if child_changed:
                continue

            child_messages, child_changed = self.ordinary.resolve(
                trade, low=low, high=high, minimum_message=minimum_message
            )
            messages.extend(child_messages)
            changed = changed or child_changed
            if trade.get("state") == "OPEN":
                child_messages, child_changed = self.zone_return.resolve(trade, spot=spot)
                messages.extend(child_messages)
                changed = changed or child_changed

        return messages, changed
