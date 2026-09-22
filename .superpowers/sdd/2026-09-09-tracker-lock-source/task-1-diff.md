# Tracker lock source task1 full added-file package

## trading_system/tree_replay/_vendor/tracker_lock.py

```diff
diff --git a/trading_system/tree_replay/_vendor/tracker_lock.py b/trading_system/tree_replay/_vendor/tracker_lock.py
new file mode 100644
index 0000000..4d7e2a8
--- /dev/null
+++ b/trading_system/tree_replay/_vendor/tracker_lock.py
@@ -0,0 +1,97 @@
+"""Private original tracker lock policy; caller supplies IO and time ports."""
+from __future__ import annotations
+from contextlib import contextmanager
+
+LOCK_TIMEOUT_S = 30.0
+RESOLVE_LOCK_WAIT_S = 3.0
+LOCK_STALL_S = 120.0
+
+class LockBusy(RuntimeError):
+    """The tracker lock is held elsewhere and the caller chose not to wait."""
+
+
+class TrackerLock:
+    def __init__(self, source):
+        self.source = source
+        self.held = {"depth": 0}
+
+    def _busy_for(self) -> float:
+        """Seconds the lock has been continuously refused to skippers."""
+        try:
+            return self.source.now_epoch() - float(self.source.read_busy())
+        except Exception:
+            try:
+                self.source.write_busy(str(self.source.now_epoch()))
+            except Exception:
+                pass
+            return 0.0
+
+    @contextmanager
+    def locked(self, *, wait: float | None = None, skip_if_busy: bool = False):
+        """Hold the tracker lock across a read-modify-write of the state file.
+
+    THE BUG THIS FIXES, found 2026-08-27. Two different gold shorts went out in
+    the same second (4,609.65 and 4,625.00) and only ONE survived in
+    open_trades.json. record() was called from market_watch OUTSIDE the lock,
+    while trade_live.py -- running every 60 seconds -- holds that same lock for
+    its own load/modify/save. A record written between trade_live's load and
+    its save is erased by that save, silently. The trade then existed in the
+    channel and nowhere in the tracker: no fill report, no stop report, and no
+    row in the record the whole measurement depends on.
+
+    Every state mutation now goes through here, so load and save are one
+    atomic section rather than two independent ones.
+
+    `wait` bounds the poll (default LOCK_TIMEOUT_S). After it, a writer
+    proceeds unlocked; with `skip_if_busy` the caller gets LockBusy instead
+    and does nothing this pass -- the resolvers' choice, see
+    RESOLVE_LOCK_WAIT_S.
+    """
+        if wait is None:
+            wait = RESOLVE_LOCK_WAIT_S if skip_if_busy else LOCK_TIMEOUT_S
+        if self.held["depth"] > 0:          # already ours — do not re-acquire
+            self.held["depth"] += 1
+            try:
+                yield
+            finally:
+                self.held["depth"] -= 1
+            return
+        self.source.ensure_lock_directory()
+        # Append mode avoids truncating the one-byte Windows lock region while
+        # another process owns it. POSIX flock did not expose that portability bug.
+        f = self.source.open_lock()
+        got = False
+        try:
+            # BOUNDED wait, not LOCK_EX. The first version blocked indefinitely and
+            # deadlocked immediately: trade_live.py holds this lock every 60
+            # seconds, so anything else taking it could wait forever -- the test
+            # suite hung, and in production it would have stalled a whole
+            # market_watch pass behind a 60-second job.
+            #
+            # Failing OPEN after the timeout is the right trade for a WRITER. The
+            # lock prevents a lost write, which is rare; blocking forever prevents
+            # every trade from being recorded, which is total. A rare lost record
+            # beats a stalled desk, and the sentry's "sent but not tracked" check
+            # is what catches the rare case. A resolver is the opposite case and
+            # skips instead (RESOLVE_LOCK_WAIT_S).
+            got = self.source.try_acquire(f, timeout=wait)
+            if got:
+                try:
+                    self.source.clear_busy()
+                except Exception:
+                    pass
+            elif skip_if_busy:
+                stuck = self._busy_for()
+                if stuck < LOCK_STALL_S:
+                    raise LockBusy(f"tracker lock held elsewhere for {wait:.0f}s")
+                self.source.warn(f"[tracker] lock refused for {stuck:.0f}s -- treating the "
+                                 "holder as hung and proceeding unlocked")
+            self.held["depth"] += 1
+            yield
+        finally:
+            self.held["depth"] = max(0, self.held["depth"] - 1)
+            try:
+                if got:
+                    self.source.release(f)
+            finally:
+                f.close()
```

