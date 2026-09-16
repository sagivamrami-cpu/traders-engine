# Task2 full new-file package

```diff
diff --git a/trading_system/tree_spec/claim_verifier_source.py b/trading_system/tree_spec/claim_verifier_source.py
new file mode 100644
index 0000000..7c3e497
--- /dev/null
+++ b/trading_system/tree_spec/claim_verifier_source.py
@@ -0,0 +1,116 @@
+"""Independent fixed-source audit of original claim verification over offline ports."""
+import ast
+import hashlib
+from pathlib import Path
+
+from .tracker_admission_source import (
+    INPUT_ERRORS, _dump, _git, _read_json, _replace_exact, _selected, _without_doc,
+)
+from .lifecycle_primitives_source import audit_lifecycle_primitives_source
+
+
+ROOT = Path(__file__).resolve().parents[2]
+RUNTIME = ROOT / "trading_system/tree_replay/_vendor/claim_verifier.py"
+COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+BLOB = "3329fdb71f8aebdf13a6fa823e8be0d85e1ced03"
+SOURCE_SYMBOLS = ["TOL", "Verdict", "_tol", "_bars", "_binance_bars", "_covers",
+    "_fill_index", "target", "_NOT_YET", "_closed_past", "_claim_clock",
+    "_fill_unseen", "_frame", "_extreme", "fill", "stop", "check_message"]
+PURE = ["TOL", "Verdict", "_tol", "_covers", "_fill_index", "_NOT_YET",
+        "_closed_past", "_fill_unseen", "_frame", "_extreme"]
+METHODS = ["_bars", "_binance_bars", "target", "_claim_clock", "fill", "stop", "check_message"]
+EXPRESSIONS = {
+    "_bars": [("_binance_bars(symbol, days)", "self._binance_bars(symbol, days)"),
+        ('basis.fetch_corrected(symbol, "15m", days)', 'self.source.fetch_corrected(symbol, "15m", days)')],
+    "_binance_bars": [('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())'),
+        ('_json.load(_rq.urlopen(url, timeout=15))', 'self.source.fetch_json(url, timeout=15)')],
+    "target": [('_bars(trade["symbol"])', 'self._bars(trade["symbol"])'),
+        ('_claim_clock(trade, "claim_ts")', 'self._claim_clock(trade, "claim_ts")')],
+    "_claim_clock": [('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())')],
+    "fill": [('_bars(trade["symbol"])', 'self._bars(trade["symbol"])'),
+        ('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(self.source.now_utc())')],
+    "stop": [('_bars(trade["symbol"])', 'self._bars(trade["symbol"])'),
+        ('_claim_clock(trade, "resolved_ts", "claim_ts")', 'self._claim_clock(trade, "resolved_ts", "claim_ts")')],
+    "check_message": [("reached(trade)", "self.movement.reached(trade)"),
+        ('target(trade, float(m.group(1).replace(",", "")))', 'self.target(trade, float(m.group(1).replace(",", "")))'),
+        ("fill(trade)", "self.fill(trade)"), ("stop(trade)", "self.stop(trade)")],
+}
+STATEMENTS = {
+    "_fill_index": [("from .tradeplan import entry_zone", "from .pricing import entry_zone")],
+    "_binance_bars": [("import json as _json", None), ("import urllib.request as _rq", None)],
+    "check_message": [("from .desk_success import reached", None)],
+}
+
+
+def _projection(text):
+    selected = _selected(text, SOURCE_SYMBOLS)
+    nodes = dict(zip(SOURCE_SYMBOLS, selected))
+    for name, pairs in EXPRESSIONS.items():
+        for old, new in pairs:
+            _replace_exact(nodes[name], old, new)
+    for name, pairs in STATEMENTS.items():
+        for old, new in pairs:
+            _replace_exact(nodes[name], old, new, statement=True)
+    cls = ast.parse("class ClaimVerifier:\n    def __init__(self, source):\n        self.source = source\n        self.movement = DeskSuccess(source)").body[0]
+    for name in METHODS:
+        node = nodes[name]
+        if not isinstance(node, ast.FunctionDef) or node.decorator_list or any(
+                a.arg == "self" for a in node.args.args):
+            raise ValueError("METHOD_SHAPE_MISMATCH:"+name)
+        node.args.args.insert(0, ast.arg(arg="self"))
+        cls.body.append(node)
+    imports = ast.parse("from __future__ import annotations\nimport re\nfrom dataclasses import dataclass\nimport pandas as pd\nfrom .desk_success import DeskSuccess").body
+    return imports + [nodes[n] for n in PURE] + [cls]
+
+
+def audit_claim_verifier_source(source_root):
+    """Inspect source/ASTs only; no import or execution of verifier or source repo."""
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
+    try:
+        text = (source_root / "chart-desk/chartdesk/verify.py").read_text(encoding="utf-8")
+        raw = text.encode("utf-8")
+        if hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest() != BLOB:
+            blockers.append("SOURCE_BLOB_MISMATCH")
+        expected = _projection(text)
+    except INPUT_ERRORS as exc:
+        blockers.append(f"SOURCE_PROJECTION_UNREADABLE:{type(exc).__name__}:{exc}")
+    else:
+        try:
+            actual = _without_doc(ast.parse(RUNTIME.read_text(encoding="utf-8")))
+            if [_dump(n) for n in actual] != [_dump(n) for n in expected]:
+                blockers.append("VENDOR_AST_MISMATCH")
+            else:
+                checked.append("claim_verifier")
+        except INPUT_ERRORS as exc:
+            blockers.append("VENDOR_UNREADABLE:"+type(exc).__name__)
+    try:
+        inherited = audit_lifecycle_primitives_source(source_root)
+        dependencies["lifecycle_primitives"] = inherited
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
diff --git a/tools/check_claim_verifier_source_parity.py b/tools/check_claim_verifier_source_parity.py
new file mode 100644
index 0000000..4eaa334
--- /dev/null
+++ b/tools/check_claim_verifier_source_parity.py
@@ -0,0 +1,23 @@
+"""Audit original independent claim verification without running the alert system."""
+import argparse
+import json
+from pathlib import Path
+import sys
+
+if __package__ in (None, ""):
+    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
+
+from trading_system.tree_spec.claim_verifier_source import audit_claim_verifier_source
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True,
+                        help="Explicit parent of retained chart-desk and trading-floor checkouts")
+    report = audit_claim_verifier_source(parser.parse_args().source_root)
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```

