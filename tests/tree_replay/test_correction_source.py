"""Source behavior and fail-closed audit mutations; live source is text only."""

from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get(
    "TR_CHARTDESK_SOURCE_ROOT",
    (Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts")) / "chart-desk"),
))
VENDOR = "trading_system/tree_replay/_vendor/correction.py"
CONTRACT = "configs/trees/correction-source-contracts.json"
BASELINE = "configs/trees/existing-alerts-baseline.json"
AUDIT = "tools/check_correction_source_parity.py"
T = datetime(2020, 2, 1, tzinfo=timezone.utc)


def module(name):
    assert importlib.util.find_spec(name) is not None, f"Missing assigned sidecar: {name}"
    return importlib.import_module(name)


def test_none_cannot_prove_shape_and_clock_is_required():
    vendor = module("trading_system.tree_replay._vendor.correction")
    assert vendor.broker_shape_ok_at(None, 20, decision_time=T) is False
    with pytest.raises(TypeError):
        vendor.broker_shape_ok_at(None, 20)


@pytest.mark.parametrize("source,offset,show,render,unverified", [
    ("none", 0, True, "⚠ OANDA:XAUUSD: example", True),
    ("mt5_broker", 0, True, "✅ OANDA:XAUUSD: example", False),
    ("tv_live", 0, False, "OANDA:XAUUSD: תוקן +0.0 (example)", False),
    ("tv_live", 12, True, "OANDA:XAUUSD: תוקן +12.0 (example)", False),
    ("tv_live", -12, True, "OANDA:XAUUSD: תוקן -12.0 (example)", False),
])
def test_complete_source_class_preserves_presentation_and_unverified(source, offset, show, render, unverified):
    vendor = module("trading_system.tree_replay._vendor.correction")
    corr = vendor.Correction("OANDA:XAUUSD", offset, source, "unknown", "example")
    assert corr.show is show
    assert corr.render() == render
    assert corr.unverified is unverified


@pytest.mark.parametrize("source,symbol,seam,days,want", [
    ("tv_daily", "COMEX:GC", None, 20, True),
    ("mt5_broker", "OANDA:XAUUSD", None, 20, True),
    ("none", "BINANCE:BTCUSDT", None, 20, True),
    ("none", "binance:btcusdt", None, 20, False),
    ("none", "COMEX:GC", None, 20, False),
    ("replay", "OANDA:XAUUSD", None, 20, False),
    ("replay", "BINANCE:BTCUSDT", None, 20, True),
    ("tv_spliced", "OANDA:XAUUSD", None, 0, False),
    ("tv_spliced", "OANDA:XAUUSD", T, 0, True),
    ("tv_spliced", "OANDA:XAUUSD", T + timedelta(microseconds=1), 0, False),
    ("tv_spliced", "OANDA:XAUUSD", T - timedelta(days=7), 7, True),
    ("tv_spliced", "OANDA:XAUUSD", T - timedelta(days=20), 20, True),
    ("tv_spliced", "OANDA:XAUUSD", T - timedelta(days=20) + timedelta(microseconds=1), 20, False),
])
def test_source_branch_and_clock_semantics(source, symbol, seam, days, want):
    vendor = module("trading_system.tree_replay._vendor.correction")
    corr = vendor.Correction(symbol, -20, source, "n/a", "", seam)
    before = vars(corr).copy()
    assert vendor.broker_shape_ok_at(corr, days, decision_time=T) is want
    assert vars(corr) == before


def test_pinned_source_audit_checks_subset_only():
    out = module("tools.check_correction_source_parity").check_source_parity(SOURCE)
    assert out["blockers"] == [], "Required pinned source missing or changed; set TR_CHARTDESK_SOURCE_ROOT: " + repr(out)
    assert out["subset_verified"] is True
    assert out["ready_for_replay"] is out["ready_for_training"] is False


def copy_inputs(tmp_path):
    # Only paths are relocated. Auditor's expected pins/contracts are never patched.
    assert (ROOT / AUDIT).is_file(), "Missing assigned source auditor"
    assert (SOURCE / "chartdesk/basis.py").is_file(), "Required pinned source fixture absent; set TR_CHARTDESK_SOURCE_ROOT"
    project = tmp_path / "project"
    source = tmp_path / "source"
    for relative in (AUDIT, VENDOR, CONTRACT, BASELINE):
        dest = project / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    dest = source / "chartdesk/basis.py"
    dest.parent.mkdir(parents=True)
    shutil.copyfile(SOURCE / "chartdesk/basis.py", dest)
    return project, source


def run_audit(project, source=None, env_source=None):
    command = [sys.executable, "-B", str(project / AUDIT)]
    if source is not None:
        command += ["--source-root", str(source)]
    env = os.environ.copy()
    if env_source is not None:
        env["TR_CHARTDESK_SOURCE_ROOT"] = str(env_source)
    run = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    return run, json.loads(run.stdout)


def assert_failed(project, source):
    run, out = run_audit(project, source)
    assert run.returncode == 2, run.stdout + run.stderr
    assert out["subset_verified"] is False
    assert out["blockers"]
    assert out["ready_for_replay"] is out["ready_for_training"] is False


