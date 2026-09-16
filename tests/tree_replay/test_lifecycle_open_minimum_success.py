"""OPEN minimum-success projection stays private, supplied-evidence only."""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib
import importlib.util
import inspect
import json

import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_open_minimum_success"
LONG = "\u05dc\u05d5\u05e0\u05d2"
SHORT = "\u05e9\u05d5\u05e8\u05d8"
NOW = 1_726_315_240.5


def api():
    assert importlib.util.find_spec(MODULE) is not None, "OPEN minimum-success module missing"
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
    """The offline clock plus raw fact port; all unrelated effects must fail."""

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

    def fetch_corrected(self, *_args):
        pytest.fail("minimum-success projection must not acquire bars")

    def quote_payload(self, *_args):
        pytest.fail("minimum-success projection must not acquire quotes")

    def load(self, *_args):
        pytest.fail("minimum-success projection must not load state")

    def save(self, *_args):
        pytest.fail("minimum-success projection must not persist state")

    def deliver(self, *_args):
        pytest.fail("minimum-success projection must not deliver messages")


def trade(**changes):
    return {
        "trade_id": "open-minimum-1",
        "state": "OPEN",
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [["TP1", 130.0]],
        "to_group": True,
        "ts": NOW - 600.0,
        "filled_ts": NOW - 60.0,
        "hit": [],
    } | changes


def resolve(source, open_trade, *, low=100.0, high=100.0, spot=100.0,
            quote=None, has_bar_extremes=False, minimum_message=None):
    return api().LifecycleOpenMinimumSuccess(source).resolve(
        open_trade,
        low=low,
        high=high,
        spot=spot,
        quote={} if quote is None else quote,
        has_bar_extremes=has_bar_extremes,
        minimum_message=minimum_message,
    )


@pytest.mark.parametrize(
    ("direction", "low", "high", "expected_step"),
    [
        (LONG, 95.0, 100.18, 2),
        (SHORT, 99.82, 105.0, 2),
    ],
)
def test_existing_bar_minimum_records_one_raw_fact_and_uses_directional_best_for_progress(
    direction, low, high, expected_step
):
    """Catch a projection that omits the bar minimum fact or swaps best extrema."""
    source = Source()
    open_trade = trade(direction=direction, stop=110.0 if direction == SHORT else 90.0)

    messages, changed, minimum_message = resolve(
        source,
        open_trade,
        low=low,
        high=high,
        minimum_message="bar-minimum",
    )

    assert (messages, changed, minimum_message) == ([("bar-minimum", True)], True, "bar-minimum")
    assert open_trade["progress_step"] == expected_step
    assert open_trade["reported_progress_points"] == 4.0
    assert [row["result"] for row in source.outcomes] == ["minimum_success"]
    assert len(source.outcomes) == 1


def test_existing_bar_minimum_does_not_advance_progress_when_protection_is_touched():
    """Catch a source-order regression that advances the ladder through protection."""
    source = Source()
    open_trade = trade()

    messages, changed, minimum_message = resolve(
        source,
        open_trade,
        low=90.0,
        high=100.18,
        minimum_message="bar-minimum",
    )

    assert (messages, changed, minimum_message) == ([("bar-minimum", True)], True, "bar-minimum")
    assert "progress_step" not in open_trade
    assert open_trade["reported_progress_points"] == 4.0
    assert [row["result"] for row in source.outcomes] == ["minimum_success"]


def test_existing_bar_minimum_suppresses_an_otherwise_eligible_quote():
    """Catch removal of the source guard that keeps a bar minimum authoritative."""
    source = Source()
    open_trade = trade()

    messages, changed, minimum_message = resolve(
        source,
        open_trade,
        low=100.0,
        high=104.0,
        spot=104.0,
        quote={"lp": 104.0, "price_ts": NOW - 10.0},
        has_bar_extremes=False,
        minimum_message="bar-minimum",
    )

    assert (messages, changed, minimum_message) == ([('bar-minimum', True)], True, "bar-minimum")
    assert "minimum_success" not in open_trade
    assert len(source.outcomes) == 1
    assert source.outcomes[0]["result"] == "minimum_success"
    assert "minimum_success" not in source.outcomes[0]
    assert source.calls == [
        ("outcomes_mkdir", "chart-desk/out", True, True),
        ("now_epoch",),
        ("open_outcomes", "a", "utf-8"),
    ]


def test_exact_fresh_matching_post_fill_quote_observes_minimum_without_bar_extremes():
    """Catch a quote branch that accepts a mismatched, stale, or pre-fill tick."""
    source = Source()
    open_trade = trade()

    messages, changed, minimum_message = resolve(
        source,
        open_trade,
        spot=104.0,
        quote={"lp": 104.0, "price_ts": NOW - 10.0},
    )

    assert changed is True
    assert minimum_message == messages[0][0]
    assert messages[0][1] is True
    assert open_trade["minimum_success"]["source"] == "exact_venue_quote"
    assert open_trade["minimum_success"]["observed_ts"] == NOW - 10.0
    assert [row["result"] for row in source.outcomes] == ["minimum_success"]


@pytest.mark.parametrize(
    ("quote", "has_bar_extremes", "low", "high"),
    [
        ({"lp": 104.0, "price_ts": NOW - 121.0}, False, 100.0, 104.0),
        ({"lp": 103.99, "price_ts": NOW - 10.0}, False, 100.0, 104.0),
        ({"lp": 104.0, "price_ts": NOW - 10.0}, True, 100.0, 104.0),
        ({"lp": 104.0, "price_ts": NOW - 10.0}, False, 90.0, 104.0),
        ({"lp": 104.0, "price_ts": NOW - 61.0}, False, 100.0, 104.0),
    ],
)
def test_stale_wrong_lp_bar_extremes_protection_or_prefill_quote_cannot_create_minimum(
    quote, has_bar_extremes, low, high
):
    """Catch any quote gate becoming sufficient without all source predicates."""
    source = Source()
    open_trade = trade()
    before = deepcopy(open_trade)

    assert resolve(
        source,
        open_trade,
        low=low,
        high=high,
        spot=104.0,
        quote=quote,
        has_bar_extremes=has_bar_extremes,
    ) == ([], False, None)

    assert open_trade == before
    assert source.outcomes == []


def test_no_minimum_leaves_trade_and_source_outcome_ports_unchanged():
    """Catch a no-op branch that writes a fact, clock stamp, or partial trade field."""
    source = Source()
    open_trade = trade()
    before = deepcopy(open_trade)

    assert resolve(source, open_trade) == ([], False, None)

    assert open_trade == before
    assert source.calls == []
    assert source.outcomes == []


def test_runtime_constructs_message_list_before_writing_raw_minimum_outcome():
    """Keep the locally unobservable source append-before-outcome order explicit."""
    tree = ast.parse(inspect.getsource(api()))
    resolve = next(
        member
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "LifecycleOpenMinimumSuccess"
        for member in node.body
        if isinstance(member, ast.FunctionDef) and member.name == "resolve"
    )
    messages_index = next(
        (
            index
            for index, statement in enumerate(resolve.body)
            if isinstance(statement, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "messages" for target in statement.targets)
            and isinstance(statement.value, ast.List)
        ),
        None,
    )
    outcome_index = next(
        index
        for index, statement in enumerate(resolve.body)
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and ast.unparse(statement.value.func) == "self.outcomes._outcome"
    )

    assert messages_index is not None, "resolve must construct its one-message list"
    assert messages_index < outcome_index
