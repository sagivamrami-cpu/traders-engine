from datetime import datetime, timezone

import pytest

from trading_system.tree_replay.causal_replay_contracts import (
    ReplayEvidenceBundle,
    ReplayEvent,
    ReplayEventCommitment,
    ReplayPassAnchor,
    ReplayPassRecord,
    ReplayRunLedger,
    TrackerActivationEvidence,
    canonical_digest,
)


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
T1 = datetime(2026, 1, 2, 9, 35, tzinfo=timezone.utc)
T2 = datetime(2026, 1, 2, 9, 40, tzinfo=timezone.utc)


def activation(**changes):
    values = {
        "evidence_id": "activation-1",
        "source": "watch-config",
        "variant": "level_reversal:5m",
        "observed_at": T0,
        "available_at": T0,
        "covered_through": T1,
        "enabled": True,
    }
    values.update(changes)
    return TrackerActivationEvidence(**values)


def event(available_at=T0, sequence=0, **changes):
    values = {
        "event_id": f"bars-{sequence}",
        "available_at": available_at,
        "sequence": sequence,
        "kind": "BAR_PUBLICATION",
        "source": "oanda",
        "variant": "level_reversal:5m",
        "payload": {"available_at": available_at.isoformat(), "bar_id": f"bar-{sequence}"},
    }
    values.update(changes)
    return ReplayEvent(**values)


def anchor(**changes):
    values = {
        "pass_id": "pass-1",
        "decision_time": T1,
        "source_variant": "level_reversal:5m",
        "required_event_ids": ("bars-0",),
        "activation": activation(),
    }
    values.update(changes)
    return ReplayPassAnchor(**values)


def record(index=0, predecessor_digest="0" * 64, **changes):
    values = {
        "pass_index": index,
        "pass_id": f"pass-{index}",
        "decision_time": T1 if index == 0 else T2,
        "outcome": "OBSERVE_ONLY",
        "consumed_event_ids": ("bars-0",),
        "activation_state": "EVIDENCED_ENABLED",
        "candidate": {"plan_id": "selected-plan-1"},
        "lifecycle_messages": (("raw lifecycle fact", False),),
        "diagnostics": ({"reason": "OUTER_ADMISSION_UNBOUND"},),
        "predecessor_digest": predecessor_digest,
    }
    values.update(changes)
    return ReplayPassRecord(**values)


def test_anchor_requires_strict_schedule_and_exact_activation_coverage():
    replay_anchor = anchor()
    assert replay_anchor.activation_state() == "EVIDENCED_ENABLED"

    with pytest.raises(ValueError, match="strictly increasing"):
        ReplayEvidenceBundle(
            run_id="run-1",
            instrument="OANDA:XAUUSD",
            events=(event(T1, 1), event(T1, 0)),
            anchors=(replay_anchor,),
        )


@pytest.mark.parametrize(
    ("decision_time", "variant", "expected"),
    [
        (T0, "level_reversal:5m", "EVIDENCED_ENABLED"),
        (T0, "other:5m", "MISMATCHED_VARIANT"),
        (datetime(2026, 1, 2, 9, 29, tzinfo=timezone.utc), "level_reversal:5m", "NOT_YET_AVAILABLE"),
        (T2, "level_reversal:5m", "COVERAGE_EXPIRED"),
    ],
)
def test_activation_state_requires_time_valid_matching_coverage(decision_time, variant, expected):
    assert activation().state_at(decision_time=decision_time, variant=variant) == expected


def test_contracts_reject_naive_and_submicrosecond_times():
    with pytest.raises(ValueError, match="timezone-aware"):
        activation(observed_at=datetime(2026, 1, 2, 9, 30))

    class NanosecondDateTime(datetime):
        nanosecond = 1

    submicrosecond = NanosecondDateTime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="microsecond-exact"):
        event(submicrosecond)


def test_bundle_rejects_duplicate_ids_unknown_kinds_and_payload_availability_mismatch():
    with pytest.raises(ValueError, match="duplicate event_id"):
        ReplayEvidenceBundle(
            run_id="run-1", instrument="OANDA:XAUUSD",
            events=(event(T0, 0), event(T1, 1, event_id="bars-0")), anchors=(anchor(),),
        )
    with pytest.raises(ValueError, match="unknown event kind"):
        event(kind="NOT_A_REPLAY_EVENT")
    with pytest.raises(ValueError, match="payload availability"):
        event(payload={"available_at": T1.isoformat()})
    with pytest.raises(ValueError, match="duplicate pass_id"):
        ReplayEvidenceBundle(
            run_id="run-1", instrument="OANDA:XAUUSD", events=(event(),),
            anchors=(anchor(), anchor(pass_id="pass-1", decision_time=T2)),
        )


def test_payload_availability_rejects_fractional_precision_beyond_microseconds():
    microsecond_later = T0.replace(microsecond=1)
    assert event(available_at=microsecond_later, payload={"available_at": "2026-01-02T09:30:00.000001Z"}).payload["available_at"] == (
        "2026-01-02T09:30:00.000001Z"
    )
    with pytest.raises(ValueError, match="microsecond"):
        event(payload={"available_at": "2026-01-02T09:30:00.0000001+00:00"})


