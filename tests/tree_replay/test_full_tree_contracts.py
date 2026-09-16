from datetime import datetime, timedelta, timezone

import pytest

from trading_system.tree_replay.full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    FullTreePass,
    full_tree_manifest,
    full_tree_manifest_digest,
    pending_plan_digest,
)


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)
T2 = T1 + timedelta(minutes=5)


def artifact(**changes):
    values = {
        "artifact_id": "calendar-1",
        "kind": "TEXT",
        "observed_at": T0,
        "available_at": T0,
        "covered_through": T2,
        "content_digest": "a" * 64,
        "value": "private calendar contents",
    }
    values.update(changes)
    return FullTreeArtifact(**values)


def operation(**changes):
    values = {
        "operation_id": "calendar-read-1",
        "kind": "CALENDAR_TEXT",
        "arguments": {"path": "news-desk/data/ff_calendar.json"},
        "artifact_id": "calendar-1",
        "sequence": 0,
    }
    values.update(changes)
    return FullTreeOperation(**values)


def replay_pass(**changes):
    values = {
        "pass_id": "pass-1",
        "decision_time": T1,
        "source_variant": "full_tree:house",
        "mode": "TREE_WALK",
        "operations": (operation(),),
    }
    values.update(changes)
    return FullTreePass(**values)


def bundle(**changes):
    values = {
        "run_id": "full-tree-run-1",
        "instrument": "OANDA:XAUUSD",
        "artifacts": (artifact(),),
        "passes": (replay_pass(),),
    }
    values.update(changes)
    return FullTreeEvidenceBundle(**values)


def test_public_manifest_commits_to_artifact_without_exposing_private_value():
    evidence = bundle()

    manifest = full_tree_manifest(evidence)

    assert manifest["artifacts"] == [{
        "artifact_id": "calendar-1",
        "kind": "TEXT",
        "observed_at": T0.isoformat(),
        "available_at": T0.isoformat(),
        "covered_through": T2.isoformat(),
        "content_digest": "a" * 64,
    }]
    assert "private calendar contents" not in repr(manifest)
    assert full_tree_manifest_digest(evidence) == full_tree_manifest_digest(evidence)


def test_bundle_rejects_artifact_that_is_not_available_at_its_pass_time():
    unavailable = artifact(available_at=T2)

    with pytest.raises(ValueError, match="FULL_TREE_ARTIFACT_UNAVAILABLE_FOR_PASS"):
        bundle(artifacts=(unavailable,))


def test_bundle_rejects_an_operation_bound_to_the_wrong_artifact_kind():
    bytes_artifact = artifact(kind="BYTES", value=b"not a calendar", artifact_id="bytes-1")
    calendar_operation = operation(artifact_id="bytes-1")

    with pytest.raises(ValueError, match="FULL_TREE_OPERATION_ARTIFACT_KIND"):
        bundle(artifacts=(bytes_artifact,), passes=(replay_pass(operations=(calendar_operation,)),))


def test_bundle_rejects_repeated_source_read_schedule_with_a_sequence_gap():
    second = operation(operation_id="calendar-read-2", sequence=2)

    with pytest.raises(ValueError, match="FULL_TREE_OPERATION_SEQUENCE"):
        replay_pass(operations=(operation(), second))


def test_contracts_reject_duplicate_artifacts_and_unsupported_variants():
    with pytest.raises(ValueError, match="FULL_TREE_DUPLICATE_ARTIFACT_ID"):
        bundle(artifacts=(artifact(), artifact()))
    with pytest.raises(ValueError, match="FULL_TREE_UNSUPPORTED_VARIANT"):
        replay_pass(source_variant="level_reversal:5m")


def test_operation_arguments_are_detached_and_reject_non_json_values():
    arguments = {"path": "news-desk/data/ff_calendar.json"}
    scheduled = operation(arguments=arguments)
    arguments["path"] = "mutated-after-construction"

    assert scheduled.arguments == {"path": "news-desk/data/ff_calendar.json"}
    with pytest.raises(ValueError, match="FULL_TREE_OPERATION_ARGUMENTS"):
        operation(arguments={"path": {"not-json"}})


def test_revalidation_pass_commits_pending_plan_without_exposing_its_value():
    pending_plan = {
        "symbol": "OANDA:XAUUSD", "direction": "לונג", "entry": 110.0,
        "stop": 99.7, "ts": T0.timestamp(), "bias_at_send": {"4h": 0.0, "1h": 0.0},
    }
    revalidation = replay_pass(
        mode="TREE_REVALIDATION",
        pending_plan=pending_plan,
        pending_plan_digest=pending_plan_digest(pending_plan),
    )
    pending_plan["entry"] = 999.0

    commitment = revalidation.commitment()
    assert commitment["pending_plan_digest"] != ""
    assert "99.7" not in repr(commitment)
    assert revalidation.pending_plan["entry"] == 110.0
    with pytest.raises(ValueError, match="FULL_TREE_PENDING_PLAN"):
        replay_pass(mode="TREE_REVALIDATION", pending_plan=None, pending_plan_digest=None)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("TEXT", b"calendar bytes are not text"),
        ("BYTES", "report text is not bytes"),
        ("CLOCK", "2026-01-02T09:30:00+00:00"),
    ],
)
def test_artifact_rejects_a_raw_value_that_does_not_match_its_kind(kind, value):
    with pytest.raises(ValueError, match="FULL_TREE_ARTIFACT_VALUE_KIND"):
        artifact(kind=kind, value=value)


@pytest.mark.parametrize("digest", ("not-a-digest", "A" * 64, "a" * 63))
def test_artifact_rejects_a_non_sha256_commitment(digest):
    with pytest.raises(ValueError, match="FULL_TREE_INVALID_ARTIFACT_DIGEST"):
        artifact(content_digest=digest)
