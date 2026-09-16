"""Offline source-order outer admission over supplied causal context."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from trading_system.tree_replay.outer_admission import OuterAdmissionAdapter, source_plan_digest
from trading_system.tree_replay.outer_admission_contracts import (
    AdmissionEvidenceRef,
    OuterAdmissionInputs,
)
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission

from test_admission_context import T, context, plan, seed, steps


def _inputs(source_plan=None, *, at=T):
    return OuterAdmissionInputs(
        input_id="outer-input-1", source_variant="level_reversal:5m",
        episode_id="source-event-1",
        plan_id="source-plan-1",
        plan_digest=source_plan_digest(source_plan) if source_plan is not None else "a" * 64,
        observed_at=at, available_at=at, covered_through=at + timedelta(minutes=5),
        evidence=(AdmissionEvidenceRef(
            event_id="outer-event-1", artifact_id="tracker-state-1", source_id="synthetic",
            artifact_digest="b" * 64, observed_at=at, available_at=at,
            covered_through=at + timedelta(minutes=5),
        ),),
    )


def _context_at(at, **changes):
    return context(**(dict(
        decision_time=at,
        tracker_seed=seed("tracker", at=at),
        quote_seed=seed("quotes", at=at),
        log_seed=seed("watch_log", at=at),
        busy_seed=seed("busy", at=at, status="ABSENT"),
        lock_steps=steps(start=at),
    ) | changes))


def test_disabled_record_guard_is_observe_only_after_all_preceding_gates():
    admission = context()
    source_plan = plan()
    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=False,
    )

    assert decision.status == "OBSERVE_ONLY"
    assert decision.gate_trace == (
        "entry_quality_annotation", "tradeable_plan", "hunting_window",
        "entry_clock", "post_stop", "occupied_slot", "same_level",
        "active_reversal", "episode", "record_alert_guard",
    )
    assert decision.tracker_id is None
    assert admission.load() == {}


@pytest.mark.parametrize(
    ("scenario", "expected_status"),
    (("disabled", "OBSERVE_ONLY"), ("rejected", "REJECTED"), ("blocked", "BLOCKED")),
)
def test_pre_record_disabled_rejected_or_blocked_admission_never_calls_tracker_record(
    monkeypatch, scenario, expected_status,
):
    admission = context()
    selected_plan = plan()

    def forbidden_record(*_args, **_kwargs):
        raise AssertionError("TrackerAdmission.record must not run for a non-admitted plan")

    monkeypatch.setattr(TrackerAdmission, "record", forbidden_record)
    if scenario == "disabled":
        inputs, evaluated_plan, enabled = _inputs(selected_plan), selected_plan, False
    elif scenario == "rejected":
        rejected_plan = plan(refusal="SOURCE_PRICE_REFUSED")
        inputs, evaluated_plan, enabled = _inputs(rejected_plan), rejected_plan, True
    else:
        inputs, evaluated_plan, enabled = _inputs(selected_plan), replace(selected_plan, stop=91.0), True

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        inputs, evaluated_plan, active_reversals={}, watch_state={}, record_alerts_enabled=enabled,
    )

    assert decision.status == expected_status
    assert admission.load() == {}


def test_tradeable_source_plan_registers_exactly_one_advisory_tracker_row():
    admission = context()
    state = {}
    source_plan = plan()
    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state=state, record_alerts_enabled=True,
    )

    assert decision.status == "ADMITTED_TRACKER"
    assert decision.gate_trace[-2:] == ("record_alert_guard", "record")
    assert decision.tracker_id is not None and decision.tracker_state_digest is not None
    assert len(admission.load()) == 1
    assert len(state) == 1


def test_entry_quality_annotation_is_detached_into_the_admission_decision():
    admission = context()
    source_plan = plan()

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=False,
    )

    assert decision.status == "OBSERVE_ONLY"
    assert decision.annotations == (
        "entry_quality:annotated",
        *(f"entry_quality:label:{label}" for label in source_plan.entry_labels),
    )


def test_mismatched_plan_digest_blocks_before_entry_quality_or_tracker_mutation():
    admission = context()
    selected_plan = plan()
    substituted_plan = replace(selected_plan, stop=91.0)

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(selected_plan), substituted_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert decision.status == "BLOCKED"
    assert decision.gate_trace == ("plan_commitment",)
    assert decision.reason == "PLAN_DIGEST_MISMATCH"
    assert decision.annotations == ()
    assert admission.load() == {}


def test_tracker_record_failure_is_a_detached_block_without_watch_mutation():
    source_plan = plan()
    admission = context(lock_steps=steps(acquire_error="supplied lock failure"))
    watch_state = {}

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state=watch_state, record_alerts_enabled=True,
    )

    assert decision.status == "BLOCKED"
    assert decision.gate_trace[-1] == "record"
    assert decision.reason == "TRACKER_RECORD_FAILED"
    assert decision.tracker_id is None and decision.tracker_state_digest is None
    assert watch_state == {}
    assert admission.load() == {}


def test_refused_source_plan_stops_before_watch_or_tracker_mutation():
    admission = context()
    source_plan = plan(refusal="SOURCE_PRICE_REFUSED")
    watch_state = {}

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state=watch_state, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace == ("entry_quality_annotation", "tradeable_plan")
    assert decision.reason == "SOURCE_PRICE_REFUSED"
    assert watch_state == {} and admission.load() == {}


def test_existing_reversal_episode_stops_before_recording_again():
    admission = context()
    source_plan = plan()
    watch_state = {f"{source_plan.symbol}:level_reversal:source-event-1": {"ts": T.timestamp()}}
    active_reversals = {}

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals=active_reversals,
        watch_state=watch_state, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace[-2:] == ("active_reversal", "episode")
    assert decision.reason == "ALREADY_ADMITTED_EPISODE"
    assert admission.load() == {}
    assert active_reversals == {source_plan.symbol: source_plan}


def test_pending_duplicate_geometry_is_rejected_by_tracker_record_not_open_slot():
    pending_quote = json.dumps({"OANDA:XAUUSD": {"lp": 200., "ts": T.timestamp()}})
    admission = context(quote_seed=seed("quotes", value=pending_quote))
    source_plan = plan()

    first = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )
    second_at = admission.decision_time
    second_admission = context(
        decision_time=second_at,
        tracker_seed=seed("tracker", at=second_at, value=json.dumps(admission.load())),
        quote_seed=seed("quotes", at=second_at, value=json.dumps({
            "OANDA:XAUUSD": {"lp": 200., "ts": second_at.timestamp()},
        })),
        log_seed=seed("watch_log", at=second_at),
        busy_seed=seed("busy", at=second_at, status="ABSENT"),
        lock_steps=steps(start=second_at),
    )
    second = OuterAdmissionAdapter(admission=second_admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert first.status == "ADMITTED_TRACKER"
    assert second.status == "REJECTED"
    assert second.reason == "DUPLICATE_TRACKER_RECORD"
    assert second.gate_trace[-1] == "record"
    assert len(second_admission.load()) == 1


def test_unreadable_tracker_state_fails_closed_at_the_open_slot_gate():
    admission = context(tracker_seed=seed("tracker", status="UNKNOWN"))
    source_plan = plan()

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace[-1] == "occupied_slot"
    assert decision.reason == "OCCUPIED_SLOT"


def test_outside_hunting_window_stops_before_entry_clock_or_tracker_mutation():
    at = datetime(2026, 1, 2, 21, 30, tzinfo=timezone.utc)  # Friday 23:30 Jerusalem.
    admission = _context_at(at)
    source_plan = plan()

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan, at=at), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace == (
        "entry_quality_annotation", "tradeable_plan", "hunting_window",
    )
    assert "מחוץ לחלון החיפוש" in decision.reason
    assert admission.load() == {}


def test_closed_market_stops_after_hunting_window_and_before_tracker_mutation():
    at = datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc)  # Saturday 12:00 Jerusalem.
    admission = _context_at(at)
    source_plan = plan()

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan, at=at), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace[-1] == "entry_clock"
    assert decision.reason == "שוק סגור"
    assert admission.load() == {}


def test_recent_stopped_short_blocks_before_open_slot_or_record():
    tracker_state = {
        "stopped": {
            "symbol": "OANDA:XAUUSD", "direction": "שורט", "state": "STOPPED",
            "entry": 100., "stop": 110., "ts": T.timestamp(),
        },
    }
    admission = context(tracker_seed=seed("tracker", value=json.dumps(tracker_state)))
    source_plan = plan(direction="שורט", stop=110., targets=[("TP1", 80.)])

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace[-1] == "post_stop"
    assert decision.reason.startswith("סטופ לפני")


def test_recent_done_same_level_blocks_before_episode_or_record():
    tracker_state = {
        "done": {
            "symbol": "OANDA:XAUUSD", "direction": "לונג", "state": "DONE",
            "entry": 100., "resolved_ts": T.timestamp(), "ts": T.timestamp(),
        },
    }
    admission = context(tracker_seed=seed("tracker", value=json.dumps(tracker_state)))
    source_plan = plan()

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={}, record_alerts_enabled=True,
    )

    assert decision.status == "REJECTED"
    assert decision.gate_trace[-1] == "same_level"
    assert decision.reason.startswith("אותה רמה נסחרה זה עתה")


def test_entry_quality_records_that_a_causal_log_tail_rejection_was_considered():
    admission = context()
    admission.log({
        "kind": "rejection", "symbol": "OANDA:XAUUSD", "direction": "לונג",
        "zone_lo": 98., "zone_hi": 102., "levels": ["PSY"], "close": 100.,
        "wick_atr": 0.5,
    })
    source_plan = plan(reasons=[])

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={},
        record_alerts_enabled=False,
    )

    assert decision.status == "OBSERVE_ONLY"
    assert "entry_quality:aligned_rejection" in decision.annotations


def test_unrelated_stopped_thesis_does_not_create_a_post_stop_block():
    tracker_state = {
        "other-thesis": {
            "symbol": "OANDA:XAUUSD", "direction": "לונג", "state": "STOPPED",
            "entry": 100., "stop": 90., "ts": T.timestamp(),
        },
    }
    admission = context(tracker_seed=seed("tracker", value=json.dumps(tracker_state)))
    source_plan = plan(direction="שורט", stop=110., targets=[("TP1", 80.)])

    decision = OuterAdmissionAdapter(admission=admission).evaluate(
        _inputs(source_plan), source_plan, active_reversals={}, watch_state={},
        record_alerts_enabled=True,
    )

    assert decision.status == "ADMITTED_TRACKER"
    assert decision.gate_trace[-1] == "record"
    assert len(admission.load()) == 2
