"""Real causal providers and original tracker; all supplied history is synthetic."""
from dataclasses import replace
from datetime import timedelta
import importlib
import importlib.util
import json

import pytest

from trading_system.tree_replay.admission_io import ArtifactSeed, InputUnavailable
from trading_system.tree_replay.tracker_storage import TrackerStateSeed, StateUnavailable
from trading_system.tree_replay._vendor.pricing import Plan
from trading_system.tree_replay._vendor.tracker_lock import LockBusy
from test_admission_frames import T, SYMBOL, KEYS, request


def api():
    name = "trading_system.tree_replay.admission_context"
    assert importlib.util.find_spec(name) is not None, "causal admission context missing"
    return importlib.import_module(name)


def seed(channel, *, at=T, status="PRESENT", value=None, through=None):
    common = dict(seed_id=channel+at.isoformat(), source="synthetic", observed_at=at,
                  available_at=at, covered_through=through or T+timedelta(minutes=5), status=status)
    if channel in ("tracker", "busy"):
        cls = TrackerStateSeed if channel == "tracker" else api().BusyMarkerSeed
        return cls(**common, text=(value if value is not None else "{}") if status == "PRESENT" else None)
    content = (json.dumps({SYMBOL: {"lp": 100, "ts": at.timestamp()}}) if channel == "quotes"
               else b"") if value is None else value
    return ArtifactSeed(**common, kind=channel, content=content if status == "PRESENT" else None)


def step(name, start=T, end=None, *, index=0, acquired=True, error=None, timeout=30.0):
    return api().LockStep(step_id=f"{index}:{name}", source="synthetic", operation=name,
        started_at=start, completed_at=end or start, timeout=timeout if name == "acquire" else None,
        acquired=acquired if name == "acquire" and error is None else None, error=error)


def steps(*, start=T, seconds=2, acquired=True, release_error=None, acquire_error=None):
    end = start+timedelta(seconds=seconds)
    rows = [step("prepare", start, index=0), step("open", start, index=1),
            step("acquire", start, end, index=2, acquired=acquired, error=acquire_error)]
    if acquired and acquire_error is None:
        rows.append(step("release", end, index=3, error=release_error))
    rows.append(step("close", end, index=4))
    return tuple(rows)


def publication(channel, payload, *, at=None, seq=0, name="pub"):
    return api().Publication(publication_id=name, source="synthetic", channel=channel,
        payload=payload, available_at=at or payload.available_at, sequence=seq)


def context(**changes):
    return api().CausalAdmissionContext(**(dict(instrument=SYMBOL, decision_time=T,
        tracker_seed=seed("tracker"), quote_seed=seed("quotes"), log_seed=seed("watch_log"),
        busy_seed=seed("busy", status="ABSENT"), newline="LF",
        frame_requests=tuple(request(tf, days) for tf, days in KEYS),
        publications=(), lock_steps=steps()) | changes))


def plan(**changes):
    return replace(Plan(SYMBOL, 100., "reversal", "לונג", entry=100., stop=90.,
                        targets=[("TP1", 120.)], reasons=["רמה: DAY-OPEN"]), **changes)


def test_real_frames_quotes_storage_lock_and_tracker_record_are_composed():
    c = context()
    assert c.tracker.record(plan())
    row = next(iter(c.load().values()))
    assert row["bias_at_send"] == {"4h": -41.25, "1h": -41.25}
    assert row["ts"] == row["filled_ts"] == (T+timedelta(seconds=2)).timestamp()
    assert row["state"] == "OPEN" and row["revalidation_verified"] is False
    assert c.pass_anchor == T and c.decision_time == T+timedelta(seconds=2)
    r = c.report()
    assert r["lock_steps_consumed"] == 5 and not r["ready_for_training"] and not r["ready_for_replay"]
    assert [e["operation"] for e in r["events"]][:3] == ["read_symbol", "read_symbol", "quote_payload"]
    assert [len(f["fetch_trace"]) for f in r["frames"]] == [2, 5]
    assert all(e["status"] == "AVAILABLE" for e in r["events"])


