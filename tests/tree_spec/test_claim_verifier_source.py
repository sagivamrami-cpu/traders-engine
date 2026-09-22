"""The independent verifier audit rejects drift without executing retained code."""
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
RUNTIME = REPO / "trading_system/tree_replay/_vendor/claim_verifier.py"


def api():
    name = "trading_system.tree_spec.claim_verifier_source"
    assert importlib.util.find_spec(name) is not None, "claim verifier auditor missing"
    return importlib.import_module(name)


def intercept(monkeypatch, path, transform):
    original = Path.read_text
    def read(p, *args, **kwargs):
        text = original(p, *args, **kwargs)
        return transform(text) if p.resolve() == path.resolve() else text
    monkeypatch.setattr(Path, "read_text", read)


def test_actual_projection_and_inherited_closure_verify():
    r = api().audit_claim_verifier_source(SOURCE)
    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
    assert r["checked_projections"] == ["claim_verifier"] and not r["blockers"]
    assert r["dependencies"]["lifecycle_primitives"]["status"] == "VERIFIED"
    assert not r["ready_for_replay"] and not r["ready_for_training"]


@pytest.mark.parametrize("old,new", [
    ("'XAU': 0.5", "'XAU': 0.0"),
    ("float(trade['ts']) - bar_s", "float(trade['ts'])"),
    ("t.timestamp() > float(trade['ts'])", "t.timestamp() >= float(trade['ts'])"),
    ("last + 900 >= float(when)", "last >= float(when)"),
    ("last >= float(when)", "last + 900 >= float(when)"),
    ("aft = df.loc[fill:]", "aft = df.loc[fill:].iloc[1:]"),
    ("t.timestamp() <= float(when)", "True"),
    ("self._claim_clock(trade, 'resolved_ts', 'claim_ts')", "self._claim_clock(trade, 'claim_ts')"),
    ("< 45 * 60", "<= 45 * 60"),
    ("pd.Timestamp(self.source.now_utc())", "pd.Timestamp.now(tz='UTC')"),
    ("if venue is not None:", "if venue is None:"),
    ("limit=1000", "limit=100"),
    ("timeout=15", "timeout=10"),
    ("float(r[4])", "float(r[3])"),
    ("columns=['t', 'open', 'high', 'low', 'close']", "columns=['t', 'open', 'low', 'high', 'close']"),
    ("self.source.fetch_json(url, timeout=15)", "[]"),
    ("self.source.fetch_corrected(symbol, '15m', days)", "self.source.fetch_corrected(symbol, '15m', 5)"),
    ("self.movement.reached(trade)", "True"),
    ("self.target(trade, float(m.group(1).replace(',', '')))", "Verdict(True)"),
    ("self.fill(trade)", "self.stop(trade)"),
    ("from .pricing import entry_zone", "from .lifecycle_bars import _entry_band as entry_zone"),
    ("import re", "import re\nimport urllib.request"),
    ("self.movement = DeskSuccess(source)", "self.movement = None"),
    ("class ClaimVerifier:", "class ClaimVerifier:\n    extra = True"),
    ("def stop(self, trade: dict)", "def stop(self, trade)"),
])
def test_mutated_behavior_transport_clock_router_and_extra_code_fail_audit(monkeypatch, old, new):
    api()
    assert old in RUNTIME.read_text(encoding="utf-8"), old
    intercept(monkeypatch, RUNTIME, lambda text: text.replace(old, new))
    r = api().audit_claim_verifier_source(SOURCE)
    assert not r["source_subset_verified"] and "VENDOR_AST_MISMATCH" in r["blockers"]


def test_retained_source_changes_cannot_become_authority(monkeypatch):
    api()
    intercept(monkeypatch, SOURCE / "chart-desk/chartdesk/verify.py", lambda text: text+"\n# drift\n")
    r = api().audit_claim_verifier_source(SOURCE)
    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH" in r["blockers"]


