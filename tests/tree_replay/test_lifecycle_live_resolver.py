"""Focused runtime coverage for the source-ordered live resolver kernel."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import importlib.util

import pandas as pd
import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_live_resolver"
NOW = datetime(2026, 9, 14, 14, tzinfo=timezone.utc).timestamp()
LONG = "לונג"


def api():
    assert importlib.util.find_spec(MODULE) is not None, "live resolver module missing"
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


class OfflineSource:
    """Explicit in-memory ports; quote payloads model the two source reads."""

    def __init__(self, *, payloads=None, corrections=None, now=NOW):
        self.payloads = list(payloads or [{}, {}])
        self.corrections = {} if corrections is None else corrections
        self.now = now
        self.calls = []

    def quote_payload(self):
        self.calls.append(("quote_payload",))
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return self.now

    def fetch_corrected(self, symbol, timeframe, days):
        self.calls.append(("fetch_corrected", symbol, timeframe, days))
        value = self.corrections[symbol]
        if isinstance(value, Exception):
            raise value
        return value

    def load(self):
        pytest.fail("live resolver must use supplied state")

    def save(self, *_args):
        pytest.fail("live resolver must not persist")

    def locked(self, *_args):
        pytest.fail("live resolver must not lock")

    def gate(self, *_args):
        pytest.fail("live resolver must not gate")

    def deliver(self, *_args):
        pytest.fail("live resolver must not deliver")


def trade(symbol, state="OPEN", **changes):
    return {
        "symbol": symbol,
        "state": state,
        "direction": LONG,
        "to_group": True,
    } | changes


def install_children(monkeypatch, module, calls, *, pending=None, postfill=None,
                     minimum=None, protection=None, ordinary=None, zone=None):
    """Replace children only to expose the resolver's composition boundary."""
    pending = pending or (lambda *_args, **_kwargs: ([], False))
    postfill = postfill or (lambda *_args, **_kwargs: (100.0, 100.0, None))
    minimum = minimum or (lambda *_args, **_kwargs: ([], False, None))
    protection = protection or (lambda *_args, **_kwargs: ([], False))
    ordinary = ordinary or (lambda *_args, **_kwargs: ([], False))
    zone = zone or (lambda *_args, **_kwargs: ([], False))

    class Pending:
        def resolve(self, *args, **kwargs):
            calls.append(("pending", args, kwargs))
            return pending(*args, **kwargs)

    class Postfill:
        def collect(self, *args, **kwargs):
            calls.append(("postfill", args, kwargs))
            return postfill(*args, **kwargs)

    class Minimum:
        def resolve(self, *args, **kwargs):
            calls.append(("minimum", args, kwargs))
            return minimum(*args, **kwargs)

    class Protection:
        def resolve(self, *args, **kwargs):
            calls.append(("protection", args, kwargs))
            return protection(*args, **kwargs)

    class Ordinary:
        def resolve(self, *args, **kwargs):
            calls.append(("ordinary", args, kwargs))
            return ordinary(*args, **kwargs)

    class Zone:
        def resolve(self, *args, **kwargs):
            calls.append(("zone", args, kwargs))
            return zone(*args, **kwargs)

    monkeypatch.setattr(module, "LifecyclePendingResolution", lambda _source: Pending())
    monkeypatch.setattr(module, "LifecycleOpenPostfillEvidence", lambda _source: Postfill())
    monkeypatch.setattr(module, "LifecycleOpenMinimumSuccess", lambda _source: Minimum())
    monkeypatch.setattr(module, "LifecycleOpenProtection", lambda _source: Protection())
    monkeypatch.setattr(module, "LifecycleOpenOrdinaryResolution", lambda _source: Ordinary())
    monkeypatch.setattr(module, "LifecycleOpenZoneReturn", lambda _source: Zone())


def resolve(source, state):
    return api().LifecycleLiveResolver(source).resolve(state)


def test_snapshot_reads_quotes_twice_carries_newer_corrected_range_and_forwards_raw_quote(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    raw_quote = {"lp": 100.0, "ts": NOW - 121.0, "marker": "second-read"}
    source = OfflineSource(
        payloads=[{symbol: {"lp": 100.0, "ts": NOW - 121.0}}, {symbol: raw_quote}],
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), low=91.0, high=108.0, close=104.0), Correction())},
    )
    calls = []
    install_children(
        monkeypatch, module, calls,
        postfill=lambda *_args, **_kwargs: (93.0, 106.0, "bar-minimum"),
        minimum=lambda *_args, **_kwargs: ([("minimum", True)], True, "actual-minimum"),
    )
    state = {"open": trade(symbol)}

    messages, changed = module.LifecycleLiveResolver(source).resolve(state)

    assert messages == [("minimum", True)] and changed is True
    assert [call for call in source.calls if call[0] == "quote_payload"] == [
        ("quote_payload",), ("quote_payload",)
    ]
    assert [call for call in source.calls if call[0] == "fetch_corrected"] == [
        ("fetch_corrected", symbol, "15m", 2)
    ]
    minimum_call = next(call for call in calls if call[0] == "minimum")
    assert minimum_call[2]["quote"] == raw_quote
    assert minimum_call[2]["has_bar_extremes"] is True
    assert minimum_call[2]["spot"] == 104.0


