"""Pinned ordinary OPEN resolution over one caller-supplied price window."""
from __future__ import annotations

from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions


class LifecycleOpenOrdinaryResolution:
    """Project the post-ambiguity OPEN branch without acquiring live evidence."""

    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)

    def resolve(self, trade: dict, *, low: float, high: float,
                minimum_message) -> tuple[list[tuple[str, bool]], bool]:
        """Return source-ordered ordinary effects for one supplied OPEN trade."""
        short = trade["direction"] == "שורט"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        protective = self.transitions._protective(trade, short)
        hit_protect = high >= protective if short else low <= protective

        tp1_now = False
        if trade["targets"]:
            target_one = float(trade["targets"][0][1])
            tp1_now = low <= target_one if short else high >= target_one
        progress = ([] if (hit_protect or minimum_message or tp1_now or "TP1" in trade["hit"])
                    else self.transitions._progress_messages(
                        trade, low if short else high, short, name, side))

        messages: list[tuple[str, bool]] = []
        changed = False
        if progress:
            messages.extend(progress)
            trade["progress_ts"] = self.source.now_epoch()
            changed = True

        for index, (_target_name, target_price) in enumerate(trade["targets"], 1):
            tag = f"TP{index}"
            if tag in trade["hit"]:
                continue
            if low <= target_price if short else high >= target_price:
                trade["hit"].append(tag)
                trade["progress_ts"] = self.source.now_epoch()
                changed = True
                messages.append((self.transitions._target_line(
                    trade, index, tag, target_price), trade["to_group"]))
                self.outcomes._outcome({**trade, "result": tag.lower()})

        hit_protect = high >= protective if short else low <= protective
        if len(trade["hit"]) >= len(trade["targets"]):
            self.transitions._mark_terminal(trade, "DONE")
            changed = True
        elif hit_protect:
            message, result, state = self.transitions._resolve_protective(trade, name, side)
            self.transitions._mark_terminal(trade, state)
            changed = True
            messages.append((message, trade["to_group"]))
            self.outcomes._outcome({**trade, "result": result})

        return messages, changed