```diff
diff --git a/tests/tree_spec/test_claim_verifier_source.py b/tests/tree_spec/test_claim_verifier_source.py
new file mode 100644
index 0000000..1d12495
--- /dev/null
+++ b/tests/tree_spec/test_claim_verifier_source.py
@@ -0,0 +1,156 @@
+"""The independent verifier audit rejects drift without executing retained code."""
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
+RUNTIME = REPO / "trading_system/tree_replay/_vendor/claim_verifier.py"
+
+
+def api():
+    name = "trading_system.tree_spec.claim_verifier_source"
+    assert importlib.util.find_spec(name) is not None, "claim verifier auditor missing"
+    return importlib.import_module(name)
+
+
+def intercept(monkeypatch, path, transform):
+    original = Path.read_text
+    def read(p, *args, **kwargs):
+        text = original(p, *args, **kwargs)
+        return transform(text) if p.resolve() == path.resolve() else text
+    monkeypatch.setattr(Path, "read_text", read)
+
+
+def test_actual_projection_and_inherited_closure_verify():
+    r = api().audit_claim_verifier_source(SOURCE)
+    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
+    assert r["checked_projections"] == ["claim_verifier"] and not r["blockers"]
+    assert r["dependencies"]["lifecycle_primitives"]["status"] == "VERIFIED"
+    assert not r["ready_for_replay"] and not r["ready_for_training"]
+
+
+@pytest.mark.parametrize("old,new", [
+    ("'XAU': 0.5", "'XAU': 0.0"),
+    ("float(trade['ts']) - bar_s", "float(trade['ts'])"),
+    ("t.timestamp() > float(trade['ts'])", "t.timestamp() >= float(trade['ts'])"),
+    ("last + 900 >= float(when)", "last >= float(when)"),
+    ("last >= float(when)", "last + 900 >= float(when)"),
+    ("aft = df.loc[fill:]", "aft = df.loc[fill:].iloc[1:]"),
+    ("t.timestamp() <= float(when)", "True"),
+    ("self._claim_clock(trade, 'resolved_ts', 'claim_ts')", "self._claim_clock(trade, 'claim_ts')"),
+    ("< 45 * 60", "<= 45 * 60"),
+    ("pd.Timestamp(self.source.now_utc())", "pd.Timestamp.now(tz='UTC')"),
+    ("if venue is not None:", "if venue is None:"),
+    ("limit=1000", "limit=100"),
+    ("timeout=15", "timeout=10"),
+    ("float(r[4])", "float(r[3])"),
+    ("columns=['t', 'open', 'high', 'low', 'close']", "columns=['t', 'open', 'low', 'high', 'close']"),
+    ("self.source.fetch_json(url, timeout=15)", "[]"),
+    ("self.source.fetch_corrected(symbol, '15m', days)", "self.source.fetch_corrected(symbol, '15m', 5)"),
+    ("self.movement.reached(trade)", "True"),
+    ("self.target(trade, float(m.group(1).replace(',', '')))", "Verdict(True)"),
+    ("self.fill(trade)", "self.stop(trade)"),
+    ("from .pricing import entry_zone", "from .lifecycle_bars import _entry_band as entry_zone"),
+    ("import re", "import re\nimport urllib.request"),
+    ("self.movement = DeskSuccess(source)", "self.movement = None"),
+    ("class ClaimVerifier:", "class ClaimVerifier:\n    extra = True"),
+    ("def stop(self, trade: dict)", "def stop(self, trade)"),
+])
+def test_mutated_behavior_transport_clock_router_and_extra_code_fail_audit(monkeypatch, old, new):
+    api()
+    assert old in RUNTIME.read_text(encoding="utf-8"), old
+    intercept(monkeypatch, RUNTIME, lambda text: text.replace(old, new))
+    r = api().audit_claim_verifier_source(SOURCE)
+    assert not r["source_subset_verified"] and "VENDOR_AST_MISMATCH" in r["blockers"]
+
+
+def test_retained_source_changes_cannot_become_authority(monkeypatch):
+    api()
+    intercept(monkeypatch, SOURCE / "chart-desk/chartdesk/verify.py", lambda text: text+"\n# drift\n")
+    r = api().audit_claim_verifier_source(SOURCE)
+    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH" in r["blockers"]
+
+
+@pytest.mark.parametrize("file,old,new", [
+    ("desk_success.py", "p['trade_id'] == t['trade_id']", "True"),
+    ("pricing.py", "def entry_zone", "def altered_entry_zone"),
+])
+def test_real_dependency_drift_blocks_verifier_certification(monkeypatch, file, old, new):
+    api()
+    target = RUNTIME.parent / file
+    assert old in target.read_text(encoding="utf-8")
+    intercept(monkeypatch, target, lambda text: text.replace(old, new))
+    r = api().audit_claim_verifier_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert any(b.startswith("DEPENDENCY:") and file in b for b in r["blockers"])
+
+
+@pytest.mark.parametrize("fault", ["head", "root", "baseline"])
+def test_root_pin_and_baseline_cannot_redefine_authority(monkeypatch, fault):
+    m = api()
+    if fault == "baseline":
+        intercept(monkeypatch, REPO / "configs/trees/existing-alerts-baseline.json",
+            lambda text: text.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0"*40))
+        want = "BASELINE_COMMIT_MISMATCH"
+    else:
+        arg, value, want = ("HEAD", "0"*40, "SOURCE_COMMIT_MISMATCH") if fault == "head" else ("--show-toplevel", str(SOURCE), "NOT_REPOSITORY_ROOT")
+        original = m._git
+        monkeypatch.setattr(m, "_git", lambda root, *args: value if args == (arg,) else original(root, *args))
+    assert want in m.audit_claim_verifier_source(SOURCE)["blockers"]
+
+
+def test_missing_source_and_candidate_are_blocked(tmp_path, monkeypatch):
+    m = api()
+    assert not m.audit_claim_verifier_source(tmp_path)["source_subset_verified"]
+    monkeypatch.setattr(m, "RUNTIME", tmp_path / "absent.py")
+    r = m.audit_claim_verifier_source(SOURCE)
+    assert not r["source_subset_verified"]
+    assert any(b.startswith("VENDOR_UNREADABLE:") for b in r["blockers"])
+
+
+@pytest.mark.parametrize("fault", ["order", "duplicate", "clock_count"])
+def test_projection_preconditions_reject_ambiguous_source_shape(fault):
+    m = api()
+    text = (SOURCE / "chart-desk/chartdesk/verify.py").read_text(encoding="utf-8")
+    if fault == "order":
+        text = text.replace("def _covers(", "def _temporary_swap(").replace(
+            "def _fill_index(", "def _covers(").replace("def _temporary_swap(", "def _fill_index(")
+    elif fault == "duplicate":
+        text += "\ndef stop(trade): return None\n"
+    else:
+        text = text.replace('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(0)')
+    with pytest.raises(ValueError):
+        m._projection(text)
+
+
+def test_cli_explicit_root_from_unrelated_cwd_and_no_runtime_imports(tmp_path):
+    api()
+    command = [sys.executable, str(REPO / "tools/check_claim_verifier_source_parity.py"), "--source-root"]
+    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
+        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
+                           text=True, encoding="utf-8", timeout=45)
+        assert p.returncode == code, p.stderr
+        r = json.loads(p.stdout)
+        assert r["status"] == status and not r["ready_for_training"]
+    script = "\n".join([
+        "import sys",
+        "class Guard:",
+        "    def find_spec(self, fullname, *args):",
+        "        if fullname.startswith(('chartdesk', 'floor', 'trading_system.tree_replay')):",
+        "            raise AssertionError('runtime/source import forbidden: '+fullname)",
+        "sys.meta_path.insert(0, Guard())",
+        "from trading_system.tree_spec.claim_verifier_source import audit_claim_verifier_source",
+        "assert audit_claim_verifier_source(sys.argv[1])['source_subset_verified']",
+    ])
+    p = subprocess.run([sys.executable, "-B", "-c", script, str(SOURCE)], cwd=REPO,
+        capture_output=True, text=True, encoding="utf-8", timeout=45)
+    assert p.returncode == 0, p.stderr

```