## trading_system/tree_spec/tracker_lock_source.py

```diff
diff --git a/trading_system/tree_spec/tracker_lock_source.py b/trading_system/tree_spec/tracker_lock_source.py
new file mode 100644
index 0000000..29582b8
--- /dev/null
+++ b/trading_system/tree_spec/tracker_lock_source.py
@@ -0,0 +1,103 @@
+"""Independent complete lock-policy AST audit; retained source is never executed."""
+import ast
+import copy
+import hashlib
+import json
+from pathlib import Path
+import subprocess
+
+from .tracker_admission_source import _dump, _git, _replace_exact, _selected, _without_doc
+
+ROOT = Path(__file__).resolve().parents[2]
+RUNTIME = ROOT / "trading_system/tree_replay/_vendor/tracker_lock.py"
+COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+BLOB = "b616b34022e436545d8c1daf85eced51614fd74e"
+ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
+          subprocess.SubprocessError)
+
+
+def _replace_counted(tree, old, new, count):
+    original = ast.parse(old, mode="eval").body
+    replacement = ast.parse(new, mode="eval").body
+    class Replace(ast.NodeTransformer):
+        found = 0
+        def visit(self, node):
+            if _dump(node) == _dump(original):
+                self.found += 1
+                return copy.deepcopy(replacement)
+            return super().visit(node)
+    visitor = Replace()
+    visitor.visit(tree)
+    if visitor.found != count:
+        raise ValueError(f"SUBSTITUTION_PRECONDITION:{old}:count={visitor.found}")
+
+
+def _projection(text):
+    timeout, resolve, stall, busy_error, busy, held, locked = _selected(text, [
+        "LOCK_TIMEOUT_S", "RESOLVE_LOCK_WAIT_S", "LOCK_STALL_S", "LockBusy",
+        "_busy_for", "_HELD", "_locked"])
+    _replace_counted(busy, "time.time()", "self.source.now_epoch()", 2)
+    _replace_exact(busy, "LOCK_BUSY.read_text()", "self.source.read_busy()")
+    _replace_exact(busy, "LOCK_BUSY.write_text(str(self.source.now_epoch()))",
+                   "self.source.write_busy(str(self.source.now_epoch()))")
+    _replace_counted(locked, "_HELD", "self.held", 6)
+    for old, new in [
+        ("LOCK.parent.mkdir(parents=True, exist_ok=True)", "self.source.ensure_lock_directory()"),
+        ('open(LOCK, "a+")', "self.source.open_lock()"),
+        ("filelock.try_acquire(f, timeout=wait)", "self.source.try_acquire(f, timeout=wait)"),
+        ("LOCK_BUSY.unlink(missing_ok=True)", "self.source.clear_busy()"),
+        ("_busy_for()", "self._busy_for()"),
+        ('print(f"[tracker] lock refused for {stuck:.0f}s -- treating the " "holder as hung and proceeding unlocked", file=sys.stderr, flush=True)',
+         'self.source.warn(f"[tracker] lock refused for {stuck:.0f}s -- treating the " "holder as hung and proceeding unlocked")'),
+        ("filelock.release(f)", "self.source.release(f)"),
+    ]:
+        _replace_exact(locked, old, new)
+    _replace_exact(locked, "from . import filelock", None, statement=True)
+    busy.args.args.insert(0, ast.arg(arg="self"))
+    locked.args.args.insert(0, ast.arg(arg="self"))
+    locked.name = "locked"
+    cls = ast.parse("class TrackerLock:\n    def __init__(self, source):\n        self.source = source").body[0]
+    # Original held initializer is an audited dependency, not a runtime-derived value.
+    held.targets = [ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()),
+                                  attr="held", ctx=ast.Store())]
+    cls.body[0].body.append(held)
+    cls.body.extend([busy, locked])
+    imports = ast.parse("from __future__ import annotations\nfrom contextlib import contextmanager").body
+    return imports + [timeout, resolve, stall, busy_error, cls]
+
+
+def audit_tracker_lock_source(source_root):
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
+            checked.extend(["tracker.lock_constants", "tracker.LockBusy",
+                            "tracker._busy_for", "tracker._locked"])
+    except ERRORS as exc:
+        blockers.append(f"VENDOR_UNREADABLE:{type(exc).__name__}")
+    if not blockers:
+        report.update(status="VERIFIED", source_subset_verified=True)
+    return report
```

