from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from trading_system.tree_replay._vendor.correction import Correction
from trading_system.tree_replay.full_tree_contracts import (
    FullTreeArtifact,
    FullTreeEvidenceBundle,
    FullTreeOperation,
    FullTreePass,
    TreeFramePayload,
    ProviderErrorPayload,
)
from trading_system.tree_replay.full_tree_provider import (
    FullTreeCausalProvider,
    FullTreeProviderError,
)


T0 = datetime(2026, 1, 2, 9, 30, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)
T2 = T1 + timedelta(minutes=5)
SYMBOL = "OANDA:XAUUSD"


def frame_payload():
    frame = pd.DataFrame(
        {"open": [100.0, 101.0], "high": [101.0, 102.0], "low": [99.0, 100.0],
         "close": [100.5, 101.5], "volume": [10.0, 11.0]},
        index=pd.to_datetime(["2026-01-02T09:20:00Z", "2026-01-02T09:25:00Z"]),
    )
    return TreeFramePayload(
        frame=frame,
        correction=Correction(SYMBOL, 0.0, "tv_daily", "exact", "test evidence"),
    )


def artifact(artifact_id, kind, value, digest):
    return FullTreeArtifact(
        artifact_id=artifact_id,
        kind=kind,
        observed_at=T0,
        available_at=T0,
        covered_through=T2,
        content_digest=digest,
        value=value,
    )


def fetch(operation_id, sequence, artifact_id):
    return FullTreeOperation(
        operation_id=operation_id,
        kind="FETCH_CORRECTED",
        arguments={"symbol": SYMBOL, "timeframe": "5m", "lookback": 600},
        artifact_id=artifact_id,
        sequence=sequence,
    )


def calendar(operation_id, sequence, artifact_id):
    return FullTreeOperation(
        operation_id=operation_id,
        kind="CALENDAR_TEXT",
        arguments={"path": "news-desk/data/ff_calendar.json"},
        artifact_id=artifact_id,
        sequence=sequence,
    )


def operation(operation_id, sequence, kind, arguments, artifact_id):
    return FullTreeOperation(
        operation_id=operation_id,
        kind=kind,
        arguments=arguments,
        artifact_id=artifact_id,
        sequence=sequence,
    )


def bundle(operations, artifacts):
    return FullTreeEvidenceBundle(
        run_id="provider-run-1",
        instrument=SYMBOL,
        artifacts=tuple(artifacts),
        passes=(FullTreePass(
            pass_id="pass-1",
            decision_time=T1,
            source_variant="full_tree:house",
            mode="TREE_WALK",
            operations=tuple(operations),
        ),),
    )


def test_repeated_fetches_consume_distinct_operations_and_return_detached_frames():
    supplied = artifact("frame-1", "FRAME", frame_payload(), "a" * 64)
    provider = FullTreeCausalProvider(
        bundle((fetch("fetch-1", 0, "frame-1"), fetch("fetch-2", 1, "frame-1")), (supplied,)),
        pass_id="pass-1",
    )

    first, _ = provider.fetch_corrected(SYMBOL, "5m", 600)
    first.iloc[0, first.columns.get_loc("close")] = -999.0
    second, _ = provider.fetch_corrected(SYMBOL, "5m", 600)

    assert second.iloc[0]["close"] == 100.5
    assert [trace["operation_id"] for trace in provider.public_trace()] == ["fetch-1", "fetch-2"]
    provider.assert_no_unexpected_calls()


def test_out_of_order_source_call_fails_closed_before_consuming_evidence():
    supplied = artifact("frame-1", "FRAME", frame_payload(), "a" * 64)
    provider = FullTreeCausalProvider(bundle((fetch("fetch-1", 0, "frame-1"),), (supplied,)), pass_id="pass-1")

    with pytest.raises(FullTreeProviderError, match="FULL_TREE_OPERATION_MISMATCH"):
        provider.calendar_text("news-desk/data/ff_calendar.json")

    assert provider.public_trace() == ()