def test_bundle_validates_before_event_selection_and_never_selects_future_events():
    bundle = ReplayEvidenceBundle(
        run_id="run-1", instrument="OANDA:XAUUSD",
        events=(event(T0, 0), event(T2, 1)), anchors=(anchor(),),
    )
    assert bundle.events_before_or_at(T1) == (event(T0, 0),)


def test_canonical_digest_rejects_nonfinite_values_and_is_order_independent():
    assert canonical_digest({"b": [2, 1], "a": "x"}) == canonical_digest({"a": "x", "b": [2, 1]})
    with pytest.raises(ValueError, match="finite JSON"):
        canonical_digest({"bad": float("nan")})
    with pytest.raises(ValueError, match="finite JSON"):
        canonical_digest({"bad": {1, 2}})


@pytest.mark.parametrize("binding", (
    None,
    {},
    {"consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-1"},
    {"consumer": "wrong", "artifact_id": "pass-1", "artifact_digest": "a" * 64},
    {"consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-1", "artifact_digest": "not-a-digest"},
))
def test_event_binding_is_all_or_nothing_and_has_exact_fields(binding):
    with pytest.raises(ValueError, match="evidence_binding"):
        event(payload={"available_at": T0.isoformat(), "evidence_binding": binding})


def test_event_commitment_covers_canonical_payload_and_optional_binding():
    replay_event = event(payload={
        "available_at": T0.isoformat(),
        "evidence_binding": {
            "consumer": "INTERNAL_REVERSAL_INPUT", "artifact_id": "pass-1", "artifact_digest": "a" * 64,
        },
    })

    commitment = replay_event.commitment()

    assert type(commitment) is ReplayEventCommitment
    assert commitment.event_id == "bars-0"
    assert commitment.consumer == "INTERNAL_REVERSAL_INPUT"
    assert commitment.payload_digest == canonical_digest(replay_event.payload)


@pytest.mark.parametrize("field", ("net_pnl", "net_R", "success", "failure"))
def test_candidate_cannot_contain_economic_or_outcome_label_fields(field):
    with pytest.raises(ValueError, match="forbidden"):
        record(candidate={"plan_id": "candidate-1", field: 1})


def test_candidate_cannot_hide_an_economic_or_outcome_label_field_in_a_nested_object():
    with pytest.raises(ValueError, match="forbidden"):
        record(candidate={"plan_id": "candidate-1", "nested": {"net_pnl": 1}})


def _nested_forbidden_field(field, nesting):
    if nesting == "dict":
        return {"trace": {"detail": {field: 1}}}
    if nesting == "list":
        return {"trace": [{"detail": {field: 1}}]}
    assert nesting == "tuple"
    return {"trace": ({"detail": {field: 1}},)}


@pytest.mark.parametrize("field", ("net_pnl", "net_R", "success", "failure"))
@pytest.mark.parametrize("nesting", ("dict", "list", "tuple"))
@pytest.mark.parametrize("surface", ("payload", "candidate", "diagnostics"))
def test_structured_replay_surfaces_reject_nested_economic_or_outcome_fields(
    surface, nesting, field,
):
    nested = _nested_forbidden_field(field, nesting)
    with pytest.raises(ValueError, match="forbidden"):
        if surface == "payload":
            event(payload={"available_at": T0.isoformat(), **nested})
        elif surface == "candidate":
            record(candidate=nested)
        else:
            record(diagnostics=(nested,))


def test_ledger_is_append_only_and_hash_chained():
    ledger = ReplayRunLedger.empty("run-1")
    first = ledger.append(record(index=0, predecessor_digest=ledger.digest))
    assert first.records[0].outcome == "OBSERVE_ONLY"
    with pytest.raises(ValueError, match="predecessor"):
        first.append(record(index=1, predecessor_digest="wrong"))
    with pytest.raises(ValueError, match="noncontiguous"):
        first.append(record(index=2, predecessor_digest=first.digest))
    with pytest.raises(ValueError, match="duplicate pass_id"):
        first.append(record(index=1, pass_id="pass-0", predecessor_digest=first.digest))
    with pytest.raises(ValueError, match="backward decision_time"):
        first.append(record(index=1, decision_time=T0, predecessor_digest=first.digest))


def test_ledger_appends_record_digest_chain_but_rejects_aggregate_ledger_digest():
    initial = ReplayRunLedger.empty("run-1")
    first = initial.append(record(index=0, predecessor_digest=initial.digest))
    second = first.append(record(index=1, predecessor_digest=first.records[-1].digest))

    assert second.records[-1].predecessor_digest == first.records[-1].digest
    with pytest.raises(ValueError, match="predecessor"):
        first.append(record(index=1, predecessor_digest=first.digest))


def test_contracts_are_frozen_and_detach_public_mappings():
    candidate = {"plan_id": "candidate-1", "trace": {"key": "value"}}
    replay_record = record(candidate=candidate)
    candidate["trace"]["key"] = "mutated"
    assert replay_record.candidate == {"plan_id": "candidate-1", "trace": {"key": "value"}}
    with pytest.raises(AttributeError):
        replay_record.outcome = "BLOCKED"
