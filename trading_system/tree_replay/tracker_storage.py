"""Supplied causal tracker artifact and original load/save; no filesystem access."""
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
import json

from .bars import _utc
from .clock import ReplayClock, _validate_binding
from .state import _identity
from ._vendor.tracker_storage import TrackerStorage


class StateUnavailable(ValueError):
    """The supplied artifact cannot establish source state at the decision time."""


@dataclass(frozen=True, kw_only=True)
class TrackerStateSeed:
    seed_id: str
    source: str
    observed_at: datetime
    available_at: datetime
    covered_through: datetime
    status: str
    text: str | None

    def __post_init__(self):
        _identity(self.seed_id, "seed_id")
        _identity(self.source, "source")
        for name in ("observed_at", "available_at", "covered_through"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if not self.observed_at <= self.available_at <= self.covered_through:
            raise ValueError("seed requires observed_at <= available_at <= covered_through")
        if type(self.status) is not str or self.status not in (
                "PRESENT", "ABSENT", "UNREADABLE", "UNKNOWN"):
            raise ValueError("invalid tracker artifact status")
        if self.status == "PRESENT":
            if type(self.text) is not str:
                raise ValueError("PRESENT artifact requires exact text")
            try:
                self.text.encode("utf-8")
            except UnicodeError as exc:
                raise ValueError("artifact text must be UTF-8 encodable") from exc
        elif self.text is not None:
            raise ValueError("non-PRESENT artifact cannot contain text")


class _Quarantine:
    def __init__(self, backend, suffix):
        self.backend = backend
        self.name = "open_trades" + suffix

    def write_text(self, text):
        self.backend.write_quarantine(self.name, text)


class _MemoryBackend:
    def __init__(self, seed, decision_time, clock=None):
        self.seed = seed
        self._decision_time = decision_time
        self._clock = clock
        self.status = seed.status
        self.text = seed.text
        self.trace = []
        self.quarantines = {}
        self.creations = []

    @property
    def decision_time(self):
        return self._decision_time if self._clock is None else self._clock.now

    def call(self, operation, action):
        event = {"operation": operation, "decision_time": self.decision_time.isoformat(),
                 "status": "BLOCKED", "exception_type": None, "blocker": None}
        self.trace.append(event)
        try:
            if self.seed.status == "UNKNOWN":
                raise StateUnavailable("STATE_UNKNOWN")
            if self.decision_time < self.seed.available_at:
                raise StateUnavailable("STATE_NOT_YET_AVAILABLE")
            if self.decision_time > self.seed.covered_through:
                raise StateUnavailable("STATE_COVERAGE_EXPIRED")
            result = action()
        except Exception as exc:
            event.update(exception_type=type(exc).__name__, blocker=str(exc))
            raise
        event["status"] = "AVAILABLE"
        return result

    def is_live_test_target(self):
        # No path input or filesystem capability exists on this backend.
        return self.call("write_guard", lambda: False)

    def exists(self):
        return self.call("exists", lambda: self.status != "ABSENT")

    def read_text(self):
        def read():
            if self.status == "UNREADABLE":
                raise OSError("supplied tracker artifact is unreadable")
            if self.status == "ABSENT":
                raise FileNotFoundError("supplied tracker artifact is absent")
            return self.text
        return self.call("read_text", read)

    def now_epoch(self):
        return self.call("clock", self.decision_time.timestamp)

    def quarantine_path(self, suffix):
        return self.call("quarantine_path", lambda: _Quarantine(self, suffix))

    def write_quarantine(self, name, text):
        def write():
            text.encode("utf-8")
            self.quarantines[name] = text
        self.call("write_quarantine", write)

    def atomic_write(self, text):
        def write():
            text.encode("utf-8")
            self.text, self.status = text, "PRESENT"
        self.call("atomic_write", write)

    def audit_creation(self, cur, d):
        def audit():
            # Original set-difference is outside its best-effort try boundary.
            new = set(d) - set(cur)
            if not new:
                return
            def emit(key):
                effect = {"origin": "replay_creation_effect",
                    "ts": self.decision_time.timestamp(), "key": key,
                    "record": {x: d[key].get(x) for x in
                        ("entry", "stop", "state", "variant", "revived_from_ts")}}
                serialized = json.dumps(effect, ensure_ascii=False)
                serialized.encode("utf-8")
                self.creations.append(json.loads(serialized))
            try:
                for key in new:
                    self.call("creation_effect", lambda: emit(key))
            except Exception:
                pass  # no fabricated historical pid/argv/stack or live forensic file
        self.call("audit_creation", audit)


class CausalTrackerStorage(TrackerStorage):
    """Fixed or explicitly shared-time storage; snapshot is not a full checkpoint."""
    def __init__(self, *, seed: TrackerStateSeed, decision_time: datetime,
                 clock: ReplayClock | None = None):
        if type(seed) is not TrackerStateSeed:
            raise ValueError("seed must be an exact TrackerStateSeed")
        seed.__post_init__()
        at = _utc(decision_time, "decision_time")
        _validate_binding(clock, at)
        super().__init__(_MemoryBackend(seed, at, clock))

    def load(self):
        return self.source.call("load", super().load)

    def save(self, d, *, allow_shrink=False):
        return self.source.call("save", lambda: super(CausalTrackerStorage, self).save(
            d, allow_shrink=allow_shrink))

    def snapshot(self):
        return self.source.call("snapshot", lambda: replace(self.source.seed,
            observed_at=self.source.decision_time, available_at=self.source.decision_time,
            status=self.source.status, text=self.source.text))

    @property
    def trace(self):
        return deepcopy(self.source.trace)

    @property
    def creation_effects(self):
        return deepcopy(self.source.creations)

    @property
    def quarantine_artifacts(self):
        return dict(self.source.quarantines)