## tools/check_tracker_lock_source_parity.py

```diff
diff --git a/tools/check_tracker_lock_source_parity.py b/tools/check_tracker_lock_source_parity.py
new file mode 100644
index 0000000..c6165b5
--- /dev/null
+++ b/tools/check_tracker_lock_source_parity.py
@@ -0,0 +1,22 @@
+"""Verify original tracker lock policy without executing retained source."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.tracker_lock_source import audit_tracker_lock_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True)
+    report = audit_tracker_lock_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
```

## tests/tree_replay/test_tracker_lock.py

```diff
diff --git a/tests/tree_replay/test_tracker_lock.py b/tests/tree_replay/test_tracker_lock.py
new file mode 100644
index 0000000..d5ef8f8
--- /dev/null
+++ b/tests/tree_replay/test_tracker_lock.py
@@ -0,0 +1,258 @@
+"""Source policy behavior with explicit low-level IO, never operating-system locks."""
+from copy import deepcopy
+import importlib
+import importlib.util
+from types import SimpleNamespace
+
+import pytest
+
+from trading_system.tree_replay._vendor.pricing import Plan
+from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
+
+
+def api():
+    name = "trading_system.tree_replay._vendor.tracker_lock"
+    assert importlib.util.find_spec(name) is not None, "tracker lock policy missing"
+    return importlib.import_module(name)
+
+
+class IO:
+    """Deterministic external-operation fixture; the policy under test is real."""
+    def __init__(self, *, acquired=True, marker="900", fail=()):
+        self.acquired, self.marker, self.fail = acquired, marker, set(fail)
+        self.calls, self.now, self.after_acquire = [], 1000.0, None
+        self.handle = SimpleNamespace(close=lambda: self.call("close"))
+
+    def call(self, name, *args):
+        self.calls.append((name, *args))
+        if name in self.fail:
+            raise OSError(name)
+
+    def now_epoch(self):
+        self.call("clock", self.now)
+        return self.now
+
+    def read_busy(self):
+        self.call("read")
+        if self.marker is None:
+            raise FileNotFoundError("busy marker absent")
+        return self.marker
+
+    def write_busy(self, text):
+        self.call("write", text)
+        self.marker = text
+
+    def clear_busy(self):
+        self.call("clear")
+        self.marker = None
+
+    def ensure_lock_directory(self):
+        self.call("mkdir")
+
+    def open_lock(self):
+        self.call("open")
+        return self.handle
+
+    def try_acquire(self, handle, *, timeout):
+        assert handle is self.handle
+        self.call("acquire", timeout)
+        if self.after_acquire:
+            self.after_acquire()
+        return self.acquired
+
+    def release(self, handle):
+        assert handle is self.handle
+        self.call("release")
+
+    def warn(self, text):
+        self.call("warn", text)
+
+
+@pytest.mark.parametrize("kwargs,wait", [({}, 30.0), ({"skip_if_busy": True}, 3.0),
+    ({"skip_if_busy": True, "wait": 30.0}, 30.0), ({"wait": 0}, 0),
+    ({"wait": -2}, -2)])
+def test_success_keeps_wait_choice_and_original_operation_order(kwargs, wait):
+    io = IO()
+    policy = api().TrackerLock(io)
+    with policy.locked(**kwargs):
+        io.call("body", policy.held["depth"])
+    assert io.calls == [("mkdir",), ("open",), ("acquire", wait), ("clear",),
+                        ("body", 1), ("release",), ("close",)]
+    assert policy.held == {"depth": 0} and io.marker is None
+
+
+@pytest.mark.parametrize("marker,entered", [
+    ("880.001", False), ("880", True), ("879", True), ("1001", False),
+    ("nan", True), ("inf", False), ("-inf", True)])
+def test_resolver_busy_age_boundary_preserves_source_float_semantics(marker, entered):
+    io = IO(acquired=False, marker=marker)
+    policy = api().TrackerLock(io)
+    bodies = []
+    if entered:
+        with policy.locked(skip_if_busy=True):
+            bodies.append(policy.held["depth"])
+        assert bodies == [1]
+        assert any(c[0] == "warn" for c in io.calls)
+    else:
+        with pytest.raises(api().LockBusy, match="held elsewhere for 3s"):
+            with policy.locked(skip_if_busy=True):
+                bodies.append("must not enter")
+        assert bodies == [] and not any(c[0] == "warn" for c in io.calls)
+    assert io.calls[-1] == ("close",)
+    assert ("release",) not in io.calls and ("clear",) not in io.calls
+    assert policy.held["depth"] == 0
+
+
+def test_writer_proceeds_without_lock_and_without_touching_busy_marker():
+    io = IO(acquired=False, fail={"read", "write"})
+    policy = api().TrackerLock(io)
+    with policy.locked():
+        io.call("body")
+    assert io.calls == [("mkdir",), ("open",), ("acquire", 30.0), ("body",), ("close",)]
+
+
+@pytest.mark.parametrize("marker,fail", [(None, ()), ("broken", ()),
+    ("broken", ("write",)), ("900", ("read",))])
+def test_missing_bad_or_unreadable_marker_stamps_current_time_then_skips(marker, fail):
+    io = IO(acquired=False, marker=marker, fail=fail)
+    policy = api().TrackerLock(io)
+    with pytest.raises(api().LockBusy):
+        with policy.locked(skip_if_busy=True):
+            pytest.fail("fresh refusal must skip")
+    assert ("write", "1000.0") in io.calls
+    assert io.marker == (marker if "write" in fail else "1000.0")
+    assert io.calls[-1] == ("close",) and policy.held["depth"] == 0
+
+
+def test_failed_clock_in_busy_read_and_stamp_is_best_effort_then_skip():
+    io = IO(acquired=False, fail={"clock"})
+    with pytest.raises(api().LockBusy):
+        with api().TrackerLock(io).locked(skip_if_busy=True):
+            pytest.fail("clock failure must not fabricate old refusal")
+    assert io.calls.count(("clock", 1000.0)) == 2
+    assert not any(c[0] in {"read", "write", "warn"} for c in io.calls)
+
+
+def test_failed_marker_clear_does_not_prevent_body_or_release():
+    io = IO(fail={"clear"})
+    with api().TrackerLock(io).locked():
+        io.call("body")
+    assert io.calls[-3:] == [("body",), ("release",), ("close",)]
+
+
+@pytest.mark.parametrize("acquired", [True, False])
+def test_nested_resolver_bypasses_second_acquire_even_inside_unlocked_writer(acquired):
+    io = IO(acquired=acquired)
+    policy = api().TrackerLock(io)
+    with policy.locked():
+        before = list(io.calls)
+        with pytest.raises(ValueError, match="nested body"):
+            with policy.locked(wait=99, skip_if_busy=True):
+                assert policy.held["depth"] == 2
+                raise ValueError("nested body")
+        assert io.calls == before and policy.held["depth"] == 1
+    assert policy.held["depth"] == 0 and io.calls[-1] == ("close",)
+    assert len([c for c in io.calls if c[0] == "acquire"]) == 1
+
+
+@pytest.mark.parametrize("failure,last", [("mkdir", "mkdir"), ("open", "open"),
+    ("acquire", "close"), ("release", "close"), ("close", "close")])
+def test_original_failure_boundaries_restore_depth_and_close_only_opened_handle(failure, last):
+    io = IO(fail={failure})
+    policy = api().TrackerLock(io)
+    entered = []
+    with pytest.raises(OSError, match=failure):
+        with policy.locked():
+            entered.append(True)
+    assert io.calls[-1][0] == last and policy.held["depth"] == 0
+    assert bool(entered) is (failure in {"release", "close"})
+    if failure in {"mkdir", "open"}:
+        assert ("close",) not in io.calls
+
+
+def test_body_failure_is_not_swallowed_and_release_close_still_run():
+    io = IO()
+    policy = api().TrackerLock(io)
+    with pytest.raises(ValueError, match="body failed"):
+        with policy.locked():
+            raise ValueError("body failed")
+    assert io.calls[-2:] == [("release",), ("close",)]
+    assert policy.held["depth"] == 0
+
+
+def test_warning_failure_still_closes_and_does_not_enter_body():
+    io = IO(acquired=False, marker="880", fail={"warn"})
+    policy = api().TrackerLock(io)
+    with pytest.raises(OSError, match="warn"):
+        with policy.locked(skip_if_busy=True):
+            pytest.fail("source diagnostic failure propagates")
+    assert io.calls[-1] == ("close",) and policy.held["depth"] == 0
+
+
+def test_continuous_busy_marker_survives_passes_until_success_clears_it():
+    io = IO(acquired=False, marker=None)
+    policy = api().TrackerLock(io)
+    for now in (1000.0, 1119.999):
+        io.now = now
+        with pytest.raises(api().LockBusy):
+            with policy.locked(skip_if_busy=True):
+                pytest.fail("not yet stalled")
+    io.now = 1120.0
+    with policy.locked(skip_if_busy=True):
+        io.call("stalled_body")
+    assert io.marker == "1000.0"
+    io.acquired = True
+    with policy.locked():
+        pass
+    assert io.marker is None
+    io.acquired = False
+    with pytest.raises(api().LockBusy):
+        with policy.locked(skip_if_busy=True):
+            pytest.fail("new refusal starts a new interval")
+    assert io.marker == "1120.0"
+
+
+class RecordIO(IO):
+    def __init__(self):
+        super().__init__()
+        self.rows = {}
+
+    def read_symbol(self, symbol, tfs):
+        self.call("matrix", self.now)
+        return {tf: SimpleNamespace(net=0.0) for tf in tfs}
+
+    def quote_payload(self):
+        self.call("quotes", self.now)
+        return {"OANDA:XAUUSD": {"lp": 100.0, "ts": self.now}}
+
+    def load(self):
+        self.call("load", self.now)
+        return deepcopy(self.rows)
+
+    def save(self, rows):
+        self.call("save", self.now)
+        self.rows = deepcopy(rows)
+
+
+@pytest.mark.parametrize("new_exposure", [False, True])
+def test_actual_record_uses_prelock_evidence_but_postacquire_state_and_clock(new_exposure):
+    io = RecordIO()
+    lock = api().TrackerLock(io)
+    io.locked = lock.locked
+    def acquired():
+        io.now = 1002.0  # Supplied fixture elapsed time, NOT configured30s timeout.
+        if new_exposure:
+            io.rows["other"] = {"symbol": "OANDA:XAUUSD", "direction": "לונג", "state": "OPEN"}
+    io.after_acquire = acquired
+    plan = Plan("OANDA:XAUUSD", 100.0, "reversal", "לונג", entry=100.0,
+                stop=90.0, targets=[("TP1", 120.0)])
+    assert TrackerAdmission(io).record(plan) is not new_exposure
+    assert io.calls[:3] == [("matrix", 1000.0), ("matrix", 1000.0), ("quotes", 1000.0)]
+    assert ("load", 1002.0) in io.calls
+    assert io.calls[-2:] == [("release",), ("close",)]
+    if new_exposure:
+        assert list(io.rows) == ["other"] and not any(c[0] == "save" for c in io.calls)
+    else:
+        row = next(iter(io.rows.values()))
+        assert row["ts"] == row["filled_ts"] == 1002.0 and row["state"] == "OPEN"
+        assert row["revalidation_verified"] is False  # Advisory OPEN, not broker fill.
```

