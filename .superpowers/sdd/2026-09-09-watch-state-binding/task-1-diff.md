# Watch storage Task1 full new-file package

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; actual untracked files.

```diff
diff --git a/trading_system/tree_replay/_vendor/watch_storage.py b/trading_system/tree_replay/_vendor/watch_storage.py
new file mode 100644
index 0000000..0dc71cd
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/watch_storage.py
@@ -0,0 +1,18 @@
+"""Pinned market_watch.main persistence statements over explicit offline ports."""
+import json
+
+
+class WatchStorage:
+    def __init__(self, source):
+        self.source = source
+
+    def load(self):
+        st = json.loads(self.source.read_text()) if self.source.exists() else {}
+        return st
+
+    def save_before_producers(self, st):
+        self.source.ensure_directory(exist_ok=True)
+        self.source.write_text(json.dumps(st))
+
+    def save_final(self, st):
+        self.source.write_text(json.dumps(st))

```

```diff
diff --git a/trading_system/tree_replay/watch_storage.py b/trading_system/tree_replay/watch_storage.py
new file mode 100644
index 0000000..bdaa43f
--- /dev/null
+++ b/trading_system/tree_replay/watch_storage.py
@@ -0,0 +1,57 @@
+"""Causal completed watch-state writes, separate from tracker storage policy."""
+from copy import deepcopy
+from dataclasses import dataclass, replace
+from datetime import datetime
+
+from .bars import _utc
+from .clock import ReplayClock, _validate_binding
+from .tracker_storage import TrackerStateSeed, _MemoryBackend
+from ._vendor.watch_storage import WatchStorage
+
+
+@dataclass(frozen=True, kw_only=True)
+class WatchStateSeed(TrackerStateSeed):
+    """Distinct watch artifact, with the accepted causal text evidence schema."""
+
+
+class _WatchBackend(_MemoryBackend):
+    def ensure_directory(self, *, exist_ok):
+        # Completed in-memory port attempt, not historical filesystem permission.
+        return self.call("ensure_directory", lambda: None)
+
+    def write_text(self, text):
+        def write():
+            text.encode("utf-8")
+            self.text, self.status = text, "PRESENT"
+        return self.call("write_text", write)
+
+
+class CausalWatchStorage(WatchStorage):
+    def __init__(self, *, seed: WatchStateSeed, decision_time: datetime,
+                 clock: ReplayClock | None = None):
+        if type(seed) is not WatchStateSeed:
+            raise ValueError("seed must be an exact WatchStateSeed")
+        seed.__post_init__()
+        at = _utc(decision_time, "decision_time")
+        _validate_binding(clock, at)
+        super().__init__(_WatchBackend(seed, at, clock))
+
+    def load(self):
+        return self.source.call("load", super().load)
+
+    def save_before_producers(self, st):
+        return self.source.call("save_before_producers", lambda:
+            super(CausalWatchStorage, self).save_before_producers(st))
+
+    def save_final(self, st):
+        return self.source.call("save_final", lambda:
+            super(CausalWatchStorage, self).save_final(st))
+
+    def snapshot(self):
+        return self.source.call("snapshot", lambda: replace(self.source.seed,
+            observed_at=self.source.decision_time, available_at=self.source.decision_time,
+            status=self.source.status, text=self.source.text))
+
+    @property
+    def trace(self):
+        return deepcopy(self.source.trace)

```

