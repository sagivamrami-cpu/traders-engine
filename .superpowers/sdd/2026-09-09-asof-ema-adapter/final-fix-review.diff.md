# Final coverage fix scoped review

Compare these two current files against the same files in final-review.diff.md.
Only the coverage guard and parity fixtures/regressions changed. Other slice
code is unchanged since final review (except the already-reviewed EOF blanks).

```diff
warning: in the working copy of 'tools/check_ema_source_parity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tools/check_ema_source_parity.py b/tools/check_ema_source_parity.py
new file mode 100644
index 0000000..d6c2a7e
--- /dev/null
+++ b/tools/check_ema_source_parity.py
@@ -0,0 +1,149 @@
+"""Verify the audited EMA subset against pinned source text; never import that repo."""
+
+import argparse
+import ast
+import hashlib
+import json
+from pathlib import Path
+import re
+
+
+ROOT = Path(__file__).resolve().parents[1]
+CONTRACT = ROOT / "configs/trees/ema-feature-contracts.json"
+SOURCE_COMMIT = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+# Fixed audit scope, independent of the manifest rows being checked. Blob values
+# remain trusted manifest configuration; this is not a manifest authenticity check.
+REQUIRED_FILES = {
+    "chartdesk/indicators.py": (
+        "trading_system/tree_replay/_vendor/indicators.py",
+        {"_seeded_recursive", "ema", "stdev"},
+        "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
+    ),
+    "chartdesk/tr.py": (
+        "trading_system/tree_replay/_vendor/tr.py",
+        {"TR_EMAS", "emas", "ema_cloud"},
+        "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
+    ),
+    "chartdesk/features.py": (None, set(), ""),
+}
+
+
+def _name(node):
+    if isinstance(node, ast.FunctionDef):
+        return node.name
+    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
+        return node.target.id
+    return None
+
+
+def _dump(node):
+    return ast.dump(node, include_attributes=False)
+
+
+def _contract_blockers(contract, pin):
+    """Validate fixed source-identity/coverage before reading source/vendor files."""
+    if not isinstance(contract, dict):
+        return ["CONTRACT_INVALID_OBJECT"]
+    blockers = []
+    for field, expected in (("schema_version", "chartdesk-ema-contracts-v1"),
+                            ("repository", "chart-desk"), ("commit", SOURCE_COMMIT)):
+        if contract.get(field) != expected:
+            blockers.append(f"CONTRACT_{field.upper()}_MISMATCH")
+    if pin != SOURCE_COMMIT:
+        blockers.append("CONTRACT_COMMIT_MISMATCH")
+    rows = contract.get("files")
+    if not isinstance(rows, list):
+        return blockers + ["CONTRACT_FILE_SET_MISMATCH"]
+    paths = [row.get("path") if isinstance(row, dict) else None for row in rows]
+    if (not all(isinstance(path, str) for path in paths) or
+            len(paths) != len(REQUIRED_FILES) or set(paths) != set(REQUIRED_FILES)):
+        return blockers + ["CONTRACT_FILE_SET_MISMATCH"]
+    for row in rows:
+        path = row["path"]
+        vendor_path, expected_symbols, expected_imports = REQUIRED_FILES[path]
+        if "vendor_path" not in row or row["vendor_path"] != vendor_path:
+            blockers.append(f"CONTRACT_VENDOR_PATH_MISMATCH:{path}")
+        symbols = row.get("symbols")
+        if (not isinstance(symbols, list) or
+                not all(isinstance(symbol, str) for symbol in symbols) or
+                len(symbols) != len(expected_symbols) or set(symbols) != expected_symbols):
+            blockers.append(f"CONTRACT_SYMBOL_SET_MISMATCH:{path}")
+        imports = row.get("allowed_imports")
+        try:
+            if not isinstance(imports, str):
+                raise ValueError("allowed_imports must be text")
+            # Compare full AST lists (order-insensitive), preserving duplicates;
+            # comments/spacing may vary but neither code nor extra imports may enter.
+            actual = sorted(_dump(node) for node in ast.parse(imports).body)
+            expected = sorted(_dump(node) for node in ast.parse(expected_imports).body)
+            if actual != expected:
+                raise ValueError("allowed_imports differs from audited scope")
+        except (ValueError, SyntaxError):
+            blockers.append(f"CONTRACT_IMPORT_MISMATCH:{path}")
+        blob = row.get("git_blob_sha1")
+        if not isinstance(blob, str) or re.fullmatch(r"[0-9a-f]{40}", blob) is None:
+            blockers.append(f"CONTRACT_BLOB_INVALID:{path}")
+    return blockers
+
+
+def check_source_parity(source_root: Path) -> dict:
+    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
+    baseline = json.loads((ROOT / "configs/trees/existing-alerts-baseline.json").read_text(encoding="utf-8"))
+    pin = next(row["commit"] for row in baseline["repositories"] if row["name"] == "chart-desk")
+    blockers = _contract_blockers(contract, pin)
+    if blockers:
+        return {"source_commit": pin, "source_subset_verified": False,
+                "blockers": blockers, "ready_for_replay": False, "ready_for_training": False}
+    for row in contract["files"]:
+        try:
+            # read_text normalizes checkout CRLF; Git blob identity is computed
+            # against the canonical LF text, including its final newline.
+            source = (Path(source_root) / row["path"]).read_text(encoding="utf-8")
+            data = source.encode("utf-8")
+            blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
+            if blob != row["git_blob_sha1"]:
+                blockers.append(f"SOURCE_BLOB_MISMATCH:{row['path']}")
+                continue
+            if row["vendor_path"] is None:
+                continue
+            original = ast.parse(source)
+            vendor = ast.parse((ROOT / row["vendor_path"]).read_text(encoding="utf-8"))
+            symbols = set(row["symbols"])
+            originals = {name: node for node in original.body if (name := _name(node)) in symbols}
+            copied = [node for node in vendor.body if _name(node) in symbols]
+            if len(copied) != len(symbols) or {_name(n) for n in copied} != symbols:
+                blockers.append(f"SYMBOL_SET_MISMATCH:{row['vendor_path']}")
+            for node in copied:
+                if _name(node) not in originals or _dump(node) != _dump(originals[_name(node)]):
+                    blockers.append(f"FUNCTION_MISMATCH:{row['path']}:{_name(node)}")
+            allowed_imports = {_dump(n) for n in ast.parse(row["allowed_imports"]).body}
+            actual_imports = {_dump(n) for n in vendor.body if isinstance(n, (ast.Import, ast.ImportFrom))}
+            if allowed_imports != actual_imports:
+                blockers.append(f"IMPORT_MISMATCH:{row['vendor_path']}")
+            for node in vendor.body:
+                if (_name(node) in symbols or isinstance(node, (ast.Import, ast.ImportFrom)) or
+                    isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
+                    continue
+                blockers.append(f"UNEXPECTED_TOP_LEVEL:{row['vendor_path']}")
+        except (OSError, ValueError, SyntaxError) as exc:
+            blockers.append(f"SOURCE_UNREADABLE:{row['path']}:{type(exc).__name__}")
+    return {"source_commit": pin, "source_subset_verified": not blockers,
+            "blockers": blockers, "ready_for_replay": False, "ready_for_training": False}
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--source-root", type=Path, required=True, help="Pinned chart-desk checkout")
+    args = parser.parse_args()
+    try:
+        report = check_source_parity(args.source_root)
+    except (OSError, ValueError, KeyError, StopIteration) as exc:
+        print(json.dumps({"error": str(exc), "source_subset_verified": False,
+                          "ready_for_replay": False, "ready_for_training": False}))
+        return 1
+    print(json.dumps(report, sort_keys=True, indent=2))
+    return 0 if report["source_subset_verified"] else 2
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())

```
```diff
warning: in the working copy of 'tests/tree_replay/test_ema.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/tests/tree_replay/test_ema.py b/tests/tree_replay/test_ema.py
new file mode 100644
index 0000000..15dc4ae
--- /dev/null
+++ b/tests/tree_replay/test_ema.py
@@ -0,0 +1,424 @@
+"""Synthetic bars and hand-derived numbers; no market feed or live source imports."""
+
+from dataclasses import replace
+from datetime import datetime, timedelta, timezone
+import json
+import hashlib
+import math
+from pathlib import Path
+import subprocess
+import sys
+
+import pandas as pd
+import pytest
+
+
+START = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
+ROOT = Path(__file__).resolve().parents[2]
+MINUTES = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
+
+
+def make_bars(closes, tf="5m"):
+    from trading_system.tree_replay.bars import ClosedBar
+    step = timedelta(minutes=MINUTES[tf])
+    return tuple(ClosedBar(
+        instrument="SYNTH:TEST", timeframe=tf, opened_at=START + i * step,
+        closed_at=START + (i + 1) * step, available_at=START + (i + 1) * step,
+        open=float(c), high=float(c) + 1, low=max(float(c) - 1, 0.5),
+        close=float(c), volume=None, source="synthetic closes",
+    ) for i, c in enumerate(closes))
+
+
+def report(bars, **kwargs):
+    from trading_system.tree_replay.ema import ema_snapshot
+    params = dict(snapshot_id="synthetic-snapshot", instrument="SYNTH:TEST",
+                  timeframe="5m", decision_time=bars[-1].closed_at if bars else START,
+                  history_start=START, max_age_seconds=300)
+    return ema_snapshot(bars, **(params | kwargs))
+
+
+def test_pinned_ema_uses_full_sma_seed_not_first_price():
+    from trading_system.tree_replay._vendor import indicators
+    result = indicators.ema(pd.Series(range(1, 11)), 5)
+    assert result.iloc[:4].isna().all()
+    assert result.iloc[4] == 3.0
+    assert result.iloc[-1] == pytest.approx(8.0)
+
+
+def test_pinned_cloud_uses_population_stdev_and_double_window():
+    from trading_system.tree_replay._vendor import tr
+    cloud = tr.ema_cloud(pd.DataFrame({"close": range(1, 101)}))
+    assert cloud["size"].iloc[:99].isna().all()
+    assert cloud["basis"].iloc[-1] == pytest.approx(75.5)
+    assert cloud["size"].iloc[-1] == pytest.approx(math.sqrt(833.25) / 4)
+
+
+@pytest.mark.parametrize("tf", MINUTES)
+def test_each_timeframe_exports_raw_numbers_and_partial_warmup(tf):
+    r = report(make_bars(range(1, 11), tf), timeframe=tf)
+    p = f"chartdesk.{tf}."
+    assert r["features"][p + "ema5"] == pytest.approx(8)
+    assert r["features"][p + "ema5_delta5"] == pytest.approx(5)
+    assert r["features"][p + "above_ema5"] is True
+    assert r["features"][p + "ema_order"] == "5"
+    assert r["features"][p + "ema13"] is None
+    assert r["availability"][p + "ema13"] == "UNKNOWN"
+    assert r["coverage"]["available_ema_periods"] == [5]
+    assert r["ready_for_replay"] is False
+    assert r["ready_for_training"] is False
+
+
+def test_source_drawer_warmup_requires_twice_length():
+    r = report(make_bars(range(1, 10)))
+    assert r["features"]["chartdesk.5m.ema5"] is None
+    assert r["availability"]["chartdesk.5m.ema5"] == "UNKNOWN"
+
+
+@pytest.mark.parametrize("falling,order", [(False, "5>13>50>200>800"), (True, "800>200>50>13>5")])
+def test_full_ema_order_preserves_both_directions(falling, order):
+    closes = [2000 - i if falling else i + 1 for i in range(1600)]
+    r = report(make_bars(closes))
+    assert r["features"]["chartdesk.5m.ema_order"] == order
+    assert r["features"]["chartdesk.5m.ema_stacked"] is True
+    assert r["coverage"]["available_ema_periods"] == [5, 13, 50, 200, 800]
+
+
+def test_equal_values_preserve_zero_false_and_source_stable_tie_order():
+    # Power-of-two price gives exact tied recursions; decimal 100 accumulates
+    # a tiny EMA200 rounding difference in the pinned implementation.
+    r = report(make_bars([128] * 1600))
+    f = r["features"]
+    assert f["chartdesk.5m.ema5_delta5"] == 0
+    assert f["chartdesk.5m.above_ema5"] is False
+    assert f["chartdesk.5m.cloud50_size"] == 0
+    assert f["chartdesk.5m.cloud50_location"] == "INSIDE"
+    assert f["chartdesk.5m.ema_order"] == "5>13>50>200>800"
+    # This is the source's stable-sort behavior, not proof of strict alignment.
+    assert f["chartdesk.5m.ema_stacked"] is True
+
+
+def test_mixed_order_is_not_reported_as_full_alignment():
+    r = report(make_bars(list(range(1, 1600)) + [1550]))
+    assert r["features"]["chartdesk.5m.ema_order"] == "13>5>50>200>800"
+    assert r["features"]["chartdesk.5m.ema_stacked"] is False
+
+
+def test_source_floating_precision_is_not_silently_rounded_before_sorting():
+    r = report(make_bars([100] * 1600))
+    assert r["features"]["chartdesk.5m.ema200"] > r["features"]["chartdesk.5m.ema5"]
+    assert r["features"]["chartdesk.5m.ema_order"] == "200>5>13>50>800"
+    assert r["features"]["chartdesk.5m.ema_stacked"] is False
+
+
+@pytest.mark.parametrize("closes,location", [(list(range(1, 101)), "ABOVE"), (list(range(200, 100, -1)), "BELOW")])
+def test_cloud_relationship_and_numeric_width(closes, location):
+    r = report(make_bars(closes))
+    assert r["features"]["chartdesk.5m.cloud50_location"] == location
+    assert r["features"]["chartdesk.5m.cloud50_size"] == pytest.approx(math.sqrt(833.25) / 4)
+
+
+def test_future_suffix_and_unavailable_final_close_cannot_change_snapshot():
+    bars = make_bars(range(1, 102))
+    decision = bars[99].closed_at
+    original = report(bars[:100], decision_time=decision)
+    future = replace(bars[100], close=1e8, high=1e8, open=1e8)
+    assert report(bars[:100] + (future,), decision_time=decision) == original
+    late = replace(bars[99], available_at=decision + timedelta(minutes=2))
+    assert report(bars[:99] + (late,), decision_time=decision) == report(bars[:99], decision_time=decision)
+
+
+def test_earlier_late_dependency_controls_feature_availability():
+    bars = list(make_bars(range(1, 101)))
+    decision = bars[-1].closed_at + timedelta(seconds=2)
+    bars[0] = replace(bars[0], available_at=decision)
+    r = report(bars, decision_time=decision)
+    prov = r["provenance"]["chartdesk.5m.ema5"]
+    assert prov["observed_at"] == "2026-09-08T20:20:00Z"
+    assert prov["available_at"] == "2026-09-08T20:20:02Z"
+
+
+@pytest.mark.parametrize("case,blocker,status", [
+    ("empty", "NO_HISTORY", "UNAVAILABLE"),
+    ("gap", "HISTORY_GAP", "UNAVAILABLE"),
+    ("head", "HISTORY_INCOMPLETE", "UNAVAILABLE"),
+    ("stale", "STALE", "STALE"),
+])
+def test_bad_history_is_not_a_compressed_or_zero_feature(case, blocker, status):
+    bars = make_bars(range(1, 101))
+    decision = bars[-1].closed_at
+    if case == "empty":
+        bars = ()
+    elif case == "gap":
+        bars = bars[:40] + bars[41:]
+    elif case == "head":
+        bars = bars[1:]
+    else:
+        decision += timedelta(seconds=301)
+    r = report(bars, decision_time=decision)
+    assert r["window_blocker"] == blocker
+    assert set(r["availability"].values()) == {status}
+    assert all(v is None for v in r["features"].values())
+
+
+def test_payload_has_independent_provenance_and_is_copy_safe():
+    bars = make_bars(range(1, 101))
+    original = report(bars)
+    other = report(bars)
+    other["features"]["chartdesk.5m.ema5"] = -10
+    assert report(bars) == original
+    assert bars[0].close == 1
+    assert original["calculation"]["source_commit"] == "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+    assert all(p["phase"] == "PRE_ENTRY" and not p["required"] for p in original["provenance"].values())
+    assert len(original["window_sha256"]) == 64
+    revised = list(bars)
+    revised[0] = replace(revised[0], source="different explicit source")
+    assert report(revised)["window_sha256"] != original["window_sha256"]
+    json.dumps(original, allow_nan=False)
+
+
+def test_extreme_numerical_overflow_is_not_reported_as_warmup():
+    with pytest.raises(ValueError, match="finite|overflow|numeric"):
+        report(make_bars([1e308] * 100))
+
+
+def test_parity_cli_missing_source_fails_closed(tmp_path):
+    r = subprocess.run([sys.executable, str(ROOT / "tools/check_ema_source_parity.py"),
+                        "--source-root", str(tmp_path)], capture_output=True, text=True)
+    assert r.returncode == 2
+    result = json.loads(r.stdout)
+    assert result["source_subset_verified"] is False
+    assert result["ready_for_replay"] is False
+
+
+@pytest.fixture
+def parity_fixture(tmp_path, monkeypatch):
+    # Small real source/vendor files exercise the verifier, not a mocked AST.
+    from tools import check_ema_source_parity as checker
+    src = tmp_path / "source"
+    pin = "68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9"
+    rows = []
+    for name, symbols, imports, body in [
+        ("indicators", ["_seeded_recursive", "ema", "stdev"],
+         "from __future__ import annotations\nimport numpy as np\nimport pandas as pd",
+         "def _seeded_recursive(x):\n    raise RuntimeError('never execute')\n"
+         "def ema(x):\n    return x * 2\n"
+         "def stdev(x):\n    raise RuntimeError('never execute')\n"),
+        ("tr", ["TR_EMAS", "emas", "ema_cloud"],
+         "from __future__ import annotations\nimport pandas as pd\nfrom . import indicators as I",
+         "TR_EMAS: tuple = (5, 13, 50, 200, 800)\n"
+         "def emas(x):\n    raise RuntimeError('never execute')\n"
+         "def ema_cloud(x):\n    raise RuntimeError('never execute')\n"),
+        ("features", [], "", "raise RuntimeError('source must never execute')\n"),
+    ]:
+        path = f"chartdesk/{name}.py"
+        source = imports + "\n" + body
+        source_path = src / path
+        source_path.parent.mkdir(parents=True, exist_ok=True)
+        source_path.write_text(source, encoding="utf-8")
+        vendor_path = f"trading_system/tree_replay/_vendor/{name}.py" if symbols else None
+        if vendor_path:
+            vendor = tmp_path / vendor_path
+            vendor.parent.mkdir(parents=True, exist_ok=True)
+            vendor.write_text(source, encoding="utf-8")
+        data = source.encode("utf-8")
+        rows.append({
+            "path": path, "git_blob_sha1": hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest(),
+            "vendor_path": vendor_path, "symbols": symbols, "allowed_imports": imports,
+        })
+    config = tmp_path / "configs/trees"
+    config.mkdir(parents=True)
+    (config / "existing-alerts-baseline.json").write_text(json.dumps({
+        "repositories": [{"name": "chart-desk", "commit": pin}]
+    }), encoding="utf-8")
+    contract = tmp_path / "fixture-contract.json"
+    contract.write_text(json.dumps({
+        "schema_version": "chartdesk-ema-contracts-v1", "repository": "chart-desk",
+        "commit": pin, "files": rows,
+    }), encoding="utf-8")
+    monkeypatch.setattr(checker, "ROOT", tmp_path)
+    monkeypatch.setattr(checker, "CONTRACT", contract)
+    return checker, src, tmp_path / rows[0]["vendor_path"]
+
+
+def test_source_parity_accepts_identical_subset_without_executing_it(parity_fixture):
+    checker, src, _ = parity_fixture
+    assert checker.check_source_parity(src)["source_subset_verified"] is True
+
+
+@pytest.mark.parametrize("case,prefix", [
+    ("source", "SOURCE_BLOB_MISMATCH"), ("body", "FUNCTION_MISMATCH"),
+    ("import", "IMPORT_MISMATCH"), ("top", "UNEXPECTED_TOP_LEVEL"),
+    ("duplicate", "SYMBOL_SET_MISMATCH"), ("missing", "SOURCE_UNREADABLE"),
+])
+def test_source_parity_blocks_changed_source_or_vendor(parity_fixture, case, prefix):
+    checker, src, vendor = parity_fixture
+    if case == "source":
+        (src / "chartdesk/indicators.py").write_text("def ema(x):\n    return x * 3\n", encoding="utf-8")
+    elif case == "missing":
+        src = src / "not-present"
+    else:
+        text = vendor.read_text(encoding="utf-8")
+        if case == "body":
+            text = text.replace("* 2", "* 3")
+        elif case == "import":
+            text = "import os\n" + text
+        elif case == "top":
+            text += "raise RuntimeError('must never execute')\n"
+        else:
+            text += text
+        vendor.write_text(text, encoding="utf-8")
+    r = checker.check_source_parity(src)
+    assert r["source_subset_verified"] is False
+    assert any(b.startswith(prefix) for b in r["blockers"])
+
+
+def test_parity_cli_invalid_contract_reports_no_readiness(parity_fixture, monkeypatch, capsys):
+    checker, src, _ = parity_fixture
+    checker.CONTRACT.write_text("{broken", encoding="utf-8")
+    monkeypatch.setattr(sys, "argv", ["check_ema_source_parity", "--source-root", str(src)])
+    assert checker.main() == 1
+    result = json.loads(capsys.readouterr().out)
+    assert result["source_subset_verified"] is False
+    assert result["ready_for_replay"] is False
+    assert result["ready_for_training"] is False
+
+
+@pytest.mark.parametrize("case", ["empty", "empty_missing_root", "omit_indicators", "omit_tr", "omit_features",
+                                       "duplicate_indicators", "duplicate_tr", "duplicate_features", "unknown_file"])
+def test_parity_contract_requires_all_three_unique_files(parity_fixture, case):
+    checker, src, _ = parity_fixture
+    contract = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
+    if case.startswith("empty"):
+        contract["files"] = []
+        if case == "empty_missing_root":
+            src /= "not-present"
+    elif case == "unknown_file":
+        row = dict(contract["files"][0], path="chartdesk/extra.py")
+        (src / row["path"]).write_text((src / "chartdesk/indicators.py").read_text(encoding="utf-8"), encoding="utf-8")
+        contract["files"].append(row)
+    else:
+        action, name = case.split("_")
+        row = next(row for row in contract["files"] if row["path"] == f"chartdesk/{name}.py")
+        if action == "omit":
+            contract["files"].remove(row)
+        else:
+            contract["files"].append(row)
+    checker.CONTRACT.write_text(json.dumps(contract), encoding="utf-8")
+    result = checker.check_source_parity(src)
+    assert result["source_subset_verified"] is False
+    assert any(b.startswith("CONTRACT_") for b in result["blockers"])
+    assert result["ready_for_replay"] is result["ready_for_training"] is False
+
+
+@pytest.mark.parametrize("index", [0, 1])
+@pytest.mark.parametrize("case", ["empty", "missing", "duplicate", "unknown"])
+def test_parity_contract_requires_exact_unique_symbols(parity_fixture, index, case):
+    checker, src, _ = parity_fixture
+    contract = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
+    symbols = contract["files"][index]["symbols"]
+    if case == "empty":
+        symbols.clear()
+    elif case == "missing":
+        symbols.pop()
+    elif case == "duplicate":
+        symbols.append(symbols[0])
+    else:
+        symbols.append("unknown_symbol")
+    checker.CONTRACT.write_text(json.dumps(contract), encoding="utf-8")
+    result = checker.check_source_parity(src)
+    assert result["source_subset_verified"] is False
+    assert any(b.startswith("CONTRACT_") for b in result["blockers"])
+
+
+@pytest.mark.parametrize("field,value", [
+    ("schema_version", "wrong-v1"), ("schema_version", None),
+    ("repository", "other-desk"), ("repository", None),
+    ("commit", "1" * 40), ("commit", None),
+])
+def test_parity_contract_requires_matching_identity(parity_fixture, field, value):
+    checker, src, _ = parity_fixture
+    contract = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
+    if value is None:
+        del contract[field]
+    else:
+        contract[field] = value
+    checker.CONTRACT.write_text(json.dumps(contract), encoding="utf-8")
+    result = checker.check_source_parity(src)
+    assert result["source_subset_verified"] is False
+    assert any(b.startswith("CONTRACT_") for b in result["blockers"])
+
+
+@pytest.mark.parametrize("index", [0, 1, 2])
+@pytest.mark.parametrize("field", ["vendor_path", "allowed_imports", "git_blob_sha1"])
+def test_parity_contract_requires_expected_paths_imports_and_blob_shape(parity_fixture, index, field):
+    checker, src, _ = parity_fixture
+    contract = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
+    row = contract["files"][index]
+    if field == "vendor_path":
+        row[field] = None if index < 2 else "copied.py"
+    elif field == "allowed_imports":
+        row[field] += "\nimport os"
+        # Matching edits to the vendor must not expand the trusted import scope.
+        if row["vendor_path"]:
+            vendor = checker.ROOT / row["vendor_path"]
+            vendor.write_text(vendor.read_text(encoding="utf-8") + "\nimport os\n", encoding="utf-8")
+    else:
+        row[field] = "not-a-blob"
+    checker.CONTRACT.write_text(json.dumps(contract), encoding="utf-8")
+    result = checker.check_source_parity(src)
+    assert result["source_subset_verified"] is False
+    assert any(b.startswith("CONTRACT_") for b in result["blockers"])
+
+
+@pytest.mark.parametrize("case", [
+    "not_object", "missing_files", "null_files", "not_row", "bad_path",
+    "missing_vendor", "missing_symbols", "null_symbols", "not_symbol",
+    "missing_imports", "null_imports", "duplicate_imports", "missing_blob",
+    "features_symbols", "baseline_commit",
+])
+def test_parity_contract_malformed_scope_fails_closed(parity_fixture, case):
+    checker, src, _ = parity_fixture
+    contract = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
+    row = contract["files"][0]
+    if case == "not_object":
+        contract = []
+    elif case == "missing_files":
+        del contract["files"]
+    elif case == "null_files":
+        contract["files"] = None
+    elif case == "not_row":
+        contract["files"][0] = None
+    elif case == "bad_path":
+        row["path"] = []
+    elif case.startswith("missing_"):
+        del row[{"missing_vendor": "vendor_path", "missing_symbols": "symbols",
+                 "missing_imports": "allowed_imports", "missing_blob": "git_blob_sha1"}[case]]
+    elif case == "null_symbols":
+        row["symbols"] = None
+    elif case == "not_symbol":
+        row["symbols"][0] = []
+    elif case == "null_imports":
+        row["allowed_imports"] = None
+    elif case == "duplicate_imports":
+        row["allowed_imports"] += "\nimport pandas as pd"
+    elif case == "features_symbols":
+        contract["files"][2]["symbols"] = ["draw_trend"]
+    else:
+        baseline = checker.ROOT / "configs/trees/existing-alerts-baseline.json"
+        baseline.write_text(json.dumps({"repositories": [{"name": "chart-desk", "commit": "1" * 40}]}), encoding="utf-8")
+    checker.CONTRACT.write_text(json.dumps(contract), encoding="utf-8")
+    result = checker.check_source_parity(src)
+    assert result["source_subset_verified"] is False
+    assert any(b.startswith("CONTRACT_") for b in result["blockers"])
+
+
+def test_parity_cli_empty_contract_and_missing_root_fails_closed(parity_fixture, monkeypatch, capsys):
+    checker, src, _ = parity_fixture
+    contract = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
+    contract["files"] = []
+    checker.CONTRACT.write_text(json.dumps(contract), encoding="utf-8")
+    monkeypatch.setattr(sys, "argv", ["check_ema_source_parity", "--source-root", str(src / "not-present")])
+    assert checker.main() == 2
+    result = json.loads(capsys.readouterr().out)
+    assert result["source_subset_verified"] is False
+    assert result["ready_for_replay"] is result["ready_for_training"] is False

```

