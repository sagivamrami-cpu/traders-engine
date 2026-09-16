# Task1 full working-file package

Two artifact files modify previously accepted untracked code; compare with prior tracker-storage-binding and causal-quote-watch-io task packages for the small optional-clock delta. Three files are new.

## trading_system/tree_replay/clock.py

```diff
diff --git a/trading_system/tree_replay/clock.py b/trading_system/tree_replay/clock.py
new file mode 100644
index 0000000..f880684
--- /dev/null
+++ b/trading_system/tree_replay/clock.py
@@ -0,0 +1,24 @@
+"""Explicit monotonic replay time, independent of artifact availability."""
+from datetime import datetime
+
+from .bars import _utc
+
+
+class ReplayClock:
+    def __init__(self, decision_time: datetime):
+        self._now = _utc(decision_time, "decision_time")
+
+    @property
+    def now(self):
+        return self._now
+
+    def advance_to(self, decision_time: datetime):
+        at = _utc(decision_time, "decision_time")
+        if at < self._now:
+            raise ValueError("replay clock cannot move backward")
+        self._now = at
+
+
+def _validate_binding(clock, decision_time):
+    if clock is not None and (type(clock) is not ReplayClock or clock.now != decision_time):
+        raise ValueError("clock must be exact ReplayClock at the declared decision_time")
```

## trading_system/tree_replay/tracker_storage.py

