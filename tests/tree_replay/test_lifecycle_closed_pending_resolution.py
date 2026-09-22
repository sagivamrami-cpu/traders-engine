"""Closed-bar PENDING resolution over a caller-supplied 15-minute window."""
from __future__ import annotations

from copy import deepcopy
import importlib
import importlib.util
import json

import pandas as pd
import pytest


MODULE = "trading_system.tree_replay._vendor.lifecycle_closed_pending_resolution"
LONG = "לונג"
SHORT = "שורט"
NOW = 1_726_400_000.0


def api():
    assert importlib.util.find_spec(MODULE) is not None, "closed PENDING runtime missing"
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


class ShelfWriter:
    def __init__(self, source):
        self.source = source
        self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def write(self, text):
        self.text += text
        return len(text)

    def flush(self):
        pass


class Source:
    def __init__(self, *, now=NOW):
        self.now = now
        self.outcomes = []
        self.shelf = None
        self._writers = {}
        self.calls = []

    def now_epoch(self):
        self.calls.append(("now_epoch",))
        return self.now

    def outcomes_mkdir(self, path, *, parents, exist_ok):
        self.calls.append(("outcomes_mkdir", path, parents, exist_ok))

    def open_outcomes(self, mode, *, encoding):
        self.calls.append(("open_outcomes", mode, encoding))
        return OutcomeWriter(self)

    def shelf_exists(self):
        return self.shelf is not None

    def shelf_text(self, *, encoding):
        return self.shelf

    def atomic_mkdir(self, path, *, parents, exist_ok):
        self.calls.append(("atomic_mkdir", path, parents, exist_ok))

    def atomic_mkstemp(self, path, *, suffix):
        key = f"{path}/pending{suffix}"
        self._writers[key] = ShelfWriter(self)
        return (key, key)

    def atomic_fdopen(self, fd, mode, *, encoding):
        return self._writers[fd]

    def atomic_fsync(self, _fh):
        pass

    def atomic_replace(self, tmp, _path):
        self.shelf = self._writers[tmp].text

    def atomic_unlink(self, _tmp):
        pass

    def load(self):
        pytest.fail("closed PENDING resolver must use the supplied state")

    def save(self, *_args):
        pytest.fail("closed PENDING resolver must not persist")

    def fetch_corrected(self, *_args):
        pytest.fail("closed PENDING resolver must not acquire bars")

    def quote_payload(self):
        pytest.fail("closed PENDING resolver must not fetch quotes")

    def gate(self, *_args):
        pytest.fail("closed PENDING resolver must not gate")

    def deliver(self, *_args):
        pytest.fail("closed PENDING resolver must not deliver")


class Validation:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def revalidate_pending(self, trade, *, now):
        self.calls.append((trade, now))
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
        "ts": NOW - 6 * 3600 - 1,
        "style": "intraday",
        "hit": [],
    } | changes


def since(*opens):
    return pd.DataFrame({"open": list(opens)})


def install_validation(monkeypatch, result):
    validation = Validation(result)
    monkeypatch.setattr(api(), "TreeRevalidation", lambda _source: validation)
    return validation


def resolve(source, pending, *, state=None, bars=None, high=100.0, low=100.0, now=NOW):
    return api().LifecycleClosedPendingResolution(source).resolve(
        pending,
        state={} if state is None else state,
        since=since(100.0) if bars is None else bars,
        high=high,
        low=low,
        now=now,
    )


@pytest.fixture(autouse=True)
def exact_entry_band(monkeypatch):
    monkeypatch.setattr(api(), "_entry_band", lambda _trade: (98.0, 102.0))


def test_expired_unfilled_long_records_hand_checked_missed_r_message_raw_fact_and_shelf(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (True, "must not run", True))
    pending = trade()

    messages, changed = resolve(source, pending, high=115.0, low=103.0)

    assert changed is True and pending["state"] == "CANCELLED"
    assert pending["resolved_ts"] == NOW
    assert validation.calls == []
    assert len(messages) == 1 and messages[0][1] is True
    assert "1.5R" in messages[0][0]
    assert source.outcomes == [{
        "ts": NOW, **pending, "result": "expired", "missed_r": 1.5,
        "missed_points": 15.0, "event_ts": NOW,
    }]
    shelved = json.loads(source.shelf)
    assert shelved["OANDA:XAUUSD|לונג|100.0"]["original_ts"] == pending["ts"]


