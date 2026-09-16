"""Offline source projection tests for the PENDING resolver slice."""
from __future__ import annotations

from copy import deepcopy
import importlib
import importlib.util
import json

import pytest

from test_tree_revalidation import Inputs as RevalidationInputs


MODULE = "trading_system.tree_replay._vendor.lifecycle_pending_resolution"
SHORT = "\u05e9\u05d5\u05e8\u05d8"
LONG = "\u05dc\u05d5\u05e0\u05d2"
NOW = 1_726_315_240.5


def api():
    assert importlib.util.find_spec(MODULE) is not None, "PENDING resolution module missing"
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
        pytest.fail("PENDING resolution must use its supplied state image")

    def save(self, *_args):
        pytest.fail("PENDING resolution must not persist")

    def locked(self, *_args):
        pytest.fail("PENDING resolution must not lock")

    def quote_payload(self):
        pytest.fail("PENDING resolution must not fetch quotes")

    def fetch_corrected(self, *_args):
        pytest.fail("PENDING resolution must not fetch bars")

    def gate(self, *_args):
        pytest.fail("PENDING resolution must not gate")

    def deliver(self, *_args):
        pytest.fail("PENDING resolution must not deliver")

    def open_logic(self, *_args):
        pytest.fail("PENDING resolution must not invoke OPEN logic")


class Validation:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def revalidate_pending(self, trade):
        self.calls.append(trade)
        return self.result


def trade(**changes):
    return {
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [["TP1", 110.0]],
        "state": "PENDING",
        "to_group": True,
        "ts": 1_726_300_000.0,
        "hit": [],
    } | changes


def resolve(source, pending, *, state=None, price=100.0, bar_extremes=None):
    return api().LifecyclePendingResolution(source).resolve(
        pending,
        state={} if state is None else state,
        price=price,
        bar_extremes={} if bar_extremes is None else bar_extremes,
    )


def install_validation(monkeypatch, result):
    validation = Validation(result)
    monkeypatch.setattr(api(), "TreeRevalidation", lambda _source: validation)
    return validation


@pytest.mark.parametrize(
    ("direction", "extremes"),
    [
        # A short can touch only because the physical bar high reaches the
        # lower entry boundary; its low must not be substituted here.
        (SHORT, (97.0, 98.0)),
        # A long can touch only because the physical bar low reaches the
        # upper entry boundary; its high must not be substituted here.
        (LONG, (102.0, 103.0)),
    ],
)
def test_one_sided_touch_opens_both_directions_at_the_source_boundary(monkeypatch, direction, extremes):
    source = Source()
    validation = install_validation(monkeypatch, (True, "still aligned", True))
    pending = trade(direction=direction)

    messages, changed = resolve(
        source,
        pending,
        state={"pending": pending},
        bar_extremes={pending["symbol"]: extremes},
    )

    assert changed is True
    assert pending["state"] == "OPEN"
    assert validation.calls == [pending]
    assert len(messages) == 1
    assert messages[0][1] is True
    assert ("SELL" if direction == SHORT else "BUY") in messages[0][0]


@pytest.mark.parametrize(
    ("direction", "extremes", "correct_touch", "swapped_touch"),
    [
        # Correct source rule: short high >= 98.  A low/high swap is false.
        (SHORT, (97.0, 98.0), True, False),
        # Its physical no-touch counterpart remains below 98 at its high.
        (SHORT, (97.0, 97.999), False, False),
        # Correct source rule: long low <= 102.  A low/high swap is false.
        (LONG, (102.0, 103.0), True, False),
        # Its physical no-touch counterpart remains above 102 at its low.
        (LONG, (102.001, 103.0), False, False),
    ],
)
def test_physical_extrema_fixtures_discriminate_the_source_touch_field(
    direction, extremes, correct_touch, swapped_touch
):
    """Catch a regression that substitutes low for high, or vice versa."""
    low, high = extremes
    zone_low, zone_high = (98.0, 102.0)
    source_touch = high >= zone_low if direction == SHORT else low <= zone_high
    low_high_swapped_touch = low >= zone_low if direction == SHORT else high <= zone_high

    assert source_touch is correct_touch
    assert low_high_swapped_touch is swapped_touch


@pytest.mark.parametrize(("direction", "price"), [(SHORT, 98.0), (LONG, 102.0)])
def test_spot_price_is_the_entry_extreme_fallback(monkeypatch, direction, price):
    source = Source()
    install_validation(monkeypatch, (True, "", True))
    pending = trade(direction=direction)

    _messages, changed = resolve(source, pending, state={"pending": pending}, price=price)

    assert changed is True and pending["state"] == "OPEN"


