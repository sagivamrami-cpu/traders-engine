"""Pinned PENDING fill/cancel branch over supplied offline evidence only."""
from __future__ import annotations

from ..tree_revalidation import TreeRevalidation
from .lifecycle_bars import _entry_band
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions


class LifecyclePendingResolution:
    """Resolve one supplied PENDING record, stopping before OPEN progression."""

    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)
        self.revalidation = TreeRevalidation(source)

    def resolve(self, trade: dict, *, state: dict, price: float,
                bar_extremes: dict) -> tuple[list[tuple[str, bool]], bool]:
        """Return source-style messages and mutation status for one PENDING trade."""
        short = trade["direction"] == "\u05e9\u05d5\u05e8\u05d8"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        zone_low, zone_high = _entry_band(trade)
        low, high = bar_extremes.get(trade["symbol"], (price, price))
        touched = high >= zone_low if short else low <= zone_high
        if not touched:
            return ([], False)

        if self.outcomes.has_open(trade["symbol"], trade["direction"], state=state):
            why = "\u05e2\u05e1\u05e7\u05d4 \u05d0\u05d7\u05e8\u05ea \u05d1\u05d0\u05d5\u05ea\u05d5 \u05e0\u05db\u05e1 \u05d5\u05d1\u05d0\u05d5\u05ea\u05d5 \u05db\u05d9\u05d5\u05d5\u05df \u05db\u05d1\u05e8 \u05e4\u05e2\u05d9\u05dc\u05d4"
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "open_slot_conflict_at_fill"})
            return ([(message, trade["to_group"])], True)

        ok, why, verified = self.revalidation.revalidate_pending(trade)
        if not ok:
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "invalidated_at_fill"})
            return ([(message, trade["to_group"])], True)

        trade["state"] = "OPEN"
        trade["revalidation_verified"] = bool(verified)
        trade["fill_verification_reason"] = why or "verified"
        trade["filled_ts"] = trade["progress_ts"] = self.source.now_epoch()
        caveat = self.transitions._fill_caveat(why, verified)
        message = self.transitions._fill_line(trade, name, side) + caveat
        return ([(message, trade["to_group"])], True)
