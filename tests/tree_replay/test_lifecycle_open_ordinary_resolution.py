"""Ordinary OPEN resolution stays an offline, source-ordered projection."""
from copy import deepcopy
import importlib
import importlib.util
import json

import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_open_ordinary_resolution"
LONG = "לונג"
SHORT = "שורט"
NOW = 1_726_315_240.5


def api():
    assert importlib.util.find_spec(MODULE) is not None, "ordinary OPEN resolver module missing"
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
    """Only the offline clock and raw-outcome ports owned by accepted helpers."""

    def __init__(self):
        self.calls = []
        self.outcomes = []

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return NOW

    def outcomes_mkdir(self, path, *, parents, exist_ok):
        self.calls.append(("outcomes_mkdir", path, parents, exist_ok))

    def open_outcomes(self, mode, *, encoding):
        self.calls.append(("open_outcomes", mode, encoding))
        return OutcomeWriter(self)

    def load(self):
        pytest.fail("ordinary OPEN resolution must not load persistent state")

    def save(self, *_args):
        pytest.fail("ordinary OPEN resolution must not persist")

    def fetch_corrected(self, *_args):
        pytest.fail("ordinary OPEN resolution must not acquire bars")

    def quote_payload(self):
        pytest.fail("ordinary OPEN resolution must not acquire quotes")

    def deliver(self, *_args):
        pytest.fail("ordinary OPEN resolution must not deliver")


@pytest.fixture
def source():
    return Source()


@pytest.fixture
def trade():
    return {
        "trade_id": "open-ordinary-1",
        "state": "OPEN",
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [["TP1", 110.0]],
        "to_group": True,
        "ts": 1_726_300_000.0,
        "hit": [],
    }


def resolve(source, open_trade, *, low, high, minimum_message=None):
    return api().LifecycleOpenOrdinaryResolution(source).resolve(
        open_trade, low=low, high=high, minimum_message=minimum_message,
    )


def outcome_results(source):
    return [row["result"] for row in source.outcomes]


def test_long_target_is_recorded_before_recomputed_protection(source, trade):
    """A target mutation must precede the post-target protective resolution."""
    trade.update(stop=100.0, targets=[["TP1", 110.0], ["TP2", 130.0]])

    messages, changed = resolve(source, trade, low=99.0, high=120.0)

    assert changed is True
    assert trade["hit"] == ["TP1"]
    assert trade["state"] == "DONE"
    assert trade["progress_ts"] == NOW
    assert outcome_results(source) == ["tp1", "be_after_tp"]
    assert len(messages) == 2
    assert "TP1" in messages[0][0]
    assert messages[1][1] is True


def test_short_progress_uses_low_and_stays_silent_when_tp1_is_now_touched(source, trade):
    """TP1 in the short-side low suppresses ladder progress before target handling."""
    trade.update(direction=SHORT, stop=110.0, targets=[["TP1", 90.0]])

    messages, changed = resolve(source, trade, low=90.0, high=105.0)

    assert changed is True
    assert not any("התקדמות מאז הכניסה" in message for message, _ in messages)
    assert trade["hit"] == ["TP1"]
    assert trade["progress_ts"] == NOW
    assert outcome_results(source) == ["tp1"]


def test_no_touch_leaves_trade_and_offline_ports_unchanged(source, trade):
    """Removing all source effects must return a clean unchanged result."""
    before = deepcopy(trade)

    assert resolve(source, trade, low=100.0, high=100.0) == ([], False)

    assert trade == before
    assert source.calls == []
    assert source.outcomes == []


def test_minimum_message_suppresses_progress_without_creating_an_outcome(source, trade):
    """The already-observed minimum success blocks progress but is not replayed here."""
    before = deepcopy(trade)

    assert resolve(source, trade, low=100.0, high=101.0, minimum_message="minimum") == ([], False)

    assert trade == before
    assert source.calls == []
    assert source.outcomes == []


def test_multiple_targets_are_recorded_in_ordinal_order_with_source_clock(source, trade):
    """The target loop must not skip TP1 or reorder facts when one high crosses two targets."""
    trade.update(targets=[["TP1", 110.0], ["TP2", 120.0], ["TP3", 130.0]])

    messages, changed = resolve(source, trade, low=100.0, high=125.0)

    assert changed is True
    assert trade["hit"] == ["TP1", "TP2"]
    assert trade["state"] == "OPEN"
    assert trade["progress_ts"] == NOW
    assert [message.splitlines()[0] for message, _ in messages] == [
        "✅ XAUUSD BUY 100.00 · TP1 הושג @ 110.00",
        "✅ XAUUSD BUY 100.00 · TP2 הושג @ 120.00",
    ]
    assert outcome_results(source) == ["tp1", "tp2"]


def test_empty_targets_preserve_source_done_behavior(source, trade):
    """The source closes a target-less record because zero hits satisfy zero targets."""
    trade["targets"] = []

    assert resolve(source, trade, low=100.0, high=100.0) == ([], True)

    assert trade["state"] == "DONE"
    assert trade["resolved_ts"] == NOW
    assert source.outcomes == []


def test_swapping_physical_low_and_high_prevents_long_target_and_protective_effects(source, trade):
    """A reversed physical window must not be interpreted as both directional touches."""
    trade.update(stop=100.0, targets=[["TP1", 110.0], ["TP2", 130.0]])
    before = deepcopy(trade)

    assert resolve(source, trade, low=120.0, high=99.0) == ([], False)

    assert trade == before
    assert source.calls == []
    assert source.outcomes == []
