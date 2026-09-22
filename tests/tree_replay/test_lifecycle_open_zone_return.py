"""Private OPEN zone-return notifications consume only supplied spot and labels."""
from __future__ import annotations

from copy import deepcopy
import importlib
import importlib.util

import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_open_zone_return"
LONG = "\u05dc\u05d5\u05e0\u05d2"
SHORT = "\u05e9\u05d5\u05e8\u05d8"


def api():
    assert importlib.util.find_spec(MODULE) is not None, "OPEN zone-return resolver module missing"
    return importlib.import_module(MODULE)


class Source:
    """Offline source whose real revalidation method is controlled per test."""

    def __init__(self, result=(True, "", True), error=None):
        self.result = result
        self.error = error
        self.calls = []

    def load(self, *_args):
        pytest.fail("zone-return projection must not load persistent state")

    def save(self, *_args):
        pytest.fail("zone-return projection must not persist state")

    def fetch_corrected(self, *_args):
        pytest.fail("zone-return projection must not acquire revalidation data")

    def quote_payload(self, *_args):
        pytest.fail("zone-return projection must not acquire market data")

    def deliver(self, *_args):
        pytest.fail("zone-return projection must not deliver messages")

    def outcomes_mkdir(self, *_args, **_kwargs):
        pytest.fail("zone-return projection must not write outcomes")

    def open_outcomes(self, *_args, **_kwargs):
        pytest.fail("zone-return projection must not write outcomes")

    def now_epoch(self):
        return 1_726_300_010.0


def trade(**changes):
    return {
        "trade_id": "open-zone-return-1",
        "state": "OPEN",
        "symbol": "OANDA:XAUUSD",
        "direction": LONG,
        "entry": 100.0,
        "stop": 90.0,
        "targets": [("TP1", 110.0), ("TP2", 120.0)],
        "hit": [],
        "progress_step": 1,
        "to_group": True,
        "ts": 1_726_300_000.0,
    } | changes


def resolve(monkeypatch, source, open_trade, *, spot):
    module = api()
    def controlled_still_valid(child, _trade):
        assert child.source is source
        if source.error is not None:
            raise source.error
        return source.result

    monkeypatch.setattr(module.Revalidation, "still_valid", controlled_still_valid)
    return module.LifecycleOpenZoneReturn(source).resolve(open_trade, spot=spot)


def test_exposes_one_private_supplied_spot_notification_resolver():
    """Catch a missing projection before any runtime behavior is assumed."""
    module = api()
    assert hasattr(module, "LifecycleOpenZoneReturn")


@pytest.mark.parametrize(
    ("direction", "spot", "expected_side"),
    [(LONG, 102.0, "BUY"), (SHORT, 98.0, "SELL")],
)
def test_zone_edge_return_emits_one_message_for_each_direction(
    monkeypatch, direction, spot, expected_side
):
    """Catch swapped one-sided entry-band comparisons for long or short trades."""
    source = Source()
    open_trade = trade(direction=direction)

    messages, changed = resolve(monkeypatch, source, open_trade, spot=spot)

    assert changed is True
    assert messages[0][1] is True
    assert messages[0][0].splitlines()[0] == (
        f"\U0001f501 XAUUSD {expected_side} 100.00 \u00b7 \u05d7\u05d6\u05e8\u05d4 \u05dc\u05d0\u05d6\u05d5\u05e8 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4"
    )
    assert open_trade["zone_return_at"] == "1/0"


@pytest.mark.parametrize(("direction", "spot"), [(LONG, 103.0), (SHORT, 97.0)])
def test_spot_outside_entry_band_is_a_noop(monkeypatch, direction, spot):
    """Catch a projection that reports a return before price reaches its side's band."""
    source = Source()
    open_trade = trade(direction=direction)
    before = deepcopy(open_trade)

    assert resolve(monkeypatch, source, open_trade, spot=spot) == ([], False)

    assert open_trade == before
    assert source.calls == []


def test_no_reported_excursion_is_a_noop_even_inside_the_band(monkeypatch):
    """Catch a zone message armed by an unreported price move."""
    source = Source()
    open_trade = trade(progress_step=0, hit=[])
    before = deepcopy(open_trade)

    assert resolve(monkeypatch, source, open_trade, spot=102.0) == ([], False)

    assert open_trade == before
    assert source.calls == []


