"""Synthetic behavior and fail-closed, text-only source parity checks."""

import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get(
    "TR_CHARTDESK_SOURCE_ROOT",
    (Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts")) / "chart-desk"),
))


def module(name):
    assert importlib.util.find_spec(name) is not None, f"Missing assigned sidecar: {name}"
    return importlib.import_module(name)


@pytest.fixture
def ranges():
    return module("trading_system.tree_replay._vendor.ranges")


@pytest.fixture
def back_days():
    return module("trading_system.tree_replay._vendor.back_days")


def audit():
    return module("tools.check_range_source_parity")


def frame(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def example():
    return frame([(100, 105, 95, 100), (100, 110, 90, 100), (100, 115, 95, 110)])


@pytest.mark.parametrize("from_open,high,low,high50,low50", [
    (False, 110, 100, 102.5, 107.5), (True, 107.5, 92.5, 100, 100),
])
@pytest.mark.parametrize("broker_bars", [False, True])
def test_average_excludes_current_and_preserves_anchors_and_verification(
    ranges, from_open, high, low, high50, low50, broker_bars,
):
    out = ranges.average_range(example(), 2, from_open=from_open, broker_bars=broker_bars)
    assert out["available"] is True
    assert out["length"] == 2
    assert out["range"] == 15
    assert (out["high"], out["low"], out["high50"], out["low50"]) == (high, low, high50, low50)
    assert out["used"] == 20
    assert out["used_pct"] == pytest.approx(400 / 3)
    assert out["verified"] is broker_bars
    assert out["from_open"] is from_open
    assert (out["note"] is not None) is from_open


@pytest.mark.parametrize("from_open,expected", [(False, (105, 125)), (True, (107.5, 92.5))])
def test_current_extremes_move_only_running_anchors(ranges, from_open, expected):
    bars = example()
    bars.loc[2, ["high", "low", "close"]] = [140, 90, 130]
    out = ranges.average_range(bars, 2, from_open=from_open)
    assert out["range"] == 15
    assert (out["high"], out["low"]) == expected
    assert out["used"] == 50


def test_mean_uses_only_requested_trailing_history(ranges):
    bars = pd.concat([frame([(100, 900, 0, 100)]), example()], ignore_index=True)
    assert ranges.average_range(bars, 2)["range"] == 15


@pytest.mark.parametrize("count", [0, 1, 2])
def test_insufficient_history_is_unavailable(ranges, count):
    assert ranges.average_range(example().iloc[:count], 2) == {"available": False, "n": count}


@pytest.mark.parametrize("from_open", [False, True])
def test_zero_prior_range_has_no_percentage_or_collapse_note(ranges, from_open):
    out = ranges.average_range(frame([(100, 100, 100, 100)] * 3), 2, from_open=from_open)
    assert out["available"] is True
    assert out["range"] == out["used"] == 0
    assert (out["high"], out["low"], out["high50"], out["low50"]) == (100, 100, 100, 100)
    assert out["used_pct"] is None
    assert out["note"] is None


@pytest.mark.parametrize("length", [15, 13])
@pytest.mark.parametrize("from_open,expected", [(False, (100, 130)), (True, (105, 95))])
def test_rd_rw_are_mean_projections_not_rolling_extrema(ranges, length, from_open, expected):
    bars = frame([(200, 210, 200, 205)] * length + [(100, 140, 90, 110)])
    out = ranges.range_hilo(bars, length, from_open=from_open, broker_bars=True)
    assert out["range"] == 10
    assert (out["high"], out["low"]) == expected
    assert out["verified"] is True


def test_pivots_use_previous_bar_and_optional_midpoints(ranges):
    bars = example()
    expected = {"PP": 100, "R1": 110, "R2": 120, "R3": 130,
                "S1": 90, "S2": 80, "S3": 70}
    assert ranges.daily_pivots(bars, include_m=False) == expected
    assert ranges.daily_pivots(bars) == expected | {
        "M0": 75, "M1": 85, "M2": 95, "M3": 105, "M4": 115, "M5": 125,
    }
    assert ranges.daily_pivots(bars.iloc[:1]) == {}
    assert ranges.daily_pivots(bars.iloc[:0]) == {}


def test_tr_levels_all_families_and_monthly_verification_asymmetry(ranges):
    daily = frame([(100, 110, 90, 100)] * 15 + [(100, 115, 95, 110)])
    weekly = frame([(200, 230, 190, 210)] * 13 + [(200, 225, 195, 220)])
    monthly = frame([(300, 350, 290, 320)] * 6 + [(300, 345, 295, 330)])
    out = ranges.tr_levels(daily, weekly, monthly, broker_bars=True)
    assert list(out) == ["pivots", "adr", "adr_from_open", "rd", "yday", "awr",
                         "awr_from_open", "rw", "lweek", "amr", "amr_from_open"]
    for key, length, width, high, low, verified in [
        ("adr", 14, 20, 115, 95, True), ("adr_from_open", 14, 20, 110, 90, True),
        ("rd", 15, 20, 115, 95, True), ("awr", 4, 40, 235, 185, True),
        ("awr_from_open", 4, 40, 220, 180, True), ("rw", 13, 40, 235, 185, True),
        ("amr", 6, 60, 355, 285, False), ("amr_from_open", 6, 60, 330, 270, False),
    ]:
        assert out[key]["available"] is True
        assert (out[key]["length"], out[key]["range"], out[key]["high"], out[key]["low"]) == (length, width, high, low)
        assert out[key]["verified"] is verified
    assert out["yday"] == {"high": 110, "low": 90, "close": 100}
    assert out["lweek"] == {"high": 230, "low": 190}
    assert out["pivots"]["PP"] == 100


@pytest.mark.parametrize("count", [0, 1, 2, 4, 5])
def test_lweek_is_nested_under_awr_warmup_and_rw_can_be_unavailable(ranges, count):
    weekly = frame([(100, 110, 90, 100)] * count)
    out = ranges.tr_levels(example(), weekly)
    assert ("lweek" in out) is (count == 5)
    assert ("awr" in out) is (count == 5)
    if count == 5:
        assert out["rw"] == {"available": False, "n": 5}


@pytest.mark.parametrize("count", [0, 1, 6, 7])
def test_monthly_warmup_controls_both_families(ranges, count):
    out = ranges.tr_levels(example(), monthly=frame([(100, 110, 90, 100)] * count))
    assert ("amr" in out) is (count == 7)
    assert ("amr_from_open" in out) is (count == 7)


def test_absent_periods_and_short_daily_do_not_create_history(ranges):
    out = ranges.tr_levels(example().iloc[:1])
    assert list(out) == ["pivots", "adr", "adr_from_open", "rd"]
    assert out["pivots"] == {}
    assert out["rd"] == {"available": False, "n": 1}


@pytest.mark.parametrize("hour", [21, 22])
def test_sunday_rollover_moves_to_next_week_without_mutating_daily(ranges, hour):
    bars = frame([(100, 105, 95, 102), (102, 110, 90, 108), (200, 220, 190, 210)])
    bars.index = pd.to_datetime(["2026-08-06T21:00Z", "2026-08-07T21:00Z", f"2026-08-09T{hour}:00Z"])
    before = bars.copy(deep=True)
    out = ranges.weekly_from_daily(bars)
    assert list(out.index) == list(pd.to_datetime(["2026-08-09T00:00Z", "2026-08-16T00:00Z"]))
    assert out.to_dict("records") == [
        {"open": 100, "high": 110, "low": 90, "close": 108},
        {"open": 200, "high": 220, "low": 190, "close": 210},
    ]
    pd.testing.assert_frame_equal(bars, before)


@pytest.mark.parametrize("function,dates,index", [
    ("weekly_from_daily", ["2026-08-09T20:59:59Z", "2026-08-09T21:00:00Z"],
     ["2026-08-09T00:00Z", "2026-08-16T00:00Z"]),
    ("monthly_from_daily", ["2026-08-31T20:59:59Z", "2026-08-31T21:00:00Z"],
     ["2026-08-01T00:00Z", "2026-09-01T00:00Z"]),
])
def test_exact_three_hour_week_and_month_boundaries(ranges, function, dates, index):
    bars = frame([(100, 110, 90, 105), (200, 220, 190, 210)])
    bars.index = pd.to_datetime(dates)
    out = getattr(ranges, function)(bars)
    assert list(out.index) == list(pd.to_datetime(index))
    assert out.to_numpy().tolist() == [[100, 110, 90, 105], [200, 220, 190, 210]]


@pytest.mark.parametrize("function", ["weekly_from_daily", "monthly_from_daily"])
def test_resampling_omits_empty_buckets(ranges, function):
    bars = frame([(100, 110, 90, 105), (200, 220, 190, 210)])
    bars.index = pd.to_datetime(["2026-01-01T00:00Z", "2026-04-01T00:00Z"])
    assert len(getattr(ranges, function)(bars)) == 2


@pytest.mark.parametrize("count", [None, 0, 1, 4])
def test_back_days_requires_full_warmup(back_days, count):
    bars = None if count is None else frame([(100, 110, 90, 105)] * count)
    assert back_days._back_day_levels(bars) == []


def test_back_days_offsets_and_order_exclude_today_yesterday_and_older_rows(back_days):
    bars = frame([(1, 9, 0, 2), (10, 19, 10, 15), (20, 29, 20, 25),
                  (30, 39, 30, 35), (40, 49, 40, 45), (50, 59, 50, 55)])
    expected = [("D2-HI", 39.0), ("D2-LO", 30.0), ("D3-HI", 29.0),
                ("D3-LO", 20.0), ("D4-HI", 19.0), ("D4-LO", 10.0)]
    assert back_days._back_day_levels(bars) == expected
    assert back_days._back_day_levels(bars.iloc[1:]) == expected


def replace_read(monkeypatch, path, replacement):
    """Mutate only the auditor's text input; leave shared and source files intact."""
    original = Path.read_text

    def read(self, *args, **kwargs):
        if self == path:
            return replacement
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)


