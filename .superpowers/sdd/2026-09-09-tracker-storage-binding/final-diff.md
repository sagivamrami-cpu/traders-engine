# Full tracker storage component after Important1

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; seven untracked additions.

```diff
warning: in the working copy of 'trading_system/tree_replay/_vendor/tracker_storage.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/_vendor/tracker_storage.py b/trading_system/tree_replay/_vendor/tracker_storage.py
new file mode 100644
index 0000000..278d40a
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tracker_storage.py
@@ -0,0 +1,32 @@
+"""Private original tracker load/save with explicit offline artifact ports."""
+import json
+
+
+class TrackerStorage:
+    def __init__(self, source):
+        self.source = source
+
+    def load(self) -> dict:
+        if not self.source.exists():
+            return {}
+        return json.loads(self.source.read_text())
+
+    def save(self, d: dict, *, allow_shrink: bool = False) -> None:
+        if self.source.is_live_test_target():
+            raise RuntimeError(
+                "refusing to write the live open_trades.json from a test process: "
+                "patch tracker.STATE (and OUTCOMES) to a temp path in setUp")
+        if not allow_shrink and self.source.exists():
+            try:
+                cur = json.loads(self.source.read_text())
+            except Exception:
+                cur = None
+            if cur is not None:
+                self.source.audit_creation(cur, d)
+            lost = set() if cur is None else set(cur) - set(d)
+            if cur is None or (len(cur) >= 4 and len(lost) > len(cur) // 2):
+                quarantine = self.source.quarantine_path(f".rejected-{int(self.source.now_epoch())}")
+                quarantine.write_text(json.dumps(d, ensure_ascii=False, indent=1))
+                detail = "state unreadable" if cur is None else f"would drop {len(lost)}/{len(cur)} keys"
+                raise RuntimeError(f"_save refused: {detail}; dict quarantined at {quarantine.name}")
+        self.source.atomic_write(json.dumps(d, ensure_ascii=False, indent=1))

```