def test_marker_suppresses_repeated_return_and_new_rungs_do_not_rearm(monkeypatch):
    """Catch repeat alerts rearmed by ladder progress instead of a later target."""
    source = Source()
    open_trade = trade(progress_step=4, hit=["TP1"], zone_return_at="1/1")
    before = deepcopy(open_trade)

    assert resolve(monkeypatch, source, open_trade, spot=102.0) == ([], False)

    assert open_trade == before


def test_only_an_additional_target_rearms_a_previous_return(monkeypatch):
    """Catch a target-only rearm branch that loses its updated excursion marker."""
    source = Source()
    open_trade = trade(progress_step=4, hit=["TP1", "TP2"], zone_return_at="1/1")

    messages, changed = resolve(monkeypatch, source, open_trade, spot=102.0)

    assert changed is True
    assert len(messages) == 1
    assert open_trade["zone_return_at"] == "4/2"


def test_malformed_previous_marker_rearms_from_zero_targets(monkeypatch):
    """Catch malformed marker parsing suppressing a legitimate first-style return."""
    source = Source()
    open_trade = trade(hit=["TP1"], zone_return_at="not/a-target-count")

    messages, changed = resolve(monkeypatch, source, open_trade, spot=102.0)

    assert changed is True
    assert len(messages) == 1
    assert open_trade["zone_return_at"] == "1/1"


def test_malformed_marker_with_zero_targets_suppresses_the_same_excursion(monkeypatch):
    """Catch changing the source's zero-target `<=` suppression to `<`."""
    source = Source()
    open_trade = trade(hit=[], zone_return_at="malformed")
    before = deepcopy(open_trade)

    assert resolve(monkeypatch, source, open_trade, spot=102.0) == ([], False)

    assert open_trade == before


def test_valid_desk_success_arms_a_zero_progress_step_excursion(monkeypatch):
    """Catch dropping DeskSuccess.reached() from the source excursion maximum."""
    source = Source()
    open_trade = trade(
        progress_step=0,
        hit=[],
        minimum_success={
            "version": "desk-minimum-2026-09-07",
            "trade_id": "open-zone-return-1",
            "trade_ts": 1_726_300_000.0,
            "symbol": "OANDA:XAUUSD",
            "minimum_points": 4.0,
            "price": 104.0,
            "observed_price": 104.0,
            "observed_ts": 1_726_300_001.0,
            "detected_ts": 1_726_300_001.0,
            "source": "exact_venue_quote",
        },
    )

    messages, changed = resolve(monkeypatch, source, open_trade, spot=102.0)

    assert (len(messages), changed) == (1, True)
    assert open_trade["zone_return_at"] == "1/0"


@pytest.mark.parametrize(
    ("result", "error", "required", "forbidden"),
    [
        (
            (True, "still intact", True),
            None,
            ("\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05e2\u05d3\u05d9\u05d9\u05df \u05de\u05ea\u05e7\u05d9\u05d9\u05de\u05d9\u05dd \u2705", "still intact"),
            (),
        ),
        (
            (False, "thesis failed", True),
            None,
            ("\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05dc\u05d0 \u05de\u05ea\u05e7\u05d9\u05d9\u05de\u05d9\u05dd \u05db\u05e2\u05ea \u2757\ufe0f", "thesis failed"),
            (),
        ),
        (
            (False, "untrusted failure", False),
            None,
            ("\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05dc\u05d0 \u05d0\u05d5\u05de\u05ea\u05d5 \u05de\u05d7\u05d3\u05e9 \u2014 \u05d0\u05d9\u05df \u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05d8\u05e8\u05d9\u05d9\u05dd.",),
            ("untrusted failure",),
        ),
        (
            (True, "", True),
            RuntimeError("recheck unavailable"),
            ("\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05e2\u05d3\u05d9\u05d9\u05df \u05de\u05ea\u05e7\u05d9\u05d9\u05de\u05d9\u05dd \u2705", "\u05ea\u05e0\u05d0\u05d9 \u05d4\u05db\u05e0\u05d9\u05e1\u05d4 \u05dc\u05d0 \u05d0\u05d5\u05de\u05ea\u05d5 \u05de\u05d7\u05d3\u05e9 \u2014 \u05d0\u05d9\u05df \u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05d8\u05e8\u05d9\u05d9\u05dd."),
            (),
        ),
    ],
)
def test_recheck_is_reported_as_valid_invalid_unverified_or_caught_error_label(
    monkeypatch, result, error, required, forbidden
):
    """Catch a recheck label being omitted, mistranslated, or made into a veto."""
    source = Source(result=result, error=error)
    open_trade = trade()

    messages, changed = resolve(monkeypatch, source, open_trade, spot=102.0)

    assert changed is True
    for text in required:
        assert text in messages[0][0]
    for text in forbidden:
        assert text not in messages[0][0]
    assert open_trade["state"] == "OPEN"


