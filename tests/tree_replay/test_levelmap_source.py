"""Hand-derived synthetic map behavior and relocated text-only audit mutations."""

import importlib
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get(
    "TR_CHARTDESK_SOURCE_ROOT",
    (Path(os.environ.get("TR_TREE_SOURCE_ROOT", Path(__file__).resolve().parents[2] / ".source-checkouts")) / "chart-desk"),
))
SYMBOL = "OANDA:XAUUSD"
NOW = pd.Timestamp("2026-09-09T14:00Z")


def module(name):
    assert importlib.util.find_spec(name) is not None, f"Missing assigned sidecar: {name}"
    return importlib.import_module(name)


def graph():
    return module("trading_system.tree_replay._vendor.levelmap_build")


def sessions():
    return module("trading_system.tree_replay._vendor.map_sessions")


def audit():
    return module("tools.check_levelmap_source_parity")


def bars(count, *, end="2026-09-09T00:00Z", freq="1D", row=(100, 110, 90, 100)):
    return pd.DataFrame([row] * count, columns=["open", "high", "low", "close"],
                        index=pd.date_range(end=end, periods=count, freq=freq))


def daily(count=16):
    frame = bars(count)
    frame.iloc[-1] = [100, 115, 95, 110]
    return frame


def correction(source="tv_daily", *, symbol=SYMBOL, seam=None):
    from trading_system.tree_replay._vendor.correction import Correction
    return Correction(symbol, 0, source, "n/a", "synthetic", seam)


class OfflineSource:
    """Only the external frame boundary is supplied; calculations remain real."""

    def __init__(self, frames, *, decision_time=NOW, broker=None, symbol=SYMBOL):
        self.frames = frames
        self.decision_time = decision_time
        self.broker = broker
        self.symbol = symbol
        self.calls = []

    def fetch_corrected(self, symbol, timeframe, lookback_days):
        assert symbol == self.symbol
        self.calls.append((timeframe, lookback_days))
        value = self.frames.get((timeframe, lookback_days), LookupError("no synthetic frame"))
        if isinstance(value, Exception):
            raise value
        frame, corr = value
        return (None if frame is None else frame.copy(deep=True)), corr

    def broker_shape_ok(self, corr, days):
        from trading_system.tree_replay._vendor.correction import broker_shape_ok_at
        if self.broker is not None:
            return self.broker
        return broker_shape_ok_at(corr, days, decision_time=self.decision_time)


def build(g, source, *, missing=None, now=NOW):
    return g.build_at(source.symbol, missing, source=source, decision_time=now)


def named(levels):
    return [(level.name, level.price) for level in levels]


def psy_frame(mode="forex"):
    # Sydney Sunday/Saturday 08:00 through next day 16:00, September UTC+10.
    end = "2026-09-07T06:00Z" if mode == "forex" else "2026-09-06T06:00Z"
    return bars(33, end=end, freq="1h", row=(100, 150, 80, 100))


@pytest.mark.parametrize("broker,rails", [
    (True, [("ADR-HI", 115), ("ADR-LO", 95), ("ADR50-HI", 110),
            ("ADR50-LO", 90), ("RD-HI", 115), ("RD-LO", 95)]),
    (False, [("ADR50-HI", 110), ("ADR50-LO", 90)]),
])
def test_daily_rails_require_shape_but_open_anchors_and_prior_days_survive(broker, rails):
    g = graph()
    source = OfflineSource({("1d", 400): (daily(), correction())}, broker=broker)
    levels, corr = build(g, source)
    assert named(levels) == rails + [
        ("YDAY-HI", 110), ("YDAY-LO", 90), ("YDAY-CLOSE", 100),
        ("D2-HI", 110), ("D2-LO", 90), ("D3-HI", 110), ("D3-LO", 90),
        ("D4-HI", 110), ("D4-LO", 90), ("DAY-OPEN", 100), ("WEEK-OPEN", 100),
        ("Q-WHOLE", 100), ("Q-QUARTER", 125), ("Q-QUARTER", 75), ("Q-HALF", 150),
    ]
    assert corr is source.frames[("1d", 400)][1]
    assert repr(levels[0]) == f"{levels[0].name}@{levels[0].price:,.1f}"


