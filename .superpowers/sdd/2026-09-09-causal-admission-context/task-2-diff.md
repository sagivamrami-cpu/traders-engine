# Task2 full new-file review package

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; untracked files, not an empty commit diff.

```diff
diff --git a/trading_system/tree_replay/admission_context.py b/trading_system/tree_replay/admission_context.py
new file mode 100644
index 0000000..90c9f4c
--- /dev/null
+++ b/trading_system/tree_replay/admission_context.py
@@ -0,0 +1,322 @@
+"""Original tracker consumers over shared-time, explicitly published evidence."""
+from copy import deepcopy
+from dataclasses import dataclass
+from datetime import datetime
+
+from .admission_frames import AdmissionFrameRequest, AdmissionFrameSource
+from .admission_io import ArtifactSeed, CausalQuoteReader, CausalWatchLog
+from .bars import _number, _utc
+from .clock import ReplayClock
+from .state import _identity
+from .tracker_storage import TrackerStateSeed, CausalTrackerStorage, _MemoryBackend
+from ._vendor.tracker_admission import TrackerAdmission
+from ._vendor.tracker_lock import TrackerLock
+
+
+class OperationUnavailable(ValueError):
+    """The supplied operation evidence does not establish this attempted action."""
+
+
+@dataclass(frozen=True, kw_only=True)
+class BusyMarkerSeed(TrackerStateSeed):
+    """Distinct artifact identity, sharing the validated causal text seed schema."""
+
+
+@dataclass(frozen=True, kw_only=True)
+class Publication:
+    publication_id: str
+    source: str
+    available_at: datetime
+    sequence: int
+    channel: str
+    payload: object
+
+    def __post_init__(self):
+        _identity(self.publication_id, "publication_id")
+        _identity(self.source, "source")
+        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))
+        if type(self.sequence) is not int or self.sequence < 0:
+            raise ValueError("publication sequence must be a native nonnegative integer")
+        if type(self.channel) is not str or self.channel not in ("tracker", "quotes", "watch_log", "busy", "frames"):
+            raise ValueError("unsupported publication channel")
+        if self.channel == "frames":
+            if type(self.payload) is not tuple or any(type(r) is not AdmissionFrameRequest for r in self.payload):
+                raise ValueError("frames publication requires exact request tuple")
+            for request in self.payload:
+                request.__post_init__()
+        else:
+            cls = {"tracker": TrackerStateSeed, "busy": BusyMarkerSeed}.get(self.channel, ArtifactSeed)
+            if type(self.payload) is not cls:
+                raise ValueError("publication payload type does not match channel")
+            self.payload.__post_init__()
+            if cls is ArtifactSeed and self.payload.kind != self.channel:
+                raise ValueError("artifact kind does not match publication channel")
+            if self.payload.available_at != self.available_at:
+                raise ValueError("artifact publication time must equal seed availability")
+
+
+@dataclass(frozen=True, kw_only=True)
+class LockStep:
+    step_id: str
+    source: str
+    operation: str
+    started_at: datetime
+    completed_at: datetime
+    timeout: float | None
+    acquired: bool | None
+    error: str | None
+
+    def __post_init__(self):
+        _identity(self.step_id, "step_id")
+        _identity(self.source, "source")
+        for field in ("started_at", "completed_at"):
+            object.__setattr__(self, field, _utc(getattr(self, field), field))
+        if self.completed_at < self.started_at:
+            raise ValueError("lock completion precedes start")
+        if type(self.operation) is not str or self.operation not in ("prepare", "open", "acquire", "release", "close", "warn"):
+            raise ValueError("unsupported lock operation")
+        if self.error is not None:
+            if type(self.error) is not str:
+                raise ValueError("lock error must be exact text or None")
+            try:
+                self.error.encode("utf-8")
+            except UnicodeError as exc:
+                raise ValueError("lock error must be UTF-8 encodable") from exc
+        if self.operation == "acquire":
+            _number(self.timeout, "timeout")
+            if (self.error is None and type(self.acquired) is not bool) or (self.error is not None and self.acquired is not None):
+                raise ValueError("acquire requires bool success or None with supplied error")
+        elif self.timeout is not None or self.acquired is not None:
+            raise ValueError("non-acquire step cannot supply timeout or acquired")
+
+
+class _Handle:
+    def __init__(self, owner):
+        self.owner, self.closed, self.acquired = owner, False, False
+
+    def close(self):
+        self.owner._step("close", handle=self)
+
+
+class CausalAdmissionContext:
+    def __init__(self, *, instrument: str, decision_time: datetime,
+                 tracker_seed: TrackerStateSeed, quote_seed: ArtifactSeed,
+                 log_seed: ArtifactSeed, busy_seed: BusyMarkerSeed, newline: str,
+                 frame_requests: tuple[AdmissionFrameRequest, ...],
+                 publications: tuple[Publication, ...], lock_steps: tuple[LockStep, ...]):
+        self._clock = ReplayClock(decision_time)
+        self._pass_anchor = self._clock.now
+        self.instrument, self._newline = instrument, newline
+        self._validate_frames(frame_requests)
+        if type(busy_seed) is not BusyMarkerSeed:
+            raise ValueError("busy seed must be exact BusyMarkerSeed")
+        busy_seed.__post_init__()
+        if type(publications) is not tuple or any(type(p) is not Publication for p in publications):
+            raise ValueError("publications must be an exact tuple of Publication")
+        previous = None
+        ids = set()
+        for p in publications:
+            p.__post_init__()
+            key = (p.available_at, p.sequence)
+            if p.available_at < self.decision_time or (previous is not None and key <= previous) or p.publication_id in ids:
+                raise ValueError("publication schedule must have unique IDs and increasing time/sequence")
+            if p.channel == "frames":
+                self._validate_frames(p.payload)
+            previous = key
+            ids.add(p.publication_id)
+        if type(lock_steps) is not tuple or any(type(s) is not LockStep for s in lock_steps):
+            raise ValueError("lock steps must be exact tuple of LockStep")
+        end, ids = self.decision_time, set()
+        for s in lock_steps:
+            s.__post_init__()
+            if s.started_at < end or s.step_id in ids:
+                raise ValueError("lock steps must be nonoverlapping with unique IDs")
+            end = s.completed_at
+            ids.add(s.step_id)
+        self._publications, self._steps = publications, lock_steps
+        self._publication_index = self._step_index = 0
+        self._events, self._artifacts, self._frame_reads = [], [], []
+        self._handle = None
+        self._frame_requests = frame_requests
+        for channel, payload in (("tracker", tracker_seed), ("quotes", quote_seed),
+                                 ("watch_log", log_seed), ("busy", busy_seed)):
+            self._install(channel, payload)
+        self._lock = TrackerLock(self)
+        self.tracker = TrackerAdmission(self)
+        self._advance(self.decision_time)
+
+    @property
+    def decision_time(self):
+        return self._clock.now
+
+    @property
+    def pass_anchor(self):
+        return self._pass_anchor
+
+    def _validate_frames(self, requests):
+        # Constructor validation is structural; no future prices are calculated.
+        AdmissionFrameSource(instrument=self.instrument, decision_time=self.decision_time, requests=requests)
+
+    def _install(self, channel, payload):
+        at = self.decision_time
+        if channel == "frames":
+            self._frame_requests = payload
+            return
+        if channel == "tracker":
+            obj = CausalTrackerStorage(seed=payload, decision_time=at, clock=self._clock)
+            self._storage = obj
+        elif channel == "quotes":
+            obj = CausalQuoteReader(seed=payload, decision_time=at, clock=self._clock)
+            self._quotes = obj
+        elif channel == "watch_log":
+            obj = CausalWatchLog(seed=payload, decision_time=at, newline=self._newline, clock=self._clock)
+            self._log = obj
+        else:
+            obj = _MemoryBackend(payload, at, self._clock)
+            self._busy = obj
+        self._artifacts.append(dict(channel=channel, seed_id=payload.seed_id, source=payload.source, instance=obj))
+
+    def _call(self, operation, action, **details):
+        event = dict(sequence=len(self._events), operation=operation,
+                     started_at=self.decision_time.isoformat(), status="BLOCKED",
+                     exception_type=None, blocker=None, **details)
+        self._events.append(event)
+        try:
+            result = action()
+        except Exception as exc:
+            event.update(exception_type=type(exc).__name__, blocker=str(exc))
+            raise
+        else:
+            event["status"] = "AVAILABLE"
+            return result
+        finally:
+            event["completed_at"] = self.decision_time.isoformat()
+
+    def _advance(self, at):
+        at = _utc(at, "decision_time")
+        if at < self.decision_time:
+            raise ValueError("context cannot move backward")
+        while self._publication_index < len(self._publications):
+            p = self._publications[self._publication_index]
+            if p.available_at > at:
+                break
+            self._clock.advance_to(p.available_at)
+            self._call("publication", lambda: self._install(p.channel, p.payload),
+                       publication_id=p.publication_id, source=p.source, channel=p.channel,
+                       publication_sequence=p.sequence)
+            self._publication_index += 1
+        self._clock.advance_to(at)
+
+    def advance_to(self, decision_time):
+        return self._call("advance", lambda: self._advance(decision_time))
+
+    def now_epoch(self):
+        return self._call("clock", lambda: self.decision_time.timestamp())
+
+    def load(self):
+        return self._call("load", self._storage.load)
+
+    def save(self, rows, *, allow_shrink=False):
+        return self._call("save", lambda: self._storage.save(rows, allow_shrink=allow_shrink))
+
+    def quote_payload(self):
+        return self._call("quote_payload", self._quotes.quote_payload)
+
+    def event_log_reader(self):
+        return self._call("event_log_reader", self._log.event_log_reader)
+
+    def log(self, row):
+        return self._call("log", lambda: self._log.log(row))
+
+    def _frame_call(self, operation, action):
+        source = AdmissionFrameSource(instrument=self.instrument, decision_time=self.decision_time,
+                                      requests=self._frame_requests)
+        self._frame_reads.append((self.decision_time, source))
+        return self._call(operation, lambda: action(source))
+
+    def read_symbol(self, symbol, tfs=("4h", "1h", "15m", "5m")):
+        return self._frame_call("read_symbol", lambda s: s.read_symbol(symbol, tfs))
+
+    def fetch_corrected(self, symbol, timeframe, lookback_days):
+        return self._frame_call("fetch_corrected", lambda s: s.fetch_corrected(symbol, timeframe, lookback_days))
+
+    def locked(self, *, wait=None, skip_if_busy=False):
+        return self._lock.locked(wait=wait, skip_if_busy=skip_if_busy)
+
+    def _step(self, operation, *, handle=None, timeout=None, message=None):
+        def consume():
+            if self._step_index == len(self._steps):
+                raise OperationUnavailable("LOCK_STEP_MISSING")
+            step = self._steps[self._step_index]
+            if step.operation != operation or step.started_at != self.decision_time:
+                raise OperationUnavailable("LOCK_STEP_OPERATION_OR_TIME_MISMATCH")
+            if operation == "acquire" and (type(timeout) not in (int, float) or step.timeout != timeout):
+                raise OperationUnavailable("LOCK_STEP_TIMEOUT_MISMATCH")
+            if operation in ("acquire", "release", "close"):
+                if handle is not self._handle or handle is None or handle.closed:
+                    raise OperationUnavailable("LOCK_HANDLE_MISMATCH")
+                if operation == "release" and not handle.acquired:
+                    raise OperationUnavailable("LOCK_NOT_ACQUIRED")
+            elif operation in ("prepare", "open") and self._handle is not None:
+                raise OperationUnavailable("LOCK_HANDLE_ALREADY_OPEN")
+            self._events[-1].update(step_id=step.step_id, evidence_source=step.source)
+            self._step_index += 1
+            self._advance(step.completed_at)
+            if operation == "close":
+                # A matched close attempt ends this local handle, even on supplied
+                # OSError. This says nothing about a historical OS descriptor.
+                handle.closed = True
+                self._handle = None
+            if step.error is not None:
+                raise OSError(step.error)
+            if operation == "open":
+                self._handle = _Handle(self)
+                return self._handle
+            if operation == "acquire":
+                handle.acquired = step.acquired
+                return step.acquired
+            if operation == "release":
+                handle.acquired = False
+        return self._call("lock."+operation, consume, timeout=timeout, message=message)
+
+    def ensure_lock_directory(self):
+        return self._step("prepare")
+
+    def open_lock(self):
+        return self._step("open")
+
+    def try_acquire(self, handle, *, timeout):
+        return self._step("acquire", handle=handle, timeout=timeout)
+
+    def release(self, handle):
+        return self._step("release", handle=handle)
+
+    def warn(self, text):
+        return self._step("warn", message=text)
+
+    def read_busy(self):
+        return self._call("busy.read", self._busy.read_text)
+
+    def write_busy(self, text):
+        return self._call("busy.write", lambda: self._busy.atomic_write(text))
+
+    def clear_busy(self):
+        def clear():
+            self._busy.status, self._busy.text = "ABSENT", None
+        return self._call("busy.clear", lambda: self._busy.call("clear", clear))
+
+    def report(self):
+        artifacts = []
+        for epoch in self._artifacts:
+            obj = epoch["instance"]
+            item = {k: epoch[k] for k in ("channel", "seed_id", "source")}
+            item["trace"] = obj.trace
+            if epoch["channel"] == "tracker":
+                item.update(creation_effects=obj.creation_effects, quarantines=obj.quarantine_artifacts)
+            artifacts.append(item)
+        return deepcopy(dict(pass_anchor=self.pass_anchor.isoformat(),
+            decision_time=self.decision_time.isoformat(), events=self._events, artifacts=artifacts,
+            frames=[dict(decision_time=at.isoformat(), fetch_trace=s.fetch_trace,
+                         matrix_trace=s.matrix_trace) for at, s in self._frame_reads],
+            publications_consumed=self._publication_index, lock_steps_consumed=self._step_index,
+            ready_for_replay=False, ready_for_training=False))

```

