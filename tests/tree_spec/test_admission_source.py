"""Audit must reject independent source/dependency/specialization corruption."""

import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts"))


@pytest.fixture
def audit():
    try:
        return importlib.import_module("trading_system.tree_spec.admission_source")
    except ModuleNotFoundError as exc:
        pytest.fail(f"Task1 source auditor missing: {exc.name}")


@pytest.fixture
def local_copy(tmp_path, monkeypatch, audit):
    for sub in ("trading_system/tree_replay/_vendor", "configs/trees"):
        shutil.copytree(ROOT / sub, tmp_path / sub)
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    return tmp_path


def test_complete_source_closure_is_verified_without_readiness(audit):
    result = audit.audit_admission_source(SOURCE)
    assert result["blockers"] == []
    assert result["source_subset_verified"] is True
    assert result["ready_for_replay"] is False
    assert result["ready_for_training"] is False


@pytest.mark.parametrize("file,old,new", [
    ("admission_matrix.py", '"tr": 1.0', '"tr": 9.0'),
    ("admission_matrix.py", "return num / den", "return num * den"),
    ("admission_matrix.py", "admission_toolkit as toolkit", "admission_indicators as toolkit"),
    ("admission_matrix.py", "basis_note=basis_note", "basis_note=None"),
    ("admission_matrix.py", "bar_ts=_bar_ts(df)", "bar_ts=0.0"),
    ("admission_toolkit.py", "I.supertrend(df, length, factor)", "I.supertrend(df, length, 1.0)"),
    ("admission_indicators.py", "return rma(true_range(df), length)", "return true_range(df)"),
    ("admission_indicators.py", "from .indicators import _seeded_recursive", "from .indicators import ema as _seeded_recursive"),
    ("indicators.py", "prev = alpha * v[i]", "prev = 0 * v[i]"),
    ("tr.py", "(5, 13, 50, 200, 800)", "(5, 13, 51, 200, 800)"),
    ("atr.py", "adjust=False", "adjust=True"),
    ("admission_clocks.py", "HUNT_START_H = 2", "HUNT_START_H = 3"),
    ("admission_clocks.py", "now.utcoffset() is None", "False"),
    ("admission_clocks.py", "return now.astimezone(TZ)", "return datetime.now(TZ)"),
    ("admission_swing.py", "SWING_K = 3", "SWING_K = 2"),
    ("admission_quality.py", "not aligned_rejection", "aligned_rejection"),
])
def test_vendor_mutations_independently_block(audit, local_copy, file, old, new):
    path = local_copy / "trading_system/tree_replay/_vendor" / file
    text = path.read_text(encoding="utf-8")
    assert old in text, file
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    result = audit.audit_admission_source(SOURCE)
    assert result["source_subset_verified"] is False
    assert any("VENDOR_AST_MISMATCH" in b for b in result["blockers"])


def test_reordered_vendor_definitions_block(audit, local_copy):
    path = local_copy / "trading_system/tree_replay/_vendor/admission_matrix.py"
    text = path.read_text(encoding="utf-8")
    start, end = text.index("def read_tr("), text.index("def read_supertrend(")
    text = text[:start] + text[end:] + "\n" + text[start:end]
    path.write_text(text, encoding="utf-8")
    assert audit.audit_admission_source(SOURCE)["source_subset_verified"] is False


@pytest.mark.parametrize("file", ["admission_matrix.py", "admission_toolkit.py", "admission_indicators.py", "admission_quality.py", "admission_clocks.py", "admission_swing.py", "tr.py", "indicators.py", "atr.py"])
def test_appended_code_in_every_dependency_is_rejected_without_execution(audit, local_copy, file):
    path = local_copy / "trading_system/tree_replay/_vendor" / file
    marker = local_copy / "must-not-exist"
    text = path.read_text(encoding="utf-8") + f"\nopen({str(marker)!r}, 'w').write('executed')\n"
    path.write_text(text, encoding="utf-8")
    result = audit.audit_admission_source(SOURCE)
    assert result["source_subset_verified"] is False
    assert not marker.exists()


@pytest.mark.parametrize("mutation", ["missing", "syntax", "signature"])
def test_broken_vendor_is_a_blocked_report(audit, local_copy, mutation):
    path = local_copy / "trading_system/tree_replay/_vendor/admission_clocks.py"
    if mutation == "missing":
        path.unlink()
    elif mutation == "syntax":
        path.write_text("def malformed:", encoding="utf-8")
    else:
        path.write_text(path.read_text(encoding="utf-8").replace("now: datetime)", "now: datetime = None)"), encoding="utf-8")
    result = audit.audit_admission_source(SOURCE)
    assert result["source_subset_verified"] is False
    assert result["blockers"]


@pytest.mark.parametrize("repo", ["chart-desk", "trading-floor"])
def test_actual_source_identity_is_required(audit, monkeypatch, repo):
    original = audit._git
    def wrong_head(path, *args):
        return "0" * 40 if path.name == repo and args == ("HEAD",) else original(path, *args)
    monkeypatch.setattr(audit, "_git", wrong_head)
    assert f"SOURCE_COMMIT_MISMATCH:{repo}" in audit.audit_admission_source(SOURCE)["blockers"]


