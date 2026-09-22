"""OPEN post-fill evidence is raw and never mutates the supplied trade."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util

import pandas as pd
import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_open_postfill_evidence"
LONG = "\u05dc\u05d5\u05e0\u05d2"
SHORT = "\u05e9\u05d5\u05e8\u05d8"
NOW = datetime(2026, 9, 14, 16, tzinfo=timezone.utc)


def api():
    assert importlib.util.find_spec(MODULE) is not None, "OPEN post-fill evidence module missing"
    return importlib.import_module(MODULE)


class Correction:
    def __init__(self, *, unverified=False, source="tv"):
        self.unverified = unverified
        self.source = source


def tape(rows):
    return pd.DataFrame(
        [{"open": low, "high": high, "low": low, "close": close}
         for offset, low, high, close in rows],
        index=pd.DatetimeIndex([NOW + timedelta(minutes=offset) for offset, *_ in rows], tz="UTC"),
    )


def trade(**changes):
    return {
        "trade_id": "open-postfill-1",
        "state": "OPEN",
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [["TP1", 160.0]],
        "ts": (NOW - timedelta(minutes=30)).timestamp(),
        "filled_ts": (NOW - timedelta(minutes=10)).timestamp(),
    } | changes


class TapePort:
    def __init__(self, response, *, now=NOW):
        self.response = response
        self.now = now
        self.calls = []

    def fetch_corrected(self, symbol, timeframe, days):
        self.calls.append(("fetch_corrected", symbol, timeframe, days))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return self.now.timestamp()

    def now_utc(self):
        self.calls.append(("now_utc",))
        return self.now

    def save(self, *_args):
        pytest.fail("post-fill evidence must not save")

    def transition(self, *_args):
        pytest.fail("post-fill evidence must not transition")

    def outcome(self, *_args):
        pytest.fail("post-fill evidence must not create an outcome")

    def deliver(self, *_args):
        pytest.fail("post-fill evidence must not deliver")


def collect(port, open_trade, spot):
    return api().LifecycleOpenPostfillEvidence(port).collect(open_trade, spot)


def test_safe_located_tape_combines_spot_with_post_fill_extrema_and_returns_minimum_message():
    # Catch a regression that lets the target-side fill-bar high count as the
    # position's earned high, or omits the always-post-fill spot observation.
    open_trade = trade()
    supplied = tape([
        (-10, 99.0, 160.0, 100.0),  # fill bar: adverse low, never earned high
        (-1, 101.0, 145.0, 140.0),
    ])
    port = TapePort((supplied, Correction()))

    low, high, minimum_message = collect(port, open_trade, spot=120.0)

    assert (low, high) == (99.0, 145.0)
    assert isinstance(minimum_message, str) and minimum_message
    assert port.calls[0] == ("fetch_corrected", "OANDA:XAUUSD", "15m", 2)
    assert "minimum_success" not in open_trade


@pytest.mark.parametrize("correction", [Correction(unverified=True), Correction(source="tv_stale")])
def test_unsafe_corrected_tape_returns_spot_only(correction):
    # Catch a regression that treats a rejected correction as a valid
    # post-fill excursion window.
    open_trade = trade(filled_ts=(NOW + timedelta(minutes=1)).timestamp())
    port = TapePort((tape([(-10, 99.0, 160.0, 100.0), (-1, 101.0, 145.0, 140.0)]), correction))

    assert collect(port, open_trade, spot=120.0) == (120.0, 120.0, None)


def test_stale_tape_with_post_fill_history_is_allowed_by_the_accepted_safety_gate():
    # Catch a regression that drops restored post-fill facts solely because
    # their correction source is tv_stale.
    open_trade = trade()
    port = TapePort((tape([(-10, 99.0, 160.0, 100.0), (-1, 101.0, 145.0, 140.0)]), Correction(source="tv_stale")))

    low, high, _minimum_message = collect(port, open_trade, spot=120.0)

    assert (low, high) == (99.0, 145.0)


def test_safe_short_tape_keeps_the_fill_bar_adverse_high_and_post_fill_favourable_low():
    # Catch a regression that reads the long tuple order for a short position.
    open_trade = trade(direction=SHORT, stop=110.0, targets=[["TP1", 40.0]])
    port = TapePort((tape([(-10, 40.0, 101.0, 100.0), (-1, 55.0, 99.0, 60.0)]), Correction()))

    low, high, _minimum_message = collect(port, open_trade, spot=80.0)

    assert (low, high) == (55.0, 101.0)


def test_unlocatable_or_failed_tape_returns_spot_only():
    # Catch a regression that substitutes arbitrary tape extrema when no
    # source fill can be located, or leaks a tape error out of the broad guard.
    unlocatable = tape([(-10, 201.0, 230.0, 220.0), (-1, 202.0, 240.0, 230.0)])

    assert collect(TapePort((unlocatable, Correction())), trade(), spot=120.0) == (120.0, 120.0, None)
    assert collect(TapePort(OSError("tape unavailable")), trade(), spot=120.0) == (120.0, 120.0, None)


def test_evidence_collection_preserves_every_supplied_object_and_invokes_no_effect_ports():
    # Catch a regression that lets DeskSuccess persist proof into the caller's
    # OPEN record, instead of keeping this slice raw evidence only.
    open_trade = trade()
    supplied = tape([(-10, 99.0, 160.0, 100.0), (-1, 101.0, 145.0, 140.0)])
    correction = Correction()
    before_trade = deepcopy(open_trade)
    before_frame = supplied.copy(deep=True)
    before_correction = deepcopy(correction.__dict__)
    port = TapePort((supplied, correction))

    assert collect(port, open_trade, spot=120.0)[:2] == (99.0, 145.0)

    assert open_trade == before_trade
    pd.testing.assert_frame_equal(supplied, before_frame)
    assert correction.__dict__ == before_correction
    assert all(call[0] not in {"save", "transition", "outcome", "deliver"} for call in port.calls)