```diff
warning: in the working copy of 'trading_system/tree_replay/tracker_storage.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_replay/tracker_storage.py b/trading_system/tree_replay/tracker_storage.py
new file mode 100644
index 0000000..5e770ec
--- /dev/null
+++ b/trading_system/tree_replay/tracker_storage.py
@@ -0,0 +1,170 @@
+"""Supplied causal tracker artifact and original load/save; no filesystem access."""
+from copy import deepcopy
+from dataclasses import dataclass, replace
+from datetime import datetime
+import json
+
+from .bars import _utc
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
+    def __init__(self, seed, decision_time):
+        self.seed = seed
+        self.decision_time = decision_time
+        self.status = seed.status
+        self.text = seed.text
+        self.trace = []
+        self.quarantines = {}
+        self.creations = []
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
+    """One decision-time storage context; snapshot is not a full replay checkpoint."""
+    def __init__(self, *, seed: TrackerStateSeed, decision_time: datetime):
+        if type(seed) is not TrackerStateSeed:
+            raise ValueError("seed must be an exact TrackerStateSeed")
+        seed.__post_init__()
+        super().__init__(_MemoryBackend(seed, _utc(decision_time, "decision_time")))
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

```diff
warning: in the working copy of 'trading_system/tree_spec/tracker_storage_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/trading_system/tree_spec/tracker_storage_source.py b/trading_system/tree_spec/tracker_storage_source.py
new file mode 100644
index 0000000..d9dd3d4
--- /dev/null
+++ b/trading_system/tree_spec/tracker_storage_source.py
@@ -0,0 +1,77 @@
+"""Independent full-module AST audit; retained source is never executed."""
+import ast
+import hashlib
+import json
+from pathlib import Path
+import subprocess
+
+from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc
+
+
+ROOT = Path(__file__).resolve().parents[2]
+RUNTIME = ROOT / "trading_system/tree_replay/_vendor/tracker_storage.py"
+COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
+ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
+          subprocess.SubprocessError)
+
+
+def _projection(text):
+    load, save = _selected(text, ["_load", "_save"])
+    for node in (load, save):
+        for old, new in [("STATE.exists()", "self.source.exists()"),
+                         ("STATE.read_text()", "self.source.read_text()")]:
+            _replace_exact(node, old, new)
+        node.args.args.insert(0, ast.arg(arg="self"))
+    load.name, save.name = "load", "save"
+    for old, new in [
+        ('STATE == ROOT / "out" / "open_trades.json" and ("unittest" in sys.modules or "pytest" in sys.modules)',
+         "self.source.is_live_test_target()"),
+        ("_audit_creation(cur, d)", "self.source.audit_creation(cur, d)"),
+        ("time.time()", "self.source.now_epoch()"),
+        ('STATE.with_suffix(f".rejected-{int(self.source.now_epoch())}")',
+         'self.source.quarantine_path(f".rejected-{int(self.source.now_epoch())}")'),
+        ("_atomic_write(STATE, json.dumps(d, ensure_ascii=False, indent=1))",
+         "self.source.atomic_write(json.dumps(d, ensure_ascii=False, indent=1))"),
+    ]:
+        _replace_exact(save, old, new)
+    _replace_exact(save, "from .basis import _atomic_write", None, statement=True)
+    expected = ast.parse("import json\nclass TrackerStorage:\n    def __init__(self, source):\n        self.source = source")
+    expected.body[1].body.extend([load, save])
+    return expected.body
+
+
+def audit_tracker_storage_source(source_root):
+    blockers, checked = [], []
+    report = {"status": "BLOCKED", "source_subset_verified": False,
+        "blockers": blockers, "checked_projections": checked,
+        "source_commits": {"chart-desk": COMMIT},
+        "ready_for_replay": False, "ready_for_training": False}
+    try:
+        root = Path(source_root) / "chart-desk"
+        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
+            blockers.append("NOT_REPOSITORY_ROOT")
+        if _git(root, "HEAD") != COMMIT:
+            blockers.append("SOURCE_COMMIT_MISMATCH")
+        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
+        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
+            blockers.append("BASELINE_COMMIT_MISMATCH")
+        text = (root / "chartdesk/tracker.py").read_text(encoding="utf-8")
+        data = text.encode("utf-8")
+        if hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest() != BLOB:
+            blockers.append("SOURCE_BLOB_MISMATCH")
+        expected = _projection(text)
+    except ERRORS as exc:
+        blockers.append(f"SOURCE_UNREADABLE:{type(exc).__name__}:{exc}")
+        return report
+    try:
+        actual = _without_doc(ast.parse(RUNTIME.read_text(encoding="utf-8")))
+        if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+            blockers.append("VENDOR_AST_MISMATCH")
+        elif not blockers:
+            checked.extend(["tracker._load", "tracker._save"])
+    except ERRORS as exc:
+        blockers.append(f"VENDOR_UNREADABLE:{type(exc).__name__}")
+    if not blockers:
+        report.update(status="VERIFIED", source_subset_verified=True)
+    return report