@pytest.mark.parametrize(
    ("direction", "extremes"),
    [
        (SHORT, (95.0, 97.999)),
        (LONG, (102.001, 105.0)),
    ],
)
def test_no_touch_leaves_every_supplied_trade_fact_unchanged(monkeypatch, direction, extremes):
    source = Source()
    validation = install_validation(monkeypatch, (True, "must not run", True))
    pending = trade(direction=direction)
    before = deepcopy(pending)

    assert resolve(source, pending, state={"pending": pending}, bar_extremes={pending["symbol"]: extremes}) == ([], False)

    assert pending == before
    assert validation.calls == []
    assert source.calls == [] and source.outcomes == []


def test_resolver_composes_the_real_revalidator_over_in_memory_raw_ports():
    """Catch a resolver/revalidator constructor seam that only works with a double."""
    source = RevalidationInputs()
    pending = trade(
        entry=110.0,
        stop=99.7,
        targets=[["TP1", 120.0]],
        ts=source.now.timestamp() - 7200.0,
        bias_at_send={"4h": 0.0, "1h": 0.0},
    )

    messages, changed = resolve(
        source,
        pending,
        state={"pending": pending},
        price=110.0,
        bar_extremes={pending["symbol"]: (110.0, 111.0)},
    )

    assert changed is True and pending["state"] == "OPEN"
    assert pending["revalidation_verified"] is True
    assert messages and messages[0][1] is True
    # The real revalidator consumes caller-supplied in-memory frames.  The
    # resolver itself did not need quote/bar acquisition ports or real I/O.
    assert ("fetch", pending["symbol"], "15m", 10) in source.calls


def test_open_slot_conflict_cancels_then_writes_the_raw_source_fact(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (True, "must not run", True))
    pending = trade()
    state = {
        "pending": pending,
        "occupant": trade(state="OPEN"),
    }

    messages, changed = resolve(source, pending, state=state, bar_extremes={pending["symbol"]: (99.0, 102.0)})

    assert changed is True and pending["state"] == "CANCELLED"
    assert pending["resolved_ts"] == NOW
    assert validation.calls == []
    assert len(messages) == 1 and messages[0][1] is True
    assert source.outcomes == [{
        "ts": NOW, **pending, "result": "open_slot_conflict_at_fill", "event_ts": NOW,
    }]


def test_failed_revalidation_cancels_with_its_reason_and_raw_source_fact(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (False, "thesis reversed (-42)", True))
    pending = trade()

    messages, changed = resolve(source, pending, state={"pending": pending}, bar_extremes={pending["symbol"]: (99.0, 102.0)})

    assert changed is True and pending["state"] == "CANCELLED"
    assert validation.calls == [pending]
    assert len(messages) == 1 and "thesis reversed" in messages[0][0]
    assert source.outcomes == [{
        "ts": NOW, **pending, "result": "invalidated_at_fill", "event_ts": NOW,
    }]


@pytest.mark.parametrize(
    ("verified", "reason"),
    [
        (True, "still aligned"),
        (False, "evidence unavailable"),
    ],
)
def test_successful_fill_sets_exact_source_fields_with_one_clock_and_no_outcome(
    monkeypatch, verified, reason
):
    source = Source()
    install_validation(monkeypatch, (True, reason, verified))
    pending = trade()

    messages, changed = resolve(source, pending, state={"pending": pending}, bar_extremes={pending["symbol"]: (99.0, 102.0)})

    assert changed is True
    assert pending["state"] == "OPEN"
    assert pending["revalidation_verified"] is verified
    assert pending["fill_verification_reason"] == reason
    assert pending["filled_ts"] == pending["progress_ts"] == NOW
    assert source.calls == [("now_epoch",)]
    assert source.outcomes == []
    assert len(messages) == 1 and messages[0][1] is True
    assert f"\n{reason}" in messages[0][0]
    if not verified:
        assert "\u05d4\u05e2\u05e1\u05e7\u05d4 \u05e0\u05e4\u05ea\u05d7\u05d4 \u05e2\u05dc \u05d4\u05ea\u05d6\u05d4 \u05d4\u05de\u05e7\u05d5\u05e8\u05d9\u05ea." in messages[0][0]


def test_successful_empty_reason_uses_verified_default_and_never_invokes_forbidden_effects(monkeypatch):
    source = Source()
    install_validation(monkeypatch, (True, "", False))
    pending = trade(to_group=False)

    messages, changed = resolve(source, pending, state={"pending": pending}, bar_extremes={pending["symbol"]: (99.0, 102.0)})

    assert changed is True and pending["fill_verification_reason"] == "verified"
    assert messages[0][1] is False
    assert source.outcomes == []
    assert source.calls == [("now_epoch",)]
