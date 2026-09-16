"""Synthetic arithmetic and fail-closed audit tests; never import chart-desk."""

import ast
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("TR_CHARTDESK_SOURCE_ROOT", Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts")) / "chart-desk"))


def vendor(name):
    qualified = f"trading_system.tree_replay._vendor.{name}"
    assert importlib.util.find_spec(qualified) is not None, f"Missing pure sidecar: {name}"
    return importlib.import_module(qualified)


@pytest.mark.parametrize("symbol,expected", [
    (" gold ", "OANDA:XAUUSD"), ("nas", "OANDA:NAS100USD"),
    ("btc", "BINANCE:BTCUSDT"), ("GC", "GC"), ("GC=F", "GC=F"),
    ("COMEX:GC", "COMEX:GC"), ("oanda:XAUUSD", "oanda:XAUUSD"),
])
def test_aliases_preserve_unknown_and_qualified_identity(symbol, expected):
    assert vendor("basis_symbols").canonical_symbol(symbol) == expected


@pytest.mark.parametrize("symbol,style,entry,raw,expected", [
    ("XAU", "scalp", 100, 98, 93), ("XAU", "scalp", 100, 102, 107),
    ("XAU", "scalp", 100, 93, 93), ("XAU", "scalp", 100, 91, 91),
    ("XAU", "scalp", 100, 80, 91), ("XAU", "scalp", 100, 120, 109),
    ("XAU", "intraday", 100, 98, 90.5),
    ("XAU", "swing", 100, 98, 74.7),
    ("NAS", "intraday", 1000, 999, 905),
    ("NAS", "swing", 1000, 999, 749.7),
    ("BTC", "scalp", 10000, 9999, 9540),
    ("BTC", "intraday", 10000, 9999, 9340),
    ("BTC", "swing", 10000, 9999, 7499.7),
    ("GC", "scalp", 100, 98, 98),
])
def test_stop_bands_from_zone_edges_and_style(symbol, style, entry, raw, expected):
    warnings = []
    assert vendor("pricing").apply_stop_band(symbol, entry, raw, 2, warnings, style) == expected
    assert not any("ImportError" in warning for warning in warnings)


@pytest.mark.parametrize("entry,raw,atr,expected,snapped", [
    (110, 100.5, 2, 99.7, True), (90, 99.5, 2, 100.3, True),
    (110.4, 100.9, 2, 100.9, False), (89.6, 99.1, 2, 99.1, False),
    (110, 100.5, 10 / 3, 99.5, True), (90, 99.5, 10 / 3, 100.5, True),
])
def test_psychological_snap_respects_midpoint_ceiling(entry, raw, atr, expected, snapped):
    warnings = []
    stop = vendor("pricing").apply_stop_band("XAU", entry, raw, atr, warnings, "intraday")
    assert stop == pytest.approx(expected)
    assert any("פסיכולוגית" in warning for warning in warnings) is snapped


def test_quarters_grid_and_pure_render():
    q = vendor("quarters")
    levels = q.nearest("XAU", 106, count=2)
    assert [(x.price, x.kind, x.distance) for x in levels] == [
        (100, "whole", -6), (125, "quarter", 19),
        (75, "quarter", -31), (150, "half", 44),
    ]
    assert levels[0].render() == "100 [WHOLE] 6.0 מתחת"
    assert q.nearest("UNKNOWN", 106) == []


@pytest.mark.parametrize("short,candidates,expected", [
    (False, [("behind", 95), ("edge", 102), ("far", 106), ("near", 103)], [("near", 103), ("far", 106)]),
    (True, [("behind", 105), ("edge", 98), ("far", 94), ("near", 97)], [("near", 97), ("far", 94)]),
])
def test_targets_exclude_zone_edges_and_wrong_side(short, candidates, expected):
    assert vendor("pricing").ladder_ready(candidates, "XAU", 100, 6, short) == expected


def test_target_merging_is_strictly_less_than_half_atr():
    assert vendor("pricing").distinct_targets(
        [("A", 110), ("B", 110.999), ("B", 110.999), ("C", 111), ("D", 120)],
        100, 2, limit=2,
    ) == [("A/B", 110), ("C", 111)]


@pytest.mark.parametrize("short,stop,candidates,targets,obstacles,refused", [
    (False, 93, [("far", 130)], [("1.5R", 110.5), ("far", 130)], [], False),
    (True, 107, [("far", 70)], [("1.5R", 89.5), ("far", 70)], [], False),
    (False, 93, [("road", 105), ("far", 130)], [("far", 130)], [("road", 105)], True),
    (True, 107, [("road", 95), ("far", 70)], [("far", 70)], [("road", 95)], True),
    (False, 90, [("eq", 112)], [("eq", 112)], [], False),
    (False, 90, [("low", 111.999)], [], [("low", 111.999)], True),
    (False, 90, [("road", 105), ("eq", 120)], [("eq", 120)], [("road", 105)], False),
    (False, 90, [("road", 105), ("over", 120.001)], [("over", 120.001)], [("road", 105)], True),
    (False, 90, [("eq", 120)], [("eq", 120)], [], False),
    (False, 90, [("over", 120.001)], [("1.5R", 115), ("over", 120.001)], [], False),
    (False, 93, [], [], [], True),
])
def test_resolver_keeps_obstacles_refusal_and_boundary_geometry(short, stop, candidates, targets, obstacles, refused):
    actual, road, refusal = vendor("pricing").resolve_ladder(candidates, "XAU", 100, stop, short, 2)
    assert actual == targets
    assert road == obstacles
    assert (refusal is not None) is refused


def test_measured_rung_rounding_and_limit():
    p = vendor("pricing")
    assert p._with_measured_rung([("far", 130)], 100.01, 93, False)[0] == ("1.5R", 110.53)
    assert p._with_measured_rung([("far", 70)], 100.01, 107.02, True)[0] == ("1.5R", 89.5)
    assert p.resolve_ladder([("a", 130), ("b", 140), ("c", 150)], "XAU", 100, 93, False, 2)[0] == [
        ("1.5R", 110.5), ("a", 130), ("b", 140)]


def test_atr_initializes_at_first_true_range_without_sma_seed():
    frame = pd.DataFrame({"high": [11, 15, 14], "low": [9, 12, 13], "close": [10, 13, 13.5]})
    # True ranges 2, 5, 1. With alpha 1/2: 2, 3.5, 2.25.
    assert vendor("atr").atr(frame, length=2).tolist() == [2, 3.5, 2.25]
    assert vendor("atr").atr(frame).tolist() == pytest.approx([2, 31 / 14, 417 / 196])


def event(**overrides):
    args = dict(symbol="XAU", timeframe="5m", direction="לונג", level_name="DAY-OPEN",
                level_price=100, approach="above", pattern="single_bar", vector_kind="green",
                vector_open_time=pd.Timestamp("2026-01-01T00:00Z"),
                confirmation_open_time=pd.Timestamp("2026-01-01T00:05Z"),
                confirmed_at=pd.Timestamp("2026-01-01T00:10Z"), sweep_extreme=98,
                close=101, event_id="synthetic")
    args.update(overrides)
    return vendor("level_reversal").Reversal(**args)


def test_build_plan_preserves_refused_geometry_and_uses_only_prior_history():
    history = pd.DataFrame({"high": [101, 1000], "low": [99, 0], "close": [100, 500]},
                           index=pd.to_datetime(["2026-01-01T00:05Z", "2026-01-01T00:10Z"]))
    p = vendor("reversal_pricing").build_plan(event(), [("road", 105), ("far", 130)], history)
    assert (p.entry, p.stop, p.atr, p.style, p.kind, p.direction) == (100, 93, 2, "scalp", "reversal", "לונג")
    assert p.targets == [("far", 130)] and p.obstacles == [("road", 105)]
    assert p.refusal and not p.tradeable
    assert p.risk == 7 and p.rr == 30 / 7 and p.rr_far == 30 / 7


def test_build_plan_short_intraday_empty_history_fallback_and_object_levels():
    history = pd.DataFrame(columns=["high", "low", "close"], index=pd.DatetimeIndex([], tz="UTC"))
    p = vendor("reversal_pricing").build_plan(
        event(timeframe="15m", direction="שורט", sweep_extreme=102),
        [SimpleNamespace(name="far", price=70)], history)
    assert (p.entry, p.stop, p.atr, p.style) == (100, 109.5, 1, "intraday")
    assert p.targets == [("1.5R", 85.75), ("far", 70)] and p.tradeable


def test_plan_projection_properties_and_independent_mutable_defaults():
    Plan = vendor("pricing").Plan
    a, b = Plan("XAU", 100, "reversal", "לונג"), Plan("XAU", 100, "reversal", "לונג")
    a.targets.append(("TP1", 112))
    assert b.targets == [] and a.risk == 0 and a.rr == 0 and a.rr_far == 0
    a.entry, a.stop = 100, 90
    assert a.rr == 1.2 and a.tradeable
    a.targets.append(("TP2", 130))
    assert a.rr_far == 3
    a.refusal = "blocked"
    assert not a.tradeable
    assert not hasattr(a, "render")


def auditor():
    assert (ROOT / "tools/check_pricing_source_parity.py").exists(), "Missing pricing auditor"
    return importlib.import_module("tools.check_pricing_source_parity")


def assert_report(report, verified):
    assert report["subset_verified"] is verified
    assert report["source_subset_verified"] is verified
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    assert bool(report["blockers"]) is not verified


def test_fixed_source_and_full_subset_audit():
    assert_report(auditor().check_source_parity(SOURCE), True)


@pytest.mark.parametrize("change", [
    "missing", "invalid", "omit_file", "omit_symbol", "blob", "imports", "commit", "projection",
])
def test_audit_rejects_manifest_tampering(monkeypatch, change):
    audit = auditor()
    read = Path.read_text

    def altered(path, *args, **kwargs):
        text = read(path, *args, **kwargs)
        if path == audit.CONTRACT:
            if change == "missing":
                raise FileNotFoundError(path)
            if change == "invalid":
                return "{"
            data = json.loads(text)
            if change == "omit_file": data["files"].pop()
            if change == "omit_symbol": data["files"][0]["symbols"].pop()
            if change == "blob": data["files"][0]["git_blob_sha1"] = "0" * 40
            if change == "imports": data["files"][0]["allowed_imports"] += "\nimport os"
            if change == "commit": data["commit"] = "0" * 40
            if change == "projection": data["plan_projection"]["methods"].pop()
            return json.dumps(data)
        return text

    monkeypatch.setattr(Path, "read_text", altered)
    assert_report(audit.check_source_parity(SOURCE), False)


@pytest.mark.parametrize("relative,mutation", [
    ("trading_system/tree_replay/_vendor/pricing.py", "field"),
    ("trading_system/tree_replay/_vendor/pricing.py", "property"),
    ("trading_system/tree_replay/_vendor/pricing.py", "decorator"),
    ("trading_system/tree_replay/_vendor/pricing.py", "extra_method"),
    ("trading_system/tree_replay/_vendor/pricing.py", "extra_statement"),
    ("trading_system/tree_replay/_vendor/basis_symbols.py", "extra_statement"),
    ("trading_system/tree_replay/_vendor/quarters.py", "extra_import"),
    ("trading_system/tree_replay/_vendor/atr.py", "extra_statement"),
    ("trading_system/tree_replay/_vendor/reversal_pricing.py", "extra_import"),
    ("trading_system/tree_replay/_vendor/level_reversal.py", "extra_statement"),
    ("trading_system/tree_replay/_vendor/pvsra.py", "extra_statement"),
])
def test_audit_rejects_vendor_and_inherited_dependency_mutations(monkeypatch, relative, mutation):
    audit = auditor()
    read = Path.read_text

    def altered(path, *args, **kwargs):
        text = read(path, *args, **kwargs)
        if path == ROOT / relative:
            tree = ast.parse(text)
            if mutation.startswith("extra_") and mutation != "extra_method":
                return text + ("\nimport os\n" if mutation == "extra_import" else "\nINJECTED = True\n")
            plan = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Plan")
            if mutation == "field":
                plan.body = [n for n in plan.body if not (isinstance(n, ast.AnnAssign) and n.target.id == "input_state_id")]
            if mutation == "property":
                next(n for n in plan.body if isinstance(n, ast.FunctionDef) and n.name == "risk").body = [ast.Return(ast.Constant(0))]
            if mutation == "decorator": plan.decorator_list = []
            if mutation == "extra_method": plan.body += ast.parse("def injected(self): return True").body
            return ast.unparse(tree)
        return text

    monkeypatch.setattr(Path, "read_text", altered)
    assert_report(audit.check_source_parity(SOURCE), False)


@pytest.mark.parametrize("target", ["chartdesk/tradeplan.py", "chartdesk/basis.py", "chartdesk/quarters.py", "chartdesk/tr.py", "chartdesk/level_reversal.py", "chartdesk/auction.py", "baseline"])
def test_audit_rejects_changed_source_blobs_or_baseline(monkeypatch, target):
    audit = auditor()
    read = Path.read_text
    target_path = ROOT / "configs/trees/existing-alerts-baseline.json" if target == "baseline" else SOURCE / target

    def altered(path, *args, **kwargs):
        text = read(path, *args, **kwargs)
        if path == target_path:
            if target == "baseline":
                return text.replace("68b1d091b5c2d6202cc8fd9ecb53790d4c0cf3a9", "0" * 40)
            return text + "\n# source mutation\n"
        return text

    monkeypatch.setattr(Path, "read_text", altered)
    assert_report(audit.check_source_parity(SOURCE), False)