def test_nested_repo_cannot_masquerade_as_root(audit, monkeypatch):
    original = audit._git
    def nested(path, *args):
        return str(path.parent) if args == ("--show-toplevel",) else original(path, *args)
    monkeypatch.setattr(audit, "_git", nested)
    result = audit.audit_admission_source(SOURCE)
    assert "NOT_REPOSITORY_ROOT:chart-desk" in result["blockers"]
    assert "NOT_REPOSITORY_ROOT:trading-floor" in result["blockers"]


def test_runtime_imports_and_calculations_need_no_retained_source_or_io():
    # A fresh process catches lazy dependencies and accidental source imports.
    script = '''
import sys
import pandas as pd
from datetime import datetime, timezone
def guard(event, args):
    if event == "open":
        path = str(args[0]).replace("\\\\", "/").lower()
        if "tr-tree-source-review" in path or "/chartdesk/" in path or "/floor/" in path:
            raise AssertionError("live source access: " + path)
    if event.startswith("socket.") or event == "subprocess.Popen":
        raise AssertionError("external IO: " + event)
sys.addaudithook(guard)
from trading_system.tree_replay._vendor import admission_matrix as matrix
from trading_system.tree_replay._vendor import admission_clocks as clocks
from trading_system.tree_replay._vendor import admission_quality as quality
from trading_system.tree_replay._vendor import admission_swing as swing
df = pd.DataFrame({"open": [100.0]*60, "high": [101.0]*60,
                   "low": [99.0]*60, "close": [100.0]*60},
                  index=pd.date_range("2026-09-07", periods=60, freq="min", tz="UTC"))
assert matrix.read_frame(df, "5m").net == -41.25
assert clocks.outside_reason(datetime(2026, 9, 7, 12, tzinfo=timezone.utc)) is None
assert quality.evaluate(direction=None, entry=None, atr=0, reasons=[])["shadow_block"]
assert swing._last_swing(df, True) == (99.0, 3)
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("mutation", ["constant", "function", "order", "alias", "clock"])
def test_source_mutations_never_execute_and_block(audit, monkeypatch, mutation):
    path = SOURCE / "chart-desk/chartdesk/matrix.py"
    original = Path.read_text
    text = original(path, encoding="utf-8")
    if mutation == "constant":
        changed = text.replace('"tr": 1.0', '"tr": 2.0')
    elif mutation == "function":
        changed = text.replace("return num / den", "return 99")
    elif mutation == "alias":
        changed = text.replace("basis, toolkit, tr", "basis, toolkit as tr, tr as toolkit")
    elif mutation == "clock":
        path = SOURCE / "trading-floor/floor/marketclock.py"
        text = original(path, encoding="utf-8")
        changed = text.replace("now.astimezone(TZ)", "datetime.now(TZ)")
    else:
        a, b = text.index("def read_tr("), text.index("def read_supertrend(")
        changed = text[:a] + text[b:] + "\n" + text[a:b]
    assert changed != text
    def read(self, *args, **kwargs):
        return changed if self == path else original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    result = audit.audit_admission_source(SOURCE)
    assert result["source_subset_verified"] is False
    assert any("SOURCE_BLOB_MISMATCH" in b for b in result["blockers"])


@pytest.mark.parametrize("mutation", ["drop_dependency", "blob", "readiness", "invalid_json", "missing"])
def test_manifest_cannot_narrow_or_redefine_audit(audit, local_copy, mutation):
    path = local_copy / "configs/trees/admission-source-contracts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "drop_dependency":
        data["files"].pop()
    elif mutation == "blob":
        data["files"][0]["git_blob_sha1"] = "0" * 40
    elif mutation == "readiness":
        data["ready_for_replay"] = True
    if mutation == "missing":
        path.unlink()
    else:
        path.write_text("{" if mutation == "invalid_json" else json.dumps(data), encoding="utf-8")
    assert audit.audit_admission_source(SOURCE)["source_subset_verified"] is False


def test_wrong_root_missing_source_and_wrong_baseline_fail_closed(audit, local_copy, tmp_path):
    assert audit.audit_admission_source(tmp_path / "missing")["source_subset_verified"] is False
    assert audit.audit_admission_source(SOURCE / "chart-desk")["source_subset_verified"] is False
    path = local_copy / "configs/trees/existing-alerts-baseline.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    next(row for row in data["repositories"] if row["name"] == "trading-floor")["commit"] = "0" * 40
    path.write_text(json.dumps(data), encoding="utf-8")
    assert "BASELINE_COMMIT_MISMATCH:trading-floor" in audit.audit_admission_source(SOURCE)["blockers"]


def test_cli_requires_parent_root_and_json_exit_codes(audit, tmp_path):
    command = [sys.executable, str(ROOT / "tools/check_admission_source_parity.py")]
    missing_arg = subprocess.run(command, capture_output=True, text=True)
    assert missing_arg.returncode == 2
    for root, code in ((SOURCE, 0), (tmp_path, 2)):
        result = subprocess.run(command + ["--source-root", str(root)], capture_output=True, text=True)
        assert result.returncode == code, result.stderr
        report = json.loads(result.stdout)
        assert report["source_subset_verified"] is (code == 0)
        assert report["ready_for_replay"] is False