def test_open_exposure_published_during_acquire_prevents_record_without_backdating():
    at = T+timedelta(seconds=1)
    body = {"other": {"symbol": SYMBOL, "direction": "לונג", "state": "OPEN", "entry": 100., "ts": at.timestamp()}}
    p = publication("tracker", seed("tracker", at=at, value=json.dumps(body)))
    c = context(publications=(p,))
    assert c.load() == {}  # Future input supplied to constructor is not current state.
    assert not c.tracker.record(plan())
    assert c.load() == body
    assert c.report()["publications_consumed"] == 1
    assert c.pass_anchor == T and c.decision_time == T+timedelta(seconds=2)


def test_quote_publication_changes_later_reads_not_already_computed_born_state():
    at = T+timedelta(seconds=1)
    p = publication("quotes", seed("quotes", at=at, value=json.dumps({SYMBOL: {"lp": 200, "ts": at.timestamp()}})))
    c = context(publications=(p,))
    assert c.tracker.record(plan())
    assert next(iter(c.load().values()))["state"] == "OPEN"  # born decision was pre-lock.
    assert c.tracker._live_prices() == {SYMBOL: 200.}


def test_same_time_publications_follow_explicit_sequence_without_merging_images():
    at = T+timedelta(seconds=1)
    first = publication("tracker", seed("tracker", at=at, value='{"first":1}'), seq=2, name="a")
    second = publication("tracker", seed("tracker", at=at, value='{"second":2}'), seq=3, name="b")
    c = context(publications=(first, second))
    c.advance_to(at)
    assert c.load() == {"second": 2}
    assert [e["publication_id"] for e in c.report()["events"] if e["operation"] == "publication"] == ["a", "b"]


def test_generated_state_and_effects_survive_advance_and_replacement_history():
    at = T+timedelta(seconds=4)
    p = publication("tracker", seed("tracker", at=at, value='{"external":{}}'))
    c = context(publications=(p,))
    c.save({"generated": {"state": "PENDING"}})
    c.advance_to(T+timedelta(seconds=2))
    assert c.load() == {"generated": {"state": "PENDING"}}
    c.advance_to(at)
    assert c.load() == {"external": {}}
    states = [a for a in c.report()["artifacts"] if a["channel"] == "tracker"]
    assert len(states) == 2 and states[0]["creation_effects"][0]["key"] == "generated"


def test_real_rejection_consumer_reads_same_pass_append_and_old_reader_stays_old():
    c = context()
    reader = c.event_log_reader()
    def recent():
        return c.tracker._recent_rejection(SYMBOL, "לונג", T.timestamp()-10, c.now_epoch(), 100.)
    assert recent() is None
    c.log({"kind": "rejection", "symbol": SYMBOL, "direction": "לונג",
           "zone_lo": 98, "zone_hi": 102, "levels": ["PSY"], "close": 100, "wick_atr": .5})
    c.advance_to(T+timedelta(seconds=2))
    assert recent()["levels"] == ["PSY"] and recent()["age_s"] == 2.
    assert reader.read() == b""


def test_log_replacement_is_full_image_and_keeps_prepublication_reader_prefix():
    at = T+timedelta(seconds=1)
    p = publication("watch_log", seed("watch_log", at=at, value=b"external\n"))
    c = context(log_seed=seed("watch_log", value=b"old\n"), publications=(p,))
    reader = c.event_log_reader()
    c.advance_to(at)
    assert c.event_log_reader().read() == b"external\n" and reader.read() == b"old\n"
    assert len([a for a in c.report()["artifacts"] if a["channel"] == "watch_log"]) == 2


