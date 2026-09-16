"""Pinned live-evidence helpers over supplied quote and bar artifacts only."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import importlib.util

import pandas as pd
import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_live_evidence"
NOW = datetime(2026, 9, 14, 12, tzinfo=timezone.utc).timestamp()


def api():
    assert importlib.util.find_spec(MODULE) is not None, "lifecycle live-evidence module missing"
    return importlib.import_module(MODULE)


class RawEvidence:
    """The complete raw boundary: detached quotes and a supplied operation clock."""

    def __init__(self, payload=None, now=NOW, quote_error=None):
        self.payload = {} if payload is None else payload
        self.now = now
        self.quote_error = quote_error
        self.calls = []

    def quote_payload(self):
        self.calls.append(("quote_payload",))
        if self.quote_error is not None:
            raise self.quote_error
        return self.payload

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return self.now


class Correction:
    def __init__(self, *, unverified=False):
        self.unverified = unverified


def open_trade(**changes):
    return {
        "state": "OPEN", "ts": NOW - 60.0, "filled_ts": NOW - 50.0,
        "symbol": "OANDA:XAUUSD", "entry": 100.0, "stop": 90.0,
        "targets": [["TP1", 110.0]], "hit": [],
    } | changes


def bars(at):
    return pd.DataFrame(
        {"open": [100.0], "high": [101.0], "low": [99.0], "close": [100.5]},
        index=pd.DatetimeIndex([at], tz="UTC"),
    )


@pytest.mark.parametrize(("quote_ts", "want"), [
    (NOW, {"ZERO": 10.0}),
    (NOW - 420.0, {"CEILING": 11.0}),
    (NOW - 420.0001, {}),
    (NOW + 0.0001, {}),
])
def test_live_prices_accepts_exact_source_age_window_and_uses_raw_operation_clock(quote_ts, want):
    symbol = next(iter(want), "OLD")
    raw = RawEvidence({symbol: {"lp": 10.0 if symbol != "CEILING" else 11.0, "ts": quote_ts}})

    assert api().LifecycleLiveEvidence(raw)._live_prices() == want

    assert raw.calls == [("quote_payload",), ("now_epoch",)]


def test_live_prices_skips_nonfinite_and_malformed_rows_without_losing_fresh_sibling():
    raw = RawEvidence({
        "GOOD": {"lp": "101.25", "ts": NOW - 1.0},
        "NAN": {"lp": "nan", "ts": NOW - 1.0},
        "INF": {"lp": "inf", "ts": NOW - 1.0},
        "ZERO": {"lp": 0, "ts": NOW - 1.0},
        "BROKEN": None,
    })

    assert api().LifecycleLiveEvidence(raw)._live_prices() == {"GOOD": 101.25}
    assert raw.calls == [("quote_payload",), ("now_epoch",)]


def test_live_prices_returns_empty_when_raw_quote_payload_cannot_be_read_before_clock():
    raw = RawEvidence(quote_error=RuntimeError("quotes unavailable"))

    assert api().LifecycleLiveEvidence(raw)._live_prices() == {}
    assert raw.calls == [("quote_payload",)]


def test_historical_replay_safety_is_open_only_and_accepts_post_fill_timestamp():
    raw = RawEvidence()
    helper = api().LifecycleLiveEvidence(raw)
    frame = bars(datetime.fromtimestamp(NOW - 49.0, tz=timezone.utc))

    assert helper._historical_replay_safe(frame, Correction(), open_trade()) is True
    assert helper._historical_replay_safe(frame, Correction(), open_trade(state="PENDING")) is False
    assert raw.calls == []


@pytest.mark.parametrize(("frame", "corr", "trade_changes"), [
    (None, None, {}),
    (pd.DataFrame(), None, {}),
    (bars(datetime.fromtimestamp(NOW - 49.0, tz=timezone.utc)), Correction(unverified=True), {}),
    (bars(datetime.fromtimestamp(NOW - 51.0, tz=timezone.utc)), None, {}),
    (bars(datetime.fromtimestamp(NOW - 49.0, tz=timezone.utc)), None, {"filled_ts": 0.0, "ts": NOW - 48.0}),
    (pd.DataFrame({"close": [1.0]}, index=["not-a-timestamp"]), None, {}),
    (bars(datetime.fromtimestamp(NOW - 49.0, tz=timezone.utc)), None, {"filled_ts": None, "ts": None}),
])
def test_historical_replay_safety_rejects_missing_unverified_pre_fill_or_unparseable_evidence(frame, corr, trade_changes):
    assert api().LifecycleLiveEvidence(RawEvidence())._historical_replay_safe(
        frame, corr, open_trade(**trade_changes)
    ) is False


def test_historical_replay_safety_uses_persisted_ts_when_filled_timestamp_is_absent():
    frame = bars(datetime.fromtimestamp(NOW - 10.0, tz=timezone.utc))
    trade = open_trade(filled_ts=0.0, ts=NOW - 11.0)

    assert api().LifecycleLiveEvidence(RawEvidence())._historical_replay_safe(frame, None, trade) is True


def test_historical_replay_safety_is_evidence_only_and_changes_no_trade_bar_or_correction_data():
    helper = api().LifecycleLiveEvidence(RawEvidence())
    frame = bars(datetime.fromtimestamp(NOW - 49.0, tz=timezone.utc))
    corr = Correction()
    trade = open_trade(state="PENDING")
    original_frame = frame.copy(deep=True)
    original_trade = deepcopy(trade)
    original_corr = deepcopy(corr.__dict__)

    assert helper._historical_replay_safe(frame, corr, trade) is False

    pd.testing.assert_frame_equal(frame, original_frame)
    assert trade == original_trade
    assert corr.__dict__ == original_corr
    assert "label" not in trade and "filled_ts" in trade


def test_live_evidence_exposes_force_bar_age_without_fetching_or_resolver_behavior():
    helper = api().LifecycleLiveEvidence(RawEvidence())

    assert helper.FORCE_BAR_AGE_S == 120.0
    assert helper.QUOTE_MAX_AGE_S == 420.0

