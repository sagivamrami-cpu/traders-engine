"""Watch persistence audit rejects changed source identity and runtime behavior."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
    Path(__file__).resolve().parents[2] / ".source-checkouts"))
RUNTIME = REPO / "trading_system/tree_replay/_vendor/watch_storage.py"


def api():
    name = "trading_system.tree_spec.watch_storage_source"
    assert importlib.util.find_spec(name) is not None, "watch storage auditor missing"
    return importlib.import_module(name)


def test_actual_source_statements_and_complete_runtime_verify():
    r = api().audit_watch_storage_source(SOURCE)
    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
    assert r["blockers"] == []
    assert r["checked_projections"] == ["watch.load", "watch.save_before_producers", "watch.save_final"]
    assert not r["ready_for_replay"] and not r["ready_for_training"]


def intercept(monkeypatch, target, transform):
    original_read = Path.read_text
    def read(path, *args, **kwargs):
        text = original_read(path, *args, **kwargs)
        return transform(text) if path.resolve() == target.resolve() else text
    monkeypatch.setattr(Path, "read_text", read)


@pytest.mark.parametrize("old,new", [
    ("else {}", "else None"),
    ("return st", "return {}"),
    ("json.dumps(st)", "json.dumps(st, sort_keys=True)"),
    ("json.dumps(st)", "json.dumps(st, ensure_ascii=False)"),
    ("json.dumps(st)", "json.dumps(st, indent=1)"),
    ("self.source.ensure_directory(exist_ok=True)", "pass"),
    ("self.source = source", "self.source = None"),
    ("import json", "import json\nimport os"),
    ("def save_final(self, st):\n        self.source.write_text(json.dumps(st))",
     "def save_final(self, st):\n        self.source.ensure_directory(exist_ok=True)\n        self.source.write_text(json.dumps(st))"),
])
def test_mutated_runtime_is_not_certified(monkeypatch, old, new):
    api()
    assert old in RUNTIME.read_text(encoding="utf-8")
    intercept(monkeypatch, RUNTIME, lambda s: s.replace(old, new))
    r = api().audit_watch_storage_source(SOURCE)
    assert not r["source_subset_verified"] and "VENDOR_AST_MISMATCH" in r["blockers"]


@pytest.mark.parametrize("fault", ["blob", "load", "first_save", "final_save"])
def test_retained_source_drift_cannot_be_hidden_by_matching_runtime(monkeypatch, fault):
    target = SOURCE / "chart-desk/scripts/market_watch.py"
    def mutate(text):
        if fault == "blob":
            return text+"\n# changed source\n"
        if fault == "load":
            return text.replace("st = json.loads(STATE.read_text()) if STATE.exists() else {}", "st = {}")
        if fault == "first_save":
            return text.replace("STATE.parent.mkdir(exist_ok=True)\n    STATE.write_text(json.dumps(st))", "STATE.write_text(json.dumps(st))")
        return text.replace("    STATE.write_text(json.dumps(st))\n    return 0", "    return 0")
    api()
    intercept(monkeypatch, target, mutate)
    r = api().audit_watch_storage_source(SOURCE)
    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH" in r["blockers"]
    if fault != "blob":
        assert any(b.startswith("SOURCE_UNREADABLE:ValueError") for b in r["blockers"])


def test_wrong_head_blocks_even_with_correct_files(monkeypatch):
    m = api()
    original = m._git
    monkeypatch.setattr(m, "_git", lambda root, *args: "0"*40 if args == ("HEAD",) else original(root, *args))
    assert "SOURCE_COMMIT_MISMATCH" in m.audit_watch_storage_source(SOURCE)["blockers"]


def test_changed_baseline_cannot_redefine_audit_authority(monkeypatch):
    api()
    target = REPO / "configs/trees/existing-alerts-baseline.json"
    intercept(monkeypatch, target, lambda s: s.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0"*40))
    assert "BASELINE_COMMIT_MISMATCH" in api().audit_watch_storage_source(SOURCE)["blockers"]


def test_missing_source_and_runtime_remain_blocked(tmp_path, monkeypatch):
    m = api()
    assert not m.audit_watch_storage_source(tmp_path)["source_subset_verified"]
    monkeypatch.setattr(m, "RUNTIME", tmp_path / "absent.py")
    r = m.audit_watch_storage_source(SOURCE)
    assert not r["source_subset_verified"] and any(b.startswith("VENDOR_UNREADABLE") for b in r["blockers"])


def test_cli_success_and_blocked_exits_from_unrelated_directory(tmp_path):
    api()
    command = [sys.executable, str(REPO / "tools/check_watch_storage_source_parity.py"), "--source-root"]
    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
                           text=True, encoding="utf-8", timeout=30)
        assert p.returncode == code, p.stderr
        r = json.loads(p.stdout)
        assert r["status"] == status and not r["ready_for_training"]
