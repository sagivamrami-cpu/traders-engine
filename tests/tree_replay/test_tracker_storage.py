"""Original storage decisions on causal text, not a fake successful save sink."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission


T = datetime(2026, 9, 9, 16, tzinfo=timezone.utc)
SYM = "OANDA:XAUUSD"
LONG = "לונג"


def api():
    name = "trading_system.tree_replay.tracker_storage"
    assert importlib.util.find_spec(name) is not None, "causal tracker storage missing"
    return importlib.import_module(name)


def seed(status="PRESENT", text="{}", **changes):
    return api().TrackerStateSeed(**(dict(seed_id="source-state-1", source="synthetic",
        observed_at=T-timedelta(hours=1), available_at=T-timedelta(minutes=30),
        covered_through=T+timedelta(hours=1), status=status,
        text=text if status == "PRESENT" else None) | changes))


def storage(status="PRESENT", text="{}", *, decision_time=T, **changes):
    return api().CausalTrackerStorage(seed=seed(status, text, **changes),
                                    decision_time=decision_time)


def test_absence_and_corrupt_state_are_not_the_same():
    assert storage("ABSENT").load() == {}
    with pytest.raises(json.JSONDecodeError):
        storage(text="{torn").load()
    with pytest.raises(OSError):
        storage("UNREADABLE").load()
    assert TrackerAdmission(storage(text="{torn")).has_open(SYM, LONG)


@pytest.mark.parametrize("text,want", [("null", None), ("[]", []), ("12", 12)])
def test_source_nonobject_json_is_not_normalized_to_empty(text, want):
    s = storage(text=text)
    assert s.load() == want
    assert TrackerAdmission(s).has_open(SYM, LONG)


def test_root_order_and_loaded_mutation_do_not_change_storage():
    s = storage(text='{"z": {"state": "PENDING"}, "a": {"state": "DONE"}}')
    first = s.load()
    assert list(first) == ["z", "a"]
    first["z"]["state"] = "OPEN"
    del first["a"]
    assert s.load() == {"z": {"state": "PENDING"}, "a": {"state": "DONE"}}
    assert list(s.load()) == ["z", "a"]


@pytest.mark.parametrize("count,remaining,refused", [(3, 0, False), (4, 2, False),
    (4, 1, True), (5, 3, False), (5, 2, True), (6, 3, False), (6, 2, True)])
def test_original_shrink_boundary(count, remaining, refused):
    initial = {str(i): {} for i in range(count)}
    wanted = {str(i): {} for i in range(remaining)}
    s = storage(text=json.dumps(initial))
    if refused:
        with pytest.raises(RuntimeError, match=f"would drop {count-remaining}/{count} keys"):
            s.save(wanted)
        assert s.load() == initial
        assert len(s.quarantine_artifacts) == 1
    else:
        s.save(wanted)
        assert s.load() == wanted and not s.quarantine_artifacts


def test_quarantine_literal_payload_name_and_same_second_replacement():
    s = storage(text='{"z": {}, "a": {}, "b": {}, "c": {}}')
    with pytest.raises(RuntimeError, match="dict quarantined at open_trades.rejected-1788969600"):
        s.save({"z": {}})
    assert s.quarantine_artifacts == {"open_trades.rejected-1788969600": '{\n "z": {}\n}'}
    with pytest.raises(RuntimeError):
        s.save({"a": {}})
    assert s.quarantine_artifacts == {"open_trades.rejected-1788969600": '{\n "a": {}\n}'}
    assert list(s.load()) == ["z", "a", "b", "c"]


@pytest.mark.parametrize("status,text", [("PRESENT", "{torn"), ("PRESENT", "null"),
                                         ("UNREADABLE", None)])
def test_unreadable_or_null_current_state_quarantines(status, text):
    s = storage(status, text)
    with pytest.raises(RuntimeError, match="state unreadable"):
        s.save({"z": {}})
    assert s.snapshot().status == status and s.snapshot().text == text
    assert list(s.quarantine_artifacts) == ["open_trades.rejected-1788969600"]


@pytest.mark.parametrize("status,text", [("PRESENT", "{torn"), ("UNREADABLE", None),
                                         ("PRESENT", '{"a": {}, "b": {}, "c": {}, "d": {}}')])
def test_explicit_allow_shrink_bypasses_source_reread_and_forensics(status, text):
    s = storage(status, text)
    s.save({"new": {"state": "PENDING"}}, allow_shrink=True)
    assert s.load() == {"new": {"state": "PENDING"}}
    assert not s.quarantine_artifacts and not s.creation_effects
    assert not any(e["operation"] == "read_text" for e in s.trace[:-2])


def test_save_rereads_current_state_not_cached_load():
    s = storage(text='{"a": {}}')
    stale = s.load()
    s.save({"a": {}, "b": {}, "c": {}, "d": {}})
    with pytest.raises(RuntimeError, match="would drop 3/4 keys"):
        s.save(stale)
    assert list(s.load()) == ["a", "b", "c", "d"]


def test_creation_effect_precedes_quarantine_and_is_not_fabricated_process_log():
    s = storage(text='{"a": {}, "b": {}, "c": {}, "d": {}}')
    with pytest.raises(RuntimeError):
        s.save({"new": {"entry": 100, "state": "PENDING"}})
    assert s.creation_effects == [{"origin": "replay_creation_effect", "ts": 1788969600.,
        "key": "new", "record": {"entry": 100, "stop": None, "state": "PENDING",
                                   "variant": None, "revived_from_ts": None}}]
    ops = [e["operation"] for e in s.trace]
    assert ops.index("audit_creation") < ops.index("write_quarantine")
    returned = s.creation_effects
    returned[0]["record"]["entry"] = -1
    assert s.creation_effects[0]["record"]["entry"] == 100


def test_forensic_bad_record_is_best_effort_but_set_errors_propagate():
    s = storage()
    s.save({"bad": 4})  # .get fails inside best-effort forensic boundary
    assert s.load() == {"bad": 4} and not s.creation_effects
    noniterable = storage(text="12")
    with pytest.raises(TypeError):
        noniterable.save({"new": {}})  # set(cur) fails before original try
    assert noniterable.load() == 12 and not noniterable.quarantine_artifacts


def test_first_file_creation_has_no_source_creation_audit_and_preserves_json_format():
    s = storage("ABSENT")
    s.save({"z": {"direction": LONG}, "a": {}})
    assert not s.creation_effects
    assert s.snapshot().text == '{\n "z": {\n  "direction": "לונג"\n },\n "a": {}\n}'


def test_unserializable_forensic_value_does_not_leave_a_creation_effect():
    s = storage()
    with pytest.raises(TypeError):
        s.save({"new": {"entry": object()}})
    assert s.creation_effects == []
    assert s.load() == {}


def test_swallowed_forensic_extraction_failure_is_traced_without_vetoing_save():
    s = storage()
    s.save({"bad": 4})
    assert s.load() == {"bad": 4} and s.creation_effects == []
    failed = [e for e in s.trace if e["operation"] == "creation_effect"]
    assert len(failed) == 1 and failed[0]["status"] == "BLOCKED"
    assert failed[0]["exception_type"] == "AttributeError"
    assert "get" in failed[0]["blocker"]
    assert next(e for e in s.trace if e["operation"] == "save")["status"] == "AVAILABLE"
    returned = s.trace
    returned[0]["status"] = "changed"
    assert s.trace[0]["status"] == "AVAILABLE"


def test_forensic_serialization_failure_has_its_own_failed_effect_trace():
    s = storage()
    with pytest.raises(TypeError):
        s.save({"bad": {"entry": object()}})
    assert s.creation_effects == [] and s.load() == {}
    failed = [e for e in s.trace if e["operation"] == "creation_effect"]
    assert len(failed) == 1 and failed[0]["status"] == "BLOCKED"
    assert failed[0]["exception_type"] == "TypeError"
    assert "JSON serializable" in failed[0]["blocker"]


def test_partial_forensic_emission_stops_after_traced_failure_but_state_saves():
    s = storage()
    rows = {key: {} for key in ("a", "b", "c")}
    # Position the bad row using this process's set order; do not assert a
    # cross-process ordering policy for forensic (non-trading) effects.
    order = list(set(rows)-set())
    rows[order[0]] = {"entry": 10}
    rows[order[1]] = 4
    rows[order[2]] = {"entry": 30}
    s.save(rows)
    assert s.load() == rows
    assert [(e["key"], e["record"]["entry"]) for e in s.creation_effects] == [(order[0], 10)]
    attempts = [e for e in s.trace if e["operation"] == "creation_effect"]
    assert [(e["status"], e["exception_type"]) for e in attempts] == [
        ("AVAILABLE", None), ("BLOCKED", "AttributeError")]
    operations = [e["operation"] for e in s.trace]
    assert operations.index("creation_effect") < operations.index("atomic_write")


@pytest.mark.parametrize("changes", [dict(available_at=T+timedelta(seconds=1)),
    dict(covered_through=T-timedelta(seconds=1)), dict(status="UNKNOWN", text=None)])
def test_unavailable_input_blocks_reads_writes_and_survives_tracker_catch(changes):
    s = storage(**changes)
    assert TrackerAdmission(s).has_open(SYM, LONG)
    with pytest.raises(api().StateUnavailable):
        s.save({}, allow_shrink=True)
    with pytest.raises(api().StateUnavailable):
        s.snapshot()
    assert not s.quarantine_artifacts and not s.creation_effects
    assert any(e["status"] == "BLOCKED" for e in s.trace)


def test_same_artifact_can_continue_at_later_time_only_within_coverage():
    s = storage("ABSENT")
    s.save({"z": {"state": "PENDING"}})
    after = s.snapshot()
    assert after.observed_at == after.available_at == T
    assert after.covered_through == T+timedelta(hours=1)
    next_store = api().CausalTrackerStorage(seed=after, decision_time=T+timedelta(minutes=5))
    next_store.save({"z": {"state": "DONE"}})
    assert s.load()["z"]["state"] == "PENDING"
    assert next_store.load()["z"]["state"] == "DONE"
    past = api().CausalTrackerStorage(seed=after, decision_time=T-timedelta(microseconds=1))
    with pytest.raises(api().StateUnavailable):
        past.load()


@pytest.mark.parametrize("changes", [dict(seed_id=""), dict(source=" x "),
    dict(seed_id="\ud800"), dict(status="present"), dict(status=1),
    dict(text=b"{}"), dict(text="\ud800"), dict(status="ABSENT", text="{}"),
    dict(observed_at=T.replace(tzinfo=None)), dict(observed_at=pd.Timestamp(T)+pd.Timedelta(1, 'ns')),
    dict(observed_at=T), dict(covered_through=T-timedelta(hours=2))])
def test_bad_seed_contract_rejected(changes):
    with pytest.raises(ValueError):
        replace(seed(), **changes)


def test_frozen_seed_and_exact_store_input_types():
    given = seed()
    with pytest.raises(FrozenInstanceError):
        given.text = "[]"
    with pytest.raises(ValueError):
        api().CausalTrackerStorage(seed={}, decision_time=T)
    with pytest.raises(ValueError):
        api().CausalTrackerStorage(seed=given, decision_time=T.replace(tzinfo=None))


def test_source_live_test_guard_remains_before_any_write(monkeypatch):
    s = storage()
    monkeypatch.setattr(s.source, "is_live_test_target", lambda: True)
    with pytest.raises(RuntimeError, match="refusing to write the live"):
        s.save({"x": {}}, allow_shrink=True)
    assert s.load() == {} and not s.quarantine_artifacts


@pytest.mark.parametrize("port", ["atomic_write", "write_quarantine"])
def test_failed_write_does_not_replace_current_state(monkeypatch, port):
    s = storage(text='{"a": {}, "b": {}, "c": {}, "d": {}}')
    def fail(*args):
        raise OSError("synthetic disk boundary failure")
    monkeypatch.setattr(s.source, port, fail)
    with pytest.raises(OSError, match="synthetic disk boundary failure"):
        s.save({"a": {}}, allow_shrink=(port == "atomic_write"))
    assert list(s.load()) == ["a", "b", "c", "d"]


def test_real_record_persists_through_source_storage_then_exposure_blocks():
    from test_tracker_admission import MemoryPorts, plan
    state = storage("ABSENT")
    class Ports(MemoryPorts):
        def load(self):
            return state.load()
        def save(self, rows):
            state.save(rows)
        def now_epoch(self):
            return T.timestamp()
    ports = Ports()
    tracker = TrackerAdmission(ports)
    assert tracker.record(plan(close=100.))
    row = next(iter(state.load().values()))
    assert row["state"] == "OPEN" and row["ts"] == 1788969600.
    assert row["revalidation_verified"] is False  # not an economic fill
    assert tracker.has_open(SYM, LONG)
    assert tracker.record(plan(close=100.)) is False
    assert len(state.load()) == 1


def test_first_same_level_match_follows_original_insertion_order():
    old = {"symbol": SYM, "direction": LONG, "state": "DONE", "entry": 100.,
           "resolved_ts": T.timestamp()-300}
    newer = old | {"resolved_ts": T.timestamp()-60}
    s = storage(text=json.dumps({"z": old, "a": newer}))
    class Ports:
        load = s.load
        def now_epoch(self):
            return T.timestamp()
    reason = TrackerAdmission(Ports()).blocked_same_level(SYM, LONG, 100.)
    assert "5" in reason and "100.00" in reason
