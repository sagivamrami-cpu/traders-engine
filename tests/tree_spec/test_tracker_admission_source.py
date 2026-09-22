"""Mandatory pinned source evidence and adversarial audit checks."""
import importlib
import os
from pathlib import Path
import json
import subprocess
import sys

import pytest

SOURCE = Path(os.environ.get("TR_TREE_SOURCE_ROOT",
    Path(__file__).resolve().parents[2] / ".source-checkouts"))


def auditor():
    try:
        return importlib.import_module("trading_system.tree_spec.tracker_admission_source")
    except ModuleNotFoundError as exc:
        pytest.fail(f"tracker source auditor missing: {exc}")


def test_complete_pinned_closure_is_verified():
    report = auditor().audit_tracker_admission_source(SOURCE)
    assert report["source_subset_verified"], f"Required pinned source evidence at {SOURCE}: {report['blockers']}"
    assert report["status"] == "VERIFIED" and report["blockers"] == []
    assert report["ready_for_replay"] is False and report["ready_for_training"] is False


def test_missing_source_is_descriptive_blocker(tmp_path):
    report = auditor().audit_tracker_admission_source(tmp_path)
    assert report["status"] == "BLOCKED" and report["source_subset_verified"] is False
    assert any("SOURCE" in b and "chart-desk" in b for b in report["blockers"])


@pytest.mark.parametrize("relative,old,new,blocker", [
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "hours >= MAX_STOP_BLOCK_H", "hours > MAX_STOP_BLOCK_H", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "self.source.load()", "self.source.quote_payload()", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "bias_at_send = self._higher_bias(sym)", "bias_at_send = self._thesis_baseline(sym, plan.direction)", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "bias_at_send = self._higher_bias(sym)\n        thesis = self._thesis_baseline(sym, plan.direction)", "thesis = self._thesis_baseline(sym, plan.direction)\n        bias_at_send = self._higher_bias(sym)", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "_tail_reader(self.source.event_log_reader)", "_tail_reader(self.source.event_log_reader())", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "lambda: BytesIO(raw)", "lambda: BytesIO(b'')", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_admission.py", "from io import BytesIO", "from io import BytesIO\nimport socket", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/tracker_symbols.py", "pip = 0.01 if", "pip = 0.02 if", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/pricing.py", "entry - half", "entry + half", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/basis_symbols.py", "return s", "return s.upper()", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/admission_quality.py", "return names or None", "return None", "VENDOR_AST_MISMATCH"),
    ("trading_system/tree_replay/_vendor/admission_swing.py", "SWING_K = 3", "SWING_K = 2", "VENDOR_AST_MISMATCH"),
    ("chart-desk/chartdesk/tracker.py", "MAX_STOP_BLOCK_H = 4.0", "MAX_STOP_BLOCK_H = 5.0", "SOURCE_BLOB_MISMATCH"),
])
def test_audit_rejects_body_port_dependency_and_source_mutations(monkeypatch, relative, old, new, blocker):
    audit = auditor()
    target = ((SOURCE if relative.startswith("chart-desk/") else audit.ROOT) / relative).resolve()
    read = Path.read_text
    original = read(target, encoding="utf-8")
    assert old in original, f"Mutation precondition missing: {relative}: {old}"
    def changed(path, *args, **kwargs):
        text = read(path, *args, **kwargs)
        return text.replace(old,new,1) if path.resolve() == target else text
    monkeypatch.setattr(Path,"read_text",changed)
    report = audit.audit_tracker_admission_source(SOURCE)
    assert report["source_subset_verified"] is False
    assert any(blocker in b for b in report["blockers"]), report


@pytest.mark.parametrize("mode", ["narrow", "pin", "duplicate"])
def test_manifest_cannot_redefine_audit_authority(monkeypatch,mode):
    audit = auditor(); read = Path.read_text
    target = (audit.ROOT / "configs/trees/tracker-admission-source-contracts.json").resolve()
    def changed(path,*args,**kwargs):
        text = read(path,*args,**kwargs)
        if path.resolve() != target:
            return text
        data = json.loads(text)
        if mode == "narrow":
            data["files"] = data["files"][:1]
        elif mode == "pin":
            data["repositories"]["chart-desk"] = "0"*40
        else:
            return text.replace('"ready_for_replay": false','"ready_for_replay": true, "ready_for_replay": false')
        return json.dumps(data)
    monkeypatch.setattr(Path,"read_text",changed)
    report = audit.audit_tracker_admission_source(SOURCE)
    assert report["source_subset_verified"] is False
    assert any("CONTRACT" in b for b in report["blockers"])


def test_repository_pin_mismatch_blocks(monkeypatch):
    audit = auditor(); git = audit._git
    def changed(repo,*args):
        return "0"*40 if args == ("HEAD",) else git(repo,*args)
    monkeypatch.setattr(audit,"_git",changed)
    assert any("SOURCE_COMMIT_MISMATCH" in b for b in audit.audit_tracker_admission_source(SOURCE)["blockers"])


def test_cli_requires_explicit_root_and_reports_missing_source(tmp_path):
    cli = Path(__file__).resolve().parents[2] / "tools/check_tracker_admission_source_parity.py"
    absent = subprocess.run([sys.executable,str(cli)],capture_output=True,text=True)
    assert absent.returncode == 2 and "--source-root" in absent.stderr
    missing = subprocess.run([sys.executable,str(cli),"--source-root",str(tmp_path)],capture_output=True,text=True)
    assert missing.returncode == 2
    assert json.loads(missing.stdout)["status"] == "BLOCKED"


@pytest.mark.parametrize("old,new", [("from . import matrix, zones", "from . import matrix"),
    ("_locked()", "_different_lock()"), ("path.open(\"rb\")", "path.open(\"r\")")])
def test_projection_refuses_missing_substitution_preconditions(old,new):
    audit = auditor()
    try:
        tracker = (SOURCE/"chart-desk/chartdesk/tracker.py").read_text(encoding="utf-8")
        tradeplan = (SOURCE/"chart-desk/chartdesk/tradeplan.py").read_text(encoding="utf-8")
    except OSError as exc:
        pytest.fail(f"Required pinned source evidence missing at {SOURCE}: {exc}")
    assert old in tracker
    with pytest.raises(ValueError,match="SUBSTITUTION_PRECONDITION"):
        audit._tracker_projection(tracker.replace(old,new),tradeplan)