```diff
diff --git a/tests/tree_replay/test_admission_context.py b/tests/tree_replay/test_admission_context.py
new file mode 100644
index 0000000..707747c
--- /dev/null
+++ b/tests/tree_replay/test_admission_context.py
@@ -0,0 +1,362 @@
+"""Real causal providers and original tracker; all supplied history is synthetic."""
+from dataclasses import replace
+from datetime import timedelta
+import importlib
+import importlib.util
+import json
+
+import pytest
+
+from trading_system.tree_replay.admission_io import ArtifactSeed, InputUnavailable
+from trading_system.tree_replay.tracker_storage import TrackerStateSeed, StateUnavailable
+from trading_system.tree_replay._vendor.pricing import Plan
+from trading_system.tree_replay._vendor.tracker_lock import LockBusy
+from test_admission_frames import T, SYMBOL, KEYS, request
+
+
+def api():
+    name = "trading_system.tree_replay.admission_context"
+    assert importlib.util.find_spec(name) is not None, "causal admission context missing"
+    return importlib.import_module(name)
+
+
+def seed(channel, *, at=T, status="PRESENT", value=None, through=None):
+    common = dict(seed_id=channel+at.isoformat(), source="synthetic", observed_at=at,
+                  available_at=at, covered_through=through or T+timedelta(minutes=5), status=status)
+    if channel in ("tracker", "busy"):
+        cls = TrackerStateSeed if channel == "tracker" else api().BusyMarkerSeed
+        return cls(**common, text=(value if value is not None else "{}") if status == "PRESENT" else None)
+    content = (json.dumps({SYMBOL: {"lp": 100, "ts": at.timestamp()}}) if channel == "quotes"
+               else b"") if value is None else value
+    return ArtifactSeed(**common, kind=channel, content=content if status == "PRESENT" else None)
+
+
+def step(name, start=T, end=None, *, index=0, acquired=True, error=None, timeout=30.0):
+    return api().LockStep(step_id=f"{index}:{name}", source="synthetic", operation=name,
+        started_at=start, completed_at=end or start, timeout=timeout if name == "acquire" else None,
+        acquired=acquired if name == "acquire" and error is None else None, error=error)
+
+
+def steps(*, start=T, seconds=2, acquired=True, release_error=None, acquire_error=None):
+    end = start+timedelta(seconds=seconds)
+    rows = [step("prepare", start, index=0), step("open", start, index=1),
+            step("acquire", start, end, index=2, acquired=acquired, error=acquire_error)]
+    if acquired and acquire_error is None:
+        rows.append(step("release", end, index=3, error=release_error))
+    rows.append(step("close", end, index=4))
+    return tuple(rows)
+
+
+def publication(channel, payload, *, at=None, seq=0, name="pub"):
+    return api().Publication(publication_id=name, source="synthetic", channel=channel,
+        payload=payload, available_at=at or payload.available_at, sequence=seq)
+
+
+def context(**changes):
+    return api().CausalAdmissionContext(**(dict(instrument=SYMBOL, decision_time=T,
+        tracker_seed=seed("tracker"), quote_seed=seed("quotes"), log_seed=seed("watch_log"),
+        busy_seed=seed("busy", status="ABSENT"), newline="LF",
+        frame_requests=tuple(request(tf, days) for tf, days in KEYS),
+        publications=(), lock_steps=steps()) | changes))
+
+
+def plan(**changes):
+    return replace(Plan(SYMBOL, 100., "reversal", "לונג", entry=100., stop=90.,
+                        targets=[("TP1", 120.)], reasons=["רמה: DAY-OPEN"]), **changes)
+
+
+def test_real_frames_quotes_storage_lock_and_tracker_record_are_composed():
+    c = context()
+    assert c.tracker.record(plan())
+    row = next(iter(c.load().values()))
+    assert row["bias_at_send"] == {"4h": -41.25, "1h": -41.25}
+    assert row["ts"] == row["filled_ts"] == (T+timedelta(seconds=2)).timestamp()
+    assert row["state"] == "OPEN" and row["revalidation_verified"] is False
+    assert c.pass_anchor == T and c.decision_time == T+timedelta(seconds=2)
+    r = c.report()
+    assert r["lock_steps_consumed"] == 5 and not r["ready_for_training"] and not r["ready_for_replay"]
+    assert [e["operation"] for e in r["events"]][:3] == ["read_symbol", "read_symbol", "quote_payload"]
+    assert [len(f["fetch_trace"]) for f in r["frames"]] == [2, 5]
+    assert all(e["status"] == "AVAILABLE" for e in r["events"])
+
+
+def test_open_exposure_published_during_acquire_prevents_record_without_backdating():
+    at = T+timedelta(seconds=1)
+    body = {"other": {"symbol": SYMBOL, "direction": "לונג", "state": "OPEN", "entry": 100., "ts": at.timestamp()}}
+    p = publication("tracker", seed("tracker", at=at, value=json.dumps(body)))
+    c = context(publications=(p,))
+    assert c.load() == {}  # Future input supplied to constructor is not current state.
+    assert not c.tracker.record(plan())
+    assert c.load() == body
+    assert c.report()["publications_consumed"] == 1
+    assert c.pass_anchor == T and c.decision_time == T+timedelta(seconds=2)
+
+
+def test_quote_publication_changes_later_reads_not_already_computed_born_state():
+    at = T+timedelta(seconds=1)
+    p = publication("quotes", seed("quotes", at=at, value=json.dumps({SYMBOL: {"lp": 200, "ts": at.timestamp()}})))
+    c = context(publications=(p,))
+    assert c.tracker.record(plan())
+    assert next(iter(c.load().values()))["state"] == "OPEN"  # born decision was pre-lock.
+    assert c.tracker._live_prices() == {SYMBOL: 200.}
+
+
+def test_same_time_publications_follow_explicit_sequence_without_merging_images():
+    at = T+timedelta(seconds=1)
+    first = publication("tracker", seed("tracker", at=at, value='{"first":1}'), seq=2, name="a")
+    second = publication("tracker", seed("tracker", at=at, value='{"second":2}'), seq=3, name="b")
+    c = context(publications=(first, second))
+    c.advance_to(at)
+    assert c.load() == {"second": 2}
+    assert [e["publication_id"] for e in c.report()["events"] if e["operation"] == "publication"] == ["a", "b"]
+
+
+def test_generated_state_and_effects_survive_advance_and_replacement_history():
+    at = T+timedelta(seconds=4)
+    p = publication("tracker", seed("tracker", at=at, value='{"external":{}}'))
+    c = context(publications=(p,))
+    c.save({"generated": {"state": "PENDING"}})
+    c.advance_to(T+timedelta(seconds=2))
+    assert c.load() == {"generated": {"state": "PENDING"}}
+    c.advance_to(at)
+    assert c.load() == {"external": {}}
+    states = [a for a in c.report()["artifacts"] if a["channel"] == "tracker"]
+    assert len(states) == 2 and states[0]["creation_effects"][0]["key"] == "generated"
+
+
+def test_real_rejection_consumer_reads_same_pass_append_and_old_reader_stays_old():
+    c = context()
+    reader = c.event_log_reader()
+    def recent():
+        return c.tracker._recent_rejection(SYMBOL, "לונג", T.timestamp()-10, c.now_epoch(), 100.)
+    assert recent() is None
+    c.log({"kind": "rejection", "symbol": SYMBOL, "direction": "לונג",
+           "zone_lo": 98, "zone_hi": 102, "levels": ["PSY"], "close": 100, "wick_atr": .5})
+    c.advance_to(T+timedelta(seconds=2))
+    assert recent()["levels"] == ["PSY"] and recent()["age_s"] == 2.
+    assert reader.read() == b""
+
+
+def test_log_replacement_is_full_image_and_keeps_prepublication_reader_prefix():
+    at = T+timedelta(seconds=1)
+    p = publication("watch_log", seed("watch_log", at=at, value=b"external\n"))
+    c = context(log_seed=seed("watch_log", value=b"old\n"), publications=(p,))
+    reader = c.event_log_reader()
+    c.advance_to(at)
+    assert c.event_log_reader().read() == b"external\n" and reader.read() == b"old\n"
+    assert len([a for a in c.report()["artifacts"] if a["channel"] == "watch_log"]) == 2
+
+
+def test_frame_publication_changes_actual_calculations_at_publication_time_only():
+    at = T+timedelta(seconds=1)
+    new = tuple(request(tf, days, price=110.) for tf, days in KEYS)
+    c = context(publications=(publication("frames", new, at=at),))
+    assert c.read_symbol(SYMBOL, ("4h",))["4h"].close == 100.
+    c.advance_to(at)
+    assert c.read_symbol(SYMBOL, ("4h",))["4h"].close == 110.
+
+
+def test_data_gap_stays_blocked_until_next_published_image():
+    at = T+timedelta(seconds=4)
+    c = context(tracker_seed=seed("tracker", through=T+timedelta(seconds=1)),
+        publications=(publication("tracker", seed("tracker", at=at, value='{"new":{}}')),))
+    c.advance_to(T+timedelta(seconds=2))
+    with pytest.raises(StateUnavailable, match="COVERAGE_EXPIRED"):
+        c.load()
+    c.advance_to(at)
+    assert c.load() == {"new": {}}
+
+
+@pytest.mark.parametrize("channel", ["tracker", "quotes", "watch_log"])
+def test_source_caught_missing_inputs_remain_in_context_and_child_traces(channel):
+    kw = {dict(tracker="tracker_seed", quotes="quote_seed", watch_log="log_seed")[channel]: seed(channel, status="UNKNOWN")}
+    c = context(**kw)
+    if channel == "tracker":
+        assert c.tracker.has_open(SYMBOL, "לונג") is True
+    elif channel == "quotes":
+        assert c.tracker._live_prices() == {}
+    else:
+        assert c.tracker._recent_rejection(SYMBOL, "לונג", 0, T.timestamp(), 100) is None
+    r = c.report()
+    assert any(e["status"] == "BLOCKED" for e in r["events"])
+    assert any(e["status"] == "BLOCKED" for a in r["artifacts"] for e in a["trace"])
+
+
+def test_missing_frame_request_keeps_original_catch_and_failure_evidence():
+    c = context(frame_requests=())
+    assert c.tracker._higher_bias(SYMBOL) is None
+    r = c.report()
+    assert r["frames"][0]["fetch_trace"][0]["blocker"] == "REQUEST_MISSING"
+    assert r["events"][0]["status"] == "BLOCKED"
+
+
+@pytest.mark.parametrize("fault", ["missing", "name", "timeout", "time"])
+def test_lock_evidence_is_required_and_exact_not_default_success(fault):
+    rows = steps()
+    if fault == "missing":
+        rows = ()
+    elif fault == "name":
+        rows = (replace(rows[0], operation="open"),)+rows[1:]
+    elif fault == "timeout":
+        rows = rows[:2]+(replace(rows[2], timeout=3.),)+rows[3:]
+    else:
+        rows = tuple(replace(s, started_at=s.started_at+timedelta(seconds=1),
+                             completed_at=s.completed_at+timedelta(seconds=1)) for s in rows)
+    c = context(lock_steps=rows)
+    with pytest.raises(api().OperationUnavailable):
+        c.tracker.record(plan())
+    assert c.load() == {}
+    assert any(e["status"] == "BLOCKED" for e in c.report()["events"])
+
+
+@pytest.mark.parametrize("where", ["acquire", "release"])
+def test_supplied_io_failure_advances_clock_and_closes_handle_with_source_semantics(where):
+    c = context(lock_steps=steps(**{where+"_error": "supplied failure"}))
+    with pytest.raises(OSError, match="supplied failure"):
+        c.tracker.record(plan())
+    assert c.decision_time == T+timedelta(seconds=2)
+    assert c.report()["events"][-1]["operation"] == "lock.close"
+    assert bool(c.load()) is (where == "release")  # Source save can precede release failure.
+
+
+def test_nested_source_lock_uses_one_script_and_preserves_depth():
+    c = context()
+    with c.locked():
+        with c.locked(skip_if_busy=True):
+            assert c.now_epoch() == (T+timedelta(seconds=2)).timestamp()
+    assert c.report()["lock_steps_consumed"] == 5
+
+
+def test_resolver_busy_marks_then_skips_without_invented_release():
+    c = context(lock_steps=steps(acquired=False))
+    with pytest.raises(LockBusy):
+        with c.locked(wait=30., skip_if_busy=True):
+            pytest.fail("must skip initial refusal")
+    assert c.report()["lock_steps_consumed"] == 4
+    assert any(e["operation"] == "busy.write" for e in c.report()["events"])
+
+
+def test_unknown_busy_clear_failure_survives_source_best_effort_catch():
+    c = context(busy_seed=seed("busy", status="UNKNOWN"))
+    with c.locked():
+        pass
+    assert any(e["operation"] == "busy.clear" and e["status"] == "BLOCKED" for e in c.report()["events"])
+
+
+def test_report_is_detached_and_does_not_expose_future_publication_payloads():
+    at = T+timedelta(seconds=3)
+    c = context(publications=(publication("tracker", seed("tracker", at=at, value='{"secret_future":42}')),))
+    c.load()
+    report = c.report()
+    assert "secret_future" not in json.dumps(report)
+    report["events"][0]["status"] = "changed"
+    assert c.report()["events"][0]["status"] == "AVAILABLE"
+
+
+@pytest.mark.parametrize("fault", ["duplicate_id", "reverse_order", "before_initial", "bad_payload"])
+def test_invalid_publication_schedule_rejected_before_context_runs(fault):
+    at = T+timedelta(seconds=2)
+    a = publication("tracker", seed("tracker", at=at), name="a")
+    b = publication("quotes", seed("quotes", at=at), seq=1, name="b")
+    if fault == "duplicate_id":
+        rows = (a, replace(b, publication_id="a"))
+    elif fault == "reverse_order":
+        rows = (b, a)
+    elif fault == "before_initial":
+        rows = (publication("tracker", seed("tracker", at=T-timedelta(seconds=1))),)
+    else:
+        with pytest.raises(ValueError):
+            replace(a, payload=seed("quotes", at=at))
+        return
+    with pytest.raises(ValueError):
+        context(publications=rows)
+
+
+def test_bad_advance_has_no_effect_on_clock_publication_cursor_or_generated_state():
+    c = context()
+    c.save({"a": {}})
+    before = c.report()["publications_consumed"]
+    with pytest.raises(ValueError):
+        c.advance_to(T-timedelta(microseconds=1))
+    assert c.decision_time == T and c.load() == {"a": {}}
+    assert c.report()["publications_consumed"] == before
+
+
+def test_consumed_lock_operations_retain_exact_evidence_identity():
+    c = context()
+    with c.locked():
+        pass
+    events = [e for e in c.report()["events"] if e["operation"].startswith("lock.")]
+    assert [e["step_id"] for e in events] == ["0:prepare", "1:open", "2:acquire", "3:release", "4:close"]
+    assert all(e["evidence_source"] == "synthetic" for e in events)
+
+
+def test_bool_timeout_call_is_not_certified_by_numeric_evidence():
+    c = context(lock_steps=tuple(replace(s, timeout=1.) if s.operation == "acquire" else s for s in steps()))
+    with pytest.raises(api().OperationUnavailable):
+        with c.locked(wait=True):
+            pytest.fail("boolean wait must not match numeric evidence")
+
+
+@pytest.mark.parametrize("change", [dict(sequence=True), dict(sequence=-1), dict(sequence=1.),
+    dict(publication_id=" "), dict(source="bad\ud800"), dict(channel="wrong"),
+    dict(available_at=T.replace(tzinfo=None)), dict(available_at=T+timedelta(seconds=1))])
+def test_publication_validation_rejects_ambiguous_identity_order_and_time(change):
+    p = publication("tracker", seed("tracker"))
+    with pytest.raises(ValueError):
+        replace(p, **change)
+
+
+@pytest.mark.parametrize("change", [dict(timeout=True), dict(timeout=float("nan")), dict(timeout=None),
+    dict(acquired=1), dict(error=123), dict(error="bad\ud800", acquired=None),
+    dict(error="failure"), dict(operation="unknown"), dict(step_id=" "),
+    dict(completed_at=T-timedelta(microseconds=1)), dict(started_at=T.replace(tzinfo=None))])
+def test_lock_step_validation_rejects_invalid_or_ambiguous_evidence(change):
+    s = step("acquire")
+    with pytest.raises(ValueError):
+        replace(s, **change)
+
+
+@pytest.mark.parametrize("fault", ["duplicate", "overlap", "list"])
+def test_lock_schedule_is_validated_before_any_port_call(fault):
+    rows = steps()
+    if fault == "duplicate":
+        rows = rows[:1]+(replace(rows[1], step_id=rows[0].step_id),)+rows[2:]
+    elif fault == "overlap":
+        rows = rows[:3]+(replace(rows[3], started_at=T+timedelta(seconds=1)),)+rows[4:]
+    else:
+        rows = list(rows)
+    with pytest.raises(ValueError):
+        context(lock_steps=rows)
+
+
+def test_unreadable_busy_marker_can_be_reset_by_original_best_effort_path():
+    c = context(busy_seed=seed("busy", status="UNREADABLE"), lock_steps=steps(acquired=False))
+    with pytest.raises(LockBusy):
+        with c.locked(wait=30., skip_if_busy=True):
+            pytest.fail("fresh marker reset should skip")
+    assert c.read_busy() == str((T+timedelta(seconds=2)).timestamp())
+    assert any(e["operation"] == "busy.read" and e["status"] == "BLOCKED" for e in c.report()["events"])
+
+
+def test_stalled_resolver_consumes_warning_evidence_and_proceeds_unlocked():
+    rows = steps(acquired=False)
+    end = T+timedelta(seconds=2)
+    rows = rows[:-1]+(step("warn", end, index=3), rows[-1])
+    c = context(busy_seed=seed("busy", value=str(T.timestamp()-121)), lock_steps=rows)
+    with c.locked(wait=30., skip_if_busy=True):
+        c.save({"stalled": {}})
+    assert c.load() == {"stalled": {}}
+    warning = next(e for e in c.report()["events"] if e["operation"] == "lock.warn")
+    assert "123s" in warning["message"] and warning["status"] == "AVAILABLE"
+
+
+def test_open_failure_uses_supplied_completion_time_without_invented_handle_close():
+    rows = (step("prepare", index=0), step("open", end=T+timedelta(seconds=1), index=1, error="open failed"))
+    c = context(lock_steps=rows)
+    with pytest.raises(OSError, match="open failed"):
+        with c.locked():
+            pytest.fail("open did not succeed")
+    assert c.decision_time == T+timedelta(seconds=1)
+    assert c.report()["events"][-1]["operation"] == "lock.open"
+    assert c.report()["lock_steps_consumed"] == 2

```

