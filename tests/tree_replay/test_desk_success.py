"""Original movement proof is identity-bound and never changes economic state."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util

import pandas as pd
import pytest

from trading_system.tree_replay.clock import ReplayClock


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
NOW = T+timedelta(minutes=45)


def api():
    name = "trading_system.tree_replay._vendor.desk_success"
    assert importlib.util.find_spec(name) is not None, "desk movement source missing"
    return importlib.import_module(name)


class ClockPorts:
    def __init__(self, at=NOW):
        self.clock = ReplayClock(at)

    def now_epoch(self):
        return self.clock.now.timestamp()

    def now_utc(self):
        return self.clock.now


def engine(at=NOW):
    return api().DeskSuccess(ClockPorts(at))


def trade(**changes):
    return dict(symbol="OANDA:XAUUSD", direction="לונג", trade_id="trade-one",
        ts=T.timestamp(), entry=100., stop=90., targets=[("TP1", 120.)],
        state="OPEN", filled_ts=(T+timedelta(minutes=15)).timestamp()) | changes


def tape(rows):
    return pd.DataFrame([dict(open=lo, high=hi, low=lo, close=hi) for _, hi, lo in rows],
        index=pd.DatetimeIndex([T+timedelta(minutes=m) for m, _, _ in rows]))


def proof(**changes):
    return dict(version="desk-minimum-2026-09-07", trade_id="trade-one",
        trade_ts=T.timestamp(), symbol="OANDA:XAUUSD", minimum_points=4., price=104.,
        observed_price=105., observed_ts=NOW.timestamp(), detected_ts=NOW.timestamp(),
        source="exact_venue_quote") | changes


@pytest.mark.parametrize("symbol,entry,price,stop,target,points,firstline", [
    ("OANDA:XAUUSD", 100., 104., 90., 120., 4., "📈 XAUUSD BUY 100.00 · הושג הסף המינימלי · +40 פיפס"),
    ("OANDA:NAS100USD", 1000., 1070., 900., 1200., 70., "📈 NAS100USD BUY 1,000.00 · הושג הסף המינימלי · +70 נק'"),
    ("BINANCE:BTCUSDT", 1000., 1200., 500., 1500., 200., "📈 BTCUSDT BUY 1,000.00 · הושג הסף המינימלי · +200 נק'"),
])
def test_literal_instrument_floors_and_original_identity_first_units(symbol, entry, price, stop, target, points, firstline):
    t = trade(symbol=symbol, entry=entry, stop=stop, targets=[("TP1", target)])
    prior = deepcopy(t)
    e = engine()
    message = e.observe(t, price, NOW.timestamp(), "exact_venue_quote")
    assert message.splitlines()[0] == firstline
    assert t["minimum_success"]["minimum_points"] == points
    assert t["minimum_success"]["price"] == price
    assert {k: v for k, v in t.items() if k != "minimum_success"} == prior
    assert e.reached(t) and e.classification(t) == "success"


def test_mirror_short_records_threshold_not_best_price_and_remains_open():
    e, t = engine(), trade(direction="שורט", stop=110., targets=[("TP1", 80.)])
    message = e.observe(t, 95., NOW.timestamp(), "exact_venue_quote")
    assert message.startswith("📈 XAUUSD SELL 100.00 · הושג הסף המינימלי · +40 פיפס")
    assert t["minimum_success"]["price"] == 96. and t["minimum_success"]["observed_price"] == 95.
    assert t["state"] == "OPEN" and t["stop"] == 110.


@pytest.mark.parametrize("field,value", [
    ("version", "old"), ("trade_id", "different"), ("trade_ts", T.timestamp()-1),
    ("symbol", "GC"), ("minimum_points", 5.), ("source", "unverified_quote"),
    ("observed_ts", T.timestamp()-1), ("observed_ts", NOW.timestamp()+1),
    ("price", float("nan")), ("price", float("inf")), ("price", 0.), ("price", 103.99),
])
def test_proof_identity_chronology_source_and_actual_movement_are_checked(field, value):
    assert engine().reached(trade(minimum_success=proof(**{field: value}))) is False


def test_proof_time_boundaries_explicit_asof_and_resolved_horizon():
    e = engine()
    t = trade(minimum_success=proof(observed_ts=T.timestamp()))
    assert e.reached(t, as_of=T.timestamp())
    t["minimum_success"] = proof()
    assert not e.reached(t, as_of=NOW.timestamp()-1)
    assert e.reached(t, as_of=NOW.timestamp())
    t["resolved_ts"] = NOW.timestamp()-1
    assert not e.reached(t)
    t["resolved_ts"] = NOW.timestamp()
    assert e.reached(t)


@pytest.mark.parametrize("change,price,observed,source", [
    (dict(symbol="GC"), 104., NOW.timestamp(), "exact_venue_quote"),
    (dict(trade_id=""), 104., NOW.timestamp(), "exact_venue_quote"),
    (dict(state="PENDING"), 104., NOW.timestamp(), "exact_venue_quote"),
    (dict(targets=[("TP1", 103.)]), 104., NOW.timestamp(), "exact_venue_quote"),
    ({}, 103.99, NOW.timestamp(), "exact_venue_quote"),
    ({}, 104., NOW.timestamp()+1, "exact_venue_quote"),
    ({}, 104., T.timestamp()-1, "exact_venue_quote"),
    ({}, 104., NOW.timestamp(), "invented_source"),
    ({}, float("inf"), NOW.timestamp(), "exact_venue_quote"),
    ({}, 104., float("nan"), "exact_venue_quote"),
])
def test_invalid_new_observation_cannot_mutate_trade(change, price, observed, source):
    e, t = engine(), trade(**change)
    prior = deepcopy(t)
    assert e.observe(t, price, observed, source) is None
    assert t == prior


def test_sticky_valid_proof_survives_later_stop_but_does_not_reemit_success():
    e, t = engine(), trade(minimum_success=proof())
    prior = deepcopy(t["minimum_success"])
    assert e.observe(t, 110., NOW.timestamp(), "exact_venue_quote") is None
    assert t["minimum_success"] == prior
    t.update(state="STOPPED", resolved_ts=NOW.timestamp()+1)
    assert e.classification(t) == "success"
    assert e.stop_note(t) == "\nניתן היה לקדם סטופ לכניסה לאחר 40 פיפס."
    assert t["stop"] == 90.  # Source note is advice, not an economic stop update.


@pytest.mark.parametrize("rows,want", [
    ([(15, 120, 99)], False),
    ([(15, 120, 99), (30, 103.99, 100)], False),
    ([(15, 120, 99), (30, 104, 100)], True),
    ([(15, 120, 90), (30, 104, 100)], False),
    ([(15, 120, 99), (30, 104, 90)], False),
    ([(15, 120, 99), (30, 103, 90), (45, 104, 100)], False),
    ([(15, 120, 99), (30, 104, 100), (45, 105, 90)], True),
    ([(15, 120, 99), (60, 104, 100)], False),
])
def test_real_bar_consumer_excludes_fill_bar_stop_bar_and_future_rows(rows, want):
    e, t = engine(), trade()
    message = e.observe_bars(t, tape(rows))
    assert bool(message) is want
    assert ("minimum_success" in t) is want
    if want:
        assert t["minimum_success"] == proof(source="verified_post_fill_bars", observed_price=104.)
        assert t["minimum_success"]["observed_ts"] == NOW.timestamp()  # not the 16:30 bar stamp.
    assert t["state"] == "OPEN" and t["stop"] == 90.


def test_short_bar_threshold_and_stop_order_are_mirrored():
    e = engine()
    t = trade(direction="שורט", stop=110., targets=[("TP1", 80.)])
    assert e.observe_bars(t, tape([(15, 101, 80), (30, 100, 96)]))
    assert t["minimum_success"]["price"] == 96.
    fresh = trade(direction="שורט", stop=110., targets=[("TP1", 80.)])
    assert e.observe_bars(fresh, tape([(15, 101, 80), (30, 110, 96)])) is None


def test_future_row_cutoff_uses_exact_datetime_not_float_rounded_epoch():
    at = NOW.replace(microsecond=123456)
    df = tape([(15, 120, 99), (30, 104, 100)])
    df.index = pd.DatetimeIndex([T+timedelta(minutes=15), at+timedelta(microseconds=1)])
    e, t = engine(at), trade()
    assert e.observe_bars(t, df) is None
    e.source.clock.advance_to(at+timedelta(microseconds=1))
    assert e.observe_bars(t, df)


@pytest.mark.parametrize("state,measurement,want", [
    ("OPEN", None, "open"), ("PENDING", None, "not_entered"), ("CANCELLED", None, "not_entered"),
    ("STOPPED", None, "unknown"), ("DONE", None, "unknown"), ("OTHER", None, "other"),
    ("STOPPED", {"peak": 3.}, "loss"), ("DONE", {"peak": 3.}, "below_floor"),
    ("STOPPED", {"peak": 4.}, "success"),
    ("STOPPED", {"peak": 3., "threshold_ambiguous": True}, "unknown"),
])
def test_classification_is_source_movement_status_not_automatic_profit_label(state, measurement, want):
    assert engine().classification(trade(state=state), measurement) == want


def test_missing_or_empty_tape_does_not_create_proof_or_advice():
    e, t = engine(), trade()
    assert e.observe_bars(t, None) is None
    assert e.observe_bars(t, pd.DataFrame()) is None
    assert e.stop_note(t) == "" and not e.reached(t)


@pytest.mark.parametrize("method,args,want", [
    ("head", ("▶️", "OANDA:XAUUSD", "שורט", 4373.35, "נכנסה"), "▶️ XAUUSD SELL 4,373.35 · נכנסה"),
    ("moved_from_entry", ("OANDA:XAUUSD", "שורט", 100., 99.), "+10 פיפס"),
    ("moved_from_entry", ("OANDA:XAUUSD", "לונג", 100., 100.01), "בכניסה"),
    ("widen_line", ("OANDA:XAUUSD", "הורחב ל-8 מקצה הטווח"), "הסטופ הורחב ל-80 פיפס מקצה האזור"),
    ("widen_line", ("OANDA:XAUUSD", "ללא הרחבה"), None),
    ("rung_points", (100., .2, 3), .6),
])
def test_real_voice_identity_units_and_management_geometry(method, args, want):
    name = "trading_system.tree_replay._vendor.lifecycle_voice"
    assert importlib.util.find_spec(name) is not None, "lifecycle voice missing"
    got = getattr(importlib.import_module(name), method)(*args)
    assert got == (pytest.approx(want) if type(want) is float else want)