def assert_blocked(report, prefix):
    assert report["subset_verified"] is False
    assert any(b.startswith(prefix) for b in report["blockers"]), report
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


def test_pinned_source_audit_never_grants_readiness():
    out = audit().check_source_parity(SOURCE)
    assert out["blockers"] == [], "Pinned source prerequisite required; set TR_CHARTDESK_SOURCE_ROOT: " + repr(out)
    assert out["subset_verified"] is True
    assert out["ready_for_replay"] is False
    assert out["ready_for_training"] is False


@pytest.mark.parametrize("mutation", ["omit_file", "omit_symbol", "reorder", "imports", "blob", "commit", "ready", "bool_number"])
def test_contract_cannot_relax_fixed_coverage(monkeypatch, mutation):
    checker = audit()
    data = json.loads(checker.CONTRACT.read_text(encoding="utf-8"))
    if mutation == "omit_file":
        data["files"].pop()
    elif mutation == "omit_symbol":
        data["files"][0]["symbols"].pop()
    elif mutation == "reorder":
        data["files"][0]["symbols"].reverse()
    elif mutation == "imports":
        data["files"][0]["allowed_imports"] += "\nimport os"
    elif mutation == "blob":
        data["files"][0]["git_blob_sha1"] = "0" * 40
    elif mutation == "commit":
        data["commit"] = "0" * 40
    elif mutation == "ready":
        data["ready_for_training"] = True
    else:
        data["ready_for_replay"] = 0
    replace_read(monkeypatch, checker.CONTRACT, json.dumps(data))
    assert_blocked(checker.check_source_parity(SOURCE), "CONTRACT_MISMATCH")