```diff
diff --git a/docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md b/docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md
new file mode 100644
index 0000000..65ee493
--- /dev/null
+++ b/docs/architecture/CAUSAL-ADMISSION-CONTEXT-USAGE.md
@@ -0,0 +1,112 @@
+# Shared-time causal admission providers
+
+`CausalAdmissionContext` connects actual accepted TrackerAdmission and TrackerLock
+to real causal frame, tracker-storage, quote and raw-log providers. It is an
+in-memory source-consumer context, not the market-watch outer loop or simulator.
+
+```python
+from trading_system.tree_replay.admission_context import CausalAdmissionContext
+
+context = CausalAdmissionContext(
+    instrument=instrument, decision_time=pass_time,
+    tracker_seed=tracker_seed, quote_seed=quote_seed, log_seed=log_seed,
+    busy_seed=busy_seed, newline="LF", frame_requests=admission_requests,
+    publications=publications, lock_steps=lock_steps,
+)
+recorded = context.tracker.record(original_selected_plan, variant=source_variant)
+evidence = context.report()
+```
+
+All variables in this wiring example are explicit caller inputs. Do not rebuild
+the Plan from reduced public producer evidence; use the accepted internal handoff.
+`recorded` is the original advisory result, NOT a broker fill, a label, a complete
+quality approval, or evidence that outer entry gates ran. `report()` always keeps
+ready_for_replay and ready_for_training false. It does not automatically certify
+its inputs or convert source fallbacks into new trading vetoes.
+
+## Time, publications and artifacts
+
+pass_anchor stays fixed at construction. decision_time advances only through
+advance_to(T) or a supplied lock step. The clock is private; no public child log
+or storage object is exposed for bypassing publication application. The original
+tracker computes bias/thesis/born state before locking and reloads state/timestamps
+after acquiring. Existing coherent-T producer interfaces remain unchanged.
+
+Initial inputs are exact TrackerStateSeed, ArtifactSeed(kind quotes/watch_log),
+BusyMarkerSeed and tuple[AdmissionFrameRequest,...]. BusyMarkerSeed is a distinct
+frozen dataclass sharing TrackerStateSeed's text/time/identity validation, not JSON
+state semantics. The busy provider reuses the accepted private causal text backend;
+known absence raises on read and unreadable text can be reset by original policy.
+
+Publication fields: publication_id, source, available_at, sequence, channel,
+payload. Channels tracker/quotes/watch_log/busy require matching exact seeds whose
+available_at equals publication time. Frames use the exact request tuple. Sequence
+is a native nonnegative integer. The tuple must already be strictly ordered by
+(available_at, sequence) with unique publication IDs, none before pass_anchor.
+No implicit sorting, merging or early exposure occurs. A full image explicitly
+replaces its channel; generated state/log effects persist until replacement.
+Earlier provider traces/effects and captured log-reader prefixes are retained.
+
+Future frames/quotes may be supplied structurally at construction, but only current
+published bindings and accepted as-of dependency guards are consumed. Advancing
+past a coverage gap does not fill it. Reads then fail until sufficient evidence
+is published; clock movement itself is not a data-quality claim. Availability and
+coverage remain caller attestations, not proof of historical feed truth, internal
+payload correctness or original symbol/contract equivalence.
+
+## Lock steps are evidence, not guessed delays
+
+Every operation has an explicit LockStep: step_id, source, operation, started_at,
+completed_at, timeout, acquired, error. Supported operations are prepare/open/
+acquire/release/close/warn. For acquire, timeout is a finite native number and a
+successful step requires a bool acquired. On supplied error acquired is None.
+Other operations require timeout/acquired None. Error is None or UTF-8 text raised
+as OSError; other historical exception classes are not simulated by this contract.
+All fields are required, IDs unique, and steps are nonoverlapping in supplied order.
+
+An uncontended writer normally consumes prepare, open, acquire, release, close.
+A failed acquisition omits release; a stalled resolver may require warn before
+close. Actual policy owns the branch. A nested call consumes no new lock steps.
+Missing/mismatched operation, time, timeout or handle is OperationUnavailable,
+not a default acquired/failed result. A boolean timeout cannot match numeric1.
+Matched operations record step identity/source, apply publications through their
+supplied completion time, and then return or raise. A30second timeout does not
+mean30seconds elapsed. A supplied2second acquisition yields post-lock reads atT+2.
+
+Busy read/write/clear uses causal in-memory text semantics, not scripted filesystem
+permissions. UNKNOWN/unpublished/expired evidence blocks these actions; source may
+catch the failure, but traces keep it. Known missing clear succeeds. A matched
+close attempt ends the local handle even on supplied OSError; this is an explicit
+local lifecycle convention, not certification of a historical OS descriptor.
+There is no operating-system lock, scheduler thread, process or network activity.
+
+## Ports and evidence
+
+Context exposes load/save, read_symbol/fetch_corrected, quote_payload,
+event_log_reader, log, now_epoch, locked and original tracker methods via tracker.
+Frame calls instantiate the real AdmissionFrameSource at current time; no fake
+matrix scores are used. report() detaches ordered attempt/start/end/error events,
+each consumed artifact's traces, storage creation/quarantine effects, frame traces,
+and consumed publication/lock-step counts. Unconsumed future payloads are omitted.
+
+AVAILABLE/BLOCKED describe individual attempts, not a new source trading decision.
+For example, a known absent quote read can fail while the source deliberately
+uses its build-close fallback. Unknown coverage is different evidence. The future
+whole-caller/data-quality assessment must preserve that distinction. A successful
+record followed by release failure is not rolled back: source storage may already
+contain it, even though record raised. No atomic whole-pass transaction is claimed.
+
+All providers/traces are retained in memory. This is not yet a disk-backed ten-year
+archive, full checkpoint/resume format, complete watch state, separate market-watch
+lock, mixed-clock producer, resolver lifecycle or cross-producer arbitration.
+Those and the economic simulator/dataset/model/evaluation remain required.
+
+## Verification
+
+```powershell
+python -m pytest tests/tree_replay/test_admission_context.py tests/tree_replay/test_shared_clock.py tests/tree_replay/test_tracker_lock.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py tests/tree_replay/test_admission_frames.py -q --tb=short
+```
+
+Source storage/watch/tracker/lock audits remain unchanged and require the pinned
+retained checkout parent. Tests use synthetic evidence and literal expected real
+matrix values, not historical market outcomes. No data acquisition or training.

```

