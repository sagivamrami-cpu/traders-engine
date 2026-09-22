# Watch storage Task2 source-audit package

Base/HEAD c1b6071633c55376c64f0a98ece843706f420f49; full untracked files.

```diff
diff --git a/trading_system/tree_spec/watch_storage_source.py b/trading_system/tree_spec/watch_storage_source.py
new file mode 100644
index 0000000..c6b9a97
--- /dev/null
+++ b/trading_system/tree_spec/watch_storage_source.py
@@ -0,0 +1,88 @@
+"""Audit exact pinned watch main persistence statements without executing source."""
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
+RUNTIME = ROOT / "trading_system/tree_replay/_vendor/watch_storage.py"
+COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+BLOB = "f530fbe82cffbaf831c7a7725c7a9bf6143e6b8b"
+ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError,
+          subprocess.SubprocessError)
+
+
+def _projection(text):
+    main, = _selected(text, ["main"])
+    patterns = [
+        "st = json.loads(STATE.read_text()) if STATE.exists() else {}",
+        "STATE.parent.mkdir(exist_ok=True)",
+        "STATE.write_text(json.dumps(st))",
+    ]
+    expected = [_dump(ast.parse(s).body[0]) for s in patterns]
+    positions = [[i for i, n in enumerate(main.body) if _dump(n) == p] for p in expected]
+    if [len(p) for p in positions] != [1, 1, 2]:
+        raise ValueError("WATCH_PERSISTENCE_CARDINALITY_MISMATCH")
+    load_i, directory_i = positions[0][0], positions[1][0]
+    first_i, final_i = positions[2]
+    if not load_i < directory_i == first_i-1 < final_i:
+        raise ValueError("WATCH_PERSISTENCE_ORDER_MISMATCH")
+    if final_i != len(main.body)-2 or _dump(main.body[-1]) != _dump(ast.parse("return 0").body[0]):
+        raise ValueError("WATCH_FINAL_PERSISTENCE_BOUNDARY_MISMATCH")
+    load, directory, first, final = [main.body[i] for i in (load_i, directory_i, first_i, final_i)]
+    for old, new in [("STATE.exists()", "self.source.exists()"),
+                     ("STATE.read_text()", "self.source.read_text()")]:
+        _replace_exact(load, old, new)
+    _replace_exact(directory, "STATE.parent.mkdir(exist_ok=True)",
+                   "self.source.ensure_directory(exist_ok=True)")
+    for node in (first, final):
+        _replace_exact(node, "STATE.write_text(json.dumps(st))", "self.source.write_text(json.dumps(st))")
+    module = ast.parse("import json\nclass WatchStorage:\n    def __init__(self, source):\n        self.source = source")
+    for signature, body in [
+        ("def load(self): pass", [load, ast.parse("return st").body[0]]),
+        ("def save_before_producers(self, st): pass", [directory, first]),
+        ("def save_final(self, st): pass", [final]),
+    ]:
+        method = ast.parse(signature).body[0]
+        method.body = body
+        module.body[1].body.append(method)
+    return module.body
+
+
+def audit_watch_storage_source(source_root):
+    blockers, checked = [], []
+    report = dict(status="BLOCKED", source_subset_verified=False, blockers=blockers,
+        checked_projections=checked, source_commits={"chart-desk": COMMIT},
+        ready_for_replay=False, ready_for_training=False)
+    try:
+        root = Path(source_root) / "chart-desk"
+        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
+            blockers.append("NOT_REPOSITORY_ROOT")
+        if _git(root, "HEAD") != COMMIT:
+            blockers.append("SOURCE_COMMIT_MISMATCH")
+        baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
+        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
+            blockers.append("BASELINE_COMMIT_MISMATCH")
+        text = (root / "scripts/market_watch.py").read_text(encoding="utf-8")
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
+            checked.extend(["watch.load", "watch.save_before_producers", "watch.save_final"])
+    except ERRORS as exc:
+        blockers.append(f"VENDOR_UNREADABLE:{type(exc).__name__}")
+    if not blockers:
+        report.update(status="VERIFIED", source_subset_verified=True)
+    return report

```

```diff
diff --git a/tools/check_watch_storage_source_parity.py b/tools/check_watch_storage_source_parity.py
new file mode 100644
index 0000000..93536a2
--- /dev/null
+++ b/tools/check_watch_storage_source_parity.py
@@ -0,0 +1,23 @@
+"""Verify pinned watch persistence source without running the alert system."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.watch_storage_source import audit_watch_storage_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True,
+                        help="Explicit parent of retained chart-desk checkout")
+    report = audit_watch_storage_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```