```diff
diff --git a/trading_system/tree_replay/tracker_storage.py b/trading_system/tree_replay/tracker_storage.py
new file mode 100644
index 0000000..70e1c1d
--- /dev/null
+++ b/trading_system/tree_replay/tracker_storage.py
@@ -0,0 +1,179 @@
+"""Supplied causal tracker artifact and original load/save; no filesystem access."""
+from copy import deepcopy
+from dataclasses import dataclass, replace
+from datetime import datetime
+import json
+
+from .bars import _utc
+from .clock import ReplayClock, _validate_binding
+from .state import _identity
+from ._vendor.tracker_storage import TrackerStorage
+
+
+class StateUnavailable(ValueError):
+    """The supplied artifact cannot establish source state at the decision time."""
+
+
+@dataclass(frozen=True, kw_only=True)
+class TrackerStateSeed:
+    seed_id: str
+    source: str
+    observed_at: datetime
+    available_at: datetime
+    covered_through: datetime
+    status: str
+    text: str | None
+
+    def __post_init__(self):
+        _identity(self.seed_id, "seed_id")
+        _identity(self.source, "source")
+        for name in ("observed_at", "available_at", "covered_through"):
+            object.__setattr__(self, name, _utc(getattr(self, name), name))
+        if not self.observed_at <= self.available_at <= self.covered_through:
+            raise ValueError("seed requires observed_at <= available_at <= covered_through")
+        if type(self.status) is not str or self.status not in (
+                "PRESENT", "ABSENT", "UNREADABLE", "UNKNOWN"):
+            raise ValueError("invalid tracker artifact status")
+        if self.status == "PRESENT":
+            if type(self.text) is not str:
+                raise ValueError("PRESENT artifact requires exact text")
+            try:
+                self.text.encode("utf-8")
+            except UnicodeError as exc:
+                raise ValueError("artifact text must be UTF-8 encodable") from exc
+        elif self.text is not None:
+            raise ValueError("non-PRESENT artifact cannot contain text")
+
+
+class _Quarantine:
+    def __init__(self, backend, suffix):
+        self.backend = backend
+        self.name = "open_trades" + suffix
+
+    def write_text(self, text):
+        self.backend.write_quarantine(self.name, text)
+
+
+class _MemoryBackend:
+    def __init__(self, seed, decision_time, clock=None):
+        self.seed = seed
+        self._decision_time = decision_time
+        self._clock = clock
+        self.status = seed.status
+        self.text = seed.text
+        self.trace = []
+        self.quarantines = {}
+        self.creations = []
+
+    @property
+    def decision_time(self):
+        return self._decision_time if self._clock is None else self._clock.now
+
+    def call(self, operation, action):
+        event = {"operation": operation, "decision_time": self.decision_time.isoformat(),
+                 "status": "BLOCKED", "exception_type": None, "blocker": None}
+        self.trace.append(event)
+        try:
+            if self.seed.status == "UNKNOWN":
+                raise StateUnavailable("STATE_UNKNOWN")
+            if self.decision_time < self.seed.available_at:
+                raise StateUnavailable("STATE_NOT_YET_AVAILABLE")
+            if self.decision_time > self.seed.covered_through:
+                raise StateUnavailable("STATE_COVERAGE_EXPIRED")
+            result = action()
+        except Exception as exc:
+            event.update(exception_type=type(exc).__name__, blocker=str(exc))
+            raise
+        event["status"] = "AVAILABLE"
+        return result
+
+    def is_live_test_target(self):
+        # No path input or filesystem capability exists on this backend.
+        return self.call("write_guard", lambda: False)
+
+    def exists(self):
+        return self.call("exists", lambda: self.status != "ABSENT")
+
+    def read_text(self):
+        def read():
+            if self.status == "UNREADABLE":
+                raise OSError("supplied tracker artifact is unreadable")
+            if self.status == "ABSENT":
+                raise FileNotFoundError("supplied tracker artifact is absent")
+            return self.text
+        return self.call("read_text", read)
+
+    def now_epoch(self):
+        return self.call("clock", self.decision_time.timestamp)
+
+    def quarantine_path(self, suffix):
+        return self.call("quarantine_path", lambda: _Quarantine(self, suffix))
+
+    def write_quarantine(self, name, text):
+        def write():
+            text.encode("utf-8")
+            self.quarantines[name] = text
+        self.call("write_quarantine", write)
+
+    def atomic_write(self, text):
+        def write():
+            text.encode("utf-8")
+            self.text, self.status = text, "PRESENT"
+        self.call("atomic_write", write)
+
+    def audit_creation(self, cur, d):
+        def audit():
+            # Original set-difference is outside its best-effort try boundary.
+            new = set(d) - set(cur)
+            if not new:
+                return
+            def emit(key):
+                effect = {"origin": "replay_creation_effect",
+                    "ts": self.decision_time.timestamp(), "key": key,
+                    "record": {x: d[key].get(x) for x in
+                        ("entry", "stop", "state", "variant", "revived_from_ts")}}
+                serialized = json.dumps(effect, ensure_ascii=False)
+                serialized.encode("utf-8")
+                self.creations.append(json.loads(serialized))
+            try:
+                for key in new:
+                    self.call("creation_effect", lambda: emit(key))
+            except Exception:
+                pass  # no fabricated historical pid/argv/stack or live forensic file
+        self.call("audit_creation", audit)
+
+
+class CausalTrackerStorage(TrackerStorage):
+    """Fixed or explicitly shared-time storage; snapshot is not a full checkpoint."""
+    def __init__(self, *, seed: TrackerStateSeed, decision_time: datetime,
+                 clock: ReplayClock | None = None):
+        if type(seed) is not TrackerStateSeed:
+            raise ValueError("seed must be an exact TrackerStateSeed")
+        seed.__post_init__()
+        at = _utc(decision_time, "decision_time")
+        _validate_binding(clock, at)
+        super().__init__(_MemoryBackend(seed, at, clock))
+
+    def load(self):
+        return self.source.call("load", super().load)
+
+    def save(self, d, *, allow_shrink=False):
+        return self.source.call("save", lambda: super(CausalTrackerStorage, self).save(
+            d, allow_shrink=allow_shrink))
+
+    def snapshot(self):
+        return self.source.call("snapshot", lambda: replace(self.source.seed,
+            observed_at=self.source.decision_time, available_at=self.source.decision_time,
+            status=self.source.status, text=self.source.text))
+
+    @property
+    def trace(self):
+        return deepcopy(self.source.trace)
+
+    @property
+    def creation_effects(self):
+        return deepcopy(self.source.creations)
+
+    @property
+    def quarantine_artifacts(self):
+        return dict(self.source.quarantines)
```

## trading_system/tree_replay/admission_io.py

