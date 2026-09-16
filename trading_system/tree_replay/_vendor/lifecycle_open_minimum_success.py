"""Pinned OPEN minimum-success branch over supplied post-fill evidence."""
from __future__ import annotations

from .desk_success import DeskSuccess, minimum
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions


class LifecycleOpenMinimumSuccess:
    """Project source minimum success without acquiring evidence or resolving OPEN state."""

    FORCE_BAR_AGE_S = 120.0

    def __init__(self, source):
        self.source = source
        self.desk_success = DeskSuccess(source)
        self.transitions = LifecycleTransitions(source)
        self.outcomes = LifecycleOutcomeShelf(source)

    def resolve(self, trade: dict, *, low: float, high: float, spot: float,
                quote: dict, has_bar_extremes: bool,
                minimum_message: str | None) -> tuple[list[tuple[str, bool]], bool, str | None]:
        """Return source-ordered minimum messages, change flag, and observed message."""
        short = trade["direction"] == "\u05e9\u05d5\u05e8\u05d8"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective
        quote_ts = float(quote.get("price_ts") or quote.get("ts") or 0)
        if (not minimum_message and not hit_protect and not has_bar_extremes
                and quote.get("lp") == spot
                and 0 <= self.source.now_epoch() - quote_ts <= self.FORCE_BAR_AGE_S
                and quote_ts >= float(trade.get("filled_ts") or self.source.now_epoch())):
            minimum_message = self.desk_success.observe(
                trade, spot, quote_ts, "exact_venue_quote"
            )

        if not minimum_message:
            return [], False, minimum_message

        steps = self.transitions._progress_steps(trade, low if short else high, short)
        if steps and not hit_protect:
            trade["progress_step"] = steps[-1][0]
        trade["reported_progress_points"] = minimum(trade["symbol"])
        messages = [(minimum_message, trade["to_group"])]
        self.outcomes._outcome({**trade, "result": "minimum_success"})
        return messages, True, minimum_message