def test_frame_publication_changes_actual_calculations_at_publication_time_only():
    at = T+timedelta(seconds=1)
    new = tuple(request(tf, days, price=110.) for tf, days in KEYS)
    c = context(publications=(publication("frames", new, at=at),))
    assert c.read_symbol(SYMBOL, ("4h",))["4h"].close == 100.
    c.advance_to(at)
    assert c.read_symbol(SYMBOL, ("4h",))["4h"].close == 110.


def test_replay_publication_schedule_view_is_read_only_and_does_not_advance_context():
    at = T + timedelta(minutes=1)
    scheduled = publication("frames", tuple(request(tf, days) for tf, days in KEYS), at=at)
    c = context(publications=(scheduled,))

    assert c.replay_publications_through(at) == (scheduled,)
    assert c.decision_time == T
    assert c.report()["publications_consumed"] == 0


def test_data_gap_stays_blocked_until_next_published_image():
    at = T+timedelta(seconds=4)
    c = context(tracker_seed=seed("tracker", through=T+timedelta(seconds=1)),
        publications=(publication("tracker", seed("tracker", at=at, value='{"new":{}}')),))
    c.advance_to(T+timedelta(seconds=2))
    with pytest.raises(StateUnavailable, match="COVERAGE_EXPIRED"):
        c.load()
    c.advance_to(at)
    assert c.load() == {"new": {}}


@pytest.mark.parametrize("channel", ["tracker", "quotes", "watch_log"])
def test_source_caught_missing_inputs_remain_in_context_and_child_traces(channel):
    kw = {dict(tracker="tracker_seed", quotes="quote_seed", watch_log="log_seed")[channel]: seed(channel, status="UNKNOWN")}
    c = context(**kw)
    if channel == "tracker":
        assert c.tracker.has_open(SYMBOL, "לונג") is True
    elif channel == "quotes":
        assert c.tracker._live_prices() == {}
    else:
        assert c.tracker._recent_rejection(SYMBOL, "לונג", 0, T.timestamp(), 100) is None
    r = c.report()
    assert any(e["status"] == "BLOCKED" for e in r["events"])
    assert any(e["status"] == "BLOCKED" for a in r["artifacts"] for e in a["trace"])


def test_missing_frame_request_keeps_original_catch_and_failure_evidence():
    c = context(frame_requests=())
    assert c.tracker._higher_bias(SYMBOL) is None
    r = c.report()
    assert r["frames"][0]["fetch_trace"][0]["blocker"] == "REQUEST_MISSING"
    assert r["events"][0]["status"] == "BLOCKED"


@pytest.mark.parametrize("fault", ["missing", "name", "timeout", "time"])
def test_lock_evidence_is_required_and_exact_not_default_success(fault):
    rows = steps()
    if fault == "missing":
        rows = ()
    elif fault == "name":
        rows = (replace(rows[0], operation="open"),)+rows[1:]
    elif fault == "timeout":
        rows = rows[:2]+(replace(rows[2], timeout=3.),)+rows[3:]
    else:
        rows = tuple(replace(s, started_at=s.started_at+timedelta(seconds=1),
                             completed_at=s.completed_at+timedelta(seconds=1)) for s in rows)
    c = context(lock_steps=rows)
    with pytest.raises(api().OperationUnavailable):
        c.tracker.record(plan())
    assert c.load() == {}
    assert any(e["status"] == "BLOCKED" for e in c.report()["events"])


@pytest.mark.parametrize("where", ["acquire", "release"])
def test_supplied_io_failure_advances_clock_and_closes_handle_with_source_semantics(where):
    c = context(lock_steps=steps(**{where+"_error": "supplied failure"}))
    with pytest.raises(OSError, match="supplied failure"):
        c.tracker.record(plan())
    assert c.decision_time == T+timedelta(seconds=2)
    assert c.report()["events"][-1]["operation"] == "lock.close"
    assert bool(c.load()) is (where == "release")  # Source save can precede release failure.


def test_nested_source_lock_uses_one_script_and_preserves_depth():
    c = context()
    with c.locked():
        with c.locked(skip_if_busy=True):
            assert c.now_epoch() == (T+timedelta(seconds=2)).timestamp()
    assert c.report()["lock_steps_consumed"] == 5