```diff
diff --git a/trading_system/tree_replay/admission_io.py b/trading_system/tree_replay/admission_io.py
new file mode 100644
index 0000000..1a888d5
--- /dev/null
+++ b/trading_system/tree_replay/admission_io.py
@@ -0,0 +1,262 @@
+"""Causal quote artifacts and byte-faithful, append-only watch logging in memory."""
+from bisect import bisect_right
+from copy import deepcopy
+from dataclasses import dataclass, replace
+from datetime import datetime
+from io import RawIOBase
+import json
+from operator import index
+
+from .bars import _utc
+from .clock import ReplayClock, _validate_binding
+from .state import _identity
+from ._vendor.watch_io import WatchLogger
+from ._vendor.watch_sessions import current_session_at
+
+
+class InputUnavailable(ValueError):
+    """No covered, published artifact can establish the source input."""
+
+
+@dataclass(frozen=True, kw_only=True)
+class ArtifactSeed:
+    seed_id: str
+    source: str
+    kind: str
+    status: str
+    observed_at: datetime
+    available_at: datetime
+    covered_through: datetime
+    content: str | bytes | None
+
+    def __post_init__(self):
+        _identity(self.seed_id, "seed_id")
+        _identity(self.source, "source")
+        if type(self.kind) is not str or self.kind not in ("quotes", "watch_log"):
+            raise ValueError("invalid artifact kind")
+        if type(self.status) is not str or self.status not in ("PRESENT", "ABSENT", "UNREADABLE", "UNKNOWN"):
+            raise ValueError("invalid artifact status")
+        for field in ("observed_at", "available_at", "covered_through"):
+            object.__setattr__(self, field, _utc(getattr(self, field), field))
+        if not self.observed_at <= self.available_at <= self.covered_through:
+            raise ValueError("artifact requires observed <= available <= covered")
+        if self.status == "PRESENT":
+            expected = str if self.kind == "quotes" else bytes
+            if type(self.content) is not expected:
+                raise ValueError("wrong artifact content type")
+            if expected is str:
+                try:
+                    self.content.encode("utf-8")
+                except UnicodeError as exc:
+                    raise ValueError("quote text must be UTF-8 encodable") from exc
+        elif self.content is not None:
+            raise ValueError("non-PRESENT content must be None")
+
+
+class _Context:
+    def __init__(self, seed, decision_time, kind, clock=None):
+        if type(seed) is not ArtifactSeed or seed.kind != kind:
+            raise ValueError("exact seed with matching artifact kind required")
+        seed.__post_init__()
+        self.seed = seed
+        self._decision_time = _utc(decision_time, "decision_time")
+        _validate_binding(clock, self._decision_time)
+        self._clock = clock
+        self.events = []
+
+    @property
+    def decision_time(self):
+        return self._decision_time if self._clock is None else self._clock.now
+
+    def _advance_time(self, at):
+        if self._clock is None:
+            self._decision_time = at
+        else:
+            self._clock.advance_to(at)
+
+    def require_available(self, at=None):
+        at = self.decision_time if at is None else at
+        if self.seed.status == "UNKNOWN":
+            raise InputUnavailable("ARTIFACT_UNKNOWN")
+        if at < self.seed.available_at:
+            raise InputUnavailable("ARTIFACT_NOT_YET_AVAILABLE")
+        if at > self.seed.covered_through:
+            raise InputUnavailable("ARTIFACT_COVERAGE_EXPIRED")
+
+    def call(self, operation, action):
+        event = dict(operation=operation, decision_time=self.decision_time.isoformat(),
+                     status="BLOCKED", exception_type=None, blocker=None)
+        self.events.append(event)
+        try:
+            result = action()
+        except Exception as exc:
+            event.update(exception_type=type(exc).__name__, blocker=str(exc))
+            raise
+        event["status"] = "AVAILABLE"
+        return result
+
+    def now_epoch(self):
+        return self.call("clock", self.decision_time.timestamp)
+
+    @property
+    def trace(self):
+        return deepcopy(self.events)
+
+
+class CausalQuoteReader(_Context):
+    def __init__(self, *, seed: ArtifactSeed, decision_time: datetime,
+                 clock: ReplayClock | None = None):
+        super().__init__(seed, decision_time, "quotes", clock)
+
+    def quote_payload(self):
+        def read():
+            self.require_available()
+            if self.seed.status == "ABSENT":
+                raise FileNotFoundError("quote artifact absent")
+            if self.seed.status == "UNREADABLE":
+                raise OSError("quote artifact unreadable")
+            return json.loads(self.seed.content)
+        return self.call("quote_payload", read)
+
+
+class _PrefixReader(RawIOBase):
+    """Seek over stable append-only chunks, clipping every read at opened length."""
+    def __init__(self, chunks, ends):
+        super().__init__()
+        self._chunks, self._ends = chunks, ends
+        self._size = ends[-1] if ends else 0
+        self._pos = 0
+
+    def readable(self):
+        return True
+
+    def seekable(self):
+        return True
+
+    def tell(self):
+        self._checkClosed()
+        return self._pos
+
+    def seek(self, offset, whence=0):
+        self._checkClosed()
+        offset, whence = index(offset), index(whence)
+        if whence not in (0, 1, 2):
+            raise ValueError("invalid whence")
+        pos = offset + (0 if whence == 0 else self._pos if whence == 1 else self._size)
+        if pos < 0:
+            raise ValueError("negative seek")
+        self._pos = pos
+        return pos
+
+    def read(self, size=-1):
+        self._checkClosed()
+        size = -1 if size is None else index(size)
+        end = self._size if size < 0 else min(self._size, self._pos+size)
+        if end <= self._pos:
+            return b""
+        parts = []
+        chunk = bisect_right(self._ends, self._pos)
+        while self._pos < end:
+            start = self._ends[chunk-1] if chunk else 0
+            stop = min(end, self._ends[chunk])
+            parts.append(self._chunks[chunk][self._pos-start:stop-start])
+            self._pos = stop
+            chunk += 1
+        return b"".join(parts)
+
+
+class _AppendWriter:
+    def __init__(self, source):
+        self.source = source
+        self.closed = False
+
+    def __enter__(self):
+        return self
+
+    def __exit__(self, exc_type, exc, tb):
+        self.source.call("close_writer", lambda: setattr(self, "closed", True))
+        return False
+
+    def write(self, text):
+        def append():
+            if self.closed:
+                raise ValueError("write to closed log writer")
+            self.source.require_available()
+            raw = text.replace("\n", self.source.newline).encode("utf-8")
+            if raw:
+                self.source.chunks.append(raw)
+                self.source.ends.append((self.source.ends[-1] if self.source.ends else 0)+len(raw))
+            return len(text)
+        return self.source.call("write", append)
+
+
+class _LogContext(_Context):
+    def __init__(self, seed, decision_time, newline, clock=None):
+        super().__init__(seed, decision_time, "watch_log", clock)
+        if type(newline) is not str or newline not in ("LF", "CRLF"):
+            raise ValueError("newline must be explicit LF or CRLF")
+        self.newline = "\n" if newline == "LF" else "\r\n"
+        self.status = seed.status
+        self.chunks = [seed.content] if seed.status == "PRESENT" and seed.content else []
+        self.ends = [len(seed.content)] if self.chunks else []
+
+    def current_session(self):
+        return self.call("current_session", lambda: current_session_at(decision_time=self.decision_time))
+
+    def ensure_out(self):
+        self.call("mkdir", lambda: None)  # completed virtual directory operation
+
+    def event_log_writer(self):
+        def open_writer():
+            self.require_available()
+            if self.status == "UNREADABLE":
+                raise OSError("cannot append an unknown byte prefix")
+            self.status = "PRESENT"  # source append open creates before serialization
+            return _AppendWriter(self)
+        return self.call("open_writer", open_writer)
+
+    def event_log_reader(self):
+        def open_reader():
+            self.require_available()
+            if self.status == "ABSENT":
+                raise FileNotFoundError("watch log absent")
+            if self.status == "UNREADABLE":
+                raise OSError("watch log unreadable")
+            return _PrefixReader(self.chunks, self.ends)
+        return self.call("open_reader", open_reader)
+
+
+class CausalWatchLog(WatchLogger):
+    def __init__(self, *, seed: ArtifactSeed, decision_time: datetime, newline: str,
+                 clock: ReplayClock | None = None):
+        super().__init__(_LogContext(seed, decision_time, newline, clock))
+
+    def log(self, row):
+        return self.source.call("log", lambda: super(CausalWatchLog, self).log(row))
+
+    def event_log_reader(self):
+        return self.source.event_log_reader()
+
+    def now_epoch(self):
+        return self.source.now_epoch()
+
+    def advance_to(self, decision_time):
+        def advance():
+            at = _utc(decision_time, "decision_time")
+            if at < self.source.decision_time:
+                raise ValueError("watch log cannot move backward")
+            self.source.require_available(at)
+            self.source._advance_time(at)
+        self.source.call("advance", advance)
+
+    def snapshot(self):
+        def snapshot():
+            self.source.require_available()
+            return replace(self.source.seed, status=self.source.status,
+                observed_at=self.source.decision_time, available_at=self.source.decision_time,
+                content=b"".join(self.source.chunks) if self.source.status == "PRESENT" else None)
+        return self.source.call("snapshot", snapshot)
+
+    @property
+    def trace(self):
+        return self.source.trace
```

