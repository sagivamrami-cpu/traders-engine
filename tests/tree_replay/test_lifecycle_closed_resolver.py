"""Closed-bar resolver composition over caller-owned corrected 15-minute bars."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import importlib.util
import json
from types import SimpleNamespace

import pandas as pd
import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_closed_resolver"
PENDING_MODULE = "trading_system.tree_replay._vendor.lifecycle_closed_pending_resolution"
LONG = "\u05dc\u05d5\u05e0\u05d2"
SHORT = "\u05e9\u05d5\u05e8\u05d8"
NOW = 1_726_500_000.0


def api():
    assert importlib.util.find_spec(MODULE) is not None, "closed resolver runtime missing"
    return importlib.import_module(MODULE)


class OutcomeWriter:
    def __init__(self, source):
        self.source = source

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def write(self, text):
        self.source.outcomes.append(json.loads(text))


class Source:
    """Corrected frames and offline ports; persistence or delivery is forbidden."""

    def __init__(self, frames):
        self.frames = frames
        self.calls = []
        self.outcomes = []

    def fetch_corrected(self, symbol, timeframe, days):
        self.calls.append(("fetch_corrected", symbol, timeframe, days))
        result = self.frames[symbol]
        if isinstance(result, Exception):
            raise result
        return result

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return NOW

    def now_utc(self):
        self.calls.append(("now_utc",))
        return datetime.fromtimestamp(NOW, timezone.utc)

    def outcomes_mkdir(self, path, *, parents, exist_ok):
        self.calls.append(("outcomes_mkdir", path, parents, exist_ok))

    def open_outcomes(self, mode, *, encoding):
        self.calls.append(("open_outcomes", mode, encoding))
        return OutcomeWriter(self)

    def load(self, *_args):
        pytest.fail("closed resolver must use supplied state")

    def save(self, *_args):
        pytest.fail("closed resolver must not persist")

    def gate(self, *_args):
        pytest.fail("closed resolver must not gate")

    def deliver(self, *_args):
        pytest.fail("closed resolver must not deliver")

    def quote_payload(self, *_args):
        pytest.fail("closed resolver must not acquire live quotes")


class Validation:
    def revalidate_pending(self, _trade, *, now):
        assert now == NOW
        return True, "verified", True


def bars(*rows):
    index = [datetime.fromtimestamp(timestamp, timezone.utc) for timestamp, _open, _high, _low in rows]
    return pd.DataFrame(
        {
            "open": [opening for _timestamp, opening, _high, _low in rows],
            "high": [high for _timestamp, _open, high, _low in rows],
            "low": [low for _timestamp, _open, _high, low in rows],
        },
        index=pd.DatetimeIndex(index),
    )


def trade(**changes):
    return {
        "trade_id": "closed-resolver-1",
        "state": "PENDING",
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [["TP1", 110.0]],
        "to_group": True,
        "ts": NOW - 600.0,
        "style": "intraday",
        "hit": [],
    } | changes


def resolve(source, state):
    return api().LifecycleClosedResolver(source).resolve(state, now=NOW)


@pytest.fixture(autouse=True)
def exact_entry_band(monkeypatch):
    bars_module = importlib.import_module("trading_system.tree_replay._vendor.lifecycle_bars")
    monkeypatch.setattr(bars_module, "_entry_band", lambda _trade: (100.0, 100.0))
    pending = importlib.import_module(PENDING_MODULE)
    monkeypatch.setattr(pending, "TreeRevalidation", lambda _source: Validation())


def test_pre_fill_high_cannot_hit_a_long_target_after_a_retest_fill():
    """A source-order regression that feeds post-send high into OPEN pays TP1 early."""
    frame = bars(
        (NOW - 300.0, 105.0, 111.0, 99.0),
        (NOW - 150.0, 100.0, 101.0, 99.0),
    )
    source = Source({"OANDA:XAUUSD": (frame, None)})
    state = {"trade": trade()}

    messages, changed = resolve(source, state)

    assert changed is True
    assert state["trade"]["state"] == "OPEN"
    assert state["trade"]["hit"] == []
    assert "BUY" in messages[0][0]


def test_closed_open_order_is_minimum_then_ambiguity_then_continue():
    """A target-before-protection composition would expose an ordinal target message."""
    frame = bars(
        (NOW - 500.0, 100.0, 100.0, 100.0),
        (NOW - 400.0, 100.0, 105.0, 100.0),
        (NOW - 300.0, 100.0, 110.0, 90.0),
    )
    source = Source({"OANDA:XAUUSD": (frame, None)})
    state = {"trade": trade(state="OPEN", filled_ts=NOW - 450.0)}

    messages, changed = resolve(source, state)

    assert changed is True
    assert state["trade"]["state"] == "STOPPED"
    assert len(messages) == 2
    assert "TP1" not in messages[0][0]
    assert "TP1" not in messages[1][0]
    assert [row["result"] for row in source.outcomes] == [
        "minimum_success", "stopped_ambiguous",
    ]


def test_short_closed_minimum_uses_post_fill_low_for_source_progress_before_protection():
    """A long-side short check suppresses the retained short minimum progress step."""
    frame = bars(
        (NOW - 500.0, 100.0, 100.0, 100.0),
        (NOW - 300.0, 100.0, 100.0, 95.0),
    )
    source = Source({"OANDA:XAUUSD": (frame, None)})
    state = {
        "trade": trade(
            state="OPEN",
            direction=SHORT,
            stop=110.0,
            targets=[["TP1", 90.0]],
            filled_ts=NOW - 400.0,
        )
    }

    messages, changed = resolve(source, state)

    assert changed is True
    assert state["trade"]["state"] == "OPEN"
    assert state["trade"]["progress_step"] == 55
    assert [row["result"] for row in source.outcomes] == ["minimum_success"]
    assert len(messages) == 1


def test_terminal_and_bad_corrected_records_are_skipped_without_blocking_later_records():
    """Removing per-record continue either fetches terminals or stops a later valid record."""
    frame = bars((NOW - 300.0, 100.0, 100.0, 100.0))
    source = Source({
        "terminal": AssertionError("terminal records must not fetch"),
        "unverified": (frame, SimpleNamespace(unverified=True)),
        "stale": (frame, SimpleNamespace(source="tv_stale")),
        "good": (frame, None),
    })
    state = {
        "terminal": trade(symbol="terminal", state="STOPPED"),
        "unverified": trade(symbol="unverified"),
        "stale": trade(symbol="stale"),
        "good": trade(symbol="good", targets=[]),
    }

    messages, changed = resolve(source, state)

    assert changed is True
    assert state["terminal"]["state"] == "STOPPED"
    assert state["unverified"]["state"] == "PENDING"
    assert state["stale"]["state"] == "PENDING"
    assert state["good"]["state"] == "DONE"
    assert [call[1] for call in source.calls if call[0] == "fetch_corrected"] == [
        "unverified", "stale", "good",
    ]
    assert len(messages) == 1


def test_strict_post_send_timestamp_excludes_a_bar_at_the_plan_timestamp():
    """Changing the source's strict cutoff to >= falsely fills the plan."""
    frame = bars((NOW - 600.0, 100.0, 101.0, 99.0))
    source = Source({"OANDA:XAUUSD": (frame, None)})
    state = {"trade": trade()}

    assert resolve(source, state) == ([], False)

    assert state["trade"]["state"] == "PENDING"