def test_expired_unfilled_short_measures_movement_from_first_open_to_low(monkeypatch):
    source = Source()
    install_validation(monkeypatch, (True, "must not run", True))
    pending = trade(direction=SHORT, entry=100.0, stop=110.0)

    messages, changed = resolve(source, pending, bars=since(105.0), high=97.0, low=85.0)

    assert changed is True and pending["state"] == "CANCELLED"
    assert "2.0R" in messages[0][0]
    assert source.outcomes[0]["missed_r"] == 2.0
    assert source.outcomes[0]["missed_points"] == 20.0


def test_unexpired_no_touch_preserves_all_trade_facts_and_has_no_effects(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (True, "must not run", True))
    pending = trade(ts=NOW - 10.0)
    before = deepcopy(pending)

    assert resolve(source, pending, high=101.0, low=102.001) == ([], False)

    assert pending == before
    assert validation.calls == [] and source.outcomes == [] and source.shelf is None


def test_open_slot_conflict_cancels_at_fill_before_revalidation(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (True, "must not run", True))
    pending = trade(ts=NOW - 10.0)
    state = {"pending": pending, "occupant": trade(state="OPEN")}

    messages, changed = resolve(source, pending, state=state, high=103.0, low=99.0)

    assert changed is True and pending["state"] == "CANCELLED"
    assert validation.calls == []
    assert source.outcomes[0]["result"] == "open_slot_conflict_at_fill"
    assert "BUY" in messages[0][0]


def test_failed_revalidation_cancels_at_fill_with_pass_clock(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (False, "thesis reversed (-42)", True))
    pending = trade(ts=NOW - 10.0)

    messages, changed = resolve(source, pending, high=103.0, low=99.0)

    assert changed is True and pending["state"] == "CANCELLED"
    assert validation.calls == [(pending, NOW)]
    assert "thesis reversed" in messages[0][0]
    assert source.outcomes[0]["result"] == "invalidated_at_fill"


def test_entry_and_stop_in_same_closed_window_is_stopped_ambiguous_after_fill_fields(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (True, "still aligned", True))
    pending = trade(ts=NOW - 10.0)

    messages, changed = resolve(source, pending, high=103.0, low=89.0)

    assert changed is True and pending["state"] == "STOPPED"
    assert pending["revalidation_verified"] is True
    assert pending["fill_verification_reason"] == "still aligned"
    assert pending["filled_ts"] == pending["progress_ts"] == NOW
    assert pending["resolved_ts"] == NOW
    assert source.outcomes[0]["result"] == "stopped_ambiguous"
    assert "סופרים סטופ" in messages[0][0]


def test_successful_fill_leaves_open_state_and_emits_the_fallthrough_indicator(monkeypatch):
    source = Source()
    validation = install_validation(monkeypatch, (True, "evidence unavailable", False))
    pending = trade(ts=NOW - 10.0, to_group=False)

    messages, changed = resolve(source, pending, high=103.0, low=99.0)

    assert changed is True and pending["state"] == "OPEN"
    assert pending["revalidation_verified"] is False
    assert pending["fill_verification_reason"] == "evidence unavailable"
    assert pending["filled_ts"] == pending["progress_ts"] == NOW
    assert source.outcomes == [] and source.shelf is None
    assert len(messages) == 1 and messages[0][1] is False
    assert "BUY" in messages[0][0] and "evidence unavailable" in messages[0][0]


def test_successful_fill_uses_fresh_source_clock_not_supplied_pass_anchor(monkeypatch):
    """Catch a regression that reuses ``now`` for the later fill transition."""
    source = Source(now=NOW + 37.0)
    validation = install_validation(monkeypatch, (True, "still aligned", True))
    pending = trade(ts=NOW - 10.0)

    _messages, changed = resolve(source, pending, high=103.0, low=99.0, now=NOW)

    assert changed is True and pending["state"] == "OPEN"
    assert validation.calls == [(pending, NOW)]
    assert pending["filled_ts"] == pending["progress_ts"] == NOW + 37.0
