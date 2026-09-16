"""A shared operation clock must not reset artifacts or imply data availability."""
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util

import pandas as pd
import pytest

from trading_system.tree_replay.admission_io import ArtifactSeed, CausalQuoteReader, CausalWatchLog, InputUnavailable
from trading_system.tree_replay.tracker_storage import CausalTrackerStorage, TrackerStateSeed, StateUnavailable
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
from trading_system.tree_replay.admission_context import CausalAdmissionContext, BusyMarkerSeed
from trading_system.tree_replay.watch_storage import CausalWatchStorage, WatchStateSeed
from trading_system.tree_replay.admission_frames import AdmissionFrameRequest

T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)


def api():
    name = "trading_system.tree_replay.clock"
    assert importlib.util.find_spec(name) is not None, "shared replay clock missing"
    return importlib.import_module(name)


def state_seed(**changes):
    return TrackerStateSeed(**(dict(seed_id="state", source="synthetic", observed_at=T,
        available_at=T, covered_through=T+timedelta(seconds=20), status="ABSENT", text=None) | changes))


def artifact(kind, **changes):
    return ArtifactSeed(**(dict(seed_id=kind, source="synthetic", kind=kind, observed_at=T,
        available_at=T, covered_through=T+timedelta(seconds=20), status="PRESENT",
        content=b"old\n" if kind == "watch_log" else '{"OANDA:XAUUSD":{"lp":100,"ts":1788969180}}') | changes))


def contexts(clock):
    return (CausalTrackerStorage(seed=state_seed(), decision_time=T, clock=clock),
            CausalQuoteReader(seed=artifact("quotes"), decision_time=T, clock=clock),
            CausalWatchLog(seed=artifact("watch_log"), decision_time=T, newline="LF", clock=clock))


def test_shared_advance_retains_generated_state_effects_and_source_quote_freshness():
    clock = api().ReplayClock(T)
    storage, quotes, log = contexts(clock)
    storage.save({"a": {"state": "PENDING"}})
    storage.save({"a": {"state": "PENDING"}, "b": {"state": "PENDING"}})
    before_effects = storage.creation_effects
    assert TrackerAdmission(quotes)._live_prices() == {"OANDA:XAUUSD": 100.0}
    clock.advance_to(T+timedelta(seconds=2))
    assert storage.load() == {"a": {"state": "PENDING"}, "b": {"state": "PENDING"}}
    assert storage.creation_effects == before_effects
    assert storage.snapshot().available_at == T+timedelta(seconds=2)
    assert TrackerAdmission(quotes)._live_prices() == {}  # Now422seconds old.
    assert log.now_epoch() == quotes.now_epoch() == 1788969602.0
    assert storage.trace[-1]["decision_time"] == "2026-09-09T16:00:02+00:00"


def test_log_uses_current_shared_timestamp_and_keeps_captured_reader_prefix():
    clock = api().ReplayClock(T)
    _, _, log = contexts(clock)
    reader = log.event_log_reader()
    clock.advance_to(T+timedelta(seconds=2))
    log.log({"kind": "probe"})
    assert reader.read() == b"old\n"
    assert log.snapshot().content == b'old\n{"ts": 1788969602.0, "kind": "probe", "sessions": ["newyork"]}\n'
    assert log.snapshot().available_at == clock.now


def test_shared_log_advance_updates_other_bindings_but_keeps_its_coverage_guard():
    clock = api().ReplayClock(T)
    storage, quotes, log = contexts(clock)
    log.advance_to(T+timedelta(seconds=3))
    assert quotes.now_epoch() == 1788969603.0
    assert storage.snapshot().available_at == clock.now == T+timedelta(seconds=3)
    with pytest.raises(InputUnavailable, match="COVERAGE_EXPIRED"):
        log.advance_to(T+timedelta(seconds=21))
    assert clock.now == T+timedelta(seconds=3)


def test_clock_can_advance_past_coverage_without_certifying_artifacts():
    clock = api().ReplayClock(T)
    storage, quotes, log = contexts(clock)
    clock.advance_to(T+timedelta(seconds=21))
    for action, error in [(storage.load, StateUnavailable),
                          (quotes.quote_payload, InputUnavailable),
                          (log.event_log_reader, InputUnavailable)]:
        with pytest.raises(error, match="COVERAGE_EXPIRED"):
            action()
    assert all(c.trace[-1]["status"] == "BLOCKED" for c in (storage, quotes, log))
    assert quotes.now_epoch() == 1788969621.0  # Time itself is independent of quotes.