## tests/tree_spec/test_tracker_lock_source.py

```diff
diff --git a/tests/tree_spec/test_tracker_lock_source.py b/tests/tree_spec/test_tracker_lock_source.py
new file mode 100644
index 0000000..438722c
--- /dev/null
+++ b/tests/tree_spec/test_tracker_lock_source.py
@@ -0,0 +1,94 @@
+"""Mutations test the auditor, independently of runtime behavioral tests."""
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
+REPO = Path(__file__).resolve().parents[2]
+SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
+    "C:/Users/roeea/AppData/Local/Temp/tr-tree-source-review-4efd65cf2e284d97a81199af6195f149"))
+RUNTIME = REPO / "trading_system/tree_replay/_vendor/tracker_lock.py"
+
+
+def api():
+    name = "trading_system.tree_spec.tracker_lock_source"
+    assert importlib.util.find_spec(name) is not None, "lock source auditor missing"
+    return importlib.import_module(name)
+
+
+def test_complete_pinned_policy_is_verified_without_full_replay_claim():
+    r = api().audit_tracker_lock_source(SOURCE)
+    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
+    assert r["checked_projections"] == ["tracker.lock_constants", "tracker.LockBusy",
+                                        "tracker._busy_for", "tracker._locked"]
+    assert r["blockers"] == [] and not r["ready_for_replay"] and not r["ready_for_training"]
+
+
+@pytest.mark.parametrize("old,new", [
+    ("LOCK_TIMEOUT_S = 30.0", "LOCK_TIMEOUT_S = 3.0"),
+    ("RESOLVE_LOCK_WAIT_S = 3.0", "RESOLVE_LOCK_WAIT_S = 30.0"),
+    ("LOCK_STALL_S = 120.0", "LOCK_STALL_S = 121.0"),
+    ("stuck < LOCK_STALL_S", "stuck <= LOCK_STALL_S"),
+    ('self.held["depth"] > 0', 'self.held["depth"] > 1'),
+    ('self.held = {"depth": 0}', 'self.held = {"depth": 1}'),
+    ("self.source.now_epoch() - float(self.source.read_busy())", "0.0"),
+    ("self.source.clear_busy()", "pass"),
+    ("self.source.release(f)", "pass"),
+    ("f.close()", "pass"),
+    ("@contextmanager", ""),
+    ("from contextlib import contextmanager", "from contextlib import contextmanager\nimport os"),
+])
+def test_changed_policy_or_extra_code_is_blocked(monkeypatch, old, new):
+    original = Path.read_text
+    text = original(RUNTIME, encoding="utf-8")
+    assert old in text
+    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw:
+        text.replace(old, new) if p.resolve() == RUNTIME.resolve() else original(p, *a, **kw))
+    r = api().audit_tracker_lock_source(SOURCE)
+    assert not r["source_subset_verified"] and "VENDOR_AST_MISMATCH" in r["blockers"]
+
+
+def test_wrong_source_commit_and_baseline_cannot_certify_same_code(monkeypatch):
+    module = api()
+    original_git = module._git
+    monkeypatch.setattr(module, "_git", lambda p, *a:
+        "0"*40 if a == ("HEAD",) else original_git(p, *a))
+    assert "SOURCE_COMMIT_MISMATCH" in module.audit_tracker_lock_source(SOURCE)["blockers"]
+    monkeypatch.setattr(module, "_git", original_git)
+    original_read = Path.read_text
+    def read(path, *a, **kw):
+        text = original_read(path, *a, **kw)
+        return text.replace(module.COMMIT, "0"*40) if path.name == "existing-alerts-baseline.json" else text
+    monkeypatch.setattr(Path, "read_text", read)
+    assert "BASELINE_COMMIT_MISMATCH" in module.audit_tracker_lock_source(SOURCE)["blockers"]
+
+
+def test_changed_source_blob_blocks_even_when_selected_functions_match(monkeypatch):
+    original = Path.read_text
+    target = SOURCE / "chart-desk/chartdesk/tracker.py"
+    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw:
+        original(p, *a, **kw)+("\n# changed\n" if p.resolve() == target.resolve() else ""))
+    assert "SOURCE_BLOB_MISMATCH" in api().audit_tracker_lock_source(SOURCE)["blockers"]
+
+
+def test_missing_root_and_runtime_report_blocked(tmp_path, monkeypatch):
+    module = api()
+    assert not module.audit_tracker_lock_source(tmp_path)["source_subset_verified"]
+    monkeypatch.setattr(module, "RUNTIME", tmp_path / "missing.py")
+    assert any("VENDOR_UNREADABLE" in b for b in module.audit_tracker_lock_source(SOURCE)["blockers"])
+
+
+def test_cli_outside_repo_emits_json_and_correct_verification_exit(tmp_path):
+    api()
+    command = [sys.executable, str(REPO / "tools/check_tracker_lock_source_parity.py"), "--source-root"]
+    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
+        run = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
+                             text=True, encoding="utf-8", timeout=30)
+        assert run.returncode == code, run.stderr
+        r = json.loads(run.stdout)
+        assert r["status"] == status and not r["ready_for_replay"] and not r["ready_for_training"]
```

