"""Inert-source auditing rejects lifecycle drift, including inherited pricing."""
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
VENDOR = REPO / "trading_system/tree_replay/_vendor"


def api():
    name = "trading_system.tree_spec.lifecycle_primitives_source"
    assert importlib.util.find_spec(name) is not None, "lifecycle auditor missing"
    return importlib.import_module(name)


def intercept(monkeypatch, target, transform):
    original = Path.read_text
    def read(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        return transform(text) if path.resolve() == target.resolve() else text
    monkeypatch.setattr(Path, "read_text", read)


def test_complete_source_projections_and_dependencies_verify():
    r = api().audit_lifecycle_primitives_source(SOURCE)
    assert r["status"] == "VERIFIED" and r["source_subset_verified"]
    assert r["blockers"] == []
    assert r["checked_projections"] == ["lifecycle_bars", "desk_success", "lifecycle_voice"]
    assert r["dependencies"]["tracker_admission"]["status"] == "VERIFIED"
    assert not r["ready_for_replay"] and not r["ready_for_training"]


@pytest.mark.parametrize("file,old,new", [
    ("lifecycle_bars.py", "x.timestamp() > float(t['ts'])", "x.timestamp() >= float(t['ts'])"),
    ("lifecycle_bars.py", "x >= _fts", "x > _fts"),
    ("lifecycle_bars.py", "window.iloc[1:] if fill_bar_first else window", "window"),
    ("lifecycle_bars.py", "from .pricing import entry_zone", "from .tradeplan import entry_zone"),
    ("lifecycle_bars.py", "import pandas as pd", "import pandas as pd\nimport os"),
    ("desk_success.py", "paying.index < stopped[stopped].index[0]", "paying.index <= stopped[stopped].index[0]"),
    ("desk_success.py", "include_fill_bar=True", "include_fill_bar=False"),
    ("desk_success.py", "p['trade_id'] == t['trade_id']", "True"),
    ("desk_success.py", "p['symbol'] == t['symbol']", "True"),
    ("desk_success.py", "p['observed_ts'] <= t['resolved_ts']", "True"),
    ("desk_success.py", "self.source.now_epoch()", "time.time()"),
    ("desk_success.py", "pd.Timestamp(self.source.now_utc())", "pd.Timestamp(self.source.now_epoch(), unit='s', tz='UTC')"),
    ("desk_success.py", "'verified_post_fill_bars'", "'unverified_bars'"),
    ("desk_success.py", "self.source = source", "self.source = None"),
    ("desk_success.py", "def reached(self, t, *, as_of=None)", "def reached(self, t, as_of=None)"),
    ("desk_success.py", "from .basis_symbols import canonical_symbol", "from .basis import canonical_symbol"),
    ("lifecycle_voice.py", "return 10.0 if is_gold(symbol) else 1.0", "return 1.0"),
    ("lifecycle_voice.py", "import re", "import re\nimport time"),
])
def test_runtime_behavior_clock_identity_units_and_extra_code_drift_blocks(monkeypatch, file, old, new):
    api()
    target = VENDOR / file
    assert old in target.read_text(encoding="utf-8"), file
    intercept(monkeypatch, target, lambda text: text.replace(old, new))
    r = api().audit_lifecycle_primitives_source(SOURCE)
    assert not r["source_subset_verified"]
    assert "VENDOR_AST_MISMATCH:"+file in r["blockers"]


@pytest.mark.parametrize("file", ["tracker.py", "desk_success.py", "voice.py"])
def test_source_blob_drift_is_not_redefined_as_authority(monkeypatch, file):
    api()
    intercept(monkeypatch, SOURCE / "chart-desk/chartdesk" / file, lambda s: s+"\n# drift\n")
    r = api().audit_lifecycle_primitives_source(SOURCE)
    assert not r["source_subset_verified"] and "SOURCE_BLOB_MISMATCH:"+file in r["blockers"]


@pytest.mark.parametrize("file,old,new", [
    ("pricing.py", "def entry_zone", "def changed_entry_zone"),
    ("basis_symbols.py", "def canonical_symbol", "def changed_canonical_symbol"),
])
def test_actual_inherited_runtime_mutation_blocks(monkeypatch, file, old, new):
    api()
    target = VENDOR / file
    assert old in target.read_text(encoding="utf-8")
    intercept(monkeypatch, target, lambda s: s.replace(old, new))
    r = api().audit_lifecycle_primitives_source(SOURCE)
    assert not r["source_subset_verified"]
    assert any(b.startswith("DEPENDENCY:") and file in b for b in r["blockers"])


@pytest.mark.parametrize("fault", ["head", "root", "baseline"])
def test_identity_and_baseline_cannot_redefine_pin(monkeypatch, fault):
    m = api()
    if fault == "baseline":
        intercept(monkeypatch, REPO / "configs/trees/existing-alerts-baseline.json",
                  lambda s: s.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0"*40))
        want = "BASELINE_COMMIT_MISMATCH"
    else:
        original = m._git
        arg, value, want = ("HEAD", "0"*40, "SOURCE_COMMIT_MISMATCH") if fault == "head" else ("--show-toplevel", str(SOURCE), "NOT_REPOSITORY_ROOT")
        monkeypatch.setattr(m, "_git", lambda root, *args: value if args == (arg,) else original(root, *args))
    assert want in m.audit_lifecycle_primitives_source(SOURCE)["blockers"]


@pytest.mark.parametrize("file", ["lifecycle_bars.py", "desk_success.py", "lifecycle_voice.py"])
def test_missing_candidate_does_not_certify_partial_closure(monkeypatch, file):
    api()
    def missing(text):
        raise FileNotFoundError(file)
    intercept(monkeypatch, VENDOR / file, missing)
    r = api().audit_lifecycle_primitives_source(SOURCE)
    assert not r["source_subset_verified"]
    assert any(b.startswith("VENDOR_UNREADABLE:"+file) for b in r["blockers"])


def test_missing_source_and_cli_exit_from_unrelated_directory(tmp_path):
    assert not api().audit_lifecycle_primitives_source(tmp_path)["source_subset_verified"]
    command = [sys.executable, str(REPO / "tools/check_lifecycle_primitives_source_parity.py"), "--source-root"]
    for root, code, status in [(SOURCE, 0, "VERIFIED"), (tmp_path, 2, "BLOCKED")]:
        p = subprocess.run(command+[str(root)], cwd=tmp_path, capture_output=True,
                           text=True, encoding="utf-8", timeout=45)
        assert p.returncode == code, p.stderr
        r = json.loads(p.stdout)
        assert r["status"] == status
        assert not r["ready_for_replay"] and not r["ready_for_training"]