## tests/tree_replay/test_shared_clock.py

```diff
diff --git a/tests/tree_replay/test_shared_clock.py b/tests/tree_replay/test_shared_clock.py
new file mode 100644
index 0000000..2a36dea
--- /dev/null
+++ b/tests/tree_replay/test_shared_clock.py
@@ -0,0 +1,160 @@
+"""A shared operation clock must not reset artifacts or imply data availability."""
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay.admission_io import ArtifactSeed, CausalQuoteReader, CausalWatchLog, InputUnavailable
+from trading_system.tree_replay.tracker_storage import CausalTrackerStorage, TrackerStateSeed, StateUnavailable
+from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+
+
+def api():
+    name = "trading_system.tree_replay.clock"
+    assert importlib.util.find_spec(name) is not None, "shared replay clock missing"
+    return importlib.import_module(name)
+
+
+def state_seed(**changes):
+    return TrackerStateSeed(**(dict(seed_id="state", source="synthetic", observed_at=T,
+        available_at=T, covered_through=T+timedelta(seconds=20), status="ABSENT", text=None) | changes))
+
+
+def artifact(kind, **changes):
+    return ArtifactSeed(**(dict(seed_id=kind, source="synthetic", kind=kind, observed_at=T,
+        available_at=T, covered_through=T+timedelta(seconds=20), status="PRESENT",
+        content=b"old\n" if kind == "watch_log" else '{"OANDA:XAUUSD":{"lp":100,"ts":1788969180}}') | changes))
+
+
+def contexts(clock):
+    return (CausalTrackerStorage(seed=state_seed(), decision_time=T, clock=clock),
+            CausalQuoteReader(seed=artifact("quotes"), decision_time=T, clock=clock),
+            CausalWatchLog(seed=artifact("watch_log"), decision_time=T, newline="LF", clock=clock))
+
+
+def test_shared_advance_retains_generated_state_effects_and_source_quote_freshness():
+    clock = api().ReplayClock(T)
+    storage, quotes, log = contexts(clock)
+    storage.save({"a": {"state": "PENDING"}})
+    storage.save({"a": {"state": "PENDING"}, "b": {"state": "PENDING"}})
+    before_effects = storage.creation_effects
+    assert TrackerAdmission(quotes)._live_prices() == {"OANDA:XAUUSD": 100.0}
+    clock.advance_to(T+timedelta(seconds=2))
+    assert storage.load() == {"a": {"state": "PENDING"}, "b": {"state": "PENDING"}}
+    assert storage.creation_effects == before_effects
+    assert storage.snapshot().available_at == T+timedelta(seconds=2)
+    assert TrackerAdmission(quotes)._live_prices() == {}  # Now422seconds old.
+    assert log.now_epoch() == quotes.now_epoch() == 1788969602.0
+    assert storage.trace[-1]["decision_time"] == "2026-09-09T16:00:02+00:00"
+
+
+def test_log_uses_current_shared_timestamp_and_keeps_captured_reader_prefix():
+    clock = api().ReplayClock(T)
+    _, _, log = contexts(clock)
+    reader = log.event_log_reader()
+    clock.advance_to(T+timedelta(seconds=2))
+    log.log({"kind": "probe"})
+    assert reader.read() == b"old\n"
+    assert log.snapshot().content == b'old\n{"ts": 1788969602.0, "kind": "probe", "sessions": ["newyork"]}\n'
+    assert log.snapshot().available_at == clock.now
+
+
+def test_shared_log_advance_updates_other_bindings_but_keeps_its_coverage_guard():
+    clock = api().ReplayClock(T)
+    storage, quotes, log = contexts(clock)
+    log.advance_to(T+timedelta(seconds=3))
+    assert quotes.now_epoch() == 1788969603.0
+    assert storage.snapshot().available_at == clock.now == T+timedelta(seconds=3)
+    with pytest.raises(InputUnavailable, match="COVERAGE_EXPIRED"):
+        log.advance_to(T+timedelta(seconds=21))
+    assert clock.now == T+timedelta(seconds=3)
+
+
+def test_clock_can_advance_past_coverage_without_certifying_artifacts():
+    clock = api().ReplayClock(T)
+    storage, quotes, log = contexts(clock)
+    clock.advance_to(T+timedelta(seconds=21))
+    for action, error in [(storage.load, StateUnavailable),
+                          (quotes.quote_payload, InputUnavailable),
+                          (log.event_log_reader, InputUnavailable)]:
+        with pytest.raises(error, match="COVERAGE_EXPIRED"):
+            action()
+    assert all(c.trace[-1]["status"] == "BLOCKED" for c in (storage, quotes, log))
+    assert quotes.now_epoch() == 1788969621.0  # Time itself is independent of quotes.
+
+
+def test_delayed_publication_becomes_readable_at_actual_shared_time():
+    clock = api().ReplayClock(T)
+    quotes = CausalQuoteReader(seed=artifact("quotes", available_at=T+timedelta(seconds=2)),
+                              decision_time=T, clock=clock)
+    assert TrackerAdmission(quotes)._live_prices() == {}
+    assert quotes.trace[-1]["status"] == "BLOCKED"
+    clock.advance_to(T+timedelta(seconds=2))
+    assert quotes.quote_payload()["OANDA:XAUUSD"]["lp"] == 100
+    assert quotes.trace[-1]["decision_time"] == "2026-09-09T16:00:02+00:00"
+
+
+@pytest.mark.parametrize("bad", [T-timedelta(microseconds=1), T.replace(tzinfo=None),
+    pd.Timestamp("2026-09-09T16:00:00.000000001Z"), "2026-09-09", None])
+def test_invalid_or_backward_advance_is_atomic(bad):
+    clock = api().ReplayClock(T)
+    with pytest.raises(ValueError):
+        clock.advance_to(bad)
+    assert clock.now == T
+
+
+def test_equal_time_and_timezone_equivalent_advance_do_not_lose_microseconds():
+    at = T+timedelta(microseconds=7)
+    clock = api().ReplayClock(at.astimezone(timezone(timedelta(hours=3))))
+    clock.advance_to(at)
+    assert clock.now == at and type(clock.now) is datetime
+    with pytest.raises(AttributeError):
+        clock.now = T
+
+
+@pytest.mark.parametrize("kind", ["storage", "quotes", "log"])
+@pytest.mark.parametrize("mode", ["wrong_type", "wrong_time"])
+def test_bound_context_requires_exact_clock_at_its_declared_initial_time(kind, mode):
+    cls = api().ReplayClock
+    clock = object() if mode == "wrong_type" else cls(T+timedelta(seconds=1))
+    with pytest.raises(ValueError):
+        if kind == "storage":
+            CausalTrackerStorage(seed=state_seed(), decision_time=T, clock=clock)
+        elif kind == "quotes":
+            CausalQuoteReader(seed=artifact("quotes"), decision_time=T, clock=clock)
+        else:
+            CausalWatchLog(seed=artifact("watch_log"), decision_time=T, newline="LF", clock=clock)
+
+
+def test_clock_subclasses_cannot_override_time_validation_in_bindings():
+    class ForeignClock(api().ReplayClock):
+        pass
+    with pytest.raises(ValueError):
+        CausalQuoteReader(seed=artifact("quotes"), decision_time=T, clock=ForeignClock(T))
+
+
+def test_standalone_contexts_remain_independent_of_external_clock():
+    clock = api().ReplayClock(T)
+    storage = CausalTrackerStorage(seed=state_seed(), decision_time=T)
+    quotes = CausalQuoteReader(seed=artifact("quotes"), decision_time=T)
+    log = CausalWatchLog(seed=artifact("watch_log"), decision_time=T, newline="LF")
+    clock.advance_to(T+timedelta(days=2))
+    assert storage.load() == {}
+    assert quotes.now_epoch() == log.now_epoch() == 1788969600.0
+    log.advance_to(T+timedelta(seconds=2))
+    assert storage.snapshot().available_at == T and quotes.now_epoch() == 1788969600.0
+
+
+def test_session_default_is_recomputed_at_shared_clock_not_construction_time():
+    early = datetime(2026, 9, 9, 11, 59, tzinfo=timezone.utc)
+    clock = api().ReplayClock(early)
+    log = CausalWatchLog(seed=artifact("watch_log", observed_at=early,
+        available_at=early, covered_through=T), decision_time=early, newline="LF", clock=clock)
+    clock.advance_to(T)
+    row = {}
+    log.log(row)
+    assert row == {"sessions": ["newyork"]}
```