def test_resolver_busy_marks_then_skips_without_invented_release():
    c = context(lock_steps=steps(acquired=False))
    with pytest.raises(LockBusy):
        with c.locked(wait=30., skip_if_busy=True):
            pytest.fail("must skip initial refusal")
    assert c.report()["lock_steps_consumed"] == 4
    assert any(e["operation"] == "busy.write" for e in c.report()["events"])


def test_unknown_busy_clear_failure_survives_source_best_effort_catch():
    c = context(busy_seed=seed("busy", status="UNKNOWN"))
    with c.locked():
        pass
    assert any(e["operation"] == "busy.clear" and e["status"] == "BLOCKED" for e in c.report()["events"])


def test_report_is_detached_and_does_not_expose_future_publication_payloads():
    at = T+timedelta(seconds=3)
    c = context(publications=(publication("tracker", seed("tracker", at=at, value='{"secret_future":42}')),))
    c.load()
    report = c.report()
    assert "secret_future" not in json.dumps(report)
    report["events"][0]["status"] = "changed"
    assert c.report()["events"][0]["status"] == "AVAILABLE"


@pytest.mark.parametrize("fault", ["duplicate_id", "reverse_order", "before_initial", "bad_payload"])
def test_invalid_publication_schedule_rejected_before_context_runs(fault):
    at = T+timedelta(seconds=2)
    a = publication("tracker", seed("tracker", at=at), name="a")
    b = publication("quotes", seed("quotes", at=at), seq=1, name="b")
    if fault == "duplicate_id":
        rows = (a, replace(b, publication_id="a"))
    elif fault == "reverse_order":
        rows = (b, a)
    elif fault == "before_initial":
        rows = (publication("tracker", seed("tracker", at=T-timedelta(seconds=1))),)
    else:
        with pytest.raises(ValueError):
            replace(a, payload=seed("quotes", at=at))
        return
    with pytest.raises(ValueError):
        context(publications=rows)


def test_bad_advance_has_no_effect_on_clock_publication_cursor_or_generated_state():
    c = context()
    c.save({"a": {}})
    before = c.report()["publications_consumed"]
    with pytest.raises(ValueError):
        c.advance_to(T-timedelta(microseconds=1))
    assert c.decision_time == T and c.load() == {"a": {}}
    assert c.report()["publications_consumed"] == before


def test_consumed_lock_operations_retain_exact_evidence_identity():
    c = context()
    with c.locked():
        pass
    events = [e for e in c.report()["events"] if e["operation"].startswith("lock.")]
    assert [e["step_id"] for e in events] == ["0:prepare", "1:open", "2:acquire", "3:release", "4:close"]
    assert all(e["evidence_source"] == "synthetic" for e in events)


def test_bool_timeout_call_is_not_certified_by_numeric_evidence():
    c = context(lock_steps=tuple(replace(s, timeout=1.) if s.operation == "acquire" else s for s in steps()))
    with pytest.raises(api().OperationUnavailable):
        with c.locked(wait=True):
            pytest.fail("boolean wait must not match numeric evidence")


@pytest.mark.parametrize("change", [dict(sequence=True), dict(sequence=-1), dict(sequence=1.),
    dict(publication_id=" "), dict(source="bad\ud800"), dict(channel="wrong"),
    dict(available_at=T.replace(tzinfo=None)), dict(available_at=T+timedelta(seconds=1))])
def test_publication_validation_rejects_ambiguous_identity_order_and_time(change):
    p = publication("tracker", seed("tracker"))
    with pytest.raises(ValueError):
        replace(p, **change)


@pytest.mark.parametrize("change", [dict(timeout=True), dict(timeout=float("nan")), dict(timeout=None),
    dict(acquired=1), dict(error=123), dict(error="bad\ud800", acquired=None),
    dict(error="failure"), dict(operation="unknown"), dict(step_id=" "),
    dict(completed_at=T-timedelta(microseconds=1)), dict(started_at=T.replace(tzinfo=None))])