def test_full_family_order_prices_kinds_excludes_pivots_and_extra_emas():
    g = graph()
    opening = bars(2)
    opening.index = pd.to_datetime(["2026-09-09T07:00Z", "2026-09-09T13:30Z"])
    opening["open"] = [103, 107]
    source = OfflineSource({
        ("1d", 400): (daily(220), correction()),
        ("5m", 3): (opening, correction()),
        ("1h", 20): (psy_frame(), correction()),
        ("1h", 240): (bars(1600, freq="1h"), correction()),
        ("4h", 240): (bars(400, freq="4h"), correction()),
    })
    missing = []
    levels, _ = build(g, source, missing=missing)
    assert named(levels) == [
        ("ADR-HI", 115), ("ADR-LO", 95), ("AWR-HI", 110), ("AWR-LO", 95),
        ("RW-HI", 110), ("RW-LO", 95), ("AMR-HI", 110), ("AMR-LO", 95),
        ("ADR50-HI", 110), ("ADR50-LO", 90), ("AWR50-HI", 110), ("AWR50-LO", 90),
        ("AMR50-HI", 110), ("AMR50-LO", 90), ("RD-HI", 115), ("RD-LO", 95),
        ("YDAY-HI", 110), ("YDAY-LO", 90), ("YDAY-CLOSE", 100),
        ("D2-HI", 110), ("D2-LO", 90), ("D3-HI", 110), ("D3-LO", 90),
        ("D4-HI", 110), ("D4-LO", 90), ("LWEEK-HI", 110), ("LWEEK-LO", 90),
        ("DAY-OPEN", 100), ("WEEK-OPEN", 100), ("LONDON-OPEN", 103), ("NY-OPEN", 107),
        ("PSY-HI", 150), ("PSY-LO", 80), ("EMA200-1h", pytest.approx(100, abs=1e-10)),
        ("EMA800-1h", pytest.approx(100, abs=1e-10)),
        ("CLOUD50-4h", 100), ("EMA200-4h", pytest.approx(100, abs=1e-10)),
        ("Q-WHOLE", 100), ("Q-QUARTER", 125), ("Q-QUARTER", 75), ("Q-HALF", 150),
    ]
    assert [x.kind for x in levels] == ["level"] * 31 + ["psy"] * 2 + ["ema"] * 4 + ["quarter"] * 4
    assert missing == []
    assert source.calls == [("1d", 400), ("5m", 3), ("1h", 20), ("1h", 240), ("4h", 240)]


def test_daily_fetch_failure_stops_without_inventing_families_or_missing_lines():
    g = graph()
    source = OfflineSource({})
    missing = []
    assert build(g, source, missing=missing) == ([], None)
    assert missing == []
    assert source.calls == [("1d", 400)]


@pytest.mark.parametrize("count,want", [
    (1, ["DAY-OPEN", "WEEK-OPEN"]),
    (2, ["YDAY-HI", "YDAY-LO", "YDAY-CLOSE", "DAY-OPEN", "WEEK-OPEN"]),
    (5, ["YDAY-HI", "YDAY-LO", "YDAY-CLOSE", "D2-HI", "D2-LO", "D3-HI", "D3-LO",
         "D4-HI", "D4-LO", "DAY-OPEN", "WEEK-OPEN"]),
])
def test_warmup_omits_families_without_hiding_remaining_levels(count, want):
    g = graph()
    source = OfflineSource({("1d", 400): (daily(count), correction())}, symbol="TEST:UNKNOWN")
    missing = []
    levels, _ = build(g, source, missing=missing)
    assert [x.name for x in levels] == want
    assert missing[:3] == [f"רמות {name} לא זמינות — 0 נרות בלבד" for name in ("AWR", "RW", "AMR")]


@pytest.mark.parametrize("count,weekly,monthly", [(16, False, False), (40, True, False), (220, True, True)])
def test_weekly_monthly_history_guards_do_not_inherit_daily_broker_veto(count, weekly, monthly):
    g = graph()
    levels, _ = build(g, OfflineSource({("1d", 400): (daily(count), correction("replay"))}))
    names = {x.name for x in levels}
    assert ("AWR-HI" in names) is weekly
    assert ("LWEEK-HI" in names) is weekly
    assert ("AWR50-HI" in names) is weekly
    assert ("AMR-HI" in names) is monthly
    assert ("AMR50-HI" in names) is monthly
    assert ("RW-HI" in names) is (count == 220)
    assert "ADR-HI" not in names and "RD-HI" not in names