@pytest.mark.parametrize("mutation", ["commit", "blob", "symbol", "order", "imports", "bool_number", "ready", "extra", "syntax"])
def test_manifest_cannot_relax_fixed_audit(tmp_path, mutation):
    project, source = copy_inputs(tmp_path)
    path = project / CONTRACT
    data = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "commit":
        data["commit"] = "0" * 40
    elif mutation == "blob":
        data["files"][0]["git_blob_sha1"] = "0" * 40
    elif mutation == "symbol":
        data["files"][0]["symbols"].pop()
    elif mutation == "order":
        data["files"][0]["symbols"].reverse()
    elif mutation == "imports":
        data["files"][0]["allowed_imports"] += "\nimport os"
    elif mutation == "bool_number":
        data["ready_for_replay"] = 0
    elif mutation == "ready":
        data["ready_for_training"] = True
    elif mutation == "extra":
        data["extra"] = "unapproved"
    path.write_text("{" if mutation == "syntax" else json.dumps(data), encoding="utf-8")
    assert_failed(project, source)


@pytest.mark.parametrize("mutation", ["commit", "omit", "duplicate", "malformed"])
def test_baseline_requires_exactly_one_matching_pin(tmp_path, mutation):
    project, source = copy_inputs(tmp_path)
    path = project / BASELINE
    data = json.loads(path.read_text(encoding="utf-8"))
    row = next(r for r in data["repositories"] if r["name"] == "chart-desk")
    if mutation == "commit":
        row["commit"] = "0" * 40
    elif mutation == "omit":
        data["repositories"].remove(row)
    elif mutation == "duplicate":
        data["repositories"].append(row.copy())
    else:
        data["repositories"] = None
    path.write_text(json.dumps(data), encoding="utf-8")
    assert_failed(project, source)


@pytest.mark.parametrize("mutation", ["constant", "branch", "clock", "extra_clock", "executable", "syntax"])
def test_changed_live_source_fails_without_execution(tmp_path, mutation):
    project, source = copy_inputs(tmp_path)
    path = source / "chartdesk/basis.py"
    before = path.read_text(encoding="utf-8")
    text = {
        "constant": lambda: before.replace('EXCHANGE_NATIVE = {"BINANCE:BTCUSDT"}', 'EXCHANGE_NATIVE = {"COMEX:GC"}'),
        "branch": lambda: before.replace('return age_days >= days', 'return age_days > days'),
        "clock": lambda: before.replace('pd.Timestamp.now("UTC")', 'pd.Timestamp.now()'),
        "extra_clock": lambda: before + '\npd.Timestamp.now("UTC")\n',
        "executable": lambda: before + '\nraise RuntimeError("LIVE SOURCE EXECUTED")\n',
        "syntax": lambda: before + '\ndef broken(\n',
    }[mutation]()
    assert text != before
    path.write_text(text, encoding="utf-8")
    assert_failed(project, source)


@pytest.mark.parametrize("mutation", [
    "constant", "branch", "clock", "rename", "optional_clock", "import", "rebind",
    "duplicate", "executable", "docstring", "order", "omit", "syntax",
])
def test_entire_vendor_module_is_audited_without_execution(tmp_path, mutation):
    project, source = copy_inputs(tmp_path)
    path = project / VENDOR
    before = path.read_text(encoding="utf-8")
    text = {
        "constant": lambda: before.replace('EXCHANGE_NATIVE = {"BINANCE:BTCUSDT"}', 'EXCHANGE_NATIVE = {"COMEX:GC"}'),
        "branch": lambda: before.replace('return age_days >= days', 'return age_days > days'),
        "clock": lambda: before.replace('pd.Timestamp(decision_time)', 'pd.Timestamp.now("UTC")'),
        "rename": lambda: before.replace('def broker_shape_ok_at(', 'def broker_shape_ok('),
        "optional_clock": lambda: before.replace('*, decision_time)', '*, decision_time=None)'),
        "import": lambda: before + '\nimport os\n',
        "rebind": lambda: before + '\nCorrection = None\n',
        "duplicate": lambda: before + '\ndef broker_shape_ok_at(*args, **kwargs):\n    return True\n',
        "executable": lambda: before + '\nraise RuntimeError("VENDOR EXECUTED")\n',
        "docstring": lambda: before.replace('May a RANGE object', 'May every object'),
        "order": lambda: before.replace('from dataclasses import dataclass', 'import pandas as pd').replace('import pandas as pd\n\n', 'from dataclasses import dataclass\n\n'),
        "omit": lambda: before[:before.index('def broker_shape_ok_at(')],
        "syntax": lambda: before + '\ndef broken(\n',
    }[mutation]()
    assert text != before
    path.write_text(text, encoding="utf-8")
    assert_failed(project, source)


@pytest.mark.parametrize("relative", [VENDOR, CONTRACT, BASELINE, "chartdesk/basis.py"])
def test_missing_prerequisites_fail_closed(tmp_path, relative):
    project, source = copy_inputs(tmp_path)
    # Remove only the temporary synthetic fixture, never the retained checkout.
    path = (source if relative == "chartdesk/basis.py" else project) / relative
    path.unlink()
    assert_failed(project, source)


def test_cli_precedence_and_crlf_normalization(tmp_path):
    project, source = copy_inputs(tmp_path)
    path = source / "chartdesk/basis.py"
    data = path.read_text(encoding="utf-8")
    path.write_bytes(data.replace("\n", "\r\n").encode("utf-8"))
    for explicit, environment, code in [(source, tmp_path / "missing", 0), (None, source, 0), (None, tmp_path / "missing", 2)]:
        run, out = run_audit(project, explicit, environment)
        assert run.returncode == code, run.stdout + run.stderr
        assert out["subset_verified"] is (code == 0)
