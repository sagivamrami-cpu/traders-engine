"""Explicit monotonic replay time, independent of artifact availability."""
from datetime import datetime

from .bars import _utc


class ReplayClock:
    def __init__(self, decision_time: datetime):
        self._now = _utc(decision_time, "decision_time")

    @property
    def now(self):
        return self._now

    def advance_to(self, decision_time: datetime):
        at = _utc(decision_time, "decision_time")
        if at < self._now:
            raise ValueError("replay clock cannot move backward")
        self._now = at


def _validate_binding(clock, decision_time):
    if clock is not None and (type(clock) is not ReplayClock or clock.now != decision_time):
        raise ValueError("clock must be exact ReplayClock at the declared decision_time")