@pytest.mark.parametrize("source_name,symbol,seam,has_rails,has_psy,has_open", [
    (None, SYMBOL, None, False, False, False),
    ("none", SYMBOL, None, False, False, False),
    ("replay", SYMBOL, None, False, False, True),
    ("tv_daily", SYMBOL, None, True, True, True),
    ("mt5_broker", SYMBOL, None, True, True, True),
    ("none", "BINANCE:BTCUSDT", None, True, True, False),
    ("replay", "BINANCE:BTCUSDT", None, True, True, True),
    ("tv_spliced", SYMBOL, "2026-08-20T14:00Z", True, True, True),
    ("tv_spliced", SYMBOL, "2026-08-20T14:00:00.000001Z", False, True, True),
    ("tv_spliced", SYMBOL, "2026-09-02T14:00Z", False, True, True),
    ("tv_spliced", SYMBOL, "2026-09-02T14:00:00.000001Z", False, False, True),
    ("tv_spliced", SYMBOL, None, False, False, True),
])
def test_source_identity_guards_are_family_specific(source_name, symbol, seam, has_rails, has_psy, has_open):
    g = graph()
    corr = None if source_name is None else correction(source_name, symbol=symbol,
                                                      seam=None if seam is None else pd.Timestamp(seam))
    opening = bars(1, end="2026-09-09T07:00Z")
    source = OfflineSource({("1d", 400): (daily(), corr), ("5m", 3): (opening, corr),
                            ("1h", 20): (psy_frame("crypto" if "BTC" in symbol else "forex"), corr)}, symbol=symbol)
    levels, _ = build(g, source)
    names = {x.name for x in levels}
    assert ("ADR-HI" in names) is has_rails
    assert ("RD-HI" in names) is has_rails
    assert ("PSY-HI" in names) is has_psy
    assert ("LONDON-OPEN" in names) is has_open
    assert "DAY-OPEN" in names and "YDAY-HI" in names


@pytest.mark.parametrize("day,london,ny", [
    ("2026-09-09", "07:00", "13:30"), ("2026-01-07", "08:00", "14:30"),
    ("2026-03-16", "08:00", "13:30"), ("2026-10-28", "08:00", "13:30"),
])
def test_exact_venue_open_moves_with_each_venues_dst(day, london, ny):
    g = graph()
    opening = bars(2)
    opening.index = pd.to_datetime([f"{day}T{london}Z", f"{day}T{ny}Z"])
    opening["open"] = [101, 109]
    source = OfflineSource({("5m", 3): (opening, correction())})
    out = g._session_open_levels_at(SYMBOL, source=source, decision_time=f"{day}T15:00Z")
    assert named(out) == [("LONDON-OPEN", 101), ("NY-OPEN", 109)]


@pytest.mark.parametrize("instant,want", [
    ("2026-09-09T06:59:59.999999Z", []),
    ("2026-09-09T07:00Z", ["LONDON-OPEN"]),
    ("2026-09-09T13:30Z", ["LONDON-OPEN", "NY-OPEN"]),
    ("2026-09-09T15:30Z", ["NY-OPEN"]), ("2026-09-09T20:00Z", []),
    ("2026-09-12T14:00Z", []), ("2026-09-13T14:00Z", []),
    ("2026-09-09 14:00", ["LONDON-OPEN", "NY-OPEN"]),
    ("2026-09-09T17:00+03:00", ["LONDON-OPEN", "NY-OPEN"]),
])
def test_session_half_open_hours_weekends_and_utc_normalization(instant, want):
    g = graph()
    day = instant[:10]
    opening = bars(2)
    opening.index = pd.to_datetime([f"{day}T07:00Z", f"{day}T13:30Z"])
    source = OfflineSource({("5m", 3): (opening, correction())})
    assert [x.name for x in g._session_open_levels_at(SYMBOL, source=source, decision_time=instant)] == want


@pytest.mark.parametrize("bar_time,seam,want", [
    ("2026-09-09T07:05Z", None, []), ("2026-09-08T07:00Z", None, []),
    ("2026-09-09T07:00Z", "2026-09-09T07:05Z", []),
    ("2026-09-09T07:00Z", "2026-09-09T07:00Z", [("LONDON-OPEN", 100)]),
])
def test_open_requires_exact_today_bar_on_or_after_splice_seam(bar_time, seam, want):
    g = graph()
    corr = correction("tv_spliced", seam=pd.Timestamp(seam)) if seam else correction()
    source = OfflineSource({("5m", 3): (bars(1, end=bar_time), corr)})
    missing = []
    assert named(g._session_open_levels_at(SYMBOL, missing, source=source,
                                           decision_time="2026-09-09T08:00Z")) == want
    assert len(missing) == (0 if want else 1)
    if not want:
        assert missing[0].startswith("LONDON-OPEN לא זמינה")