def test_provider_exposes_only_scheduled_ports_and_keeps_shadow_contents_private():
    artifacts = (
        artifact("utc-1", "CLOCK", T1, "a" * 64),
        artifact("epoch-1", "CLOCK", T1, "b" * 64),
        artifact("timestamp-1", "CLOCK", T1, "c" * 64),
        artifact("calendar-exists-1", "SHADOW_RESULT", False, "d" * 64),
        artifact("reports-1", "REPORT_LIST", ["report-1.json"], "e" * 64),
        artifact("report-1", "TEXT", '{"wall": 100}', "f" * 64),
        artifact("tv-1", "TEXT", "time,close\n2026-01-02T09:30:00Z,100\n", "1" * 64),
        artifact("deep-exists-1", "SHADOW_RESULT", True, "2" * 64),
        artifact("deep-bytes-1", "BYTES", b"time,close\n", "3" * 64),
        artifact("shadow-parent-1", "SHADOW_RESULT", None, "4" * 64),
        artifact("shadow-open-1", "SHADOW_RESULT", None, "5" * 64),
    )
    operations = (
        operation("utc-call", 0, "NOW_UTC", {}, "utc-1"),
        operation("epoch-call", 1, "NOW_EPOCH", {}, "epoch-1"),
        operation("timestamp-call", 2, "NOW_TIMESTAMP", {"tz": "UTC"}, "timestamp-1"),
        operation("calendar-exists-call", 3, "CALENDAR_EXISTS", {"path": "calendar.json"}, "calendar-exists-1"),
        operation("reports-call", 4, "LIST_REPORTS", {}, "reports-1"),
        operation("report-call", 5, "READ_REPORT", {"logical_id": "report-1.json"}, "report-1"),
        operation("tv-call", 6, "READ_TV_CSV", {"filename": "tv.csv"}, "tv-1"),
        operation("deep-exists-call", 7, "DEEP_EXISTS", {"key": "deep/XAU.csv"}, "deep-exists-1"),
        operation("deep-bytes-call", 8, "DEEP_BYTES", {"key": "deep/XAU.csv"}, "deep-bytes-1"),
        operation("shadow-parent-call", 9, "ENSURE_SHADOW_PARENT", {"parents": True, "exist_ok": True}, "shadow-parent-1"),
        operation("shadow-open-call", 10, "SHADOW_OPEN", {"mode": "a", "encoding": "utf-8"}, "shadow-open-1"),
    )
    provider = FullTreeCausalProvider(bundle(operations, artifacts), pass_id="pass-1")

    assert provider.now_utc() == T1
    assert provider.now_epoch() == T1.timestamp()
    assert provider.now_timestamp(tz="UTC") == pd.Timestamp(T1)
    assert provider.calendar_exists("calendar.json") is False
    assert provider.list_reports() == ["report-1.json"]
    assert provider.read_report("report-1.json") == '{"wall": 100}'
    assert provider.read_tv_csv("tv.csv").startswith("time,close")
    assert provider.deep_exists("deep/XAU.csv") is True
    assert provider.deep_bytes("deep/XAU.csv") == b"time,close\n"
    assert provider.ensure_shadow_parent(parents=True, exist_ok=True) is None
    with provider.shadow_open("a", encoding="utf-8") as shadow:
        assert shadow.write("private shadow entry\n") == len("private shadow entry\n")
    provider.assert_no_unexpected_calls()

    trace = provider.public_trace()
    assert "private shadow entry" not in repr(trace)
    assert trace[-1]["shadow_write_digest"] != ""


def test_scheduled_source_error_is_raised_at_its_call_but_its_text_stays_private():
    private_message = "raw report bytes are unavailable"
    supplied_error = artifact(
        "report-error-1",
        "ERROR",
        ProviderErrorPayload(error_type=OSError, message=private_message),
        "f" * 64,
    )
    provider = FullTreeCausalProvider(
        bundle((operation("report-call", 0, "READ_REPORT", {"logical_id": "report.json"}, "report-error-1"),),
               (supplied_error,)),
        pass_id="pass-1",
    )

    with pytest.raises(OSError, match=private_message):
        provider.read_report("report.json")

    trace = provider.public_trace()
    assert [item["operation_id"] for item in trace] == ["report-call"]
    assert private_message not in repr(trace)
