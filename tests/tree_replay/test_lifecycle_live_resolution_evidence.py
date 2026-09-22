"""Live-resolution evidence over supplied raw ports, never resolver effects."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import importlib.util

import pandas as pd
import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_live_resolution_evidence"
NOW = datetime(2026, 9, 14, 14, tzinfo=timezone.utc).timestamp()


def api():
    assert importlib.util.find_spec(MODULE) is not None, "live-resolution evidence module missing"
    return importlib.import_module(MODULE)


class Correction:
    def __init__(self, *, unverified=False, source="tv"):
        self.unverified = unverified
        self.source = source


def frame(at, *, low=98.0, high=103.0, close=101.0):
    return pd.DataFrame(
        {"open": [100.0], "low": [low], "high": [high], "close": [close]},
        index=pd.DatetimeIndex([at], tz="UTC"),
    )


def active(symbol, state="PENDING"):
    return {"state": state, "symbol": symbol}


class EvidencePort:
    def __init__(self, *, payload=None, corrections=None, quote_error=None, now=NOW):
        self.payload = {} if payload is None else payload
        self.corrections = {} if corrections is None else corrections
        self.quote_error = quote_error
        self.now = now
        self.calls = []

    def quote_payload(self):
        self.calls.append(("quote_payload",))
        if self.quote_error is not None:
            raise self.quote_error
        return self.payload

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return self.now

    def fetch_corrected(self, symbol, timeframe, days):
        self.calls.append(("fetch_corrected", symbol, timeframe, days))
        value = self.corrections[symbol]
        if isinstance(value, Exception):
            raise value
        return value

    def transition(self, *args):
        pytest.fail(f"evidence collector invoked transition: {args!r}")

    def outcome(self, *args):
        pytest.fail(f"evidence collector invoked outcome: {args!r}")

    def check_live(self, *args):
        pytest.fail(f"evidence collector invoked caller: {args!r}")

    def save(self, *args):
        pytest.fail(f"evidence collector invoked persistence: {args!r}")


def collect(port, state):
    return api().LifecycleLiveResolutionEvidence(port).collect(state)


def test_collector_filters_to_pending_and_open_symbols_before_corrected_requests():
    open_bar = frame(datetime.fromtimestamp(NOW - 10.0, tz=timezone.utc), close=111.0)
    port = EvidencePort(
        payload={},
        corrections={
            "PENDING": (open_bar, Correction()),
            "OPEN": (open_bar, Correction()),
        },
    )
    state = {
        "pending": active("PENDING"),
        "open": active("OPEN", "OPEN"),
        "closed": active("CLOSED", "CLOSED"),
        "rejected": active("REJECTED", "REJECTED"),
    }

    prices, extremes = collect(port, state)

    assert prices == {"PENDING": 111.0, "OPEN": 111.0}
    assert extremes == {"PENDING": (98.0, 103.0), "OPEN": (98.0, 103.0)}
    assert {call[1] for call in port.calls if call[0] == "fetch_corrected"} == {"PENDING", "OPEN"}


@pytest.mark.parametrize(("age", "want_fetch"), [(120.0, False), (120.0001, True)])
def test_collector_observes_exact_force_bar_age_boundary(age, want_fetch):
    symbol = "OANDA:XAUUSD"
    port = EvidencePort(
        payload={symbol: {"lp": 100.0, "ts": NOW - age}},
        corrections={symbol: (frame(datetime.fromtimestamp(NOW, tz=timezone.utc), close=101.0), Correction())},
    )

    prices, extremes = collect(port, {"trade": active(symbol)})

    calls = [call for call in port.calls if call[0] == "fetch_corrected"]
    assert bool(calls) is want_fetch
    if want_fetch:
        assert prices == {symbol: 101.0} and extremes == {symbol: (98.0, 103.0)}
    else:
        assert prices == {symbol: 100.0} and extremes == {}


def test_collector_requests_only_source_identity_for_an_absent_price():
    symbol = "OANDA:XAGUSD"
    port = EvidencePort(
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=30.5), Correction())}
    )

    assert collect(port, {"trade": active(symbol)}) == ({symbol: 30.5}, {symbol: (98.0, 103.0)})
    assert [call for call in port.calls if call[0] == "fetch_corrected"] == [
        ("fetch_corrected", symbol, "15m", 2)
    ]


def test_collector_uses_corrected_fallback_when_active_symbol_quote_is_none():
    symbol = "OANDA:XAGUSD"
    port = EvidencePort(
        payload={symbol: None},
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=30.5), Correction())},
    )

    assert collect(port, {"trade": active(symbol)}) == ({symbol: 30.5}, {symbol: (98.0, 103.0)})
    assert [call for call in port.calls if call[0] == "fetch_corrected"] == [
        ("fetch_corrected", symbol, "15m", 2)
    ]


def test_collector_propagates_a_malformed_active_quote_timestamp_before_fallback():
    symbol = "OANDA:XAGUSD"
    port = EvidencePort(payload={symbol: {"lp": 30.0, "ts": "not-a-timestamp"}})

    with pytest.raises(ValueError, match="could not convert string to float"):
        collect(port, {"trade": active(symbol)})

    assert [call for call in port.calls if call[0] == "fetch_corrected"] == []


@pytest.mark.parametrize("corr", [Correction(unverified=True), Correction(source="tv_stale")])
def test_collector_rejects_unverified_or_stale_corrections(corr):
    symbol = "OANDA:XAUUSD"
    port = EvidencePort(
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=101.0), corr)}
    )

    assert collect(port, {"trade": active(symbol)}) == ({}, {})


@pytest.mark.parametrize(("bar_age", "want"), [(300.0, False), (299.999, True)])
def test_collector_requires_strictly_newer_bar_than_raw_quote_timestamp(bar_age, want):
    symbol = "OANDA:XAUUSD"
    port = EvidencePort(
        payload={symbol: {"lp": 100.0, "ts": NOW - 300.0}},
        corrections={
            symbol: (frame(datetime.fromtimestamp(NOW - bar_age, tz=timezone.utc), close=101.0), Correction())
        },
    )

    prices, extremes = collect(port, {"trade": active(symbol)})

    assert prices == {symbol: 101.0 if want else 100.0}
    assert extremes == ({symbol: (98.0, 103.0)} if want else {})


def test_collector_carries_the_winning_forming_bar_low_and_high_with_its_close():
    symbol = "OANDA:XAUUSD"
    port = EvidencePort(
        corrections={
            symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), low=91.25, high=107.75, close=103.5), Correction())
        }
    )

    assert collect(port, {"trade": active(symbol)}) == ({symbol: 103.5}, {symbol: (91.25, 107.75)})


def test_one_fallback_failure_does_not_suppress_a_valid_active_sibling():
    good = "OANDA:XAGUSD"
    port = EvidencePort(
        corrections={
            "BROKEN": ValueError("bad corrected tape"),
            good: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=31.0), Correction()),
        }
    )

    assert collect(port, {"broken": active("BROKEN"), "good": active(good)}) == (
        {good: 31.0}, {good: (98.0, 103.0)}
    )


def test_raw_payload_failure_is_contained_and_missing_quote_can_still_use_supplied_fallback():
    symbol = "OANDA:XAUUSD"
    port = EvidencePort(
        quote_error=OSError("raw quote unavailable"),
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=101.0), Correction())},
    )

    assert collect(port, {"trade": active(symbol)}) == ({symbol: 101.0}, {symbol: (98.0, 103.0)})
    assert port.calls[:3] == [("quote_payload",), ("quote_payload",), ("now_epoch",)]


def test_collector_is_evidence_only_and_mutates_no_supplied_state_frame_or_correction():
    symbol = "OANDA:XAUUSD"
    supplied_frame = frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=101.0)
    corr = Correction()
    state = {"trade": active(symbol)}
    state_before = deepcopy(state)
    frame_before = supplied_frame.copy(deep=True)
    corr_before = deepcopy(corr.__dict__)
    port = EvidencePort(corrections={symbol: (supplied_frame, corr)})

    assert collect(port, state) == ({symbol: 101.0}, {symbol: (98.0, 103.0)})

    assert state == state_before
    pd.testing.assert_frame_equal(supplied_frame, frame_before)
    assert corr.__dict__ == corr_before
    assert all(call[0] not in {"transition", "outcome", "check_live", "save"} for call in port.calls)