@pytest.mark.parametrize("file,old,new", [
    ("desk_success.py", "p['trade_id'] == t['trade_id']", "True"),
    ("pricing.py", "def entry_zone", "def altered_entry_zone"),
])
def test_real_dependency_drift_blocks_verifier_certification(monkeypatch, file, old, new):
    api()
    target = RUNTIME.parent / file
    assert old in target.read_text(encoding="utf-8")
    intercept(monkeypatch, target, lambda text: text.replace(old, new))
    r = api().audit_claim_verifier_source(SOURCE)
    assert not r["source_subset_verified"]
    assert any(b.startswith("DEPENDENCY:") and file in b for b in r["blockers"])


@pytest.mark.parametrize("fault", ["head", "root", "baseline"])
def test_root_pin_and_baseline_cannot_redefine_authority(monkeypatch, fault):
    m = api()
    if fault == "baseline":
        intercept(monkeypatch, REPO / "configs/trees/existing-alerts-baseline.json",
            lambda text: text.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0"*40))
        want = "BASELINE_COMMIT_MISMATCH"
    else:
        arg, value, want = ("HEAD", "0"*40, "SOURCE_COMMIT_MISMATCH") if fault == "head" else ("--show-toplevel", str(SOURCE), "NOT_REPOSITORY_ROOT")
        original = m._git
        monkeypatch.setattr(m, "_git", lambda root, *args: value if args == (arg,) else original(root, *args))
    assert want in m.audit_claim_verifier_source(SOURCE)["blockers"]


def test_missing_source_and_candidate_are_blocked(tmp_path, monkeypatch):
    m = api()
    assert not m.audit_claim_verifier_source(tmp_path)["source_subset_verified"]
    monkeypatch.setattr(m, "RUNTIME", tmp_path / "absent.py")
    r = m.audit_claim_verifier_source(SOURCE)
    assert not r["source_subset_verified"]
    assert any(b.startswith("VENDOR_UNREADABLE:") for b in r["blockers"])


@pytest.mark.parametrize("fault", ["order", "duplicate", "clock_count"])
def test_projection_preconditions_reject_ambiguous_source_shape(fault):
    m = api()
    text = (SOURCE / "chart-desk/chartdesk/verify.py").read_text(encoding="utf-8")
    if fault == "order":
        text = text.replace("def _covers(", "def _temporary_swap(").replace(
            "def _fill_index(", "def _covers(").replace("def _temporary_swap(", "def _fill_index(")
    elif fault == "duplicate":
        text += "\ndef stop(trade): return None\n"
    else:
        text = text.replace('pd.Timestamp.now(tz="UTC")', 'pd.Timestamp(0)')
    with pytest.raises(ValueError):
        m._projection(text)


def test_cli_explicit_root_from_unrelated_cwd_and_no_runtime_imports(tmp_path):
    api()
    command = [sys.executable, str(REPO / "tools/check_claim_verifier_source_parity.py"), "--source-root"]
    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
                           text=True, encoding="utf-8", timeout=45)
        assert p.returncode == code, p.stderr
        r = json.loads(p.stdout)
        assert r["status"] == status and not r["ready_for_training"]
    script = "\n".join([
        "import sys",
        "class Guard:",
        "    def find_spec(self, fullname, *args):",
        "        if fullname.startswith(('chartdesk', 'floor', 'trading_system.tree_replay')):",
        "            raise AssertionError('runtime/source import forbidden: '+fullname)",
        "sys.meta_path.insert(0, Guard())",
        "from trading_system.tree_spec.claim_verifier_source import audit_claim_verifier_source",
        "assert audit_claim_verifier_source(sys.argv[1])['source_subset_verified']",
    ])
    p = subprocess.run([sys.executable, "-B", "-c", script, str(SOURCE)], cwd=REPO,
        capture_output=True, text=True, encoding="utf-8", timeout=45)
    assert p.returncode == 0, p.stderr
