# Task2 full new-file package

```diff
diff --git a/trading_system/tree_spec/lifecycle_primitives_source.py b/trading_system/tree_spec/lifecycle_primitives_source.py
new file mode 100644
index 0000000..a62c0e7
--- /dev/null
+++ b/trading_system/tree_spec/lifecycle_primitives_source.py
@@ -0,0 +1,120 @@
+"""Independently pin and audit inert lifecycle source, complete projections and dependencies."""
+import ast
+import hashlib
+from pathlib import Path
+
+from .tracker_admission_source import (
+    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
+    audit_tracker_admission_source,
+)
+
+
+ROOT = Path(__file__).resolve().parents[2]
+VENDOR = ROOT / "trading_system/tree_replay/_vendor"
+COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+BLOBS = {
+    "tracker.py": "b616b34022e436545d8c1daf85eced51614fd74e",
+    "desk_success.py": "d2b2fdb2889841f587338e56041ffdc8df6c298c",
+    "voice.py": "46fc6912ed8914b54209f9c08c12de9f48a19059",
+}
+BAR_SYMBOLS = ["_fill_on_tape", "_position_extremes", "position_bars", "_open_extremes", "_entry_band"]
+METHODS = ["reached", "observe", "observe_bars", "classification", "stop_note"]
+# Exact expressions once per named function, not a broad name-based rewrite.
+EXPRESSIONS = {
+    "reached": [("time.time()", "self.source.now_epoch()")],
+    "observe": [("reached(t)", "self.reached(t)"),
+                ("reached(candidate)", "self.reached(candidate)"),
+                ("time.time()", "self.source.now_epoch()")],
+    "observe_bars": [("reached(t)", "self.reached(t)"),
+        ('tracker.pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())'),
+        ('observe(t, float(hits.loc[at, column]), time.time(), "verified_post_fill_bars")',
+         'self.observe(t, float(hits.loc[at, column]), self.source.now_epoch(), "verified_post_fill_bars")')],
+    "classification": [("reached(t)", "self.reached(t)")],
+    "stop_note": [("reached(t)", "self.reached(t)")],
+}
+
+
+def _bars_projection(text):
+    nodes = _selected(text, BAR_SYMBOLS)
+    _replace_exact(nodes[-1], "from .tradeplan import entry_zone",
+                   "from .pricing import entry_zone", statement=True)
+    return ast.parse("import pandas as pd").body + nodes
+
+
+def _success_projection(text):
+    nodes = _selected(text, ["VERSION", "FLOOR", "minimum"]+METHODS)
+    _replace_exact(nodes[2], "from .basis import canonical_symbol",
+                   "from .basis_symbols import canonical_symbol", statement=True)
+    cls = ast.parse("class DeskSuccess:\n    def __init__(self, source):\n        self.source = source").body[0]
+    for name, node in zip(METHODS, nodes[3:]):
+        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
+                arg.arg == "self" for arg in node.args.args):
+            raise ValueError("METHOD_SHAPE_MISMATCH:"+name)
+        for old, new in EXPRESSIONS[name]:
+            _replace_exact(node, old, new)
+        if name == "observe_bars":
+            _replace_exact(node, "from . import tracker", "from . import lifecycle_bars as tracker", statement=True)
+        node.args.args.insert(0, ast.arg(arg="self"))
+        cls.body.append(node)
+    imports = ast.parse("from __future__ import annotations\nimport math\nimport pandas as pd\nfrom . import lifecycle_voice as voice").body
+    return imports + nodes[:3] + [cls]
+
+
+def audit_lifecycle_primitives_source(source_root):
+    """Only source inspection: never import or execute retained chart-desk code."""
+    blockers, checked, dependencies = [], [], {}
+    report = dict(status="BLOCKED", source_subset_verified=False, blockers=blockers,
+        checked_projections=checked, dependencies=dependencies,
+        source_commits={"chart-desk": COMMIT}, ready_for_replay=False, ready_for_training=False)
+    try:
+        source_root = Path(source_root)
+    except INPUT_ERRORS as exc:
+        blockers.append("SOURCE_ROOT_INVALID:"+type(exc).__name__)
+        return report
+    try:
+        root = source_root / "chart-desk"
+        if Path(_git(root, "--show-toplevel")).resolve() != root.resolve():
+            blockers.append("NOT_REPOSITORY_ROOT")
+        if _git(root, "HEAD") != COMMIT:
+            blockers.append("SOURCE_COMMIT_MISMATCH")
+        baseline = _read_json(ROOT / "configs/trees/existing-alerts-baseline.json")
+        if [r.get("commit") for r in baseline["repositories"] if r.get("name") == "chart-desk"] != [COMMIT]:
+            blockers.append("BASELINE_COMMIT_MISMATCH")
+    except INPUT_ERRORS as exc:
+        blockers.append("SOURCE_IDENTITY_UNREADABLE:"+type(exc).__name__)
+    for file, candidate, project in [
+        ("tracker.py", "lifecycle_bars", _bars_projection),
+        ("desk_success.py", "desk_success", _success_projection),
+        ("voice.py", "lifecycle_voice", lambda text: _without_doc(ast.parse(text))),
+    ]:
+        try:
+            text = (source_root / "chart-desk/chartdesk" / file).read_text(encoding="utf-8")
+            raw = text.encode("utf-8")
+            digest = hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
+            if digest != BLOBS[file]:
+                blockers.append("SOURCE_BLOB_MISMATCH:"+file)
+                continue
+            expected = project(text)
+        except INPUT_ERRORS as exc:
+            blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{file}:{type(exc).__name__}:{exc}")
+            continue
+        try:
+            actual = _without_doc(ast.parse((VENDOR / (candidate+".py")).read_text(encoding="utf-8")))
+            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+                blockers.append("VENDOR_AST_MISMATCH:"+candidate+".py")
+            else:
+                checked.append(candidate)
+        except INPUT_ERRORS as exc:
+            blockers.append(f"VENDOR_UNREADABLE:{candidate}.py:{type(exc).__name__}")
+    try:
+        inherited = audit_tracker_admission_source(source_root)
+        dependencies["tracker_admission"] = inherited
+        if not inherited["source_subset_verified"]:
+            blockers.extend("DEPENDENCY:"+b for b in inherited["blockers"])
+            if not inherited["blockers"]:
+                blockers.append("DEPENDENCY:NOT_VERIFIED")
+    except INPUT_ERRORS as exc:
+        blockers.append("DEPENDENCY_UNREADABLE:"+type(exc).__name__)
+    if not blockers:
+        report.update(status="VERIFIED", source_subset_verified=True)
+    return report

```