## docs/architecture/SHARED-REPLAY-CLOCK-USAGE.md

```diff
diff --git a/docs/architecture/SHARED-REPLAY-CLOCK-USAGE.md b/docs/architecture/SHARED-REPLAY-CLOCK-USAGE.md
new file mode 100644
index 0000000..eb6ae29
--- /dev/null
+++ b/docs/architecture/SHARED-REPLAY-CLOCK-USAGE.md
@@ -0,0 +1,38 @@
+# Explicit shared operation clock
+
+`ReplayClock` holds caller-supplied aware microsecond UTC time; no wall-clock read
+or sleeping occurs. It permits equal/forward time only, validating before mutation.
+It does not certify any input availability or implement a publication scheduler.
+
+```python
+from trading_system.tree_replay.clock import ReplayClock
+from trading_system.tree_replay.tracker_storage import CausalTrackerStorage
+
+clock = ReplayClock(decision_time)
+storage = CausalTrackerStorage(seed=tracker_seed, decision_time=decision_time, clock=clock)
+clock.advance_to(next_operation_time)
+rows = storage.load()  # Checks the same artifact against the NEW operation time.
+```
+
+The seed and times above are supplied caller inputs, not market defaults.
+`CausalQuoteReader` and `CausalWatchLog` accept the same optional `clock` parameter.
+At binding its type must be exactly ReplayClock, and now must equal decision_time.
+Omitting the parameter preserves existing fixed-time behavior. No existing source
+projection, threshold or data fallback is changed.
+
+Advancing the clock does not reset state, creations, quarantines or log chunks.
+Quote freshness, session calculation, trace times and artifact snapshots use the
+current clock. Already-open log readers keep their captured byte prefix. Crossing
+coverage or reaching unknown evidence still causes guarded reads/writes to fail;
+source catches do not remove provider failure traces. Time may advance even when
+an artifact is missing. Clock.now is read-only; use advance_to, not private fields.
+
+`log.advance_to(T)` retains its original artifact guard. With a bound clock it
+advances the shared clock only after that guard; other contexts then observe T.
+An application with scheduled publications should own the clock privately and
+advance it through its coordinator, not bypass that schedule using a child log.
+No implicit thread safety, rollback, elapsed-time inference or checkpoint exists.
+
+This is a prerequisite for combined admission context. It is not the whole watch
+loop or a guarantee of historical feed coverage, OS timing, trade fills or training.
+Run `python -m pytest tests/tree_replay/test_shared_clock.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_frames.py -q --tb=short`.
```

