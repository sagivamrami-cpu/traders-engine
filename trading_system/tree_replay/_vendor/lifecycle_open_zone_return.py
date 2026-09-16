"""Pinned OPEN zone-return notification over one caller-supplied spot price."""
from __future__ import annotations

from . import lifecycle_voice as voice
from .lifecycle_bars import _entry_band
from .lifecycle_transitions import LifecycleTransitions
from .revalidation import Revalidation


_ZONE_UNVERIFIED = "\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05dc\u05d0 \u05d0\u05d5\u05de\u05ea\u05d5 \u05de\u05d7\u05d3\u05e9 \u2014 \u05d0\u05d9\u05df \u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05d8\u05e8\u05d9\u05d9\u05dd."


class LifecycleOpenZoneReturn:
    """Construct one advisory return-to-entry notice; never resolve the trade."""

    def __init__(self, source):
        self.source = source
        self.transitions = LifecycleTransitions(source)
        self.revalidation = Revalidation(source)

    def _excursion(self, trade: dict) -> str:
        step = max(
            int(trade.get("progress_step") or 0),
            int(self.transitions.desk_success.reached(trade)),
        )
        return f"{step}/{len(trade.get('hit') or [])}"

    def _entry_recheck(self, trade: dict) -> str:
        try:
            ok, why, verified = self.revalidation.still_valid(trade)
        except Exception:
            ok, why, verified = True, "", False
        why = self.transitions._no_score(why)
        if not ok and not verified:
            return _ZONE_UNVERIFIED
        if ok:
            return (
                voice.check("\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05e2\u05d3\u05d9\u05d9\u05df \u05de\u05ea\u05e7\u05d9\u05d9\u05de\u05d9\u05dd", True)
                + (f"\n{why}" if why else "")
                + ("" if verified else f"\n{_ZONE_UNVERIFIED}")
            )
        return (
            voice.check("\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05dc\u05d0 \u05de\u05ea\u05e7\u05d9\u05d9\u05de\u05d9\u05dd \u05db\u05e2\u05ea", False)
            + (f"\n{why}" if why else "")
        )

    def _zone_return_message(self, trade: dict, spot: float, short: bool) -> str | None:
        gone = self._excursion(trade)
        if gone == "0/0":
            return None
        said = trade.get("zone_return_at")
        if said is not None:
            try:
                said_targets = int(str(said).split("/")[1])
            except (IndexError, ValueError):
                said_targets = 0
            if len(trade.get("hit") or []) <= said_targets:
                return None
        zone_low, zone_high = _entry_band(trade)
        if not (spot >= zone_low if short else spot <= zone_high):
            return None
        symbol, direction, entry = trade["symbol"], trade["direction"], float(trade["entry"])
        stop = float(trade["stop"])
        lines = [
            voice.head("\U0001f501", symbol, direction, entry, "\u05d7\u05d6\u05e8\u05d4 \u05dc\u05d0\u05d6\u05d5\u05e8 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4"),
            "",
            f"\u05de\u05d7\u05d9\u05e8 \u05d1\u05e2\u05d3\u05db\u05d5\u05df: {spot:,.2f}\n\u05d0\u05d6\u05d5\u05e8: {zone_low:,.2f}\u2013{zone_high:,.2f}",
            f"\u05e1\u05d8\u05d5\u05e4 \u05de\u05e7\u05d5\u05e8\u05d9: {stop:,.2f} \u00b7 \u05de\u05e8\u05d7\u05e7 {voice.dist(symbol, spot - stop)}",
            "",
        ]
        journey = self.transitions._journey(trade)
        if journey:
            lines.append(journey)
        lines.append(self._entry_recheck(trade))
        lines.append("\n\u05d4\u05e1\u05d8\u05d5\u05e4 \u05d5\u05d4\u05d9\u05e2\u05d3\u05d9\u05dd \u05dc\u05dc\u05d0 \u05e9\u05d9\u05e0\u05d5\u05d9. \u05d6\u05d4 \u05d0\u05d9\u05e0\u05d5 \u05d0\u05d5\u05ea \u05dc\u05db\u05e0\u05d9\u05e1\u05d4 \u05e0\u05d5\u05e1\u05e4\u05ea.")
        trade["zone_return_at"] = gone
        return "\n".join(lines)

    def resolve(self, trade: dict, *, spot: float) -> tuple[list[tuple[str, bool]], bool]:
        """Return one source-style notification for an eligible supplied spot."""
        short = trade["direction"] == "\u05e9\u05d5\u05e8\u05d8"
        message = self._zone_return_message(trade, float(spot), short)
        if message is None:
            return ([], False)
        return ([(message, trade["to_group"])], True)