def test_closed_open_target_loop_stays_ordinal_and_empty_targets_keep_source_done_semantics():
    """Skipping ordinal target traversal or its zero-target completion changes terminal facts."""
    frame = bars(
        (NOW - 500.0, 100.0, 100.0, 100.0),
        (NOW - 300.0, 100.0, 125.0, 99.0),
    )
    source = Source({"OANDA:XAUUSD": (frame, None)})
    state = {
        "targets": trade(
            state="OPEN", filled_ts=NOW - 400.0,
            targets=[["first", 110.0], ["second", 120.0], ["third", 130.0]],
        ),
        "empty": trade(state="OPEN", filled_ts=NOW - 400.0, targets=[]),
    }

    messages, changed = resolve(source, state)

    assert changed is True
    assert state["targets"]["hit"] == ["TP1", "TP2"]
    assert state["targets"]["state"] == "OPEN"
    assert state["empty"]["state"] == "DONE"
    assert [row["result"] for row in source.outcomes] == ["minimum_success", "tp1", "tp2", "minimum_success"]
    assert sum("TP1" in message for message, _group in messages) == 1
    assert sum("TP2" in message for message, _group in messages) == 1


def test_nonambiguous_closed_protective_touch_runs_after_ordinary_target_attempts():
    """Omitting the ordinary branch leaves an OPEN trade despite a closed protective touch."""
    frame = bars(
        (NOW - 500.0, 100.0, 100.0, 100.0),
        (NOW - 400.0, 100.0, 105.0, 100.0),
        (NOW - 300.0, 100.0, 105.0, 90.0),
    )
    source = Source({"OANDA:XAUUSD": (frame, None)})
    state = {"trade": trade(state="OPEN", filled_ts=NOW - 450.0)}

    messages, changed = resolve(source, state)

    assert changed is True
    assert state["trade"]["state"] == "STOPPED"
    assert [row["result"] for row in source.outcomes] == ["minimum_success", "stopped"]
    assert len(messages) == 2
