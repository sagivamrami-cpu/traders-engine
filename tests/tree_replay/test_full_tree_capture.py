from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib

import pandas as pd
import pytest

from trading_system.tree_replay.full_tree_replay import FullTreeCausalReplay


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SuppliedInput:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def read(self, kind, arguments, *, decision_time):
        self.calls.append((kind, dict(arguments), decision_time))
        return self.values[(kind, tuple(sorted(arguments.items())))]


def captured(value, *, observed=T0, available=T0, covered=T1, source="private-source"):
    api = __import__("trading_system.tree_replay.full_tree_capture", fromlist=["CapturedValue"])
    return api.CapturedValue(
        value=value,
        observed_at=observed,
        available_at=available,
        covered_through=covered,
        content_digest=digest(source),
    )


def test_recorder_builds_distinct_scheduled_artifacts_from_supplied_values():
    api = __import__("trading_system.tree_replay.full_tree_capture", fromlist=["FullTreeEvidenceCapture"])
    frame = pd.DataFrame({"open": [100.0], "high": [101.0], "low": [99.0], "close": [100.5]})
    source = SuppliedInput({
        ("FETCH_CORRECTED", (("lookback", 10), ("symbol", "OANDA:XAUUSD"), ("timeframe", "15m"))): captured(
            api.TreeFramePayload(frame=frame, correction=None), source="frame"
        ),
        ("NOW_UTC", ()): captured(T1, source="clock"),
    })
    capture = api.FullTreeEvidenceCapture(
        source, run_id="capture-1", instrument="OANDA:XAUUSD", pass_id="pass-1",
        decision_time=T1, source_variant="full_tree:house",
    )

    returned_frame, correction = capture.source.fetch_corrected("OANDA:XAUUSD", "15m", 10)
    returned_frame.iloc[0, 0] = -1.0
    assert correction is None
    assert capture.source.now_utc() == T1
    result = capture.finish()

    assert source.calls == [
        ("FETCH_CORRECTED", {"symbol": "OANDA:XAUUSD", "timeframe": "15m", "lookback": 10}, T1),
        ("NOW_UTC", {}, T1),
    ]
    assert [operation.kind for operation in result.bundle.passes[0].operations] == ["FETCH_CORRECTED", "NOW_UTC"]
    assert [operation.sequence for operation in result.bundle.passes[0].operations] == [0, 1]
    assert len({artifact.artifact_id for artifact in result.bundle.artifacts}) == 2
    assert result.bundle.artifacts[0].value.frame.iloc[0, 0] == 100.0
    assert result.receipt.operation_count == 2
    assert "private-source" not in repr(result.receipt)
    assert "100.5" not in repr(result.receipt)


def test_recorder_fails_closed_when_a_supplied_value_is_not_available_at_decision_time():
    api = __import__("trading_system.tree_replay.full_tree_capture", fromlist=["FullTreeEvidenceCapture", "FullTreeCaptureError"])
    source = SuppliedInput({
        ("NOW_UTC", ()): captured(
            T1, available=T1 + timedelta(microseconds=1), covered=T1 + timedelta(minutes=1),
        ),
    })
    capture = api.FullTreeEvidenceCapture(
        source, run_id="capture-1", instrument="OANDA:XAUUSD", pass_id="pass-1",
        decision_time=T1, source_variant="full_tree:house",
    )

    with pytest.raises(api.FullTreeCaptureError, match="FULL_TREE_CAPTURE_UNAVAILABLE"):
        capture.source.now_utc()


class ScheduledBundleInput:
    """Re-supplies a literal tape without exposing a source result to capture."""

    def __init__(self, bundle):
        self._operations = list(bundle.passes[0].operations)
        self._artifacts = {artifact.artifact_id: artifact for artifact in bundle.artifacts}
        self._cursor = 0

    def read(self, kind, arguments, *, decision_time):
        operation = self._operations[self._cursor]
        self._cursor += 1
        assert operation.kind == kind
        assert dict(operation.arguments) == dict(arguments)
        artifact = self._artifacts[operation.artifact_id]
        return captured(
            artifact.value,
            observed=artifact.observed_at,
            available=artifact.available_at,
            covered=artifact.covered_through,
            source=artifact.content_digest,
        )


@pytest.mark.parametrize("variant", ("house", "strict"))
def test_capture_runs_the_actual_tree_then_replays_the_recorded_schedule(variant):
    from test_full_tree_replay import _successful_full_tree_bundle

    api = __import__("trading_system.tree_replay.full_tree_capture", fromlist=["FullTreeEvidenceCapture"])
    literal_tape = _successful_full_tree_bundle(variant)
    original_pass = literal_tape.passes[0]
    capture = api.FullTreeEvidenceCapture(
        ScheduledBundleInput(literal_tape), run_id=f"captured-{variant}", instrument="OANDA:XAUUSD",
        pass_id=f"captured-{variant}-pass", decision_time=original_pass.decision_time,
        source_variant=original_pass.source_variant,
    )

    captured_result = capture.capture_walk()
    replayed = FullTreeCausalReplay(captured_result.bundle).run_pass(f"captured-{variant}-pass")

    assert captured_result.receipt.operation_count == len(original_pass.operations)
    assert replayed.record.trace_digest == captured_result.receipt.trace_digest
    assert replayed.record.outcome == "TREE_CANDIDATE_OBSERVED"


def test_capture_preserves_a_source_caught_error_at_its_scheduled_call():
    api = __import__("trading_system.tree_replay.full_tree_capture", fromlist=["FullTreeEvidenceCapture", "ProviderErrorPayload"])
    source = SuppliedInput({
        ("FETCH_CORRECTED", (("lookback", 10), ("symbol", "OANDA:XAUUSD"), ("timeframe", "15m"))): captured(
            api.ProviderErrorPayload(error_type=LookupError, message="historical tape absent"), source="missing-frame",
        ),
    })
    capture = api.FullTreeEvidenceCapture(
        source, run_id="captured-error", instrument="OANDA:XAUUSD", pass_id="error-pass",
        decision_time=T1, source_variant="full_tree:house",
    )

    captured_result = capture.capture_walk()
    replayed = FullTreeCausalReplay(captured_result.bundle).run_pass("error-pass")

    assert captured_result.receipt.operation_count == 1
    assert captured_result.bundle.artifacts[0].kind == "ERROR"
    assert replayed.record.outcome == "TREE_STOPPED"
    assert replayed.record.trace_digest == captured_result.receipt.trace_digest


def test_capture_revalidation_uses_the_actual_pending_check_and_replays_its_trace():
    from test_full_tree_replay import _captured_revalidation_bundle

    api = __import__("trading_system.tree_replay.full_tree_capture", fromlist=["FullTreeEvidenceCapture"])
    literal_tape = _captured_revalidation_bundle(7200.0)
    original_pass = literal_tape.passes[0]
    capture = api.FullTreeEvidenceCapture(
        ScheduledBundleInput(literal_tape), run_id="captured-revalidation", instrument="OANDA:XAUUSD",
        pass_id="captured-revalidation-pass", decision_time=original_pass.decision_time,
        source_variant="full_tree:house",
    )

    captured_result = capture.capture_revalidation(original_pass.pending_plan)
    replayed = FullTreeCausalReplay(captured_result.bundle).run_pass("captured-revalidation-pass")

    assert captured_result.bundle.passes[0].mode == "TREE_REVALIDATION"
    assert captured_result.receipt.operation_count == len(original_pass.operations)
    assert replayed.record.trace_digest == captured_result.receipt.trace_digest
    assert replayed.record.revalidation_verified is True