def test_fallback_wick_reaches_pending_as_the_real_low_high_pair(monkeypatch):
    module = api()
    symbol = "OANDA:XAGUSD"
    source = OfflineSource(
        payloads=[{symbol: {"lp": 30.0, "ts": NOW - 121.0}}, {symbol: {"lp": 30.0, "ts": NOW - 121.0}}],
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), low=28.25, high=31.75, close=30.5), Correction())},
    )
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({"pending": trade(symbol, "PENDING")}) == ([], False)

    pending_call = next(call for call in calls if call[0] == "pending")
    assert pending_call[2]["price"] == 30.5
    assert pending_call[2]["bar_extremes"] == {symbol: (28.25, 31.75)}


@pytest.mark.parametrize("correction", [Correction(unverified=True), Correction(source="tv_stale")])
def test_rejected_correction_cannot_price_an_active_record(monkeypatch, correction):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=101.0), correction)}
    )
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({"pending": trade(symbol, "PENDING")}) == ([], False)

    assert calls == []
    assert [call for call in source.calls if call[0] == "fetch_corrected"] == [
        ("fetch_corrected", symbol, "15m", 2)
    ]


def test_exact_force_bar_age_keeps_fresh_quote_without_a_corrected_request(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    quote = {"lp": 100.0, "ts": NOW - 120.0}
    source = OfflineSource(
        payloads=[{symbol: quote}, {symbol: quote}],
        corrections={symbol: pytest.fail},
    )
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({"pending": trade(symbol, "PENDING")}) == ([], False)

    pending_call = next(call for call in calls if call[0] == "pending")
    assert pending_call[2]["price"] == 100.0
    assert pending_call[2]["bar_extremes"] == {}
    assert not [call for call in source.calls if call[0] == "fetch_corrected"]


@pytest.mark.parametrize(
    ("bar_age", "expected_price", "expected_extremes"),
    [
        (300.0, 100.0, {}),
        (299.999, 101.0, {"OANDA:XAUUSD": (98.0, 103.0)}),
    ],
)
def test_corrected_close_replaces_quote_only_when_strictly_newer(monkeypatch, bar_age, expected_price, expected_extremes):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(
        payloads=[{symbol: {"lp": 100.0, "ts": NOW - 300.0}}, {symbol: {"lp": 100.0, "ts": NOW - 300.0}}],
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - bar_age, tz=timezone.utc), close=101.0), Correction())},
    )
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({"pending": trade(symbol, "PENDING")}) == ([], False)

    pending_call = next(call for call in calls if call[0] == "pending")
    assert pending_call[2]["price"] == expected_price
    assert pending_call[2]["bar_extremes"] == expected_extremes


def test_one_failed_fallback_does_not_suppress_a_fallback_priced_sibling(monkeypatch):
    module = api()
    broken = "OANDA:BROKEN"
    good = "OANDA:XAGUSD"
    source = OfflineSource(
        corrections={
            broken: OSError("broken corrected tape"),
            good: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), low=29.0, high=32.0, close=31.0), Correction()),
        }
    )
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({
        "broken": trade(broken, "PENDING"),
        "good": trade(good, "PENDING"),
    }) == ([], False)

    pending_call = next(call for call in calls if call[0] == "pending")
    assert pending_call[1][0]["symbol"] == good
    assert pending_call[2]["price"] == 31.0
    assert pending_call[2]["bar_extremes"] == {good: (29.0, 32.0)}
    assert {call[1] for call in source.calls if call[0] == "fetch_corrected"} == {broken, good}


def test_second_raw_quote_failure_uses_empty_quote_and_continues_with_fallback_price(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(
        payloads=[{symbol: {"lp": 100.0, "ts": NOW - 121.0}}, OSError("raw snapshot unavailable")],
        corrections={symbol: (frame(datetime.fromtimestamp(NOW - 1.0, tz=timezone.utc), close=101.0), Correction())},
    )
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({"open": trade(symbol)}) == ([], False)

    assert [call for call in source.calls if call[0] == "quote_payload"] == [
        ("quote_payload",), ("quote_payload",)
    ]
    minimum_call = next(call for call in calls if call[0] == "minimum")
    assert minimum_call[2]["quote"] == {}
    assert minimum_call[2]["spot"] == 101.0


def test_no_prices_returns_without_running_children_after_two_quote_observations(monkeypatch):
    module = api()
    source = OfflineSource(payloads=[{}, {}])
    calls = []
    install_children(monkeypatch, module, calls)

    assert module.LifecycleLiveResolver(source).resolve({"open": trade("OANDA:XAUUSD")}) == ([], False)

    assert calls == []
    assert [call for call in source.calls if call[0] == "quote_payload"] == [
        ("quote_payload",), ("quote_payload",)
    ]


def test_scan_skips_terminal_and_missing_price_records_and_leaves_pending_no_touch(monkeypatch):
    module = api()
    active = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{active: {"lp": 100.0, "ts": NOW}}, {active: {"lp": 100.0, "ts": NOW}}])
    calls = []
    install_children(monkeypatch, module, calls)
    state = {
        "stopped": trade("STOPPED", "STOPPED"),
        "done": trade("DONE", "DONE"),
        "cancelled": trade("CANCELLED", "CANCELLED"),
        "missing": trade("MISSING"),
        "pending": trade(active, "PENDING"),
    }

    assert module.LifecycleLiveResolver(source).resolve(state) == ([], False)

    assert [call[0] for call in calls] == ["pending"]
    assert state["pending"]["state"] == "PENDING"