```diff
diff --git a/tests/tree_spec/test_watch_storage_source.py b/tests/tree_spec/test_watch_storage_source.py
new file mode 100644
index 0000000..4fce0e2
--- /dev/null
+++ b/tests/tree_spec/test_watch_storage_source.py
@@ -0,0 +1,110 @@
+"""Watch persistence audit rejects changed source identity and runtime behavior."""
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
+RUNTIME = REPO / "trading_system/tree_replay/_vendor/watch_storage.py"
+
+
+def api():
+    name = "trading_system.tree_spec.watch_storage_source"
+    assert importlib.util.find_spec(name) is not None, "watch storage auditor missing"
+    return importlib.import_module(name)
+
+
+def test_actual_source_statements_and_complete_runtime_verify():
+    r = api().audit_watch_storage_source(SOURCE)
+    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
+    assert r["blockers"] == []
+    assert r["checked_projections"] == ["watch.load", "watch.save_before_producers", "watch.save_final"]
+    assert not r["ready_for_replay"] and not r["ready_for_training"]
+
+
+def intercept(monkeypatch, target, transform):
+    original_read = Path.read_text
+    def read(path, *args, **kwargs):
+        text = original_read(path, *args, **kwargs)
+        return transform(text) if path.resolve() == target.resolve() else text
+    monkeypatch.setattr(Path, "read_text", read)
+
+
+@pytest.mark.parametrize("old,new", [
+    ("else {}", "else None"),
+    ("return st", "return {}"),
+    ("json.dumps(st)", "json.dumps(st, sort_keys=True)"),
+    ("json.dumps(st)", "json.dumps(st, ensure_ascii=False)"),
+    ("json.dumps(st)", "json.dumps(st, indent=1)"),
+    ("self.source.ensure_directory(exist_ok=True)", "pass"),
+    ("self.source = source", "self.source = None"),
+    ("import json", "import json\nimport os"),
+    ("def save_final(self, st):\n        self.source.write_text(json.dumps(st))",
+     "def save_final(self, st):\n        self.source.ensure_directory(exist_ok=True)\n        self.source.write_text(json.dumps(st))"),
+])
+def test_mutated_runtime_is_not_certified(monkeypatch, old, new):
+    api()
+    assert old in RUNTIME.read_text(encoding="utf-8")
+    intercept(monkeypatch, RUNTIME, lambda s: s.replace(old, new))
+    r = api().audit_watch_storage_source(SOURCE)
+    assert not r["source_subset_verified"] and "VENDOR_AST_MISMATCH" in r["blockers"]
+
+
+@pytest.mark.parametrize("fault", ["blob", "load", "first_save", "final_save"])
+def test_retained_source_drift_cannot_be_hidden_by_matching_runtime(monkeypatch, fault):
+    target = SOURCE / "chart-desk/scripts/market_watch.py"
+    def mutate(text):
+        if fault == "blob":
+            return text+"\n# changed source\n"
+        if fault == "load":
+            return text.replace("st = json.loads(STATE.read_text()) if STATE.exists() else {}", "st = {}")
+        if fault == "first_save":
+            return text.replace("STATE.parent.mkdir(exist_ok=True)\n    STATE.write_text(json.dumps(st))", "STATE.write_text(json.dumps(st))")
+        return text.replace("    STATE.write_text(json.dumps(st))\n    return 0", "    return 0")
+    api()
+    intercept(monkeypatch, target, mutate)
+    r = api().audit_watch_storage_source(SOURCE)
+    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH" in r["blockers"]
+    if fault != "blob":
+        assert any(b.startswith("SOURCE_UNREADABLE:ValueError") for b in r["blockers"])
+
+
+def test_wrong_head_blocks_even_with_correct_files(monkeypatch):
+    m = api()
+    original = m._git
+    monkeypatch.setattr(m, "_git", lambda root, *args: "0"*40 if args == ("HEAD",) else original(root, *args))
+    assert "SOURCE_COMMIT_MISMATCH" in m.audit_watch_storage_source(SOURCE)["blockers"]
+
+
+def test_changed_baseline_cannot_redefine_audit_authority(monkeypatch):
+    api()
+    target = REPO / "configs/trees/existing-alerts-baseline.json"
+    intercept(monkeypatch, target, lambda s: s.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0"*40))
+    assert "BASELINE_COMMIT_MISMATCH" in api().audit_watch_storage_source(SOURCE)["blockers"]
+
+
+def test_missing_source_and_runtime_remain_blocked(tmp_path, monkeypatch):
+    m = api()
+    assert not m.audit_watch_storage_source(tmp_path)["source_subset_verified"]
+    monkeypatch.setattr(m, "RUNTIME", tmp_path / "absent.py")
+    r = m.audit_watch_storage_source(SOURCE)
+    assert not r["source_subset_verified"] and any(b.startswith("VENDOR_UNREADABLE") for b in r["blockers"])
+
+
+def test_cli_success_and_blocked_exits_from_unrelated_directory(tmp_path):
+    api()
+    command = [sys.executable, str(REPO / "tools/check_watch_storage_source_parity.py"), "--source-root"]
+    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
+        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
+                           text=True, encoding="utf-8", timeout=30)
+        assert p.returncode == code, p.stderr
+        r = json.loads(p.stdout)
+        assert r["status"] == status and not r["ready_for_training"]

```