@pytest.mark.parametrize("filename", ["chartdesk/tr.py", "chartdesk/levelmap.py"])
def test_source_blob_mutation_is_rejected_without_execution(monkeypatch, filename):
    checker = audit()
    path = SOURCE / filename
    replace_read(monkeypatch, path, path.read_text(encoding="utf-8") + "\nraise AssertionError('SOURCE MUST NEVER EXECUTE')\n")
    assert_blocked(checker.check_source_parity(SOURCE), "SOURCE_BLOB_MISMATCH")


@pytest.mark.parametrize("filename,mutation", [
    ("ranges.py", "formula"), ("ranges.py", "import"), ("ranges.py", "duplicate"),
    ("ranges.py", "reorder"), ("ranges.py", "omit"), ("ranges.py", "syntax"),
    ("back_days.py", "constant"), ("back_days.py", "import"),
    ("back_days.py", "executable"), ("back_days.py", "docstring"),
])
def test_vendor_mutations_and_additions_are_rejected(monkeypatch, filename, mutation):
    checker = audit()
    path = ROOT / "trading_system/tree_replay/_vendor" / filename
    text = path.read_text(encoding="utf-8")
    if mutation == "formula":
        text = text.replace("ar = float(rng.mean())", "ar = float(rng.max())")
    elif mutation == "constant":
        text = text.replace("BACK_DAYS = 4", "BACK_DAYS = 3")
    elif mutation == "import":
        text += "\nimport os\n"
    elif mutation == "duplicate":
        text += "\ndef average_range(*args, **kwargs):\n    return {}\n"
    elif mutation == "reorder":
        text = text.replace("from __future__ import annotations\n\nimport pandas as pd", "import pandas as pd\n\nfrom __future__ import annotations")
    elif mutation == "omit":
        text = text[:text.index("def tr_levels(")]
    elif mutation == "syntax":
        text += "\ndef broken(\n"
    elif mutation == "docstring":
        text += '\n"unexpected statement"\n'
    else:
        text += "\nraise AssertionError('VENDOR MUST NEVER EXECUTE DURING AUDIT')\n"
    assert text != path.read_text(encoding="utf-8")
    replace_read(monkeypatch, path, text)
    prefix = "VENDOR_UNREADABLE" if mutation == "syntax" else "VENDOR_AST_MISMATCH"
    assert_blocked(checker.check_source_parity(SOURCE), prefix)


