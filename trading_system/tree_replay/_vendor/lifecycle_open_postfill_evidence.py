"""Pinned OPEN post-fill window evidence over caller-supplied spot and tape."""
from copy import copy

from .desk_success import DeskSuccess
from .lifecycle_bars import _fill_on_tape, _position_extremes
from .lifecycle_live_evidence import LifecycleLiveEvidence


class LifecycleOpenPostfillEvidence:
    """Recover raw extrema and a provisional minimum message without effects."""

    def __init__(self, source):
        self.source = source
        self.live_evidence = LifecycleLiveEvidence(source)

    def collect(self, trade: dict, spot: float) -> tuple[float, float, str | None]:
        """Return ``(low, high, minimum_message)`` for one supplied OPEN record."""
        low = high = spot
        minimum_message = None
        try:
            tape, correction = self.source.fetch_corrected(trade["symbol"], "15m", 2)
            bad_tape = correction is not None and (
                getattr(correction, "unverified", False)
                or getattr(correction, "source", "") == "tv_stale"
            )
            fill = (
                _fill_on_tape(tape, trade)
                if not bad_tape or self.live_evidence._historical_replay_safe(tape, correction, trade)
                else None
            )
            if fill is not None:
                minimum_message = DeskSuccess(self.source).observe_bars(copy(trade), tape)
                tape_high, tape_low = _position_extremes(
                    tape.loc[fill:], trade, fill_bar_first=True
                )
                low, high = min(spot, tape_low), max(spot, tape_high)
        except Exception:
            pass
        return low, high, minimum_message
