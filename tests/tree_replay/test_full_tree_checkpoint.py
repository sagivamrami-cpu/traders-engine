from datetime import datetime, timedelta, timezone
from dataclasses import replace

import pytest

from trading_system.tree_replay.full_tree_checkpoint import FullTreeProviderBaseline
from trading_system.tree_replay.full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    FullTreePass,
    ProviderErrorPayload,
)
from trading_system.tree_replay.full_tree_replay import FullTreeCausalReplay


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
SYMBOL = "OANDA:XAUUSD"


def three_pass_bundle(*, changed_second_operation=False, changed_second_artifact_digest=False):
    artifacts, passes = [], []
    for index in range(3):
        decision = T0 + timedelta(minutes=5 * (index + 1))
        artifact_id = f"error-{index}"
        artifacts.append(FullTreeArtifact(
            artifact_id=artifact_id, kind="ERROR", observed_at=T0, available_at=T0,
            covered_through=T0 + timedelta(minutes=20),
            content_digest=("f" * 64 if changed_second_artifact_digest and index == 1 else f"{index + 1:064x}"),
            value=ProviderErrorPayload(error_type=LookupError, message="tape unavailable"),
        ))
        lookback = 11 if changed_second_operation and index == 1 else 10
        passes.append(FullTreePass(
            pass_id=f"pass-{index}", decision_time=decision, source_variant="full_tree:house",
            mode="TREE_WALK", operations=(FullTreeOperation(
                operation_id=f"fetch-{index}", kind="FETCH_CORRECTED",
                arguments={"symbol": SYMBOL, "timeframe": "15m", "lookback": lookback},
                artifact_id=artifact_id, sequence=0,
            ),),
        ))
    return FullTreeEvidenceBundle(
        run_id="checkpoint-run", instrument=SYMBOL, artifacts=tuple(artifacts), passes=tuple(passes),
    )


def test_resume_at_completed_pass_boundary_matches_the_uninterrupted_public_ledger():
    bundle = three_pass_bundle()
    uninterrupted = FullTreeCausalReplay(bundle).run_all()
    interrupted = FullTreeCausalReplay(bundle)
    first = interrupted.run_pass("pass-0")
    checkpoint = interrupted.checkpoint_after(first, next_pass_index=1)

    resumed = FullTreeCausalReplay.resume(bundle, checkpoint).run_all()

    assert resumed.records == uninterrupted.records
    assert checkpoint.bundle_manifest_digest == FullTreeProviderBaseline.capture(bundle).bundle_manifest_digest
    assert "tape unavailable" not in repr(checkpoint.as_dict())


def test_resume_rejects_a_changed_future_operation_schedule():
    original = three_pass_bundle()
    interrupted = FullTreeCausalReplay(original)
    checkpoint = interrupted.checkpoint_after(interrupted.run_pass("pass-0"), next_pass_index=1)

    with pytest.raises(ValueError, match="FULL_TREE_CHECKPOINT_BUNDLE_MISMATCH"):
        FullTreeCausalReplay.resume(three_pass_bundle(changed_second_operation=True), checkpoint)


def test_resume_rejects_changed_artifact_commitment_and_tampered_ledger_record():
    original = three_pass_bundle()
    interrupted = FullTreeCausalReplay(original)
    checkpoint = interrupted.checkpoint_after(interrupted.run_pass("pass-0"), next_pass_index=1)

    with pytest.raises(ValueError, match="FULL_TREE_CHECKPOINT_BUNDLE_MISMATCH"):
        FullTreeCausalReplay.resume(three_pass_bundle(changed_second_artifact_digest=True), checkpoint)
    tampered = replace(
        checkpoint,
        records=(replace(checkpoint.records[0], outcome="TREE_BLOCKED"),),
    )
    with pytest.raises(ValueError, match="FULL_TREE_CHECKPOINT_RECORD"):
        FullTreeCausalReplay.resume(original, tampered)