```diff
diff --git a/tests/tree_replay/test_watch_storage.py b/tests/tree_replay/test_watch_storage.py
new file mode 100644
index 0000000..681c682
--- /dev/null
+++ b/tests/tree_replay/test_watch_storage.py
@@ -0,0 +1,175 @@
+"""Watch state keeps source JSON/persistence semantics, not tracker-save rules."""
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+import json
+
+import pytest
+
+from trading_system.tree_replay.clock import ReplayClock
+from trading_system.tree_replay.tracker_storage import TrackerStateSeed, StateUnavailable
+
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+
+
+def api():
+    name = "trading_system.tree_replay.watch_storage"
+    assert importlib.util.find_spec(name) is not None, "causal watch storage missing"
+    return importlib.import_module(name)
+
+
+def seed(text="{}", **changes):
+    return api().WatchStateSeed(**(dict(seed_id="watch-test", source="synthetic",
+        observed_at=T, available_at=T, covered_through=T+timedelta(seconds=10),
+        status="PRESENT", text=text) | changes))
+
+
+def store(text="{}", *, at=T, clock=None, **changes):
+    return api().CausalWatchStorage(seed=seed(text, **changes), decision_time=at, clock=clock)
+
+
+def test_heterogeneous_mutations_and_deletion_persist_only_on_explicit_save():
+    s = store('{"cooldown":7,"episode":{"ts":8},"remove":true}')
+    working = s.load()
+    working.pop("remove")
+    working["cooldown"] = 9
+    working["episode"]["ts"] = 10
+    assert s.load() == {"cooldown": 7, "episode": {"ts": 8}, "remove": True}
+    s.save_before_producers(working)
+    assert s.snapshot().text == '{"cooldown": 9, "episode": {"ts": 10}}'
+    working["episode"]["ts"] = 11
+    assert s.load()["episode"]["ts"] == 10
+    s.save_final(working)
+    assert s.load()["episode"]["ts"] == 11
+
+
+def test_first_save_and_final_save_have_different_directory_effects():
+    s = store()
+    s.save_before_producers({"a": 1})
+    s.save_final({"b": 2})
+    assert [e["operation"] for e in s.trace] == [
+        "save_before_producers", "ensure_directory", "write_text", "save_final", "write_text"]
+    assert s.load() == {"b": 2}
+
+
+def test_source_serialization_preserves_order_and_uses_default_ascii_spacing():
+    s = store()
+    s.save_final({"z": 2, "a": "א", "b": [True, None]})
+    assert s.snapshot().text == '{"z": 2, "a": "\\u05d0", "b": [true, null]}'
+
+
+@pytest.mark.parametrize("text,want", [("null", None), ("[1, false]", [1, False]), ("3", 3), ('"x"', "x")])
+def test_nonobject_json_is_not_silently_normalized(text, want):
+    s = store(text)
+    assert s.load() == want
+    s.save_final(want)
+    assert s.load() == want
+
+
+def test_watch_save_can_delete_majority_without_tracker_shrink_guard():
+    s = store('{"a":1,"b":2,"c":3,"d":4}')
+    s.save_final({"d": 4})
+    assert s.load() == {"d": 4}
+    assert [e["operation"] for e in s.trace][:2] == ["save_final", "write_text"]
+
+
+def test_absent_load_is_known_empty_but_not_a_fabricated_present_file():
+    s = store(None, status="ABSENT")
+    assert s.load() == {}
+    assert s.snapshot().status == "ABSENT"
+    s.save_final({"new": 0})
+    assert s.snapshot().status == "PRESENT" and s.load() == {"new": 0}
+
+
+def test_unreadable_file_raises_on_load_but_can_be_overwritten_without_reread():
+    s = store(None, status="UNREADABLE")
+    with pytest.raises(OSError):
+        s.load()
+    assert [e["status"] for e in s.trace] == ["BLOCKED", "AVAILABLE", "BLOCKED"]
+    s.save_final({"new": 1})
+    assert s.load() == {"new": 1}
+
+
+def test_malformed_json_raises_and_retains_outer_error_not_empty_state():
+    s = store("{broken")
+    with pytest.raises(json.JSONDecodeError):
+        s.load()
+    assert s.trace[0]["status"] == "BLOCKED"
+    assert s.trace[0]["exception_type"] == "JSONDecodeError"
+    assert s.snapshot().text == "{broken"
+
+
+@pytest.mark.parametrize("method", ["save_before_producers", "save_final"])
+def test_failed_serialization_preserves_saved_image_and_original_mkdir_order(method):
+    s = store('{"old":1}')
+    with pytest.raises(TypeError):
+        getattr(s, method)({"invalid": object()})
+    events = s.trace
+    assert [e["operation"] for e in events] == ([method, "ensure_directory"] if method == "save_before_producers" else [method])
+    assert events[0]["status"] == "BLOCKED"
+    assert s.snapshot().text == '{"old":1}'
+
+
+@pytest.mark.parametrize("fault,reason", [("unknown", "STATE_UNKNOWN"), ("future", "STATE_NOT_YET_AVAILABLE"), ("expired", "STATE_COVERAGE_EXPIRED")])
+@pytest.mark.parametrize("operation", ["load", "save_before_producers", "save_final", "snapshot"])
+def test_unavailable_artifacts_block_without_invented_writes(fault, reason, operation):
+    kw = dict(text=None, status="UNKNOWN") if fault == "unknown" else {}
+    at = T-timedelta(microseconds=1) if fault == "future" else T+timedelta(seconds=11) if fault == "expired" else T
+    s = store(at=at, **kw)
+    with pytest.raises(StateUnavailable, match=reason):
+        getattr(s, operation)(*([{}] if operation.startswith("save") else []))
+    assert len(s.trace) == 1 and s.trace[0]["status"] == "BLOCKED"
+
+
+def test_shared_clock_preserves_saved_image_and_snapshot_handoff_at_coverage_edge():
+    clock = ReplayClock(T)
+    s = store(clock=clock)
+    s.save_before_producers({"saved": 1})
+    clock.advance_to(T+timedelta(seconds=10))
+    handoff = s.snapshot()
+    assert handoff.observed_at == handoff.available_at == clock.now
+    assert handoff.covered_through == clock.now
+    resumed = api().CausalWatchStorage(seed=handoff, decision_time=clock.now)
+    assert resumed.load() == {"saved": 1}
+    clock.advance_to(clock.now+timedelta(microseconds=1))
+    with pytest.raises(StateUnavailable):
+        s.save_final({"too_late": 1})
+    assert resumed.load() == {"saved": 1}
+
+
+def test_restart_image_excludes_mutations_after_first_save():
+    s = store()
+    working = {"cooldown": 1}
+    s.save_before_producers(working)
+    working["unsaved_episode"] = {"ts": 2}
+    restarted = api().CausalWatchStorage(seed=s.snapshot(), decision_time=T)
+    assert restarted.load() == {"cooldown": 1}
+    s.save_final(working)
+    assert s.load() == {"cooldown": 1, "unsaved_episode": {"ts": 2}}
+    assert restarted.load() == {"cooldown": 1}
+
+
+def test_trace_is_detached_from_caller_changes():
+    s = store()
+    s.load()
+    trace = s.trace
+    trace[0]["status"] = "forged"
+    trace.clear()
+    assert s.trace[0]["status"] == "AVAILABLE"
+
+
+@pytest.mark.parametrize("fault", ["tracker_seed", "mismatched_clock", "fake_clock", "naive_time"])
+def test_exact_seed_and_shared_clock_binding_are_required(fault):
+    original = seed()
+    kw = dict(seed=original, decision_time=T)
+    if fault == "tracker_seed":
+        kw["seed"] = TrackerStateSeed(**original.__dict__)
+    elif fault == "mismatched_clock":
+        kw["clock"] = ReplayClock(T+timedelta(seconds=1))
+    elif fault == "fake_clock":
+        kw["clock"] = object()
+    else:
+        kw["decision_time"] = T.replace(tzinfo=None)
+    with pytest.raises(ValueError):
+        api().CausalWatchStorage(**kw)

```