@pytest.mark.parametrize("value", [None, "empty", "error"])
def test_session_unavailable_frames_omit_levels_without_throwing(value):
    g = graph()
    supplied = RuntimeError() if value == "error" else (None if value is None else bars(0), correction())
    source = OfflineSource({("5m", 3): supplied})
    assert g._session_open_levels_at(SYMBOL, source=source, decision_time=NOW) == []


@pytest.mark.parametrize("hourly,four_hour,want", [
    (399, 99, []), (400, 100, ["EMA200-1h", "CLOUD50-4h"]),
    (1599, 399, ["EMA200-1h", "CLOUD50-4h"]),
    (1600, 400, ["EMA200-1h", "EMA800-1h", "CLOUD50-4h", "EMA200-4h"]),
])
def test_ema_history_must_reach_twice_period_with_source_order(hourly, four_hour, want):
    g = graph()
    source = OfflineSource({("1h", 240): (bars(hourly, freq="1h"), None),
                            ("4h", 240): (bars(four_hour, freq="4h"), None)})
    missing = []
    out = g._ema_levels(SYMBOL, missing, source=source)
    assert [x.name for x in out] == want
    assert [x.price for x in out] == pytest.approx([100] * len(want), abs=1e-10)
    assert len(missing) == 4 - len(want)
    for name, count, required in [("EMA200-1h", hourly, 400), ("EMA800-1h", hourly, 1600),
                                   ("CLOUD50-4h", four_hour, 100), ("EMA200-4h", four_hour, 400)]:
        if name not in want:
            assert f"רמת {name} לא קיימת — {count} נרות, נדרשים {required}" in missing


def test_cloud50_level_is_ema_basis_not_upper_or_lower_band():
    g = graph()
    frame = bars(100, freq="4h")
    frame["close"] = range(1, 101)
    frame["open"] = frame["close"]
    frame["high"] = frame["close"] + 0.5
    frame["low"] = frame["close"] - 0.5
    source = OfflineSource({("4h", 240): (frame, None)})
    out = g._ema_levels(SYMBOL, source=source)
    assert [x.name for x in out] == ["CLOUD50-4h"]
    assert out[0].price == pytest.approx(75.5)


def test_ema_fetch_failure_reports_type_and_continues_other_timeframe():
    g = graph()
    source = OfflineSource({("1h", 240): ValueError("bad"), ("4h", 240): (bars(100, freq="4h"), None)})
    missing = []
    assert named(g._ema_levels(SYMBOL, missing, source=source)) == [("CLOUD50-4h", 100)]
    assert missing == ["רמות EMA-1h לא נקראו (ValueError)", "רמת EMA200-4h לא קיימת — 100 נרות, נדרשים 400"]


@pytest.mark.parametrize("mode,end", [("forex", "2026-09-07T07:00Z"), ("crypto", "2026-09-06T07:00Z")])
def test_psy_uses_week_open_window_excludes_end_and_reports_planned_close(mode, end):
    s = sessions()
    frame = psy_frame(mode)
    frame.loc[pd.Timestamp(end)] = [100, 999, 1, 100]
    out = s.psy_levels(frame, mode=mode)
    assert out["available"] is True
    assert (out["psy_high"], out["psy_low"], out["bars"]) == (150, 80, 33)
    assert pd.Timestamp(out["window_end"]) == pd.Timestamp(end)
    assert pd.Timestamp(out["end"]) == pd.Timestamp(end) - pd.Timedelta(hours=1)
    forming = s.psy_levels(frame.iloc[:2], mode=mode)
    assert pd.Timestamp(forming["window_end"]) == pd.Timestamp(end)
    assert forming["bars"] == 2


@pytest.mark.parametrize("gap,want_high,want_bars", [(12, 900, 22), (13, 150, 20)])
def test_psy_gap_group_boundary_is_strictly_greater_than_twelve_hours(gap, want_high, want_bars):
    s = sessions()
    frame = psy_frame()
    frame.iloc[0, frame.columns.get_loc("high")] = 900
    frame = pd.concat([frame.iloc[:1], frame.iloc[gap:]])
    out = s.psy_levels(frame, mode="forex")
    assert (out["psy_high"], out["psy_low"], out["bars"]) == (want_high, 80, want_bars)


