"""Public admission evidence is immutable and payload-free."""
from datetime import datetime, timedelta, timezone

import pytest

from trading_system.tree_replay.outer_admission_contracts import (
    AdmissionEvidenceRef,
    OuterAdmissionDecision,
    OuterAdmissionInputs,
)


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)


def _evidence(*, event_id="tracker-at-1", artifact_id="tracker-state-1", digest="b" * 64):
    return AdmissionEvidenceRef(
        event_id=event_id,
        artifact_id=artifact_id,
        source_id="tracker-storage",
        artifact_digest=digest,
        observed_at=T0,
        available_at=T0,
        covered_through=T0 + timedelta(minutes=5),
    )


def test_admission_evidence_commits_source_and_causal_coverage():
    evidence = AdmissionEvidenceRef(
        event_id="tracker-at-1",
        artifact_id="tracker-state-1",
        source_id="tracker-storage",
        artifact_digest="b" * 64,
        observed_at=T0,
        available_at=T0 + timedelta(seconds=5),
        covered_through=T0 + timedelta(minutes=5),
    )

    assert evidence.as_dict() == {
        "event_id": "tracker-at-1",
        "artifact_id": "tracker-state-1",
        "source_id": "tracker-storage",
        "artifact_digest": "b" * 64,
        "observed_at": "2026-01-02T09:30:00+00:00",
        "available_at": "2026-01-02T09:30:05+00:00",
        "covered_through": "2026-01-02T09:35:00+00:00",
    }


def test_outer_admission_inputs_export_only_causal_commitments():
    inputs = OuterAdmissionInputs(
        input_id="admission-pass-1",
        source_variant="level_reversal:5m",
        episode_id="source-event-1",
        plan_id="source-plan-1",
        plan_digest="a" * 64,
        observed_at=T0,
        available_at=T0 + timedelta(seconds=5),
        covered_through=T0 + timedelta(minutes=5),
        evidence=(_evidence(),),
    )

    assert inputs.as_dict() == {
        "input_id": "admission-pass-1",
        "source_variant": "level_reversal:5m",
        "episode_id": "source-event-1",
        "plan_id": "source-plan-1",
        "plan_digest": "a" * 64,
        "observed_at": "2026-01-02T09:30:00+00:00",
        "available_at": "2026-01-02T09:30:05+00:00",
        "covered_through": "2026-01-02T09:35:00+00:00",
        "evidence": [{
            "event_id": "tracker-at-1",
            "artifact_id": "tracker-state-1",
            "source_id": "tracker-storage",
            "artifact_digest": "b" * 64,
            "observed_at": "2026-01-02T09:30:00+00:00",
            "available_at": "2026-01-02T09:30:00+00:00",
            "covered_through": "2026-01-02T09:35:00+00:00",
        }],
    }


def test_admitted_tracker_decision_commits_tracker_identity_without_economics():
    decision = OuterAdmissionDecision(
        decision_id="admission-decision-1",
        input_id="admission-pass-1",
        status="ADMITTED_TRACKER",
        gate_trace=("hunting", "entry_clock", "post_stop", "record"),
        reason=None,
        tracker_id="OANDA:XAUUSD|long|100.00",
        tracker_state_digest="c" * 64,
    )

    assert decision.as_dict() == {
        "decision_id": "admission-decision-1",
        "input_id": "admission-pass-1",
        "status": "ADMITTED_TRACKER",
        "gate_trace": ["hunting", "entry_clock", "post_stop", "record"],
        "reason": None,
        "tracker_id": "OANDA:XAUUSD|long|100.00",
        "tracker_state_digest": "c" * 64,
        "annotations": [],
    }


def test_outer_admission_inputs_reject_unsupported_source_variant():
    with pytest.raises(ValueError, match="source_variant"):
        OuterAdmissionInputs(
            input_id="admission-pass-1",
            source_variant="tree:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1",
            plan_digest="a" * 64,
            observed_at=T0,
            available_at=T0,
            covered_through=T0 + timedelta(minutes=5),
            evidence=(_evidence(),),
        )