```diff
diff --git a/docs/architecture/WATCH-STATE-BINDING-USAGE.md b/docs/architecture/WATCH-STATE-BINDING-USAGE.md
new file mode 100644
index 0000000..7868d4e
--- /dev/null
+++ b/docs/architecture/WATCH-STATE-BINDING-USAGE.md
@@ -0,0 +1,58 @@
+# Causal watch-state storage
+
+This artifact adapter preserves the original market-watch persistence statements,
+separately from tracker state. It performs no live file IO and does not run the
+full watch loop, its separate lock, or the tracker lifecycle.
+
+```python
+from trading_system.tree_replay.watch_storage import CausalWatchStorage
+
+storage = CausalWatchStorage(seed=watch_seed, decision_time=decision_time)
+working_state = storage.load()
+# Actual original caller updates scalar cooldowns and object episodes here.
+storage.save_before_producers(working_state)
+# Later original producer processing makes further updates or deletions.
+storage.save_final(working_state)
+persisted = storage.snapshot()
+```
+
+watch_seed must be an exact WatchStateSeed with seed_id/source, observed_at,
+available_at, covered_through, status and text. It shares the validated causal
+text schema of TrackerStateSeed but is a distinct type. Status is PRESENT with
+UTF8-encodable text, or ABSENT/UNREADABLE/UNKNOWN with textNone. Times are aware,
+microsecond-exact UTC with observed <= available <= covered. They are caller
+evidence, not independent certification of the historical artifact.
+
+Optional `clock=ReplayClock(T)` requires matching initial decision_time and
+subsequently uses its current time without resetting state. Availability and
+coverage guards run at each operation; advancement does not fill unknown history.
+Standalone calls remain at their fixed decision_time.
+
+Source behavior: known absent load yields{}, unreadable or malformed JSON raises.
+Other valid JSON roots are not normalized into objects. Mutating a returned value
+does not update persisted storage. Explicit saves preserve JSON default spacing,
+ASCII escaping, insertion order, scalar/object values and deletions. There is no
+tracker shrink/quarantine/creation guard or reread before overwriting. First save
+records ensure_directory then write_text; final save only write_text. Serialization
+failure preserves the last completed image but can follow the first mkdir attempt.
+
+snapshot gives the last completed saved text with current-time observed/available
+and original coverage. Reconstructing another storage from it cannot see unsaved
+caller changes. This is one artifact handoff, not full replay checkpoint/resume.
+Original filesystem writes are direct/non-atomic. The in-memory implementation
+models completed writes only; it does not claim torn-write recovery, permission
+fidelity, fsync or atomic transaction guarantees. Historical partial/corrupt text
+must be supplied explicitly, not generated as a fabricated filesystem history.
+
+trace returns a detached ordered list of parent/child attempts and errors, including
+serialization and data-availability failures. Directory ports represent completed
+in-memory attempts, not access to actual directories. Full caller/publication
+binding, lifecycle, outcome labels and training remain outside this component.
+
+```powershell
+python -m pytest tests/tree_replay/test_watch_storage.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_shared_clock.py -q --tb=short
+```
+
+Independent source audit implementation and component reviews must be accepted
+before claiming source parity. Read the latest exchange status, not this example,
+to determine acceptance. Synthetic storage tests are not historical market proof.

```

