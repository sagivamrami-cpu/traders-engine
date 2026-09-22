"""Watch state keeps source JSON/persistence semantics, not tracker-save rules."""
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json

import pytest

from trading_system.tree_replay.clock import ReplayClock
from trading_system.tree_replay.tracker_storage import TrackerStateSeed, StateUnavailable


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)


def api():
    name = "trading_system.tree_replay.watch_storage"
    assert importlib.util.find_spec(name) is not None, "causal watch storage missing"
    return importlib.import_module(name)


def seed(text="{}", **changes):
    return api().WatchStateSeed(**(dict(seed_id="watch-test", source="synthetic",
        observed_at=T, available_at=T, covered_through=T+timedelta(seconds=10),
        status="PRESENT", text=text) | changes))


def store(text="{}", *, at=T, clock=None, **changes):
    return api().CausalWatchStorage(seed=seed(text, **changes), decision_time=at, clock=clock)


def test_heterogeneous_mutations_and_deletion_persist_only_on_explicit_save():
    s = store('{"cooldown":7,"episode":{"ts":8},"remove":true}')
    working = s.load()
    working.pop("remove")
    working["cooldown"] = 9
    working["episode"]["ts"] = 10
    assert s.load() == {"cooldown": 7, "episode": {"ts": 8}, "remove": True}
    s.save_before_producers(working)
    assert s.snapshot().text == '{"cooldown": 9, "episode": {"ts": 10}}'
    working["episode"]["ts"] = 11
    assert s.load()["episode"]["ts"] == 10
    s.save_final(working)
    assert s.load()["episode"]["ts"] == 11


def test_first_save_and_final_save_have_different_directory_effects():
    s = store()
    s.save_before_producers({"a": 1})
    s.save_final({"b": 2})
    assert [e["operation"] for e in s.trace] == [
        "save_before_producers", "ensure_directory", "write_text", "save_final", "write_text"]
    assert s.load() == {"b": 2}


def test_source_serialization_preserves_order_and_uses_default_ascii_spacing():
    s = store()
    s.save_final({"z": 2, "a": "א", "b": [True, None]})
    assert s.snapshot().text == '{"z": 2, "a": "\\u05d0", "b": [true, null]}'


@pytest.mark.parametrize("text,want", [("null", None), ("[1, false]", [1, False]), ("3", 3), ('"x"', "x")])
def test_nonobject_json_is_not_silently_normalized(text, want):
    s = store(text)
    assert s.load() == want
    s.save_final(want)
    assert s.load() == want


def test_watch_save_can_delete_majority_without_tracker_shrink_guard():
    s = store('{"a":1,"b":2,"c":3,"d":4}')
    s.save_final({"d": 4})
    assert s.load() == {"d": 4}
    assert [e["operation"] for e in s.trace][:2] == ["save_final", "write_text"]


def test_absent_load_is_known_empty_but_not_a_fabricated_present_file():
    s = store(None, status="ABSENT")
    assert s.load() == {}
    assert s.snapshot().status == "ABSENT"
    s.save_final({"new": 0})
    assert s.snapshot().status == "PRESENT" and s.load() == {"new": 0}


def test_unreadable_file_raises_on_load_but_can_be_overwritten_without_reread():
    s = store(None, status="UNREADABLE")
    with pytest.raises(OSError):
        s.load()
    assert [e["status"] for e in s.trace] == ["BLOCKED", "AVAILABLE", "BLOCKED"]
    s.save_final({"new": 1})
    assert s.load() == {"new": 1}


def test_malformed_json_raises_and_retains_outer_error_not_empty_state():
    s = store("{broken")
    with pytest.raises(json.JSONDecodeError):
        s.load()
    assert s.trace[0]["status"] == "BLOCKED"
    assert s.trace[0]["exception_type"] == "JSONDecodeError"
    assert s.snapshot().text == "{broken"


@pytest.mark.parametrize("method", ["save_before_producers", "save_final"])
def test_failed_serialization_preserves_saved_image_and_original_mkdir_order(method):
    s = store('{"old":1}')
    with pytest.raises(TypeError):
        getattr(s, method)({"invalid": object()})
    events = s.trace
    assert [e["operation"] for e in events] == ([method, "ensure_directory"] if method == "save_before_producers" else [method])
    assert events[0]["status"] == "BLOCKED"
    assert s.snapshot().text == '{"old":1}'


@pytest.mark.parametrize("fault,reason", [("unknown", "STATE_UNKNOWN"), ("future", "STATE_NOT_YET_AVAILABLE"), ("expired", "STATE_COVERAGE_EXPIRED")])
@pytest.mark.parametrize("operation", ["load", "save_before_producers", "save_final", "snapshot"])
def test_unavailable_artifacts_block_without_invented_writes(fault, reason, operation):
    kw = dict(text=None, status="UNKNOWN") if fault == "unknown" else {}
    at = T-timedelta(microseconds=1) if fault == "future" else T+timedelta(seconds=11) if fault == "expired" else T
    s = store(at=at, **kw)
    with pytest.raises(StateUnavailable, match=reason):
        getattr(s, operation)(*([{}] if operation.startswith("save") else []))
    assert len(s.trace) == 1 and s.trace[0]["status"] == "BLOCKED"


def test_shared_clock_preserves_saved_image_and_snapshot_handoff_at_coverage_edge():
    clock = ReplayClock(T)
    s = store(clock=clock)
    s.save_before_producers({"saved": 1})
    clock.advance_to(T+timedelta(seconds=10))
    handoff = s.snapshot()
    assert handoff.observed_at == handoff.available_at == clock.now
    assert handoff.covered_through == clock.now
    resumed = api().CausalWatchStorage(seed=handoff, decision_time=clock.now)
    assert resumed.load() == {"saved": 1}
    clock.advance_to(clock.now+timedelta(microseconds=1))
    with pytest.raises(StateUnavailable):
        s.save_final({"too_late": 1})
    assert resumed.load() == {"saved": 1}


def test_restart_image_excludes_mutations_after_first_save():
    s = store()
    working = {"cooldown": 1}
    s.save_before_producers(working)
    working["unsaved_episode"] = {"ts": 2}
    restarted = api().CausalWatchStorage(seed=s.snapshot(), decision_time=T)
    assert restarted.load() == {"cooldown": 1}
    s.save_final(working)
    assert s.load() == {"cooldown": 1, "unsaved_episode": {"ts": 2}}
    assert restarted.load() == {"cooldown": 1}


def test_trace_is_detached_from_caller_changes():
    s = store()
    s.load()
    trace = s.trace
    trace[0]["status"] = "forged"
    trace.clear()
    assert s.trace[0]["status"] == "AVAILABLE"


@pytest.mark.parametrize("fault", ["tracker_seed", "mismatched_clock", "fake_clock", "naive_time"])
def test_exact_seed_and_shared_clock_binding_are_required(fault):
    original = seed()
    kw = dict(seed=original, decision_time=T)
    if fault == "tracker_seed":
        kw["seed"] = TrackerStateSeed(**original.__dict__)
    elif fault == "mismatched_clock":
        kw["clock"] = ReplayClock(T+timedelta(seconds=1))
    elif fault == "fake_clock":
        kw["clock"] = object()
    else:
        kw["decision_time"] = T.replace(tzinfo=None)
    with pytest.raises(ValueError):
        api().CausalWatchStorage(**kw)