def test_pending_cancellation_is_terminal_for_the_current_pass(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{symbol: {"lp": 100.0, "ts": NOW}}, {symbol: {"lp": 100.0, "ts": NOW}}])
    calls = []

    def cancel(record, **_kwargs):
        record["state"] = "CANCELLED"
        return [("cancel", True)], True

    install_children(monkeypatch, module, calls, pending=cancel)
    state = {"pending": trade(symbol, "PENDING")}

    assert module.LifecycleLiveResolver(source).resolve(state) == ([("cancel", True)], True)

    assert state["pending"]["state"] == "CANCELLED"
    assert [call[0] for call in calls] == ["pending"]


def test_pending_fill_falls_through_to_open_children_in_the_same_pass(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{symbol: {"lp": 100.0, "ts": NOW}}, {symbol: {"lp": 100.0, "ts": NOW}}])
    calls = []

    def fill(record, **_kwargs):
        record["state"] = "OPEN"
        return [("fill", True)], True

    install_children(monkeypatch, module, calls, pending=fill)
    state = {"pending": trade(symbol, "PENDING")}

    assert module.LifecycleLiveResolver(source).resolve(state) == ([("fill", True)], True)

    assert [call[0] for call in calls] == ["pending", "postfill", "minimum", "protection", "ordinary", "zone"]


def test_open_order_passes_actual_minimum_message_to_ordinary_after_protection(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{symbol: {"lp": 100.0, "ts": NOW}}, {symbol: {"lp": 100.0, "ts": NOW}}])
    calls = []
    install_children(
        monkeypatch, module, calls,
        postfill=lambda *_args, **_kwargs: (95.0, 105.0, "provisional"),
        minimum=lambda *_args, **_kwargs: ([("minimum", True)], True, "actual"),
    )

    messages, changed = module.LifecycleLiveResolver(source).resolve({"open": trade(symbol)})

    assert messages == [("minimum", True)] and changed is True
    assert [call[0] for call in calls] == ["postfill", "minimum", "protection", "ordinary", "zone"]
    ordinary_call = next(call for call in calls if call[0] == "ordinary")
    assert ordinary_call[2]["minimum_message"] == "actual"


def test_ambiguity_message_continues_without_ordinary_or_zone_return(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{symbol: {"lp": 100.0, "ts": NOW}}, {symbol: {"lp": 100.0, "ts": NOW}}])
    calls = []
    install_children(monkeypatch, module, calls, protection=lambda *_args, **_kwargs: ([("ambiguous", False)], True))

    assert module.LifecycleLiveResolver(source).resolve({"open": trade(symbol)}) == ([("ambiguous", False)], True)

    assert [call[0] for call in calls] == ["postfill", "minimum", "protection"]


def test_ordinary_terminal_state_suppresses_zone_return(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{symbol: {"lp": 100.0, "ts": NOW}}, {symbol: {"lp": 100.0, "ts": NOW}}])
    calls = []

    def terminal(record, **_kwargs):
        record["state"] = "DONE"
        return [("target", True)], True

    install_children(monkeypatch, module, calls, ordinary=terminal)

    assert module.LifecycleLiveResolver(source).resolve({"open": trade(symbol)}) == ([("target", True)], True)

    assert [call[0] for call in calls] == ["postfill", "minimum", "protection", "ordinary"]


def test_unchanged_open_reaches_zone_return_after_ordinary(monkeypatch):
    module = api()
    symbol = "OANDA:XAUUSD"
    source = OfflineSource(payloads=[{symbol: {"lp": 100.0, "ts": NOW}}, {symbol: {"lp": 100.0, "ts": NOW}}])
    calls = []
    install_children(monkeypatch, module, calls, zone=lambda *_args, **_kwargs: ([("zone", True)], True))

    assert module.LifecycleLiveResolver(source).resolve({"open": trade(symbol)}) == ([("zone", True)], True)

    assert [call[0] for call in calls] == ["postfill", "minimum", "protection", "ordinary", "zone"]