def test_lock_step_validation_rejects_invalid_or_ambiguous_evidence(change):
    s = step("acquire")
    with pytest.raises(ValueError):
        replace(s, **change)


@pytest.mark.parametrize("fault", ["duplicate", "overlap", "list"])
def test_lock_schedule_is_validated_before_any_port_call(fault):
    rows = steps()
    if fault == "duplicate":
        rows = rows[:1]+(replace(rows[1], step_id=rows[0].step_id),)+rows[2:]
    elif fault == "overlap":
        rows = rows[:3]+(replace(rows[3], started_at=T+timedelta(seconds=1)),)+rows[4:]
    else:
        rows = list(rows)
    with pytest.raises(ValueError):
        context(lock_steps=rows)


def test_unreadable_busy_marker_can_be_reset_by_original_best_effort_path():
    c = context(busy_seed=seed("busy", status="UNREADABLE"), lock_steps=steps(acquired=False))
    with pytest.raises(LockBusy):
        with c.locked(wait=30., skip_if_busy=True):
            pytest.fail("fresh marker reset should skip")
    assert c.read_busy() == str((T+timedelta(seconds=2)).timestamp())
    assert any(e["operation"] == "busy.read" and e["status"] == "BLOCKED" for e in c.report()["events"])


def test_stalled_resolver_consumes_warning_evidence_and_proceeds_unlocked():
    rows = steps(acquired=False)
    end = T+timedelta(seconds=2)
    rows = rows[:-1]+(step("warn", end, index=3), rows[-1])
    c = context(busy_seed=seed("busy", value=str(T.timestamp()-121)), lock_steps=rows)
    with c.locked(wait=30., skip_if_busy=True):
        c.save({"stalled": {}})
    assert c.load() == {"stalled": {}}
    warning = next(e for e in c.report()["events"] if e["operation"] == "lock.warn")
    assert "123s" in warning["message"] and warning["status"] == "AVAILABLE"


def test_open_failure_uses_supplied_completion_time_without_invented_handle_close():
    rows = (step("prepare", index=0), step("open", end=T+timedelta(seconds=1), index=1, error="open failed"))
    c = context(lock_steps=rows)
    with pytest.raises(OSError, match="open failed"):
        with c.locked():
            pytest.fail("open did not succeed")
    assert c.decision_time == T+timedelta(seconds=1)
    assert c.report()["events"][-1]["operation"] == "lock.open"
    assert c.report()["lock_steps_consumed"] == 2


def test_snapshot_restore_rejects_checksum_recomputed_packed_submicrosecond_timestamp():
    from trading_system.tree_replay.causal_replay_contracts import canonical_digest
    from trading_system.tree_replay.clock import ReplayClock
    c = context(lock_steps=())
    snapshot = c.replay_snapshot()
    snapshot["state"]["quotes"]["fields"]["covered_through"]["value"] = "2026-09-09T16:05:00.1234567+00:00"
    snapshot["checksum"] = canonical_digest(snapshot["state"])
    with pytest.raises(ValueError, match="microsecond-exact"):
        api().CausalAdmissionContext.from_replay_snapshot(snapshot, clock=ReplayClock(T))


def test_snapshot_restore_rejects_checksum_recomputed_packed_basic_submicrosecond_timestamp():
    from trading_system.tree_replay.causal_replay_contracts import canonical_digest
    from trading_system.tree_replay.clock import ReplayClock
    c = context(lock_steps=())
    snapshot = c.replay_snapshot()
    snapshot["state"]["quotes"]["fields"]["covered_through"]["value"] = "20260909T160500.0000000+0000"
    snapshot["checksum"] = canonical_digest(snapshot["state"])
    with pytest.raises(ValueError, match="microsecond-exact"):
        api().CausalAdmissionContext.from_replay_snapshot(snapshot, clock=ReplayClock(T))
