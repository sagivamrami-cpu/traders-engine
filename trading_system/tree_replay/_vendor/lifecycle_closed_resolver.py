"""Pinned closed-bar lifecycle composition over caller-supplied mutable state."""
from __future__ import annotations

import pandas as pd

from .desk_success import DeskSuccess, minimum
from .lifecycle_bars import _open_extremes
from .lifecycle_closed_pending_resolution import LifecycleClosedPendingResolution
from .lifecycle_open_ordinary_resolution import LifecycleOpenOrdinaryResolution
from .lifecycle_open_protection import LifecycleOpenProtection
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions


class LifecycleClosedResolver:
    """Resolve the retained closed 15-minute-bar branch without persistence or delivery."""

    TERMINAL = ("STOPPED", "DONE", "CANCELLED")

    def __init__(self, source):
        self.source = source
        self.pending = LifecycleClosedPendingResolution(source)
        self.desk_success = DeskSuccess(source)
        self.protection = LifecycleOpenProtection(source)
        self.ordinary = LifecycleOpenOrdinaryResolution(source)
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)

    def _resolve_closed_open(self, trade: dict, *, since, low: float, high: float):
        """Apply the retained closed-bar OPEN ordering to one post-fill window."""
        short = trade["direction"] == "שורט"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective
        minimum_message = self.desk_success.observe_bars(trade, since)

        messages: list[tuple[str, bool]] = []
        changed = False
        if minimum_message:
            steps = self.transitions._progress_steps(trade, low if short else high, short)
            if steps and not hit_protect:
                trade["progress_step"] = steps[-1][0]
            trade["reported_progress_points"] = minimum(trade["symbol"])
            messages.append((minimum_message, trade["to_group"]))
            self.outcomes._outcome({**trade, "result": "minimum_success"})
            changed = True

        child_messages, child_changed = self.protection.resolve(trade, low=low, high=high)
        messages.extend(child_messages)
        changed = changed or child_changed
        if child_changed:
            return messages, changed

        child_messages, child_changed = self.ordinary.resolve(
            trade, low=low, high=high, minimum_message=minimum_message
        )
        messages.extend(child_messages)
        return messages, changed or child_changed

    def resolve(self, state: dict, *, now: float) -> tuple[list[tuple[str, bool]], bool]:
        """Advance all supplied nonterminal records from corrected closed bars at one pass clock."""
        messages: list[tuple[str, bool]] = []
        changed = False
        for _key, trade in list(state.items()):
            if trade.get("state") in self.TERMINAL:
                continue
            try:
                frame, correction = self.source.fetch_corrected(trade["symbol"], "15m", 3)
                if correction is not None and (
                    getattr(correction, "unverified", False)
                    or getattr(correction, "source", "") == "tv_stale"
                ):
                    continue
            except Exception:
                continue

            timestamps = pd.to_datetime(frame.index, utc=True)
            since = frame[[timestamp.timestamp() > float(trade["ts"]) for timestamp in timestamps]]
            if since.empty:
                continue
            high = float(since["high"].max())
            low = float(since["low"].min())
            extrema = _open_extremes(since, trade)
            post_fill_high, post_fill_low = extrema or (float(trade["entry"]),) * 2

            child_messages, child_changed = self.pending.resolve(
                trade, state=state, since=since, high=high, low=low, now=now
            )
            messages.extend(child_messages)
            changed = changed or child_changed
            if trade.get("state") != "OPEN":
                continue

            child_messages, child_changed = self._resolve_closed_open(
                trade, since=since, high=post_fill_high, low=post_fill_low
            )
            messages.extend(child_messages)
            changed = changed or child_changed

        return messages, changed