```diff
diff --git a/tools/check_lifecycle_primitives_source_parity.py b/tools/check_lifecycle_primitives_source_parity.py
new file mode 100644
index 0000000..d016147
--- /dev/null
+++ b/tools/check_lifecycle_primitives_source_parity.py
@@ -0,0 +1,23 @@
+"""Audit pinned position geometry and movement proof without running the alert system."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.lifecycle_primitives_source import audit_lifecycle_primitives_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True,
+                        help="Explicit parent of retained chart-desk and trading-floor checkouts")
+    report = audit_lifecycle_primitives_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```

```diff
diff --git a/tests/tree_spec/test_lifecycle_primitives_source.py b/tests/tree_spec/test_lifecycle_primitives_source.py
new file mode 100644
index 0000000..a888cb2
--- /dev/null
+++ b/tests/tree_spec/test_lifecycle_primitives_source.py
@@ -0,0 +1,128 @@
+"""Inert-source auditing rejects lifecycle drift, including inherited pricing."""
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
+VENDOR = REPO / "trading_system/tree_replay/_vendor"
+
+
+def api():
+    name = "trading_system.tree_spec.lifecycle_primitives_source"
+    assert importlib.util.find_spec(name) is not None, "lifecycle auditor missing"
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch, target, transform):
+    original = Path.read_text
+    def read(path, *args, **kwargs):
+        text = original(path, *args, **kwargs)
+        return transform(text) if path.resolve() == target.resolve() else text
+    monkeypatch.setattr(Path, "read_text", read)
+
+
+def test_complete_source_projections_and_dependencies_verify():
+    r = api().audit_lifecycle_primitives_source(SOURCE)
+    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
+    assert r["blockers"] == []
+    assert r["checked_projections"] == ["lifecycle_bars", "desk_success", "lifecycle_voice"]
+    assert r["dependencies"]["tracker_admission"]["status"] == "VERIFIED"
+    assert not r["ready_for_replay"] and not r["ready_for_training"]
+
+
+@pytest.mark.parametrize("file,old,new", [
+    ("lifecycle_bars.py", "x.timestamp() > float(t['ts'])", "x.timestamp() >= float(t['ts'])"),
+    ("lifecycle_bars.py", "x >= _fts", "x > _fts"),
+    ("lifecycle_bars.py", "window.iloc[1:] if fill_bar_first else window", "window"),
+    ("lifecycle_bars.py", "from .pricing import entry_zone", "from .tradeplan import entry_zone"),
+    ("lifecycle_bars.py", "import pandas as pd", "import pandas as pd\nimport os"),
+    ("desk_success.py", "paying.index < stopped[stopped].index[0]", "paying.index <= stopped[stopped].index[0]"),
+    ("desk_success.py", "include_fill_bar=True", "include_fill_bar=False"),
+    ("desk_success.py", "p['trade_id'] == t['trade_id']", "True"),
+    ("desk_success.py", "p['symbol'] == t['symbol']", "True"),
+    ("desk_success.py", "p['observed_ts'] <= t['resolved_ts']", "True"),
+    ("desk_success.py", "self.source.now_epoch()", "time.time()"),
+    ("desk_success.py", "pd.Timestamp(self.source.now_utc())", "pd.Timestamp(self.source.now_epoch(), unit='s', tz='UTC')"),
+    ("desk_success.py", "'verified_post_fill_bars'", "'unverified_bars'"),
+    ("desk_success.py", "self.source = source", "self.source = None"),
+    ("desk_success.py", "def reached(self, t, *, as_of=None)", "def reached(self, t, as_of=None)"),
+    ("desk_success.py", "from .basis_symbols import canonical_symbol", "from .basis import canonical_symbol"),
+    ("lifecycle_voice.py", "return 10.0 if is_gold(symbol) else 1.0", "return 1.0"),
+    ("lifecycle_voice.py", "import re", "import re\nimport time"),
+])
+def test_runtime_behavior_clock_identity_units_and_extra_code_drift_blocks(monkeypatch, file, old, new):
+    api()
+    target = VENDOR / file
+    assert old in target.read_text(encoding="utf-8"), file
+    intercept(monkeypatch, target, lambda text: text.replace(old, new))
+    r = api().audit_lifecycle_primitives_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert "VENDOR_AST_MISMATCH:"+file in r["blockers"]
+
+
+@pytest.mark.parametrize("file", ["tracker.py", "desk_success.py", "voice.py"])
+def test_source_blob_drift_is_not_redefined_as_authority(monkeypatch, file):
+    api()
+    intercept(monkeypatch, SOURCE / "chart-desk/chartdesk" / file, lambda s: s+"\n# drift\n")
+    r = api().audit_lifecycle_primitives_source(SOURCE)
+    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH:"+file in r["blockers"]
+
+
+@pytest.mark.parametrize("file,old,new", [
+    ("pricing.py", "def entry_zone", "def changed_entry_zone"),
+    ("basis_symbols.py", "def canonical_symbol", "def changed_canonical_symbol"),
+])
+def test_actual_inherited_runtime_mutation_blocks(monkeypatch, file, old, new):
+    api()
+    target = VENDOR / file
+    assert old in target.read_text(encoding="utf-8")
+    intercept(monkeypatch, target, lambda s: s.replace(old, new))
+    r = api().audit_lifecycle_primitives_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert any(b.startswith("DEPENDENCY:") and file in b for b in r["blockers"])
+
+
+@pytest.mark.parametrize("fault", ["head", "root", "baseline"])
+def test_identity_and_baseline_cannot_redefine_pin(monkeypatch, fault):
+    m = api()
+    if fault == "baseline":
+        intercept(monkeypatch, REPO / "configs/trees/existing-alerts-baseline.json",
+                  lambda s: s.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0"*40))
+        want = "BASELINE_COMMIT_MISMATCH"
+    else:
+        original = m._git
+        arg, value, want = ("HEAD", "0"*40, "SOURCE_COMMIT_MISMATCH") if fault == "head" else ("--show-toplevel", str(SOURCE), "NOT_REPOSITORY_ROOT")
+        monkeypatch.setattr(m, "_git", lambda root, *args: value if args == (arg,) else original(root, *args))
+    assert want in m.audit_lifecycle_primitives_source(SOURCE)["blockers"]
+
+
+@pytest.mark.parametrize("file", ["lifecycle_bars.py", "desk_success.py", "lifecycle_voice.py"])
+def test_missing_candidate_does_not_certify_partial_closure(monkeypatch, file):
+    api()
+    def missing(text):
+        raise FileNotFoundError(file)
+    intercept(monkeypatch, VENDOR / file, missing)
+    r = api().audit_lifecycle_primitives_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert any(b.startswith("VENDOR_UNREADABLE:"+file) for b in r["blockers"])
+
+
+def test_missing_source_and_cli_exit_from_unrelated_directory(tmp_path):
+    assert not api().audit_lifecycle_primitives_source(tmp_path)["source_subset_verified"]
+    command = [sys.executable, str(REPO / "tools/check_lifecycle_primitives_source_parity.py"), "--source-root"]
+    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
+        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
+                           text=True, encoding="utf-8", timeout=45)
+        assert p.returncode == code, p.stderr
+        r = json.loads(p.stdout)
+        assert r["status"] == status
+        assert not r["ready_for_replay"] and not r["ready_for_training"]

```
