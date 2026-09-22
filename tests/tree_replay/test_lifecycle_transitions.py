"""Tracker transition helpers over offline clocks and accepted child projections."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib

import pytest

from trading_system.tree_replay._vendor import lifecycle_voice as voice


NOW = datetime(2026, 9, 14, 12, 34, tzinfo=timezone.utc).timestamp()


def api():
    return importlib.import_module(
        "trading_system.tree_replay._vendor.lifecycle_transitions"
    )


class RawClock:
    def __init__(self, now=NOW):
        self.now = now
        self.calls = 0

    def now_epoch(self):
        self.calls += 1
        return self.now


class FailingClock:
    def __init__(self):
        self.calls = 0

    def now_epoch(self):
        self.calls += 1
        raise RuntimeError("clock unavailable")


def trade(**changes):
    return {
        "symbol": "OANDA:XAUUSD",
        "direction": "׳לונג",
        "entry": 100.0,
        "stop": 90.0,
        "targets": [("TP1", 110.0), ("TP2", 120.0)],
        "hit": [],
        "state": "OPEN",
        "to_group": True,
    } | changes


def engine(now=NOW):
    raw = RawClock(now)
    return api().LifecycleTransitions(raw), raw


def test_progress_percentage_and_steps_use_source_symbol_ladder_and_cap_below_tp1():
    e, _raw = engine()
    t = trade()
    assert e._progress_pct("XAUUSD") == 0.09
    assert e._progress_pct("NAS100") == 0.12
    assert e._progress_pct("BTCUSDT") == 2.0
    assert e._progress_pct("SPY") == 0.10
    steps = e._progress_steps(t, 110.0, False)
    assert len(steps) == 111
    assert steps[0] == (1, 100.09)
    assert steps[-1] == (111, pytest.approx(109.99))
    assert all(level < 110.0 for _step, level in steps)


def test_progress_messages_emit_unseen_steps_and_mutate_only_ladder_fields():
    e, _raw = engine()
    t = trade(progress_step=1)
    prior = deepcopy(t)
    got = e._progress_messages(t, 100.27, False, "ignored", "ignored")
    assert len(got) == 1 and all(to_group is True for _text, to_group in got)
    assert got[0][0].splitlines()[0] == "📈 XAUUSD BUY 100.00 · +2 פיפס"
    assert "תנועת המחיר, לא רווח ממומש." in got[-1][0]
    assert t["progress_step"] == 2 and t["reported_progress_points"] == pytest.approx(0.18)
    assert {k: v for k, v in t.items() if k not in ("progress_step", "reported_progress_points")} == {
        k: v for k, v in prior.items() if k not in ("progress_step", "reported_progress_points")
    }


@pytest.mark.parametrize("changes,want", [
    ({"hit": []}, "stopped_ambiguous"),
    ({"hit": ["TP1"], "stop": 100.0}, "be_after_tp_ambiguous"),
    ({"hit": ["TP1"], "stop": 105.0}, "trailed_stop_ambiguous"),
    ({"hit": ["TP1"], "stop": 95.0}, "published_stop_after_tp_ambiguous"),
])
def test_ambiguous_result_uses_published_protection_and_records_source_category(changes, want):
    e, _raw = engine()
    t = trade(**changes)
    message, result = e._resolve_ambiguous(t, "ignored", "ignored")
    assert result == want and t["terminal_result"] == want
    assert message.startswith("🛑 XAUUSD BUY 100.00")
    assert "סדר האירועים אינו ידוע" in message
    assert "לא נטען שהיעד הושג לפניו." in message


def test_ambiguous_touch_requires_protection_and_an_unhit_target():
    e, _raw = engine()
    t = trade()
    assert e._ambiguous_touch(t, 89.0, 111.0, False, 90.0)
    assert not e._ambiguous_touch(t, 91.0, 111.0, False, 90.0)
    assert not e._ambiguous_touch(trade(hit=["TP1", "TP2"]), 89.0, 111.0, False, 90.0)


@pytest.mark.parametrize("changes,result,state,marker", [
    ({"hit": []}, "stopped", "STOPPED", "🛑"),
    ({"hit": ["TP1"], "stop": 100.0}, "be_after_tp", "DONE", "🏁"),
    ({"hit": ["TP1"], "stop": 105.0}, "trailed_stop", "DONE", "🏁"),
    ({"hit": ["TP1"], "stop": 95.0}, "published_stop_after_tp", "DONE", "🛑"),
])
def test_protective_result_categories_keep_published_stop(changes, result, state, marker):
    e, _raw = engine()
    t = trade(**changes)
    message, got_result, got_state = e._resolve_protective(t, "ignored", "ignored")
    assert (got_result, got_state) == (result, state)
    assert t["terminal_result"] == result
    assert message.startswith(f"{marker} XAUUSD BUY 100.00")


def test_mark_terminal_changes_only_state_and_uses_raw_source_epoch_once():
    e, raw = engine(123.456)
    t = trade(other="kept")
    e._mark_terminal(t, "DONE")
    assert t == trade(other="kept", state="DONE", resolved_ts=123.456)
    assert raw.calls == 1


def test_mark_terminal_propagates_clock_failure_after_source_order_state_mutation():
    raw = FailingClock()
    e = api().LifecycleTransitions(raw)
    t = trade(other="kept")

    with pytest.raises(RuntimeError, match="clock unavailable"):
        e._mark_terminal(t, "DONE")

    assert t == trade(other="kept", state="DONE")
    assert raw.calls == 1


@pytest.mark.parametrize("missing", ["targets", "hit"])
def test_ambiguous_touch_propagates_missing_required_trade_fields(missing):
    e, _raw = engine()
    t = trade()
    t.pop(missing)

    with pytest.raises(KeyError) as error:
        e._ambiguous_touch(t, 89.0, 111.0, False, 90.0)

    assert error.value.args == (missing,)


def test_fill_target_cancel_and_score_lines_keep_source_message_contracts():
    e, _raw = engine()
    t = trade()
    assert e._fill_line(t, "ignored", "ignored") == "▶️ XAUUSD BUY 100.00 · המחיר הגיע לאזור הכניסה\nאזור 98.00–102.00 · סטופ 90.00"
    target = e._target_line(t, 1, "TP1", 110.0)
    assert target.splitlines()[0] == "✅ XAUUSD BUY 100.00 · TP1 הושג @ 110.00"
    assert "אפשר לשקול הגנה בכניסה" in target
    assert e._no_score("הטיה התהפכה (-158)") == "הטיה התהפכה"
    assert e._no_score("plain reason") == "plain reason"
    cancelled = e._cancel_line(t, "הטיה התהפכה (-158)")
    assert cancelled.startswith("✖️ ")
    assert cancelled.endswith("הטיה התהפכה")


def test_fill_caveat_journey_clock_and_dependency_fallbacks_keep_source_boundaries():
    e, _raw = engine()
    assert e._fill_caveat("because", True) == "\nbecause"
    assert "העסקה נפתחה על התזה המקורית." in e._fill_caveat("", False)
    assert e._il_clock("bad") == ""
    t = trade(progress_step=1, reported_progress_points=0.09, be_level=100.0, be_ts=NOW)
    assert e._journey(t).startswith("הגיעה ל-+1 פיפס · ההגנה הוצעה ב-")
    assert e._protective(trade(stop="91.25"), False) == 91.25
    assert e._fill_line(trade(symbol="UNKNOWN"), "ignored", "ignored").splitlines()[1] == "סטופ 90.00"


def test_transition_helpers_do_not_call_unprovided_feed_persistence_or_delivery_ports():
    e, raw = engine()
    t = trade()
    e._progress_messages(t, 100.09, False, "ignored", "ignored")
    e._resolve_protective(t, "ignored", "ignored")
    assert raw.calls == 0
