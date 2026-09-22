"""Pinned closed-bar PENDING lifecycle branch over caller-supplied evidence only."""
from __future__ import annotations

from ..tree_revalidation import TreeRevalidation
from . import lifecycle_voice as voice
from .lifecycle_bars import _entry_band
from .lifecycle_outcome_shelf import LifecycleOutcomeShelf
from .lifecycle_transitions import LifecycleTransitions


class LifecycleClosedPendingResolution:
    """Resolve one PENDING record before the caller enters any OPEN branch."""

    def __init__(self, source):
        self.source = source
        self.outcomes = LifecycleOutcomeShelf(source)
        self.transitions = LifecycleTransitions(source)
        self.revalidation = TreeRevalidation(source)

    def resolve(self, trade: dict, *, state: dict, since, high: float, low: float,
                now: float) -> tuple[list[tuple[str, bool]], bool]:
        """Return messages and changed state for the closed-bar PENDING slice."""
        if trade.get("state") != "PENDING":
            return ([], False)

        short = trade["direction"] == "שורט"
        name = trade["symbol"].split(":")[-1]
        side = "SELL" if short else "BUY"
        zone_low, zone_high = _entry_band(trade)
        touched_entry = high >= zone_low if short else low <= zone_high
        touched_stop = high >= float(trade["stop"]) if short else low <= float(trade["stop"])

        if (float(now) - float(trade["ts"])) > self.outcomes._expire_h(trade) * 3600 and not touched_entry:
            self.transitions._mark_terminal(trade, "CANCELLED")
            risk = abs(float(trade["entry"]) - float(trade["stop"])) or 1e-9
            start = float(since["open"].iloc[0])
            ran = (start - float(low)) if short else (float(high) - start)
            missed_r = ran / risk
            extra = ""
            if missed_r >= 1.0:
                extra = (f"\nהכיוון היה נכון: המחיר רץ {voice.dist(trade['symbol'], ran)} "
                         f"({missed_r:.1f}R) לכיוון העסקה בלי לגעת בכניסה.")
            message = (voice.head("✖️", trade["symbol"], trade["direction"], trade["entry"], "פגה")
                       + f"\nהכניסה לא מומשה תוך {self.outcomes._expire_h(trade):.0f} שעות."
                       + extra)
            self.outcomes._outcome({**trade, "result": "expired",
                                    "missed_r": round(missed_r, 2),
                                    "missed_points": round(ran, 2)})
            self.outcomes._shelve(trade)
            return ([(message, trade["to_group"])], True)

        if not touched_entry:
            return ([], False)

        if self.outcomes.has_open(trade["symbol"], trade["direction"], state=state):
            why = "עסקה אחרת באותו נכס ובאותו כיוון כבר פעילה"
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "open_slot_conflict_at_fill"})
            return ([(message, trade["to_group"])], True)

        ok, why, verified = self.revalidation.revalidate_pending(trade, now=now)
        if not ok:
            self.transitions._mark_terminal(trade, "CANCELLED")
            message = self.transitions._cancel_line(trade, why)
            self.outcomes._outcome({**trade, "result": "invalidated_at_fill"})
            return ([(message, trade["to_group"])], True)

        trade["state"] = "OPEN"
        trade["revalidation_verified"] = bool(verified)
        trade["fill_verification_reason"] = why or "verified"
        trade["filled_ts"] = trade["progress_ts"] = self.source.now_epoch()
        note = self.transitions._fill_caveat(why, verified)
        if touched_stop:
            self.transitions._mark_terminal(trade, "STOPPED")
            message = (voice.head("🛑", trade["symbol"], trade["direction"], trade["entry"],
                                  f"סטופ @ {float(trade['stop']):,.2f}")
                       + "\nהכניסה והסטופ נגעו באותו חלון — במקרה כזה אנחנו סופרים סטופ (השמרני).")
            self.outcomes._outcome({**trade, "result": "stopped_ambiguous"})
            return ([(message, trade["to_group"])], True)

        message = self.transitions._fill_line(trade, name, side) + note
        return ([(message, trade["to_group"])], True)
