"""OPEN ambiguity protection is a supplied-window, offline lifecycle slice."""
from __future__ import annotations

from copy import deepcopy
import importlib
import importlib.util
import json

import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_open_protection"
LONG = "לונג"
SHORT = "שורט"
NOW = 1_726_315_240.5


def api():
    assert importlib.util.find_spec(MODULE) is not None, "OPEN protection module missing"
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
    def __init__(self, *, now=NOW):
        self.now = now
        self.calls = []
        self.outcomes = []

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return self.now

    def outcomes_mkdir(self, path, *, parents, exist_ok):
        self.calls.append(("outcomes_mkdir", path, parents, exist_ok))

    def open_outcomes(self, mode, *, encoding):
        self.calls.append(("open_outcomes", mode, encoding))
        return OutcomeWriter(self)

    def load(self):
        pytest.fail("OPEN protection must use only its supplied trade and window")

    def save(self, *_args):
        pytest.fail("OPEN protection must not persist")

    def fetch_corrected(self, *_args):
        pytest.fail("OPEN protection must not acquire bars")

    def quote_payload(self):
        pytest.fail("OPEN protection must not acquire quotes")

    def deliver(self, *_args):
        pytest.fail("OPEN protection must not deliver")


def trade(**changes):
    return {
        "trade_id": "open-protection-1",
        "state": "OPEN",
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [["TP1", 110.0]],
        "to_group": True,
        "ts": 1_726_300_000.0,
        "hit": [],
    } | changes


def resolve(source, open_trade, *, low, high):
    return api().LifecycleOpenProtection(source).resolve(open_trade, low=low, high=high)


@pytest.mark.parametrize(
    ("direction", "stop", "targets", "low", "high"),
    [
        # Long: the low reaches protection and the high reaches TP1.
        (LONG, 90.0, [["TP1", 110.0]], 90.0, 110.0),
        # Short: the high reaches protection and the low reaches TP1.
        (SHORT, 110.0, [["TP1", 90.0]], 90.0, 110.0),
    ],
)
def test_unhit_target_and_protection_in_one_window_stop_both_directions(
    direction, stop, targets, low, high
):
    """Resolve physical protective-and-target touches conservatively."""
    source = Source()
    open_trade = trade(direction=direction, stop=stop, targets=targets)

    messages, changed = resolve(source, open_trade, low=low, high=high)

    assert changed is True
    assert open_trade["state"] == "STOPPED"
    assert open_trade["terminal_result"] == "stopped_ambiguous"
    assert open_trade["resolved_ts"] == NOW
    assert len(messages) == 1 and messages[0][1] is True
    assert source.outcomes == [{
        "ts": NOW, **open_trade, "result": "stopped_ambiguous", "event_ts": NOW,
    }]


@pytest.mark.parametrize(
    ("direction", "targets", "low", "high"),
    [
        # Long: after TP1, low reaches the protective stop and high reaches TP2.
        (LONG, [["TP1", 110.0], ["TP2", 120.0]], 100.0, 120.0),
        # Short: after TP1, high reaches the protective stop and low reaches TP2.
        (SHORT, [["TP1", 90.0], ["TP2", 80.0]], 80.0, 100.0),
    ],
)
def test_ambiguous_unhit_later_target_after_a_hit_marks_done_and_writes_raw_fact(
    direction, targets, low, high
):
    """Catch a regression that marks a post-hit ambiguity STOPPED or skips its fact."""
    source = Source()
    open_trade = trade(
        direction=direction,
        stop=100.0,
        targets=targets,
        hit=["TP1"],
        to_group=False,
    )

    messages, changed = resolve(source, open_trade, low=low, high=high)

    assert changed is True
    assert open_trade["state"] == "DONE"
    assert open_trade["terminal_result"] == "be_after_tp_ambiguous"
    assert open_trade["resolved_ts"] == NOW
    assert len(messages) == 1 and messages[0][1] is False
    assert source.outcomes == [{
        "ts": NOW, **open_trade, "result": "be_after_tp_ambiguous", "event_ts": NOW,
    }]


@pytest.mark.parametrize(
    ("direction", "stop", "targets", "hit", "to_group", "low", "high", "state", "result"),
    [
        # Long: low alone reaches the protective stop; high alone reaches TP1.
        (LONG, 90.0, [["TP1", 110.0]], [], True, 90.0, 110.0,
         "STOPPED", "stopped_ambiguous"),
        # Short: high alone reaches the protective stop; low alone reaches TP1.
        (SHORT, 110.0, [["TP1", 90.0]], [], True, 90.0, 110.0,
         "STOPPED", "stopped_ambiguous"),
        # Long after TP1: low alone reaches BE protection; high alone reaches TP2.
        (LONG, 100.0, [["TP1", 110.0], ["TP2", 120.0]], ["TP1"], False,
         100.0, 120.0, "DONE", "be_after_tp_ambiguous"),
        # Short after TP1: high alone reaches BE protection; low alone reaches TP2.
        (SHORT, 100.0, [["TP1", 90.0], ["TP2", 80.0]], ["TP1"], False,
         80.0, 100.0, "DONE", "be_after_tp_ambiguous"),
    ],
)
def test_asymmetric_ambiguous_window_resolves_source_but_not_low_high_swapped_mutant(
    monkeypatch, direction, stop, targets, hit, to_group, low, high, state, result
):
    """Kill the mutation that calls the source ambiguity predicate as ``(high, low)``."""
    source = Source()
    open_trade = trade(
        direction=direction,
        stop=stop,
        targets=targets,
        hit=hit,
        to_group=to_group,
    )

    messages, changed = resolve(source, open_trade, low=low, high=high)

    assert changed is True
    assert open_trade["state"] == state
    assert open_trade["terminal_result"] == result
    assert len(messages) == 1 and messages[0][1] is to_group
    assert source.outcomes == [{
        "ts": NOW, **open_trade, "result": result, "event_ts": NOW,
    }]

    transitions = importlib.import_module(
        "trading_system.tree_replay._vendor.lifecycle_transitions"
    ).LifecycleTransitions
    source_touch = transitions._ambiguous_touch

    def low_high_swapped_touch(self, t, lo, hi, short, protective):
        return source_touch(self, t, hi, lo, short, protective)

    mutant_source = Source()
    mutant_trade = trade(
        direction=direction,
        stop=stop,
        targets=targets,
        hit=hit,
        to_group=to_group,
    )
    mutant_before = deepcopy(mutant_trade)
    with monkeypatch.context() as patched:
        patched.setattr(transitions, "_ambiguous_touch", low_high_swapped_touch)
        assert resolve(mutant_source, mutant_trade, low=low, high=high) == ([], False)

    assert mutant_trade == mutant_before
    assert mutant_source.calls == []
    assert mutant_source.outcomes == []


@pytest.mark.parametrize(
    ("direction", "stop", "targets", "low", "high"),
    [
        (LONG, 90.0, [["TP1", 110.0]], 95.0, 111.0),
        (SHORT, 110.0, [["TP1", 90.0]], 89.0, 105.0),
    ],
)
def test_nonambiguous_supplied_window_has_no_message_mutation_or_raw_fact(
    direction, stop, targets, low, high
):
    """Catch a resolver that turns ordinary progress into a terminal ambiguity."""
    source = Source()
    open_trade = trade(direction=direction, stop=stop, targets=targets)
    before = deepcopy(open_trade)

    assert resolve(source, open_trade, low=low, high=high) == ([], False)

    assert open_trade == before
    assert source.calls == []
    assert source.outcomes == []
