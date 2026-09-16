"""Causal completed watch-state writes, separate from tracker storage policy."""
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime

from .bars import _utc
from .clock import ReplayClock, _validate_binding
from .tracker_storage import TrackerStateSeed, _MemoryBackend
from ._vendor.watch_storage import WatchStorage


@dataclass(frozen=True, kw_only=True)
class WatchStateSeed(TrackerStateSeed):
    """Distinct watch artifact, with the accepted causal text evidence schema."""


class _WatchBackend(_MemoryBackend):
    def ensure_directory(self, *, exist_ok):
        # Completed in-memory port attempt, not historical filesystem permission.
        return self.call("ensure_directory", lambda: None)

    def write_text(self, text):
        def write():
            text.encode("utf-8")
            self.text, self.status = text, "PRESENT"
        return self.call("write_text", write)


class CausalWatchStorage(WatchStorage):
    def __init__(self, *, seed: WatchStateSeed, decision_time: datetime,
                 clock: ReplayClock | None = None):
        if type(seed) is not WatchStateSeed:
            raise ValueError("seed must be an exact WatchStateSeed")
        seed.__post_init__()
        at = _utc(decision_time, "decision_time")
        _validate_binding(clock, at)
        super().__init__(_WatchBackend(seed, at, clock))

    def load(self):
        return self.source.call("load", super().load)

    def save_before_producers(self, st):
        return self.source.call("save_before_producers", lambda:
            super(CausalWatchStorage, self).save_before_producers(st))

    def save_final(self, st):
        return self.source.call("save_final", lambda:
            super(CausalWatchStorage, self).save_final(st))

    def snapshot(self):
        return self.source.call("snapshot", lambda: replace(self.source.seed,
            observed_at=self.source.decision_time, available_at=self.source.decision_time,
            status=self.source.status, text=self.source.text))

    @property
    def trace(self):
        return deepcopy(self.source.trace)