def test_actual_revalidation_child_boundary_is_called_for_the_advisory_label(monkeypatch):
    """Catch replacing the retained Revalidation(source).still_valid call with a label port."""
    module = api()
    source = Source()
    open_trade = trade()
    calls = []

    def spy_still_valid(child, received_trade):
        calls.append((child, received_trade))
        return True, "child reply", True

    monkeypatch.setattr(module.Revalidation, "still_valid", spy_still_valid)
    resolver = module.LifecycleOpenZoneReturn(source)
    messages, changed = resolver.resolve(open_trade, spot=102.0)

    assert type(resolver.revalidation) is module.Revalidation
    assert calls == [(resolver.revalidation, open_trade)]
    assert (len(messages), changed) == (1, True)


def test_full_message_keeps_source_order_and_direct_unverified_recheck_reason(monkeypatch):
    """Catch removal or reordering of spot, zone, stop, journey, recheck, or footer."""
    source = Source(result=(True, "still intact", False))
    open_trade = trade(
        stop=91.0,
        hit=["TP1"],
        progress_step=2,
        reported_progress_points=0.18,
    )

    messages, changed = resolve(monkeypatch, source, open_trade, spot=102.0)

    assert changed is True
    assert messages == [(
        "\n".join((
            "🔁 XAUUSD BUY 100.00 · חזרה לאזור הכניסה",
            "",
            "מחיר בעדכון: 102.00",
            "אזור: 98.00–102.00",
            "סטופ מקורי: 91.00 · מרחק 110 פיפס",
            "",
            "הגיעה ל-+2 פיפס",
            "תנאי הכניסה עדיין מתקיימים ✅",
            "still intact",
            "תנאי הכניסה לא אומתו מחדש — אין נתונים טריים.",
            "",
            "הסטופ והיעדים ללא שינוי. זה אינו אות לכניסה נוספת.",
        )),
        True,
    )]


def test_direct_valid_unverified_reason_is_distinct_from_caught_error_label(monkeypatch):
    """Catch collapsing a direct unverified recheck into the caught-error fallback."""
    direct_source = Source(result=(True, "direct unverified reason", False))
    error_source = Source(error=RuntimeError("offline recheck failed"))

    direct_messages, direct_changed = resolve(monkeypatch, direct_source, trade(), spot=102.0)
    error_messages, error_changed = resolve(monkeypatch, error_source, trade(), spot=102.0)

    assert (direct_changed, error_changed) == (True, True)
    assert "direct unverified reason" in direct_messages[0][0]
    assert "direct unverified reason" not in error_messages[0][0]
    assert "תנאי הכניסה לא אומתו מחדש — אין נתונים טריים." in direct_messages[0][0]
    assert "תנאי הכניסה לא אומתו מחדש — אין נתונים טריים." in error_messages[0][0]


def test_notification_mutates_only_marker_with_a_controlled_recheck_label(monkeypatch):
    """Catch zone-return itself changing lifecycle fields or writing an outcome."""
    source = Source(result=(True, "label only", False))
    open_trade = trade(
        terminal_result="kept",
        stop=91.0,
        targets=[("TP1", 110.0), ("TP2", 120.0)],
        hit=["TP1"],
        progress_step=2,
    )
    before = deepcopy(open_trade)

    messages, changed = resolve(monkeypatch, source, open_trade, spot=102.0)

    assert (len(messages), changed) == (1, True)
    assert {key: value for key, value in open_trade.items() if key != "zone_return_at"} == before
    assert open_trade["zone_return_at"] == "2/1"
    assert source.calls == []