@pytest.mark.parametrize("count,freq,reason", [(1, "1h", "not enough bars"),
                                             (4, "4h", "needs 1h bars or finer"),
                                             (4, "1h", "no forex week-open session in sample")])
def test_psy_insufficient_resolution_or_absent_window_stays_unavailable(count, freq, reason):
    assert sessions().psy_levels(bars(count, freq=freq), mode="forex") == {"available": False, "reason": reason}


def test_psy_invalid_mode_does_not_choose_a_calendar():
    with pytest.raises(ValueError, match="mode must be"):
        sessions().psy_levels(psy_frame(), mode="equities")


@pytest.mark.parametrize("first,has_psy,fallback", [
    ("empty", True, True), ("unverified", True, True), ("missing_correction", True, True),
    ("valid", True, False), ("coarse", False, False), ("empty_after_seam", False, False),
    ("error", False, False),
])
def test_psy_fallback_depends_on_frame_acceptance_not_psy_result(first, has_psy, fallback):
    g = graph()
    frame, corr = psy_frame(), correction()
    if first == "empty":
        frame = frame.iloc[:0]
    elif first == "unverified":
        corr = correction("replay")
    elif first == "missing_correction":
        corr = None
    elif first == "coarse":
        frame = frame.iloc[::4]
    elif first == "empty_after_seam":
        corr = correction("tv_spliced", seam=NOW)
    supplied = ValueError("unavailable") if first == "error" else (frame, corr)
    quarter_hour = bars(132, end="2026-09-07T06:45Z", freq="15min", row=(100, 150, 80, 100))
    source = OfflineSource({("1d", 400): (daily(), correction()), ("1h", 20): supplied,
                            ("15m", 20): (quarter_hour, correction())},
                           broker=True if first == "empty_after_seam" else None)
    levels, _ = build(g, source)
    assert [(x.name, x.price) for x in levels if x.kind == "psy"] == (
        [("PSY-HI", 150), ("PSY-LO", 80)] if has_psy else [])
    assert (("15m", 20) in source.calls) is fallback


def test_psy_splice_clips_pre_seam_extremes_before_window_calculation():
    g = graph()
    frame = psy_frame()
    frame.iloc[0] = [100, 999, 1, 100]
    corr = correction("tv_spliced", seam=frame.index[1])
    source = OfflineSource({("1d", 400): (daily(), correction()), ("1h", 20): (frame, corr)}, broker=True)
    levels, _ = build(g, source)
    assert [(x.name, x.price) for x in levels if x.kind == "psy"] == [("PSY-HI", 150), ("PSY-LO", 80)]


def assert_blocked(report, prefix):
    assert report["subset_verified"] is False
    assert any(item.startswith(prefix) for item in report["blockers"]), report
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False


@pytest.fixture
def relocated(tmp_path):
    return lambda: _relocated(tmp_path)


def _relocated(tmp_path):
    audit()  # RED is an assertion on the missing assigned tool, not a copy error.
    root = tmp_path / "project"
    for directory in ("configs/trees", "trading_system/tree_replay/_vendor"):
        shutil.copytree(ROOT / directory, root / directory, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "tools").mkdir()
    for name in ("levelmap", "range", "pricing", "reversal", "ema", "correction"):
        filename = f"check_{name}_source_parity.py"
        shutil.copyfile(ROOT / "tools" / filename, root / "tools" / filename)
    source = tmp_path / "source"
    # Source remains text-only; copy just the dependency audit inputs.
    for filename in ("levelmap.py", "sessions.py", "tr.py", "basis.py", "quarters.py",
                     "tradeplan.py", "level_reversal.py", "indicators.py", "features.py", "auction.py"):
        target = source / "chartdesk" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / "chartdesk" / filename, target)
    return root, source


def run_audit(root, source=None, *, env_source=None):
    command = [sys.executable, "-B", str(root / "tools/check_levelmap_source_parity.py")]
    if source is not None:
        command += ["--source-root", str(source)]
    env = dict(os.environ)
    if env_source is not None:
        env["TR_CHARTDESK_SOURCE_ROOT"] = str(env_source)
    run = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    assert run.returncode in (0, 2), run.stderr + run.stdout
    report = json.loads(run.stdout)
    assert run.returncode == (0 if report["subset_verified"] else 2)
    return report


