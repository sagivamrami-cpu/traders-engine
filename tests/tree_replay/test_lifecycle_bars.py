"""Original position-window semantics, exercised on literal synthetic OHLC."""
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util

import pandas as pd
import pytest


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)


def api():
    name = "trading_system.tree_replay._vendor.lifecycle_bars"
    assert importlib.util.find_spec(name) is not None, "lifecycle geometry missing"
    return importlib.import_module(name)


def tape(rows):
    # (minutes since T, high, low): close/open are inside each literal range.
    return pd.DataFrame([dict(open=lo, high=hi, low=lo, close=hi) for _, hi, lo in rows],
        index=pd.DatetimeIndex([T+timedelta(minutes=m) for m, _, _ in rows]))


def trade(**changes):
    return dict(symbol="OANDA:XAUUSD", direction="לונג", entry=100.,
                state="PENDING", ts=T.timestamp()) | changes


@pytest.mark.parametrize("side,rows,want", [
    ("לונג", [(15, 120, 99), (30, 106, 100)], (106., 99.)),
    ("שורט", [(15, 101, 80), (30, 100, 94)], (101., 94.)),
    ("לונג", [(15, 120, 99)], (100., 99.)),
    ("שורט", [(15, 101, 80)], (101., 100.)),
])
def test_fill_bar_counts_adversely_but_never_as_earned_movement(side, rows, want):
    assert api()._open_extremes(tape(rows), trade(direction=side)) == want


@pytest.mark.parametrize("side,rows,minute", [
    ("לונג", [(-15, 120, 99), (0, 120, 99), (15, 110, 103), (30, 110, 102)], 30),
    ("שורט", [(-15, 101, 80), (0, 101, 80), (15, 97, 90), (30, 98, 90)], 30),
])
def test_touch_uses_source_zone_edges_and_strictly_after_send(side, rows, minute):
    assert api()._fill_on_tape(tape(rows), trade(direction=side)) == pd.Timestamp(T+timedelta(minutes=minute))


@pytest.mark.parametrize("side,rows", [
    ("לונג", [(0, 120, 99), (15, 110, 102.01)]),
    ("שורט", [(0, 101, 80), (15, 97.99, 90)]),
])
def test_no_postsend_touch_returns_none_not_a_position(side, rows):
    b, t = api(), trade(direction=side)
    assert b._fill_on_tape(tape(rows), t) is None
    assert b.position_bars(tape(rows), t) is None
    assert b._open_extremes(tape(rows), t) is None


@pytest.mark.parametrize("include,fill_minute,want_start,first", [
    (False, 15, 15, False), (False, 16, 30, False),
    (True, 15, 15, True), (True, 16, 15, True),
])
def test_open_fill_stamp_and_include_fill_bar_select_distinct_windows(include, fill_minute, want_start, first):
    df = tape([(0, 150, 50), (15, 101, 99), (30, 106, 100)])
    t = trade(state="OPEN", filled_ts=(T+timedelta(minutes=fill_minute)).timestamp())
    got, flag = api().position_bars(df, t, include_fill_bar=include)
    assert got.index[0] == pd.Timestamp(T+timedelta(minutes=want_start)) and flag is first
    assert got.index[-1] == pd.Timestamp(T+timedelta(minutes=30))


def test_open_fill_inside_last_bar_never_falls_back_to_send_extremes():
    t = trade(state="OPEN", filled_ts=(T+timedelta(minutes=16)).timestamp())
    df = tape([(0, 150, 50), (15, 105, 98)])
    got, first = api().position_bars(df, t)
    assert list(got.index) == [pd.Timestamp(T+timedelta(minutes=15))] and first
    assert api()._open_extremes(df, t) == (100., 98.)


def test_open_without_fill_stamp_uses_actual_first_tape_touch():
    df = tape([(15, 110, 103), (30, 109, 101), (45, 108, 102)])
    got, first = api().position_bars(df, trade(state="OPEN"))
    assert got.index[0] == pd.Timestamp(T+timedelta(minutes=30)) and first
    assert api()._open_extremes(df, trade(state="OPEN")) == (108., 101.)


def test_full_life_mode_without_containing_fill_bar_has_no_window():
    df = tape([(15, 109, 100)])
    t = trade(state="OPEN", filled_ts=(T+timedelta(minutes=10)).timestamp())
    assert api().position_bars(df, t, include_fill_bar=True) is None


@pytest.mark.parametrize("side,want", [("לונג", (120., 99.)), ("שורט", (120., 99.))])
def test_window_already_after_fill_earns_its_first_bar(side, want):
    assert api()._position_extremes(tape([(15, 120, 99)]), trade(direction=side), fill_bar_first=False) == want


def test_source_fill_error_catch_and_empty_window_remain_distinct():
    b = api()
    assert b._fill_on_tape(pd.DataFrame(), trade()) is None
    assert b._fill_on_tape(tape([(15, 110, 99)]), {"entry": 100.}) is None
    assert b.position_bars(pd.DataFrame(), trade()) is None
    with pytest.raises(ValueError, match="max"):
        b.position_bars(tape([]), trade(state="OPEN", filled_ts=T.timestamp()))


def test_explicit_source_band_and_unknown_symbol_point_fallback():
    b = api()
    assert b._entry_band(trade()) == (98., 102.)
    assert b._entry_band(trade(symbol="UNKNOWN")) == (100., 100.)
    assert b._entry_band({"entry": "123.5"}) == (123.5, 123.5)
