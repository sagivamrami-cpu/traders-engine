from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib

import pandas as pd
import pytest


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