```

```diff
warning: in the working copy of 'tools/check_tracker_storage_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_tracker_storage_source_parity.py b/tools/check_tracker_storage_source_parity.py
new file mode 100644
index 0000000..282b471
--- /dev/null
+++ b/tools/check_tracker_storage_source_parity.py
@@ -0,0 +1,22 @@
+"""Verify original tracker storage branches without executing retained source."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.tracker_storage_source import audit_tracker_storage_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True)
+    report = audit_tracker_storage_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```

```diff
warning: in the working copy of 'tests/tree_replay/test_tracker_storage.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_tracker_storage.py b/tests/tree_replay/test_tracker_storage.py
new file mode 100644
index 0000000..a917d13
--- /dev/null
+++ b/tests/tree_replay/test_tracker_storage.py
@@ -0,0 +1,300 @@
+"""Original storage decisions on causal text, not a fake successful save sink."""
+from dataclasses import FrozenInstanceError, replace
+from datetime import datetime, timedelta, timezone
+import importlib
+import importlib.util
+import json
+
+import pandas as pd
+import pytest
+
+from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
+
+
+T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
+SYM = "OANDA:XAUUSD"
+LONG = "לונג"
+
+
+def api():
+    name = "trading_system.tree_replay.tracker_storage"
+    assert importlib.util.find_spec(name) is not None, "causal tracker storage missing"
+    return importlib.import_module(name)
+
+
+def seed(status="PRESENT", text="{}", **changes):
+    return api().TrackerStateSeed(**(dict(seed_id="source-state-1", source="synthetic",
+        observed_at=T-timedelta(hours=1), available_at=T-timedelta(minutes=30),
+        covered_through=T+timedelta(hours=1), status=status,
+        text=text if status == "PRESENT" else None) | changes))
+
+
+def storage(status="PRESENT", text="{}", *, decision_time=T, **changes):
+    return api().CausalTrackerStorage(seed=seed(status, text, **changes),
+                                    decision_time=decision_time)
+
+
+def test_absence_and_corrupt_state_are_not_the_same():
+    assert storage("ABSENT").load() == {}
+    with pytest.raises(json.JSONDecodeError):
+        storage(text="{torn").load()
+    with pytest.raises(OSError):
+        storage("UNREADABLE").load()
+    assert TrackerAdmission(storage(text="{torn")).has_open(SYM, LONG)
+
+
+@pytest.mark.parametrize("text,want", [("null", None), ("[]", []), ("12", 12)])
+def test_source_nonobject_json_is_not_normalized_to_empty(text, want):
+    s = storage(text=text)
+    assert s.load() == want
+    assert TrackerAdmission(s).has_open(SYM, LONG)
+
+
+def test_root_order_and_loaded_mutation_do_not_change_storage():
+    s = storage(text='{"z": {"state": "PENDING"}, "a": {"state": "DONE"}}')
+    first = s.load()
+    assert list(first) == ["z", "a"]
+    first["z"]["state"] = "OPEN"
+    del first["a"]
+    assert s.load() == {"z": {"state": "PENDING"}, "a": {"state": "DONE"}}
+    assert list(s.load()) == ["z", "a"]
+
+
+@pytest.mark.parametrize("count,remaining,refused", [(3, 0, False), (4, 2, False),
+    (4, 1, True), (5, 3, False), (5, 2, True), (6, 3, False), (6, 2, True)])
+def test_original_shrink_boundary(count, remaining, refused):
+    initial = {str(i): {} for i in range(count)}
+    wanted = {str(i): {} for i in range(remaining)}
+    s = storage(text=json.dumps(initial))
+    if refused:
+        with pytest.raises(RuntimeError, match=f"would drop {count-remaining}/{count} keys"):
+            s.save(wanted)
+        assert s.load() == initial
+        assert len(s.quarantine_artifacts) == 1
+    else:
+        s.save(wanted)
+        assert s.load() == wanted and not s.quarantine_artifacts
+
+
+def test_quarantine_literal_payload_name_and_same_second_replacement():
+    s = storage(text='{"z": {}, "a": {}, "b": {}, "c": {}}')
+    with pytest.raises(RuntimeError, match="dict quarantined at open_trades.rejected-1788969600"):
+        s.save({"z": {}})
+    assert s.quarantine_artifacts == {"open_trades.rejected-1788969600": '{\n "z": {}\n}'}
+    with pytest.raises(RuntimeError):
+        s.save({"a": {}})
+    assert s.quarantine_artifacts == {"open_trades.rejected-1788969600": '{\n "a": {}\n}'}
+    assert list(s.load()) == ["z", "a", "b", "c"]
+
+
+@pytest.mark.parametrize("status,text", [("PRESENT", "{torn"), ("PRESENT", "null"),
+                                         ("UNREADABLE", None)])
+def test_unreadable_or_null_current_state_quarantines(status, text):
+    s = storage(status, text)
+    with pytest.raises(RuntimeError, match="state unreadable"):
+        s.save({"z": {}})
+    assert s.snapshot().status == status and s.snapshot().text == text
+    assert list(s.quarantine_artifacts) == ["open_trades.rejected-1788969600"]
+
+
+@pytest.mark.parametrize("status,text", [("PRESENT", "{torn"), ("UNREADABLE", None),
+                                         ("PRESENT", '{"a": {}, "b": {}, "c": {}, "d": {}}')])
+def test_explicit_allow_shrink_bypasses_source_reread_and_forensics(status, text):
+    s = storage(status, text)
+    s.save({"new": {"state": "PENDING"}}, allow_shrink=True)
+    assert s.load() == {"new": {"state": "PENDING"}}
+    assert not s.quarantine_artifacts and not s.creation_effects
+    assert not any(e["operation"] == "read_text" for e in s.trace[:-2])
+
+
+def test_save_rereads_current_state_not_cached_load():
+    s = storage(text='{"a": {}}')
+    stale = s.load()
+    s.save({"a": {}, "b": {}, "c": {}, "d": {}})
+    with pytest.raises(RuntimeError, match="would drop 3/4 keys"):
+        s.save(stale)
+    assert list(s.load()) == ["a", "b", "c", "d"]
+
+
+def test_creation_effect_precedes_quarantine_and_is_not_fabricated_process_log():
+    s = storage(text='{"a": {}, "b": {}, "c": {}, "d": {}}')
+    with pytest.raises(RuntimeError):
+        s.save({"new": {"entry": 100, "state": "PENDING"}})
+    assert s.creation_effects == [{"origin": "replay_creation_effect", "ts": 1788969600.,
+        "key": "new", "record": {"entry": 100, "stop": None, "state": "PENDING",
+                                   "variant": None, "revived_from_ts": None}}]
+    ops = [e["operation"] for e in s.trace]
+    assert ops.index("audit_creation") < ops.index("write_quarantine")
+    returned = s.creation_effects
+    returned[0]["record"]["entry"] = -1
+    assert s.creation_effects[0]["record"]["entry"] == 100
+
+
+def test_forensic_bad_record_is_best_effort_but_set_errors_propagate():
+    s = storage()
+    s.save({"bad": 4})  # .get fails inside best-effort forensic boundary
+    assert s.load() == {"bad": 4} and not s.creation_effects
+    noniterable = storage(text="12")
+    with pytest.raises(TypeError):
+        noniterable.save({"new": {}})  # set(cur) fails before original try
+    assert noniterable.load() == 12 and not noniterable.quarantine_artifacts
+
+
+def test_first_file_creation_has_no_source_creation_audit_and_preserves_json_format():
+    s = storage("ABSENT")
+    s.save({"z": {"direction": LONG}, "a": {}})
+    assert not s.creation_effects
+    assert s.snapshot().text == '{\n "z": {\n  "direction": "לונג"\n },\n "a": {}\n}'
+
+
+def test_unserializable_forensic_value_does_not_leave_a_creation_effect():
+    s = storage()
+    with pytest.raises(TypeError):
+        s.save({"new": {"entry": object()}})
+    assert s.creation_effects == []
+    assert s.load() == {}
+
+
+def test_swallowed_forensic_extraction_failure_is_traced_without_vetoing_save():
+    s = storage()
+    s.save({"bad": 4})
+    assert s.load() == {"bad": 4} and s.creation_effects == []
+    failed = [e for e in s.trace if e["operation"] == "creation_effect"]
+    assert len(failed) == 1 and failed[0]["status"] == "BLOCKED"
+    assert failed[0]["exception_type"] == "AttributeError"
+    assert "get" in failed[0]["blocker"]
+    assert next(e for e in s.trace if e["operation"] == "save")["status"] == "AVAILABLE"
+    returned = s.trace
+    returned[0]["status"] = "changed"
+    assert s.trace[0]["status"] == "AVAILABLE"
+
+
+def test_forensic_serialization_failure_has_its_own_failed_effect_trace():
+    s = storage()
+    with pytest.raises(TypeError):
+        s.save({"bad": {"entry": object()}})
+    assert s.creation_effects == [] and s.load() == {}
+    failed = [e for e in s.trace if e["operation"] == "creation_effect"]
+    assert len(failed) == 1 and failed[0]["status"] == "BLOCKED"
+    assert failed[0]["exception_type"] == "TypeError"
+    assert "JSON serializable" in failed[0]["blocker"]
+
+
+def test_partial_forensic_emission_stops_after_traced_failure_but_state_saves():
+    s = storage()
+    rows = {key: {} for key in ("a", "b", "c")}
+    # Position the bad row using this process's set order; do not assert a
+    # cross-process ordering policy for forensic (non-trading) effects.
+    order = list(set(rows)-set())
+    rows[order[0]] = {"entry": 10}
+    rows[order[1]] = 4
+    rows[order[2]] = {"entry": 30}
+    s.save(rows)
+    assert s.load() == rows
+    assert [(e["key"], e["record"]["entry"]) for e in s.creation_effects] == [(order[0], 10)]
+    attempts = [e for e in s.trace if e["operation"] == "creation_effect"]
+    assert [(e["status"], e["exception_type"]) for e in attempts] == [
+        ("AVAILABLE", None), ("BLOCKED", "AttributeError")]
+    operations = [e["operation"] for e in s.trace]
+    assert operations.index("creation_effect") < operations.index("atomic_write")
+
+
+@pytest.mark.parametrize("changes", [dict(available_at=T+timedelta(seconds=1)),
+    dict(covered_through=T-timedelta(seconds=1)), dict(status="UNKNOWN", text=None)])
+def test_unavailable_input_blocks_reads_writes_and_survives_tracker_catch(changes):
+    s = storage(**changes)
+    assert TrackerAdmission(s).has_open(SYM, LONG)
+    with pytest.raises(api().StateUnavailable):
+        s.save({}, allow_shrink=True)
+    with pytest.raises(api().StateUnavailable):
+        s.snapshot()
+    assert not s.quarantine_artifacts and not s.creation_effects
+    assert any(e["status"] == "BLOCKED" for e in s.trace)
+
+
+def test_same_artifact_can_continue_at_later_time_only_within_coverage():
+    s = storage("ABSENT")
+    s.save({"z": {"state": "PENDING"}})
+    after = s.snapshot()
+    assert after.observed_at == after.available_at == T
+    assert after.covered_through == T+timedelta(hours=1)
+    next_store = api().CausalTrackerStorage(seed=after, decision_time=T+timedelta(minutes=5))
+    next_store.save({"z": {"state": "DONE"}})
+    assert s.load()["z"]["state"] == "PENDING"
+    assert next_store.load()["z"]["state"] == "DONE"
+    past = api().CausalTrackerStorage(seed=after, decision_time=T-timedelta(microseconds=1))
+    with pytest.raises(api().StateUnavailable):
+        past.load()
+
+
+@pytest.mark.parametrize("changes", [dict(seed_id=""), dict(source=" x "),
+    dict(seed_id="\ud800"), dict(status="present"), dict(status=1),
+    dict(text=b"{}"), dict(text="\ud800"), dict(status="ABSENT", text="{}"),
+    dict(observed_at=T.replace(tzinfo=None)), dict(observed_at=pd.Timestamp(T)+pd.Timedelta(1, 'ns')),
+    dict(observed_at=T), dict(covered_through=T-timedelta(hours=2))])
+def test_bad_seed_contract_rejected(changes):
+    with pytest.raises(ValueError):
+        replace(seed(), **changes)
+
+
+def test_frozen_seed_and_exact_store_input_types():
+    given = seed()
+    with pytest.raises(FrozenInstanceError):
+        given.text = "[]"
+    with pytest.raises(ValueError):
+        api().CausalTrackerStorage(seed={}, decision_time=T)
+    with pytest.raises(ValueError):
+        api().CausalTrackerStorage(seed=given, decision_time=T.replace(tzinfo=None))
+
+
+def test_source_live_test_guard_remains_before_any_write(monkeypatch):
+    s = storage()
+    monkeypatch.setattr(s.source, "is_live_test_target", lambda: True)
+    with pytest.raises(RuntimeError, match="refusing to write the live"):
+        s.save({"x": {}}, allow_shrink=True)
+    assert s.load() == {} and not s.quarantine_artifacts
+
+
+@pytest.mark.parametrize("port", ["atomic_write", "write_quarantine"])
+def test_failed_write_does_not_replace_current_state(monkeypatch, port):
+    s = storage(text='{"a": {}, "b": {}, "c": {}, "d": {}}')
+    def fail(*args):
+        raise OSError("synthetic disk boundary failure")
+    monkeypatch.setattr(s.source, port, fail)
+    with pytest.raises(OSError, match="synthetic disk boundary failure"):
+        s.save({"a": {}}, allow_shrink=(port == "atomic_write"))
+    assert list(s.load()) == ["a", "b", "c", "d"]
+
+
+def test_real_record_persists_through_source_storage_then_exposure_blocks():
+    from test_tracker_admission import MemoryPorts, plan
+    state = storage("ABSENT")
+    class Ports(MemoryPorts):
+        def load(self):
+            return state.load()
+        def save(self, rows):
+            state.save(rows)
+        def now_epoch(self):
+            return T.timestamp()
+    ports = Ports()
+    tracker = TrackerAdmission(ports)
+    assert tracker.record(plan(close=100.))
+    row = next(iter(state.load().values()))
+    assert row["state"] == "OPEN" and row["ts"] == 1788969600.
+    assert row["revalidation_verified"] is False  # not an economic fill
+    assert tracker.has_open(SYM, LONG)
+    assert tracker.record(plan(close=100.)) is False
+    assert len(state.load()) == 1
+
+
+def test_first_same_level_match_follows_original_insertion_order():
+    old = {"symbol": SYM, "direction": LONG, "state": "DONE", "entry": 100.,
+           "resolved_ts": T.timestamp()-300}
+    newer = old | {"resolved_ts": T.timestamp()-60}
+    s = storage(text=json.dumps({"z": old, "a": newer}))
+    class Ports:
+        load = s.load
+        def now_epoch(self):
+            return T.timestamp()
+    reason = TrackerAdmission(Ports()).blocked_same_level(SYM, LONG, 100.)
+    assert "5" in reason and "100.00" in reason

```

```diff
warning: in the working copy of 'tests/tree_spec/test_tracker_storage_source.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_spec/test_tracker_storage_source.py b/tests/tree_spec/test_tracker_storage_source.py
new file mode 100644
index 0000000..fea8837
--- /dev/null
+++ b/tests/tree_spec/test_tracker_storage_source.py
@@ -0,0 +1,92 @@
+"""Independent source-identity and complete-projection mutation checks."""
+import importlib
+import importlib.util
+import json
+import os
+from pathlib import Path
+import subprocess
+import sys
+
+import pytest
+
+
+REPO = Path(__file__).resolve().parents[2]
+SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
+    "C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149"))
+RUNTIME = REPO / "trading_system/tree_replay/_vendor/tracker_storage.py"
+
+
+def api():
+    name = "trading_system.tree_spec.tracker_storage_source"
+    assert importlib.util.find_spec(name) is not None, "storage source auditor missing"
+    return importlib.import_module(name)
+
+
+def test_actual_pinned_source_and_whole_projection_verify():
+    r = api().audit_tracker_storage_source(SOURCE)
+    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
+    assert r["blockers"] == []
+    assert not r["ready_for_replay"] and not r["ready_for_training"]
+    assert r["checked_projections"] == ["tracker._load", "tracker._save"]
+
+
+@pytest.mark.parametrize("old,new", [
+    ("len(cur) >= 4", "len(cur) >= 5"),
+    ("len(lost) > len(cur) // 2", "len(lost) >= len(cur) // 2"),
+    ("cur = json.loads(self.source.read_text())", "cur = {}"),
+    ("self.source.audit_creation(cur, d)", "pass"),
+    ("if self.source.is_live_test_target():", "if False:"),
+    ("ensure_ascii=False, indent=1", "ensure_ascii=False, indent=1, sort_keys=True"),
+    ("self.source = source", "self.source = None"),
+    ("import json", "import json\nimport os"),
+])
+def test_changed_runtime_logic_or_extra_code_is_not_accepted(monkeypatch, old, new):
+    original_read = Path.read_text
+    actual = original_read(RUNTIME, encoding="utf-8")
+    assert old in actual
+    def read(path, *args, **kwargs):
+        return actual.replace(old, new) if path.resolve() == RUNTIME.resolve() else original_read(path, *args, **kwargs)
+    monkeypatch.setattr(Path, "read_text", read)
+    r = api().audit_tracker_storage_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert "VENDOR_AST_MISMATCH" in r["blockers"]
+
+
+def test_changed_retained_source_blob_is_blocked(monkeypatch):
+    original_read = Path.read_text
+    target = SOURCE / "chart-desk/chartdesk/tracker.py"
+    def read(path, *args, **kwargs):
+        text = original_read(path, *args, **kwargs)
+        return text+"\n# different source bytes\n" if path.resolve() == target.resolve() else text
+    monkeypatch.setattr(Path, "read_text", read)
+    r = api().audit_tracker_storage_source(SOURCE)
+    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH" in r["blockers"]
+
+
+def test_wrong_commit_blocks_even_with_matching_working_tree(monkeypatch):
+    module = api()
+    original_git = module._git
+    monkeypatch.setattr(module, "_git", lambda path, *args:
+        "0"*40 if args == ("HEAD",) else original_git(path, *args))
+    r = module.audit_tracker_storage_source(SOURCE)
+    assert not r["source_subset_verified"] and "SOURCE_COMMIT_MISMATCH" in r["blockers"]
+
+
+def test_missing_root_and_missing_runtime_are_blocked(tmp_path, monkeypatch):
+    module = api()
+    assert not module.audit_tracker_storage_source(tmp_path)["source_subset_verified"]
+    monkeypatch.setattr(module, "RUNTIME", tmp_path / "absent.py")
+    r = module.audit_tracker_storage_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert any("VENDOR_UNREADABLE" in b for b in r["blockers"])
+
+
+def test_cli_reports_scoped_verification_and_blocked_exit(tmp_path):
+    api()  # Missing feature fails here, not as a misleading CLI argument failure.
+    command = [sys.executable, str(REPO / "tools/check_tracker_storage_source_parity.py"), "--source-root"]
+    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
+        result = subprocess.run(command+[str(root)], cwd=tmp_path, text=True,
+                                capture_output=True, encoding="utf-8", timeout=30)
+        assert result.returncode == code, result.stderr
+        report = json.loads(result.stdout)
+        assert report["status"] == status and not report["ready_for_training"]

```

```diff
warning: in the working copy of 'docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md b/docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md
new file mode 100644
index 0000000..8052e8b
--- /dev/null
+++ b/docs/architecture/TRACKER-STORAGE-BINDING-USAGE.md
@@ -0,0 +1,94 @@
+# Causal tracker storage
+
+Use `TrackerStateSeed` and `CausalTrackerStorage` from
+`trading_system.tree_replay.tracker_storage`. This binds original tracker
+load/save to an in-memory artifact, not live open_trades.json or broker state.
+
+```python
+seed = TrackerStateSeed(
+    seed_id="approved-input-state", source="supplied-source-artifact",
+    observed_at=observed, available_at=published, covered_through=coverage_end,
+    status="PRESENT", text=original_ordered_json,
+)
+store = CausalTrackerStorage(seed=seed, decision_time=decision_time)
+rows = store.load()
+# Original tracker calculations may update rows before the original save:
+store.save(rows)
+next_seed = store.snapshot()
+```
+
+The names in the example describe inputs, not automatic approval. `source` and
+coverage are caller attestations. Coverage asserts no unrepresented external
+state changes between observation and covered_through. At T use only a published,
+covered artifact. The full replay will own authoritative source-generated
+changes and must establish this coverage, not repeatedly load a final live file.
+
+## Input semantics
+
+- PRESENT: exact UTF-8 text, including malformed JSON. JSON parsing is deferred
+  until the original read; source root ordering is retained.
+- ABSENT: explicit evidence the source file did not exist; no text. load returns{}.
+- UNREADABLE: known existing artifact with read error; no text. load raises;
+  ordinary save quarantines and refuses; explicit allow_shrink can replace it.
+- UNKNOWN: no reliable state evidence; no text. All reads/saves/handoffs blocked.
+
+Times must be aware/microsecond-exact; observed<=available<=covered. Before
+publication or after coverage, even allow_shrink=True is unavailable. A missing
+history is never treated as an empty desk. Identity/text are UTF-8 checked.
+Supplied raw payload timestamps and malformed values are not silently rewritten.
+
+## Source storage behavior
+
+`load()` returns freshly parsed JSON: modifying a returned dictionary has no
+effect until save. `save(d, allow_shrink=False)` preserves original unsorted
+ensure_ascii=False/indent1 serialization and rereads current state, not an old
+load. It rejects unreadable/null current state or losing more than half the keys
+when at least four existed. Exactly half may be removed. Smaller dictionaries
+follow the source rule. This is fidelity, not a new recommended safety policy.
+The first creation from an absent artifact has no original creation audit.
+
+Rejected writes become separate in-memory open_trades.rejected-<integer epoch>
+artifacts before the original RuntimeError. Same-second refusals replace that
+same quarantine name. Main content stays unchanged. Successful writes replace
+the text as one local operation. No runtime filesystem, network or wall clock.
+Source live-test guard is retained through an explicit port; concrete in-memory
+backend cannot target a real file. Source JSON quirks are retained, not promoted
+to acceptable training values. The later dataset allowlist remains mandatory.
+
+`creation_effects` is a detached, explicitly replay_creation_effect list. It
+keeps original new-key extraction/serialization failure boundaries and timestamp,
+but does not invent historical PID, argv or stack. These are not byte-identical
+trade_creations.jsonl records. Per-set iteration ordering is not deterministic.
+`quarantine_artifacts` and `trace` are detached snapshots as well. Trace retains
+ordered load/save/port attempts and failures even when TrackerAdmission catches
+the exception. Do not mutate private backend attributes to create evidence.
+Each attempted creation effect has its own trace entry. A BLOCKED creation_effect
+retains its exception even when the enclosing best-effort audit and state save
+succeed; AVAILABLE on a parent operation does not mean every child effect succeeded.
+
+`snapshot()` returns current text/status observed and available at this fixed T,
+retaining coverage and provenance. Another instance can consume it at a later
+covered T; old instances are unaffected. This is one artifact handoff, NOT a
+complete loop checkpoint. Quarantines/effects/traces, lock state, clock, pending
+orders, watch state, logs, feed cursors and lifecycle need full-run ownership.
+
+## Verification and limits
+
+```text
+python -m pytest tests/tree_replay/test_tracker_storage.py tests/tree_spec/test_tracker_storage_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_admission_frames.py tests/tree_replay/test_state.py -q --tb=short
+python tools/check_tracker_storage_source_parity.py --source-root <retained-source-parent>
+```
+
+Tests can set TR_TREE_SOURCE_ROOT for the retained source parent; no audit is
+silently skipped if unavailable. The auditor pins actual repo/commit/blob and
+checks the entire projected load/save module with exact enumerated substitutions.
+It never executes the retained source. Changed thresholds, removed reread/audit,
+sorted serialization, altered initialization or extra imports fail its checks.
+The AST audit covers private load/save, not the new in-memory backend, simulated
+forensic effects or actual OS atomicity; those have separate behavioral tests.
+
+Real tracker record/exposure and first same-level selection use this store in
+tests. Other matrix/quote/lock ports are controlled fixtures there. This does
+not certify lock timeout/fail-open/reentrancy, multiwriter races, real I/O fault
+recovery, full watch ordering, quotes/raw logs, lifecycle or economic execution.
+No labels/dataset/model/live readiness. See latest exchange review/acceptance.

```