def test_outer_admission_inputs_reject_noncausal_or_ambiguous_evidence():
    evidence = _evidence()
    duplicate = _evidence(artifact_id="tracker-state-2", digest="c" * 64)

    with pytest.raises(ValueError, match="available_at"):
        OuterAdmissionInputs(
            input_id="admission-pass-1", source_variant="level_reversal:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1", plan_digest="a" * 64,
            observed_at=T0 + timedelta(seconds=1), available_at=T0,
            covered_through=T0 + timedelta(minutes=5), evidence=(evidence,),
        )
    with pytest.raises(ValueError, match="covered_through"):
        OuterAdmissionInputs(
            input_id="admission-pass-1", source_variant="level_reversal:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1", plan_digest="a" * 64,
            observed_at=T0, available_at=T0 + timedelta(seconds=1),
            covered_through=T0, evidence=(evidence,),
        )
    with pytest.raises(ValueError, match="immutable"):
        OuterAdmissionInputs(
            input_id="admission-pass-1", source_variant="level_reversal:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1", plan_digest="a" * 64,
            observed_at=T0, available_at=T0, covered_through=T0 + timedelta(minutes=5),
            evidence=[evidence],
        )
    with pytest.raises(ValueError, match="reuse an event_id"):
        OuterAdmissionInputs(
            input_id="admission-pass-1", source_variant="level_reversal:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1", plan_digest="a" * 64,
            observed_at=T0, available_at=T0, covered_through=T0 + timedelta(minutes=5),
            evidence=(evidence, duplicate),
        )


def test_outer_admission_inputs_reject_future_evidence_and_economic_fields():
    future_evidence = AdmissionEvidenceRef(
        event_id="tracker-at-1", artifact_id="tracker-state-1", source_id="tracker-storage",
        artifact_digest="b" * 64, observed_at=T0,
        available_at=T0 + timedelta(seconds=1), covered_through=T0 + timedelta(minutes=5),
    )

    with pytest.raises(ValueError, match="evidence cannot be available"):
        OuterAdmissionInputs(
            input_id="admission-pass-1", source_variant="level_reversal:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1", plan_digest="a" * 64,
            observed_at=T0, available_at=T0, covered_through=T0 + timedelta(minutes=5),
            evidence=(future_evidence,),
        )
    with pytest.raises(TypeError, match="net_pnl"):
        OuterAdmissionInputs(
            input_id="admission-pass-1", source_variant="level_reversal:5m",
            episode_id="source-event-1",
            plan_id="source-plan-1", plan_digest="a" * 64,
            observed_at=T0, available_at=T0, covered_through=T0 + timedelta(minutes=5),
            evidence=(_evidence(),), net_pnl=1.0,
        )


def test_nonadmitted_decision_cannot_claim_tracker_or_economic_state():
    with pytest.raises(ValueError, match="tracker identity"):
        OuterAdmissionDecision(
            decision_id="admission-decision-1", input_id="admission-pass-1",
            status="REJECTED", gate_trace=("hunting",), reason="occupied-slot",
            tracker_id="OANDA:XAUUSD|long|100.00", tracker_state_digest="c" * 64,
        )

    decision = OuterAdmissionDecision(
        decision_id="admission-decision-1", input_id="admission-pass-1",
        status="REJECTED", gate_trace=("hunting",), reason="occupied-slot",
        tracker_id=None, tracker_state_digest=None,
    )

    assert set(decision.as_dict()).isdisjoint({"fill", "net_pnl", "net_R", "success", "failure"})


@pytest.mark.parametrize(
    ("tracker_id", "tracker_state_digest"),
    [
        ("OANDA:XAUUSD|long|100.00", None),
        (None, "c" * 64),
    ],
)
def test_decision_rejects_partial_tracker_identity(tracker_id, tracker_state_digest):
    with pytest.raises(ValueError, match="tracker identity"):
        OuterAdmissionDecision(
            decision_id="admission-decision-1", input_id="admission-pass-1",
            status="REJECTED", gate_trace=("hunting",), reason="occupied-slot",
            tracker_id=tracker_id, tracker_state_digest=tracker_state_digest,
        )
