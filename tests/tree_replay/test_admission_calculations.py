"""Synthetic source behavior, with expectations independent of the port."""

from datetime import datetime, timezone
from importlib import import_module
import math

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def modules():
    # Missing modules are an explicit RED assertion, not a collection error.
    names = ("matrix", "toolkit", "indicators", "quality", "clocks", "swing")
    result = {}
    for name in names:
        try:
            result[name] = import_module("trading_system.tree_replay._vendor.admission_" + name)
        except ModuleNotFoundError as exc:
            pytest.fail(f"Task1 calculation sidecar missing: {exc.name}")
    return result


def frame(prices, *, start="2026-09-07T02:00:00Z", volume=1.0):
    p = np.asarray(prices, dtype=float)
    return pd.DataFrame({"open": p, "high": p + 1, "low": p - 1,
                         "close": p, "volume": volume},
                        index=pd.date_range(start, periods=len(p), freq="min"))


@pytest.mark.parametrize("stamp,reason", [
    ("2026-09-07T01:59:00+03:00", "01:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
    ("2026-09-07T02:00:00+03:00", None),
    ("2026-09-07T20:59:59+03:00", None),
    ("2026-09-07T21:00:00+03:00", "21:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
    ("2026-01-05T00:00:00+00:00", None),
    ("2026-09-06T23:00:00+00:00", None),
    ("2026-10-25T01:30:00+03:00", "01:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
    ("2026-10-25T01:30:00+02:00", "01:00 — מחוץ לחלון החיפוש (02:00-21:00)"),
])
def test_hunting_exact_boundaries_dst_and_instant_equivalence(modules, stamp, reason):
    clocks = modules["clocks"]
    t = datetime.fromisoformat(stamp)
    assert clocks.outside_reason(t) == reason
    assert clocks.outside_reason(t.astimezone(timezone.utc)) == reason
    assert clocks.hunting(t) is (reason is None)


@pytest.mark.parametrize("stamp,closed,minutes,blocked", [
    ("2026-09-11T21:29:59+03:00", False, 90 + 1 / 60, None),
    ("2026-09-11T21:30:00+03:00", False, 90, "סגירת שבוע בעוד 90 דק' — לא נפתחות עסקאות חדשות (גאפ בפתיחה לא ניתן להגנה בסטופ)"),
    ("2026-09-11T22:40:00+03:00", False, 20, "סגירת שבוע בעוד 20 דק' — לא נפתחות עסקאות חדשות (גאפ בפתיחה לא ניתן להגנה בסטופ)"),
    ("2026-09-11T23:00:00+03:00", True, None, "שוק סגור"),
    ("2026-09-12T12:00:00+03:00", True, None, "שוק סגור"),
    ("2026-09-13T16:00:00+03:00", True, None, "שוק סגור"),
    ("2026-09-14T00:59:59+03:00", True, None, "שוק סגור"),
    ("2026-09-14T01:00:00+03:00", False, None, None),
    ("2026-01-05T01:00:00+02:00", False, None, None),
])
def test_floor_weekend_preclose_and_open_boundaries(modules, stamp, closed, minutes, blocked):
    clocks = modules["clocks"]
    t = datetime.fromisoformat(stamp)
    for instant in (t, t.astimezone(timezone.utc)):
        assert clocks.is_closed(instant) is closed
        assert clocks.minutes_to_close(instant) == pytest.approx(minutes)
        assert clocks.entry_blocked(instant) == blocked


@pytest.mark.parametrize("name", ["now_il", "hunting", "outside_reason", "is_closed", "minutes_to_close", "entry_blocked"])
def test_clock_entry_points_reject_missing_naive_or_invalid_time(modules, name):
    fn = getattr(modules["clocks"], name)
    with pytest.raises(TypeError):
        fn()
    for value in (None, datetime(2026, 9, 7, 2), "2026-09-07T02:00:00Z", pd.NaT):
        with pytest.raises((TypeError, ValueError)):
            fn(value)


@pytest.mark.parametrize("prices,directions,strengths,net", [
    (np.arange(100, 160), [1, 1, 1, 0], [100, 90, 72, 0], 67.25),
    (np.arange(160, 100, -1), [-1, -1, -1, 0], [100, 90, 72, 0], -67.25),
    (np.full(60, 100), [0, -1, -1, 0], [20, 90, 100, 0], -41.25),
])
def test_matrix_golden_rising_falling_flat_nan(modules, prices, directions, strengths, net):
    # Linear bars: TR fan=11.25 ATR, z=sqrt(3*59/61)=1.7034199.
    # Flat VWAP's z is NaN: the source emits short strength 100, not neutral.
    df = frame(prices)
    before = df.copy(deep=True)
    view = modules["matrix"].read_frame(df, "5m", basis_note="supplied")
    assert view.tf == "5m" and view.basis_note == "supplied"
    assert view.close == float(prices[-1])
    assert view.atr == 2
    assert view.bar_ts == 1788749940.0
    assert [r.tool for r in view.reads] == ["tr", "supertrend", "vwap", "structure"]
    assert [r.direction for r in view.reads] == directions
    assert [r.strength for r in view.reads] == strengths
    assert view.net == pytest.approx(net)
    assert view.agree == (directions.count(1), directions.count(-1))
    pd.testing.assert_frame_equal(df, before)


@pytest.mark.parametrize("highs,lows,direction,strength", [
    ([10, 11], [1, 2], 1, 70), ([11, 10], [2, 1], -1, 70),
    ([10, 11], [2, 1], 0, 30),
])
def test_structure_confirmed_sequences(modules, highs, lows, direction, strength):
    # Slopes between extrema avoid accidental equal-height plateau pivots.
    df = frame(np.interp(np.arange(24), [0, 3, 9, 15, 20, 23],
                         [5, highs[0], lows[0], highs[1], lows[1], 5]))
    r = modules["matrix"].read_structure(df)
    assert (r.direction, r.strength) == (direction, strength)


def test_matrix_golden_mixed_oscillating_prices(modules):
    df = frame([100, 102] * 30)
    view = modules["matrix"].read_frame(df, "15m")
    assert [r.direction for r in view.reads] == [1, -1, 1, 0]
    assert [r.strength for r in view.reads] == [5, 90, 55, 30]
    assert view.net == -10.625
    assert view.agree == (2, 1)
    assert view.label() == "ניטרלי"
    assert view.atr == pytest.approx(3 - (13 / 14) ** 59)
    assert view.basis_note is None


def test_supertrend_fast_flip_keeps_slow_bands_bearish(modules):
    df = frame([100] * 15 + [103])
    result = modules["toolkit"].ladder_state(df)
    assert result["state"] == "pullback"
    assert result["n_bull"] == 1 and result["n_bands"] == 3
    assert [b["line"] for b in result["bands"]] == pytest.approx([100.8, 104, 106])
    assert [b["just_flipped"] for b in result["bands"]] == [True, False, False]
    assert result["bands"][0]["bars_in_trend"] == 1
    read = modules["matrix"].read_supertrend(df)
    assert (read.direction, read.strength) == (0, 16)


def test_source_short_history_nan_and_zero_range_are_preserved(modules):
    matrix = modules["matrix"]
    df = frame([100])
    view = matrix.read_frame(df, "5m")
    assert [r.strength for r in view.reads] == [100, 0, 100, 0]
    assert [r.direction for r in view.reads] == [0, 0, -1, 0]
    assert matrix._bar_ts(df.reset_index(drop=True)) == 0
    df["high"] = df["low"] = 100
    assert matrix._atr(df) == 1e-9
    with pytest.raises(IndexError):
        matrix.read_frame(df.iloc[:0], "5m")


def test_vwap_volume_weighting_zero_fallback_and_utc_day_reset(modules):
    toolkit = modules["toolkit"]
    df = frame([10, 12, 20, 24], start="2026-09-07T23:58Z", volume=[1, 3, 2, 2])
    got = toolkit.vwap_bands(df)
    assert got.vwap.tolist() == [10, 11.5, 20, 22]
    assert got.sigma.tolist() == pytest.approx([0, math.sqrt(0.75), 0, 2])
    assert got.z.iloc[1] == pytest.approx(0.5 / math.sqrt(0.75))
    assert got.upper3.iloc[-1] == 28 and got.lower3.iloc[-1] == 16
    localized = df.tz_convert("Asia/Jerusalem")
    assert toolkit.vwap_bands(localized).vwap.tolist() == got.vwap.tolist()
    for no_vol in (df.assign(volume=0), df.drop(columns="volume")):
        assert toolkit.vwap_bands(no_vol).vwap.tolist() == [10, 11, 20, 22]
    df["volume"] = [0, 1, 0, 0]
    assert toolkit.vwap_bands(df).vwap.isna().tolist() == [True, False, True, True]


def test_seeded_supertrend_atr_is_distinct_from_matrix_atr(modules):
    df = frame([10, 14, 14])
    seeded = modules["indicators"].atr(df, 3)
    assert seeded.isna().tolist() == [True, True, False]
    assert seeded.iloc[-1] == 3
    # Unseeded ranges [2,5,2], alpha 1/14, last = 2 + 3*13/196.
    assert modules["matrix"]._atr(df) == pytest.approx(2 + 39 / 196)
    assert modules["toolkit"].ladder_state(df) == {"available": False}


@pytest.mark.parametrize("up", [True, False])
def test_swing_requires_three_bars_to_right_and_returns_age(modules, up):
    df = frame([5, 4, 3, 1, 3, 4, 5])
    if not up:
        df = frame([5, 6, 7, 9, 7, 6, 5])
    fn = modules["swing"]._last_swing
    assert fn(df.iloc[:-1], up) is None
    assert fn(df, up) == (0.0 if up else 10.0, 3)
    df.iloc[6, df.columns.get_loc("low" if up else "high")] = 0 if up else 10
    assert fn(df, up) == (0.0 if up else 10.0, 3)  # ties qualify in source


@pytest.mark.parametrize("reasons,names,trigger,shadow", [
    ([], [], None, True),
    (["רמה: אין"], [], None, True),
    (["כניסה: Q-WHOLE · ביטול: PSY-HI"], ["Q-WHOLE"], None, False),
    (["כניסה בריטסט ל-Q-QUARTER, לא במחיר השוק"], ["Q-QUARTER"], None, False),
    (["רמה: 3 רמות: D4-HI/PSY-HI/Q-QUARTER"], ["D4-HI", "PSY-HI", "Q-QUARTER"], None, False),
    (["commitment: כן"], [], "commitment", False),
    (["תבנית W מאושרת (סגירה מעבר לצוואר)"], [], "confirmed_W", False),
    (["תבנית W לא מאושרת"], [], None, True),
    (["תבנית W מתגבשת"], [], None, True),
    (["מלכודת: היערך לונג"], [], "trap", False),
])
def test_quality_named_anchors_and_shadow_are_annotations(modules, reasons, names, trigger, shadow):
    result = modules["quality"].evaluate(direction="לונג", entry=100, atr=2, reasons=reasons)
    assert result["anchor_names"] == names
    assert result["aligned_trigger"] == trigger
    assert result["shadow_block"] is shadow
    assert set(result) == {"anchor_names", "aligned_trigger", "aligned_rejection",
                           "opposing_rejection", "labels", "shadow_block", "predicate"}


def test_quality_rejections_are_supplied_not_freshness_filtered_or_vetoes(modules):
    rej = {"zone_lo": 90, "zone_hi": 95, "gap": 5, "age_s": 99999,
           "levels": ["A", "B", "C", "D"]}
    evaluate = modules["quality"].evaluate
    against = evaluate(direction="שורט", entry=100, atr=2, reasons=[], opposing_rejection=rej)
    assert against["shadow_block"] is True
    assert against["opposing_rejection"]["distance_atr"] == 2.5
    assert against["labels"][-1] == "נגד דחייה טרייה מ־90.00–95.00 (A · B · C)"
    broken = evaluate(direction="שורט", entry=89, atr=0, reasons=[], opposing_rejection=rej)
    assert broken["opposing_rejection"] is None
    aligned = evaluate(direction="שורט", entry=100, atr=0, reasons=[], aligned_rejection=rej)
    assert aligned["shadow_block"] is False
    assert aligned["aligned_rejection"]["distance_atr"] is None