def test_delayed_publication_becomes_readable_at_actual_shared_time():
    clock = api().ReplayClock(T)
    quotes = CausalQuoteReader(seed=artifact("quotes", available_at=T+timedelta(seconds=2)),
                              decision_time=T, clock=clock)
    assert TrackerAdmission(quotes)._live_prices() == {}
    assert quotes.trace[-1]["status"] == "BLOCKED"
    clock.advance_to(T+timedelta(seconds=2))
    assert quotes.quote_payload()["OANDA:XAUUSD"]["lp"] == 100
    assert quotes.trace[-1]["decision_time"] == "2026-09-09T16:00:02+00:00"


@pytest.mark.parametrize("bad", [T-timedelta(microseconds=1), T.replace(tzinfo=None),
    pd.Timestamp("2026-09-09T16:00:00.000000001Z"), "2026-09-09", None])
def test_invalid_or_backward_advance_is_atomic(bad):
    clock = api().ReplayClock(T)
    with pytest.raises(ValueError):
        clock.advance_to(bad)
    assert clock.now == T


def test_equal_time_and_timezone_equivalent_advance_do_not_lose_microseconds():
    at = T+timedelta(microseconds=7)
    clock = api().ReplayClock(at.astimezone(timezone(timedelta(hours=3))))
    clock.advance_to(at)
    assert clock.now == at and type(clock.now) is datetime
    with pytest.raises(AttributeError):
        clock.now = T


@pytest.mark.parametrize("kind", ["storage", "quotes", "log"])
@pytest.mark.parametrize("mode", ["wrong_type", "wrong_time"])
def test_bound_context_requires_exact_clock_at_its_declared_initial_time(kind, mode):
    cls = api().ReplayClock
    clock = object() if mode == "wrong_type" else cls(T+timedelta(seconds=1))
    with pytest.raises(ValueError):
        if kind == "storage":
            CausalTrackerStorage(seed=state_seed(), decision_time=T, clock=clock)
        elif kind == "quotes":
            CausalQuoteReader(seed=artifact("quotes"), decision_time=T, clock=clock)
        else:
            CausalWatchLog(seed=artifact("watch_log"), decision_time=T, newline="LF", clock=clock)


def test_clock_subclasses_cannot_override_time_validation_in_bindings():
    class ForeignClock(api().ReplayClock):
        pass
    with pytest.raises(ValueError):
        CausalQuoteReader(seed=artifact("quotes"), decision_time=T, clock=ForeignClock(T))


def test_standalone_contexts_remain_independent_of_external_clock():
    clock = api().ReplayClock(T)
    storage = CausalTrackerStorage(seed=state_seed(), decision_time=T)
    quotes = CausalQuoteReader(seed=artifact("quotes"), decision_time=T)
    log = CausalWatchLog(seed=artifact("watch_log"), decision_time=T, newline="LF")
    clock.advance_to(T+timedelta(days=2))
    assert storage.load() == {}
    assert quotes.now_epoch() == log.now_epoch() == 1788969600.0
    log.advance_to(T+timedelta(seconds=2))
    assert storage.snapshot().available_at == T and quotes.now_epoch() == 1788969600.0


def test_session_default_is_recomputed_at_shared_clock_not_construction_time():
    early = datetime(2026, 9, 9, 11, 59, tzinfo=timezone.utc)
    clock = api().ReplayClock(early)
    log = CausalWatchLog(seed=artifact("watch_log", observed_at=early,
        available_at=early, covered_through=T), decision_time=early, newline="LF", clock=clock)
    clock.advance_to(T)
    row = {}
    log.log(row)
    assert row == {"sessions": ["newyork"]}


def test_context_and_watch_share_one_monotonic_clock():
    from test_admission_context import context as make_context
    clock = api().ReplayClock(T)
    admission = make_context(clock=clock)
    watch = CausalWatchStorage(seed=WatchStateSeed(
        seed_id="watch", source="synthetic", observed_at=T, available_at=T,
        covered_through=T + timedelta(seconds=20), status="PRESENT", text="{}",
    ), decision_time=T, clock=clock)
    admission.advance_to(T + timedelta(seconds=1))
    assert admission.decision_time == watch.snapshot().observed_at == clock.now
