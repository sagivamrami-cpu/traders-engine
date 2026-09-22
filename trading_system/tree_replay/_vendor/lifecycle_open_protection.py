"""Pinned conservative OPEN ambiguity protection over a supplied price window."""
from __future__ import annotations

from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions


class LifecycleOpenProtection:
    """Resolve only an unordered protective/target touch for one OPEN record."""

    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)

    def resolve(self, trade: dict, *, low: float, high: float) -> tuple[list[tuple[str, bool]], bool]:
        """Return the conservative terminal effect from one supplied post-fill window."""
        short = trade["direction"] == "שורט"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        protective = self.transitions._protective(trade, short)
        if not self.transitions._ambiguous_touch(trade, low, high, short, protective):
            return ([], False)

        self.transitions._mark_terminal(trade, "STOPPED" if not trade["hit"] else "DONE")
        message, result = self.transitions._resolve_ambiguous(trade, name, side)
        self.outcomes._outcome({**trade, "result": result})
        return ([(message, trade["to_group"])], True)