def mutate(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_pinned_graph_and_all_dependency_audits_verify_without_readiness():
    report = audit().check_source_parity(SOURCE)
    assert report["blockers"] == [], report
    assert report["subset_verified"] is True
    assert report["ready_for_replay"] is False
    assert report["ready_for_training"] is False
    assert set(report["dependency_audits"]) == {"range", "pricing", "ema", "correction"}
    assert all(result["source_subset_verified"] is True for result in report["dependency_audits"].values())


@pytest.mark.parametrize("change", ["commit", "duplicate", "missing"])
def test_baseline_requires_exactly_one_chartdesk_pin(relocated, change):
    root, source = relocated()
    path = root / "configs/trees/existing-alerts-baseline.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    row = next(row for row in value["repositories"] if row["name"] == "chart-desk")
    if change == "commit":
        row["commit"] = "0" * 40
    elif change == "duplicate":
        value["repositories"].append(row.copy())
    else:
        value["repositories"].remove(row)
    path.write_text(json.dumps(value), encoding="utf-8")
    assert_blocked(run_audit(root, source), "BASELINE_COMMIT_MISMATCH")


@pytest.mark.parametrize("change", ["omit_file", "omit_symbol", "order", "imports", "blob", "commit", "ready", "zero"])
def test_manifest_cannot_relax_fixed_projection(relocated, change):
    root, source = relocated()
    path = root / "configs/trees/levelmap-source-contracts.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if change == "omit_file":
        value["files"].pop()
    elif change == "omit_symbol":
        value["files"][0]["symbols"].pop()
    elif change == "order":
        value["files"][0]["symbols"].reverse()
    elif change == "imports":
        value["files"][0]["allowed_imports"] += "\nimport os"
    elif change == "blob":
        value["files"][0]["git_blob_sha1"] = "0" * 40
    elif change == "commit":
        value["commit"] = "0" * 40
    else:
        value["ready_for_replay"] = 0 if change == "zero" else True
    path.write_text(json.dumps(value), encoding="utf-8")
    assert_blocked(run_audit(root, source), "CONTRACT_MISMATCH")


@pytest.mark.parametrize("filename", ["levelmap.py", "sessions.py"])
def test_changed_source_is_rejected_as_text_without_execution(relocated, filename):
    root, source = relocated()
    path = source / "chartdesk" / filename
    path.write_text(path.read_text(encoding="utf-8") + "\nraise RuntimeError('must not execute source')\n", encoding="utf-8")
    assert_blocked(run_audit(root, source), "SOURCE_BLOB_MISMATCH")


@pytest.mark.parametrize("filename,old,new", [
    ("levelmap_build.py", "basis.broker_shape_ok(corr, 20)", "basis.broker_shape_ok(corr, 0)"),
    ("levelmap_build.py", "pd.Timestamp(decision_time)", "pd.Timestamp.now('UTC')"),
    ("levelmap_build.py", "start <= local < end", "start <= local <= end"),
    ("levelmap_build.py", 'len(df) >= 2 * n', 'len(df) >= n'),
    ("levelmap_build.py", "source, decision_time", "source=None, decision_time=None"),
    ("levelmap_build.py", "basis = source", "basis = None"),
    ("map_sessions.py", "pd.Timedelta(hours=12)", "pd.Timedelta(hours=13)"),
    ("map_sessions.py", '"08:00", "16:30"', '"09:00", "16:30"'),
    ("map_tr.py", "from .tr import emas", "from .tr import ema_cloud as emas"),
])
def test_vendor_guards_clocks_signatures_composition_cannot_drift(relocated, filename, old, new):
    root, source = relocated()
    mutate(root / "trading_system/tree_replay/_vendor" / filename, old, new)
    assert_blocked(run_audit(root, source), "VENDOR_AST_MISMATCH")


@pytest.mark.parametrize("filename", ["levelmap_build.py", "map_sessions.py", "map_tr.py"])
@pytest.mark.parametrize("extra", ["\nimport os\n", "\nraise RuntimeError('must not execute vendor')\n",
                                   "\nNamedLevel = None\n", '\n"extra statement"\n'])
def test_whole_module_audit_rejects_extra_or_rebound_code(relocated, filename, extra):
    root, source = relocated()
    path = root / "trading_system/tree_replay/_vendor" / filename
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    assert_blocked(run_audit(root, source), "VENDOR_AST_MISMATCH")


@pytest.mark.parametrize("filename,old,new,dependency", [
    ("ranges.py", "ar = float(rng.mean())", "ar = float(rng.max())", "range"),
    ("quarters.py", '"gold": 25.0', '"gold": 30.0', "pricing"),
    ("indicators.py", "def ema(", "def changed_ema(", "ema"),
    ("correction.py", "age_days >= days", "age_days > days", "correction"),
    ("level_reversal.py", "def detect_frame(", "def changed_detect_frame(", "pricing"),
])
def test_all_inherited_calculations_are_audited_including_pricing_reversal(relocated, filename, old, new, dependency):
    root, source = relocated()
    mutate(root / "trading_system/tree_replay/_vendor" / filename, old, new)
    assert_blocked(run_audit(root, source), f"DEPENDENCY_AUDIT_FAILED:{dependency}")


@pytest.mark.parametrize("dependency,manifest", [
    ("range", "range-level-contracts.json"), ("pricing", "reversal-pricing-contracts.json"),
    ("ema", "ema-feature-contracts.json"), ("correction", "correction-source-contracts.json"),
])
@pytest.mark.parametrize("change", ["missing", "invalid", "readiness", "blob"])
def test_dependency_manifests_missing_invalid_or_relaxed_fail_closed(relocated, dependency, manifest, change):
    root, source = relocated()
    path = root / "configs/trees" / manifest
    if change == "missing":
        path.unlink()
    elif change == "invalid":
        path.write_text("{", encoding="utf-8")
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        if change == "readiness":
            value["ready_for_training"] = True
        else:
            value["files"][0]["git_blob_sha1"] = "0" * 40
        path.write_text(json.dumps(value), encoding="utf-8")
    report = run_audit(root, source)
    assert_blocked(report, f"DEPENDENCY_CONTRACT_{'UNREADABLE' if change in ('missing', 'invalid') else 'MISMATCH'}:{dependency}")


@pytest.mark.parametrize("filename,old,new", [
    ("levelmap_build.py", "def build_at(", "def omitted_build_at("),
    ("levelmap_build.py", '    kind: str', '    changed_kind: str'),
    ("levelmap_build.py", '    return levels, corr', '    return levels, None'),
    ("map_sessions.py", "def psy_levels(", "def omitted_psy_levels("),
    ("map_sessions.py", "from zoneinfo import ZoneInfo\nimport numpy as np", "import numpy as np\nfrom zoneinfo import ZoneInfo"),
    ("map_tr.py", "from .tr import emas\nfrom .ranges import weekly_from_daily, monthly_from_daily, tr_levels",
     "from .ranges import weekly_from_daily, monthly_from_daily, tr_levels\nfrom .tr import emas"),
])
def test_omitted_symbols_class_fields_and_statement_order_are_audited(relocated, filename, old, new):
    root, source = relocated()
    mutate(root / "trading_system/tree_replay/_vendor" / filename, old, new)
    assert_blocked(run_audit(root, source), "VENDOR_AST_MISMATCH")


@pytest.mark.parametrize("old,new", [
    ("now=None)", "now=0)"),
    ('pd.Timestamp.now("UTC") if now is None else pd.Timestamp(now)', 'pd.Timestamp(now)'),
    ('    now = pd.Timestamp.now("UTC")', '    changed_now = pd.Timestamp.now("UTC")'),
    ('_session_open_levels(symbol, missing)', '_session_open_levels(symbol)'),
    ('_ema_levels(symbol, missing)', '_ema_levels(symbol)'),
    ('from . import basis, data, quarters, sessions, tr', 'from . import data, basis, quarters, sessions, tr'),
    ('SESSION_OPEN_LEVELS =', 'OMITTED_SESSION_OPEN_LEVELS ='),
    ('    levels: list[NamedLevel] = []', '    source = None\n    levels: list[NamedLevel] = []'),
])
def test_projection_preconditions_reject_unexpected_source_shapes_without_execution(old, new):
    checker = audit()
    text = (SOURCE / "chartdesk/levelmap.py").read_text(encoding="utf-8")
    assert old in text
    with pytest.raises(ValueError, match="SOURCE_"):
        checker._expected_module(text.replace(old, new, 1), "chartdesk/levelmap.py")


def test_missing_dependency_checker_is_blocked_report_not_traceback(relocated):
    root, source = relocated()
    (root / "tools/check_ema_source_parity.py").unlink()
    assert_blocked(run_audit(root, source), "DEPENDENCY_AUDIT_UNREADABLE:ema")


def test_cli_root_precedence_and_missing_source_fail_closed(relocated, tmp_path):
    root, source = relocated()
    explicit = run_audit(root, source, env_source=tmp_path / "absent")
    assert explicit["subset_verified"] is True, explicit
    environment = run_audit(root, env_source=source)
    assert environment["subset_verified"] is True, environment
    assert_blocked(run_audit(root, env_source=tmp_path / "absent"), "SOURCE_UNREADABLE")


@pytest.mark.parametrize("filename", ["levelmap_build.py", "map_sessions.py", "map_tr.py"])
def test_missing_vendor_and_syntax_errors_fail_closed(relocated, filename):
    root, source = relocated()
    path = root / "trading_system/tree_replay/_vendor" / filename
    path.write_text("def broken(\n", encoding="utf-8")
    assert_blocked(run_audit(root, source), "VENDOR_UNREADABLE")
    path.unlink()
    assert_blocked(run_audit(root, source), "VENDOR_UNREADABLE")


def legacy_ema_report(root, source):
    run = subprocess.run([sys.executable, "-B", str(root / "tools/check_ema_source_parity.py"),
                          "--source-root", str(source)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr + run.stdout
    return json.loads(run.stdout)


def test_joint_indicators_source_vendor_manifest_change_cannot_repin_trusted_closure(relocated):
    root, source = relocated()
    path = source / "chartdesk/indicators.py"
    old, new = "2.0 / (length + 1.0)", "1.0 / (length + 1.0)"
    mutate(path, old, new)
    mutate(root / "trading_system/tree_replay/_vendor/indicators.py", old, new)
    manifest = root / "configs/trees/ema-feature-contracts.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    data = path.read_text(encoding="utf-8").encode("utf-8")
    row = next(row for row in value["files"] if row["path"] == "chartdesk/indicators.py")
    row["git_blob_sha1"] = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    manifest.write_text(json.dumps(value), encoding="utf-8")
    # Demonstrate the inherited trust gap without executing either calculation.
    assert legacy_ema_report(root, source)["source_subset_verified"] is True
    report = run_audit(root, source)
    assert_blocked(report, "DEPENDENCY_CONTRACT_MISMATCH:ema")
    assert_blocked(report, "STRICT_EMA_SOURCE_BLOB_MISMATCH:chartdesk/indicators.py")


def test_tr_emas_after_function_default_is_rejected_even_if_legacy_audit_passes(relocated):
    root, source = relocated()
    path = root / "trading_system/tree_replay/_vendor/tr.py"
    text = path.read_text(encoding="utf-8")
    declaration = "TR_EMAS: tuple[int, ...] = (5, 13, 50, 200, 800)"
    assert text.count(declaration) == 1
    path.write_text(text.replace(declaration, "") + "\n" + declaration + "\n", encoding="utf-8")
    assert legacy_ema_report(root, source)["source_subset_verified"] is True
    assert_blocked(run_audit(root, source), "STRICT_EMA_VENDOR_AST_MISMATCH")


@pytest.mark.parametrize("filename,change", [("tr.py", "imports"), ("tr.py", "duplicate_import"),
                                           ("indicators.py", "order"), ("indicators.py", "extra_string")])
def test_strict_ema_projection_rejects_order_duplicates_and_noninitial_statements(relocated, filename, change):
    root, source = relocated()
    path = root / "trading_system/tree_replay/_vendor" / filename
    text = path.read_text(encoding="utf-8")
    if change == "imports":
        text = text.replace("from __future__ import annotations", "import pandas as pd", 1).replace(
            "import pandas as pd\n\nfrom .", "from __future__ import annotations\n\nfrom .", 1)
    elif change == "duplicate_import":
        text += "\nimport pandas as pd\n"
    elif change == "order":
        start, end = text.index("def ema("), text.index("def stdev(")
        text = text[:start] + text[end:] + "\n\n" + text[start:end]
    else:
        text += '\n"not an initial module docstring"\n'
    assert text != path.read_text(encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    assert legacy_ema_report(root, source)["source_subset_verified"] is True
    assert_blocked(run_audit(root, source), "STRICT_EMA_VENDOR_AST_MISMATCH")


def test_strict_ema_projection_allows_only_harmless_initial_module_documentation(relocated):
    root, source = relocated()
    for filename in ("tr.py", "indicators.py"):
        path = root / "trading_system/tree_replay/_vendor" / filename
        text = path.read_text(encoding="utf-8")
        assert text.startswith('"""')
        end = text.index('"""', 3) + 3
        path.write_text('"""Different harmless module description."""' + text[end:], encoding="utf-8")
    report = run_audit(root, source)
    assert report["subset_verified"] is True, report