## docs/architecture/TRACKER-LOCK-SOURCE-USAGE.md

```diff
diff --git a/docs/architecture/TRACKER-LOCK-SOURCE-USAGE.md b/docs/architecture/TRACKER-LOCK-SOURCE-USAGE.md
new file mode 100644
index 0000000..235ce17
--- /dev/null
+++ b/docs/architecture/TRACKER-LOCK-SOURCE-USAGE.md
@@ -0,0 +1,83 @@
+# Original tracker lock policy over offline ports
+
+The private `trading_system.tree_replay._vendor.tracker_lock.TrackerLock` retains
+original tracker locking policy, not an operating-system lock implementation.
+It supplies the context manager consumed by original TrackerAdmission.record
+and, later, original resolver callers. No live module is imported or executed.
+
+```python
+from trading_system.tree_replay._vendor.tracker_lock import TrackerLock, LockBusy
+
+policy = TrackerLock(supplied_lock_ports)
+# The application wires tracker_source.locked to this same policy.locked.
+try:
+    with policy.locked(wait=30.0, skip_if_busy=True):
+        run_supplied_resolver_calls()
+except LockBusy:
+    pass  # Source caller skips its resolver calls, not necessarily later producers.
+```
+
+`supplied_lock_ports` and the resolver callable are application dependencies in
+this wiring example, not provided historical backends or a complete replay API.
+Every entry point representing one source process must share the policy instance.
+Its `held` dictionary models process-global reentrance, not thread-local ownership.
+No default successful acquisition, blank busy history or elapsed-time assumption
+is supplied. Existing causal state/quote/log/frame providers remain separate.
+
+## Exact port responsibilities
+
+| Method | Required external behavior |
+| --- | --- |
+| ensure_lock_directory() | Complete or fail the source directory preparation |
+| open_lock() | Source append-mode, nontruncating open; return handle with close() |
+| try_acquire(handle, timeout=wait) | Return supplied acquisition outcome; expose any actual post-attempt clock/publications through the caller's shared scheduler |
+| release(handle) | Release only after source says acquisition succeeded |
+| read_busy() | Read original marker text; absent/read failure raises |
+| write_busy(text) | Complete or fail writing source's clock string |
+| clear_busy() | Delete marker if present; absence is successful, matching missing_ok |
+| now_epoch() | Actual operation clock; not always initial decision time |
+| warn(text) | Record replay diagnostic, or raise its supplied failure; no real stderr write |
+
+Ports must preserve availability and failed-attempt evidence when bound to real
+historical artifacts. Source catches a failed marker read/write/clear; their
+failure evidence must survive those catches in that future backend. The policy
+alone is not an evidence journal or source-data approval.
+
+## Preserved behavior
+
+Writer default is30seconds; resolver default3seconds; market-watch explicitly
+requests30seconds for its resolver wrapper. These are maximum-wait arguments,
+not proof that the clock advances by those durations. Real OS polling is separate.
+Writers proceed even when acquire returns false. Resolvers raise LockBusy when
+continuous refusal age is below120seconds; at120 or above they proceed unlocked.
+Malformed marker text is best-effort reset and treated as zero age. Negative and
+nonfinite float ages preserve source comparisons, including NaN fail-open.
+
+Nested sections increment/decrement shared depth without reopening/reacquiring,
+even inside a writer that proceeded unlocked. A body failure unwinds depth and
+releases an acquired handle. Release failure still closes it. Open failure occurs
+before the source finally, so there is no invented close on a nonexistent handle.
+The component deliberately does not repair questionable source behaviors silently.
+
+Original record computes bias/thesis/born state before entering its lock; state
+reload and new record timestamp occur afterwards. Integration tests exercise the
+real record method with supplied acquisition-time state and clock changes. They
+do not certify all causal providers together or model competing real processes.
+Advisory OPEN continues to mean unverified broker fill, not economic execution.
+
+## Verification
+
+```powershell
+python -m pytest tests/tree_replay/test_tracker_lock.py tests/tree_spec/test_tracker_lock_source.py tests/tree_replay/test_tracker_admission.py tests/tree_replay/test_tracker_storage.py tests/tree_replay/test_admission_io.py -q --tb=short
+python tools/check_tracker_lock_source_parity.py --source-root C:/path/to/retained-parent
+```
+
+The source CLI audits full constants/exception/initializer/methods/imports against
+the pinned chart-desk tracker. It parses source only and exits0verified/2blocked.
+Both readiness flags remain false. Tests accept TR_TREE_SOURCE_ROOT to locate the
+required pinned checkout; missing evidence fails rather than silently skipping.
+
+Required next work: shared scheduler and supplied lock outcomes/publications,
+full watch state and caller/resolver lifecycle; other tree branches; economic
+simulator/dataset/models/evaluation. No live actions, historical data acquisition,
+new outcome labels or training are enabled by this source-policy component.
```

