"""Closed-bar causal replay uses supplied evidence without registering trades."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import json
from types import SimpleNamespace

import pytest

from trading_system.tree_replay.admission_context import CausalAdmissionContext
from trading_system.tree_replay.causal_replay_checkpoint import ReplayProviderBaseline
from trading_system.tree_replay.causal_replay_contracts import (
    canonical_digest,
    canonical_evidence_digest,
    ReplayEvent,
    ReplayEvidenceBundle,
    ReplayPassAnchor,
    TrackerActivationEvidence,
)
from trading_system.tree_replay.clock import ReplayClock
from trading_system.tree_replay.outer_admission import source_plan_digest
from trading_system.tree_replay.outer_admission_contracts import (
    AdmissionEvidenceRef,
    OuterAdmissionInputs,
)
from trading_system.tree_replay.watch_storage import CausalWatchStorage, WatchStateSeed
from trading_system.tree_replay._vendor.tracker_admission import TrackerAdmission
from trading_system.tree_replay.causal_replay import ClosedBarCausalReplay, InternalReversalInputs

from test_admission_context import SYMBOL, T, context, plan as source_plan, publication, seed, steps
from test_admission_frames import request
from test_reversal_producer import maps, reversal


LONG = "\u05dc\u05d5\u05e0\u05d2"
SUPPORTED = "level_reversal:5m"


def activation(**changes):
    values = dict(
        evidence_id="activation", source="watch-config", variant=SUPPORTED,
        observed_at=T, available_at=T, covered_through=T + timedelta(minutes=10), enabled=True,
    )
    values.update(changes)
    return TrackerActivationEvidence(**values)


def event(at, sequence, **changes):
    values = dict(
        event_id=f"event-{sequence}", available_at=at, sequence=sequence,
        kind="BAR_PUBLICATION", source="synthetic", variant=SUPPORTED,
        payload={"available_at": at.isoformat(), "event": sequence},
    )
    values.update(changes)
    return ReplayEvent(**values)


def bundle(*, count=2, first_activation=None, variant=SUPPORTED, future_event=None):
    events = tuple(event(
        T + timedelta(minutes=index), index,
        payload={
            "available_at": (T + timedelta(minutes=index)).isoformat(),
            "event": index,
            "evidence_binding": {
                "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": f"pass-{index}",
                "artifact_digest": canonical_evidence_digest(reversal_input(index)),
            },
        },
    ) for index in range(count))
    if future_event is not None:
        events += (future_event,)
    anchors = tuple(
        ReplayPassAnchor(
            pass_id=f"pass-{index}", decision_time=T + timedelta(minutes=index),
            source_variant=variant,
            required_event_ids=(f"event-{index}",),
            activation=first_activation if index == 0 and first_activation is not None else activation(),
        )
        for index in range(count)
    )
    return ReplayEvidenceBundle(run_id="causal-run", instrument=SYMBOL, events=events, anchors=anchors)


def reversal_input(index):
    return InternalReversalInputs(
        snapshot_id=f"snapshot-{index}", map_requests=maps(),
        reversal_requests=(reversal(), reversal("15m", short=True)),
    )


def outer_input(index, *, at=None, plan=None):
    at = T + timedelta(minutes=index) if at is None else at
    plan = source_plan() if plan is None else plan
    return OuterAdmissionInputs(
        input_id=f"outer-input-{index}", source_variant=SUPPORTED,
        episode_id=f"source-event-{index}", plan_id=f"source-plan-{index}",
        plan_digest=source_plan_digest(plan), observed_at=at, available_at=at,
        covered_through=at + timedelta(minutes=5),
        evidence=(AdmissionEvidenceRef(
            event_id=f"outer-evidence-{index}", artifact_id=f"outer-artifact-{index}",
            source_id="synthetic", artifact_digest="c" * 64, observed_at=at,
            available_at=at, covered_through=at + timedelta(minutes=5),
        ),),
    )


def bundle_with_outer_input(*, outer_at=T):
    internal = event(T, 0, payload={
        "available_at": T.isoformat(), "event": "internal",
        "evidence_binding": {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-0",
            "artifact_digest": canonical_evidence_digest(reversal_input(0)),
        },
    })
    outer = event(outer_at, 1, event_id="outer-binding", kind="WATCH_PUBLICATION", payload={
        "available_at": outer_at.isoformat(), "event": "outer",
        "evidence_binding": {
            "consumer": "OUTER_ADMISSION_INPUT", "artifact_id": "pass-0",
            "artifact_digest": canonical_evidence_digest(outer_input(0)),
        },
    })
    return ReplayEvidenceBundle(
        run_id="causal-outer-admission", instrument=SYMBOL, events=(internal, outer),
        anchors=(ReplayPassAnchor(
            pass_id="pass-0", decision_time=T, source_variant=SUPPORTED,
            required_event_ids=("event-0",), activation=activation(),
        ),),
    )


def bundle_with_outer_inputs(*, count=2):
    events = []
    anchors = []
    for index in range(count):
        at = T + timedelta(minutes=index)
        events.extend((
            event(at, index * 2, event_id=f"internal-{index}", payload={
                "available_at": at.isoformat(), "event": f"internal-{index}",
                "evidence_binding": {
                    "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": f"pass-{index}",
                    "artifact_digest": canonical_evidence_digest(reversal_input(index)),
                },
            }),
            event(at, index * 2 + 1, event_id=f"outer-{index}", kind="WATCH_PUBLICATION", payload={
                "available_at": at.isoformat(), "event": f"outer-{index}",
                "evidence_binding": {
                    "consumer": "OUTER_ADMISSION_INPUT", "artifact_id": f"pass-{index}",
                    "artifact_digest": canonical_evidence_digest(outer_input(index)),
                },
            }),
        ))
        anchors.append(ReplayPassAnchor(
            pass_id=f"pass-{index}", decision_time=at, source_variant=SUPPORTED,
            required_event_ids=(f"internal-{index}",), activation=activation(),
        ))
    return ReplayEvidenceBundle(
        run_id="causal-outer-admission-resume", instrument=SYMBOL,
        events=tuple(events), anchors=tuple(anchors),
    )


def outer_lock_steps(*, count):
    rows = []
    for index in range(count):
        rows.extend(
            replace(step, step_id=f"pass-{index}:{step.step_id}")
            for step in steps(start=T + timedelta(minutes=index))
        )
    return tuple(rows)


def open_trade(*, state="OPEN", target=110.0):
    return {
        "trade_id": "supplied-trade", "state": state, "symbol": SYMBOL,
        "direction": LONG, "entry": 100.0, "stop": 90.0,
        "targets": [["TP1", target]], "to_group": False,
        "ts": (T - timedelta(minutes=30)).timestamp(), "style": "intraday", "hit": [],
    }


def make_replay(*, replay_bundle=None, inputs=None, outer_inputs=None, tracker_state=None, frame_request=None,
                publications=(), lock_steps=()):
    replay_bundle = replay_bundle or bundle()
    clock = ReplayClock(T)
    watch = CausalWatchStorage(
        seed=WatchStateSeed(
            seed_id="watch", source="synthetic", observed_at=T, available_at=T,
            covered_through=T + timedelta(minutes=20), status="PRESENT", text="{}",
        ),
        decision_time=T, clock=clock,
    )
    tracker_seed = seed("tracker", value=json.dumps(tracker_state or {}), through=T + timedelta(minutes=20))
    admission = context(
        clock=clock, tracker_seed=tracker_seed,
        frame_requests=(frame_request or request("15m", 5),),
        publications=publications, lock_steps=lock_steps,
    )
    baseline = ReplayProviderBaseline.capture(watch=watch, admission=admission)
    if inputs is None:
        inputs = {anchor.pass_id: reversal_input(index) for index, anchor in enumerate(replay_bundle.anchors)}
    return ClosedBarCausalReplay(
        replay_bundle, clock=clock, watch=watch, admission=admission,
        reversal_inputs=inputs, outer_admission_inputs=outer_inputs, baseline=baseline,
    )


def no_candidate(*_args, **_kwargs):
    return SimpleNamespace(report={"status": "NO_CANDIDATE", "reason": "NO_SOURCE_SELECTION"})


def selected_candidate(*_args, **_kwargs):
    return SimpleNamespace(report={
        "status": "PRODUCER_SELECTED_UNADMITTED",
        "selected": {"source_plan": {"plan_id": "supplied-plan"}},
        "decision_id": "supplied-decision",
        "evaluation_sha256": "a" * 64,
    })


def selected_candidate_with_retained_plan(*_args, **_kwargs):
    return SimpleNamespace(
        report={
            "status": "PRODUCER_SELECTED_UNADMITTED",
            "selected": {"source_plan": {"plan_id": "supplied-plan"}},
            "decision_id": "supplied-decision",
            "evaluation_sha256": "a" * 64,
        },
        selected_plan=source_plan(),
    )


def test_enabled_outer_admission_registers_one_advisory_tracker_row(monkeypatch):
    monkeypatch.setattr(
        "trading_system.tree_replay.causal_replay._evaluate_reversal_asof",
        selected_candidate_with_retained_plan,
    )
    replay = make_replay(
        replay_bundle=bundle_with_outer_input(), outer_inputs={"pass-0": outer_input(0)},
        lock_steps=steps(),
    )

    ledger = replay.run()

    assert ledger.records[0].outcome == "ADMITTED_TRACKER"
    assert len(replay.admission.load()) == 1
    admission_diagnostic = next(item for item in ledger.records[0].diagnostics if item["stage"] == "admission")
    assert admission_diagnostic["status"] == "ADMITTED_TRACKER"
    assert set(admission_diagnostic).isdisjoint({"fill", "net_pnl", "net_R", "success", "failure"})


@pytest.mark.parametrize("outer_events", [(), ("future",)])
def test_enabled_outer_admission_requires_current_bound_evidence_before_watch_mutation(
    monkeypatch, outer_events,
):
    monkeypatch.setattr(
        "trading_system.tree_replay.causal_replay._evaluate_reversal_asof",
        selected_candidate_with_retained_plan,
    )
    replay_bundle = bundle(count=1)
    if outer_events:
        replay_bundle = bundle_with_outer_input(outer_at=T + timedelta(microseconds=1))
    replay = make_replay(
        replay_bundle=replay_bundle, outer_inputs={"pass-0": outer_input(0)}, lock_steps=steps(),
    )

    ledger = replay.run()

    assert ledger.records[0].outcome == "BLOCKED"
    assert replay.watch.trace == []
    assert replay.admission.load() == {}


def test_outer_admission_one_shot_and_resume_have_identical_ledger_and_state(monkeypatch):
    monkeypatch.setattr(
        "trading_system.tree_replay.causal_replay._evaluate_reversal_asof",
        selected_candidate_with_retained_plan,
    )
    replay_bundle = bundle_with_outer_inputs()
    outer_inputs = {f"pass-{index}": outer_input(index) for index in range(2)}
    one_shot_replay = make_replay(
        replay_bundle=replay_bundle, outer_inputs=outer_inputs, lock_steps=outer_lock_steps(count=2),
    )
    one_shot = one_shot_replay.run()
    partial = make_replay(
        replay_bundle=replay_bundle, outer_inputs=outer_inputs, lock_steps=outer_lock_steps(count=2),
    )
    _prefix, checkpoint = partial.run_until(1)
    resumed_replay = ClosedBarCausalReplay.restore(
        checkpoint, bundle=replay_bundle, clock=ReplayClock(T + timedelta(seconds=2)),
        baseline=partial.baseline,
        reversal_inputs={f"pass-{index}": reversal_input(index) for index in range(2)},
        outer_admission_inputs=outer_inputs,
    )
    resumed = resumed_replay.run()

    assert [row.outcome for row in one_shot.records] == ["ADMITTED_TRACKER", "REJECTED"]
    assert resumed.digest == one_shot.digest
    assert resumed_replay.admission.load() == one_shot_replay.admission.load()
    assert resumed_replay.watch.snapshot().text == one_shot_replay.watch.snapshot().text


def test_run_advances_shared_clock_and_keeps_new_selected_plan_observe_only(monkeypatch):
    replay = make_replay()

    def forbidden_record(*_args, **_kwargs):
        raise AssertionError("new replay candidates must never call TrackerAdmission.record")

    monkeypatch.setattr(TrackerAdmission, "record", forbidden_record)
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", selected_candidate)
    ledger = replay.run()

    assert [row.outcome for row in ledger.records] == ["OBSERVE_ONLY", "OBSERVE_ONLY"]
    assert ledger.records[0].candidate["source_plan"] is not None
    assert ledger.records[1].predecessor_digest == ledger.records[0].digest
    assert replay.clock.now == replay.bundle.anchors[-1].decision_time
    assert replay.admission.decision_time == replay.clock.now
    assert replay.watch.snapshot().observed_at == replay.clock.now


def test_future_publication_cannot_change_previous_pass_or_lifecycle(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    future = event(T + timedelta(minutes=2), 2, payload={
        "available_at": (T + timedelta(minutes=2)).isoformat(), "changed": "future-only",
    })
    baseline = make_replay(replay_bundle=bundle(count=2)).run_until(1)[0]
    changed = make_replay(replay_bundle=bundle(count=2, future_event=future)).run_until(1)[0]

    assert baseline.records[0].digest == changed.records[0].digest


def test_same_event_identity_with_changed_bound_payload_blocks_before_provider_use(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    original = bundle(count=1)
    changed_event = replace(original.events[0], payload={
        "available_at": T.isoformat(), "event": 0,
        "evidence_binding": {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-0",
            "artifact_digest": "0" * 64,
        },
    })
    changed = ReplayEvidenceBundle(
        run_id=original.run_id, instrument=original.instrument, events=(changed_event,), anchors=original.anchors,
    )

    assert make_replay(replay_bundle=original).run().records[0].outcome == "NO_CANDIDATE"
    replay = make_replay(replay_bundle=changed)
    assert replay.run().records[0].outcome == "BLOCKED"
    assert replay.watch.trace == []
    assert replay.admission.report()["publications_consumed"] == 0


def test_future_reversal_binding_cannot_feed_an_earlier_pass(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    late = event(T + timedelta(microseconds=1), 0, payload={
        "available_at": (T + timedelta(microseconds=1)).isoformat(),
        "evidence_binding": {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-0",
            "artifact_digest": canonical_evidence_digest(reversal_input(0)),
        },
    })
    replay_bundle = ReplayEvidenceBundle(
        run_id="causal-run", instrument=SYMBOL, events=(late,), anchors=(ReplayPassAnchor(
            pass_id="pass-0", decision_time=T, source_variant=SUPPORTED,
            required_event_ids=("event-0",), activation=activation(),
        ),),
    )
    replay = make_replay(replay_bundle=replay_bundle, inputs={"pass-0": reversal_input(0)})

    assert replay.run().records[0].outcome == "BLOCKED"
    assert replay.watch.trace == []


@pytest.mark.parametrize("required_binding", (None, "pass-1"))
def test_required_event_cannot_be_substituted_by_a_nonrequired_internal_input_binding(
    monkeypatch, required_binding,
):
    calls = []

    def producer(*_args, **_kwargs):
        calls.append("producer")
        return no_candidate()

    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", producer)
    required_payload = {"available_at": T.isoformat(), "event": "required"}
    if required_binding is not None:
        required_payload["evidence_binding"] = {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": required_binding,
            "artifact_digest": canonical_evidence_digest(reversal_input(0)),
        }
    required = event(T, 0, event_id="required-unrelated", payload=required_payload)
    nonrequired = event(T, 1, event_id="input-binding", payload={
        "available_at": T.isoformat(),
        "evidence_binding": {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-0",
            "artifact_digest": canonical_evidence_digest(reversal_input(0)),
        },
    })
    replay_bundle = ReplayEvidenceBundle(
        run_id="required-binding", instrument=SYMBOL, events=(required, nonrequired),
        anchors=(ReplayPassAnchor(
            pass_id="pass-0", decision_time=T, source_variant=SUPPORTED,
            required_event_ids=("required-unrelated",), activation=activation(),
        ),),
    )
    replay = make_replay(replay_bundle=replay_bundle, inputs={"pass-0": reversal_input(0)})

    assert replay.run().records[0].outcome == "BLOCKED"
    assert calls == []
    assert replay.watch.trace == []
    assert replay.admission.report()["publications_consumed"] == 0


def _publication_replay(*, publication_events):
    at = T + timedelta(minutes=1)
    published = publication("frames", (request("15m", 5),), at=at, name="frames-at-one")
    internal = event(T, 0, payload={
        "available_at": T.isoformat(),
        "evidence_binding": {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-0",
            "artifact_digest": canonical_evidence_digest(reversal_input(0)),
        },
    })
    replay_bundle = ReplayEvidenceBundle(
        run_id="publication-binding", instrument=SYMBOL, events=(internal,) + publication_events,
        anchors=(ReplayPassAnchor(
            pass_id="pass-0", decision_time=at, source_variant=SUPPORTED,
            required_event_ids=("event-0",), activation=activation(),
        ),),
    )
    return make_replay(replay_bundle=replay_bundle, publications=(published,))


@pytest.mark.parametrize("fault", ("missing", "mismatched", "duplicate"))
def test_due_publication_requires_one_exact_eligible_binding_before_context_advance(monkeypatch, fault):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    at = T + timedelta(minutes=1)
    digest = canonical_evidence_digest(publication("frames", (request("15m", 5),), at=at, name="frames-at-one"))
    payload = {
        "available_at": at.isoformat(),
        "evidence_binding": {
            "consumer": "ADMISSION_PUBLICATION", "artifact_id": "frames-at-one",
            "artifact_digest": digest if fault != "mismatched" else "0" * 64,
        },
    }
    first = event(at, 0, event_id="publication-a", kind="FRAME_PUBLICATION", payload=payload)
    events = () if fault == "missing" else (first,)
    if fault == "duplicate":
        events += (event(at, 1, event_id="publication-b", kind="FRAME_PUBLICATION", payload=payload),)
    replay = _publication_replay(publication_events=events)

    record = replay.run().records[0]
    assert record.outcome == "BLOCKED"
    assert replay.watch.trace == []
    assert replay.admission.report()["publications_consumed"] == 0


def test_record_commits_payload_digest_binding_and_provider_baseline(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    replay = make_replay(replay_bundle=bundle(count=1))

    record = replay.run().records[0]

    commitment = record.consumed_event_commitments[0]
    assert commitment.payload_digest == canonical_digest(replay.bundle.events[0].payload)
    assert commitment.consumer == "INTERNAL_REVERSAL_INPUT"
    assert commitment.artifact_id == "pass-0"
    assert record.provider_baseline_fingerprint == replay.baseline.fingerprint


def test_split_run_matches_one_shot_run(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    replay_bundle = bundle(count=3)
    one_shot = make_replay(replay_bundle=replay_bundle).run()
    partial = make_replay(replay_bundle=replay_bundle)
    prefix, checkpoint = partial.run_until(2)
    resumed = ClosedBarCausalReplay.restore(
        checkpoint, bundle=replay_bundle, clock=ReplayClock(T + timedelta(minutes=1)),
        baseline=partial.baseline, reversal_inputs={
            anchor.pass_id: reversal_input(index) for index, anchor in enumerate(replay_bundle.anchors)
        },
    ).run()

    assert len(prefix.records) == 2
    assert resumed.digest == one_shot.digest


def test_seeded_pending_is_checked_without_fabricating_a_fill(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    replay = make_replay(replay_bundle=bundle(count=1), tracker_state={"pending": open_trade(state="PENDING")})

    ledger = replay.run()

    assert ledger.records[0].outcome == "NO_CANDIDATE"
    assert ledger.records[0].lifecycle_messages == ()
    assert replay.admission.load()["pending"]["state"] == "PENDING"


def test_seeded_open_resolves_through_closed_lifecycle_in_message_order(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    base = request("15m", 3)
    rows = tuple(replace(bar, high=140.0, low=90.0) for bar in base.frame.bars)
    replay = make_replay(
        replay_bundle=bundle(count=1), tracker_state={"open": open_trade()},
        frame_request=replace(base, frame=replace(base.frame, bars=rows)),
    )

    ledger = replay.run()

    messages = ledger.records[0].lifecycle_messages
    assert replay.admission.load()["open"]["state"] == "STOPPED"
    assert len(messages) == 1
    assert "TP1" not in messages[0][0]
    assert "@ 90.00" in messages[0][0]
    assert messages[0][1] is False


@pytest.mark.parametrize(
    ("evidence", "activation_state"),
    [
        (activation(enabled=False), "EVIDENCED_DISABLED"),
        (activation(available_at=T + timedelta(microseconds=1), covered_through=T + timedelta(minutes=1)),
         "NOT_YET_AVAILABLE"),
    ],
)
def test_disabled_or_future_activation_is_diagnostic_only_for_a_selected_plan(
    monkeypatch, evidence, activation_state,
):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", selected_candidate)
    ledger = make_replay(replay_bundle=bundle(count=1, first_activation=evidence)).run()

    assert ledger.records[0].outcome == "OBSERVE_ONLY"
    assert ledger.records[0].activation_state == activation_state
    assert ledger.records[0].candidate == {"source_plan": {"plan_id": "supplied-plan"}}


def test_unknown_source_variant_is_unsupported_before_producer_evaluation(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", selected_candidate)

    ledger = make_replay(replay_bundle=bundle(count=1, variant="other:5m")).run()

    assert ledger.records[0].outcome == "UNSUPPORTED"
    assert ledger.records[0].activation_state == "MISMATCHED_VARIANT"


def test_missing_reversal_input_producer_error_and_unknown_variant_are_explicit(monkeypatch):
    absent = make_replay(replay_bundle=bundle(count=1), inputs={}).run()
    assert absent.records[0].outcome == "BLOCKED"

    def boom(*_args, **_kwargs):
        raise RuntimeError("synthetic producer fault")

    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", boom)
    failed = make_replay(replay_bundle=bundle(count=1)).run()
    assert failed.records[0].outcome == "BLOCKED"
    assert failed.records[0].diagnostics[0]["exception_type"] == "RuntimeError"

    unsupported = make_replay(replay_bundle=bundle(count=1, variant="tree:5m")).run()
    assert unsupported.records[0].outcome == "UNSUPPORTED"


def test_required_future_evidence_blocks_before_watch_state_writes(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    delayed = event(T + timedelta(minutes=1), 0)
    replay_bundle = ReplayEvidenceBundle(
        run_id="causal-run", instrument=SYMBOL, events=(delayed,),
        anchors=(ReplayPassAnchor(
            pass_id="pass-0", decision_time=T, source_variant=SUPPORTED,
            required_event_ids=("event-0",), activation=activation(),
        ),),
    )
    replay = make_replay(replay_bundle=replay_bundle, inputs={"pass-0": reversal_input(0)})

    ledger = replay.run()

    assert ledger.records[0].outcome == "BLOCKED"
    assert [row["operation"] for row in replay.watch.trace] == []


def test_watch_state_uses_preproducer_then_final_source_order(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    replay = make_replay(replay_bundle=bundle(count=1))

    replay.run()

    operations = [row["operation"] for row in replay.watch.trace]
    assert [operation for operation in operations if operation in {
        "load", "save_before_producers", "save_final",
    }] == ["load", "save_before_producers", "save_final"]
    assert operations.count("ensure_directory") == 1
    assert operations.count("write_text") == 2
    assert operations.index("ensure_directory") < operations.index("save_final")


def test_restore_rejects_malformed_checkpoint(monkeypatch):
    monkeypatch.setattr("trading_system.tree_replay.causal_replay._evaluate_reversal_asof", no_candidate)
    replay = make_replay(replay_bundle=bundle(count=1))
    _ledger, checkpoint = replay.run_until(1)
    checkpoint["state"]["ledger_digest"] = "0" * 64

    with pytest.raises(ValueError, match="checksum|digest"):
        ClosedBarCausalReplay.restore(
            checkpoint, bundle=replay.bundle, clock=ReplayClock(T), baseline=replay.baseline,
            reversal_inputs={"pass-0": reversal_input(0)},
        )