@pytest.mark.parametrize("mutation", ["commit", "omit", "duplicate"])
def test_baseline_pin_mismatch_is_rejected(monkeypatch, mutation):
    checker = audit()
    path = ROOT / "configs/trees/existing-alerts-baseline.json"
    baseline = json.loads(path.read_text(encoding="utf-8"))
    row = next(r for r in baseline["repositories"] if r["name"] == "chart-desk")
    if mutation == "commit":
        row["commit"] = "0" * 40
    elif mutation == "omit":
        baseline["repositories"].remove(row)
    else:
        baseline["repositories"].append(row.copy())
    replace_read(monkeypatch, path, json.dumps(baseline))
    assert_blocked(checker.check_source_parity(SOURCE), "BASELINE_COMMIT_MISMATCH")


def test_missing_source_is_explicit_failure(tmp_path):
    assert_blocked(audit().check_source_parity(tmp_path), "SOURCE_UNREADABLE")


def test_cli_success_and_missing_prerequisite_exit_codes(tmp_path):
    audit()
    command = [sys.executable, "-B", str(ROOT / "tools/check_range_source_parity.py"), "--source-root"]
    for source, code, verified in [(SOURCE, 0, True), (tmp_path, 2, False)]:
        run = subprocess.run(command + [str(source)], capture_output=True, text=True, check=False)
        assert run.returncode == code, run.stderr + run.stdout
        report = json.loads(run.stdout)
        assert report["subset_verified"] is verified
        assert report["ready_for_replay"] is False
        assert report["ready_for_training"] is False
