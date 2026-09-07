from datetime import UTC, datetime

import pytest

from trading_system.research.manual_tree_replay_alignment import (
    build_manual_tree_golden_alerts,
    build_manual_tree_replay_alignment_report,
)

FIXED_TIME = datetime(2026, 9, 7, 23, 30, tzinfo=UTC)


def manual_alert_inputs() -> list[dict]:
    return [
        {
            "source_row_index": 1,
            "asset": "XAUUSD",
            "alert_date": "2026-08-31",
            "alert_time": "08:58",
            "direction": "SELL",
            "entry_price": 4445.45,
            "targets_hit_visible": 0,
            "max_favorable_move": 116.0,
            "outcome_status": "FILLED",
        },
        {
            "source_row_index": 2,
            "asset": "XAUUSD",
            "alert_date": "2026-09-04",
            "alert_time": "11:05",
            "direction": "BUY",
            "entry_price": 4482.45,
            "targets_hit_visible": 0,
            "max_favorable_move": 17.0,
            "outcome_status": "BELOW_THRESHOLD",
        },
    ]


def gc_manifest() -> dict:
    return {
        "dataset_id": "gc-dataset",
        "dataset_name": "gc-30m-real-research-dataset",
        "summary": {
            "first_bar_start": "2010-06-07T00:00:00Z",
            "last_bar_start": "2026-08-05T23:30:00Z",
        },
    }


def test_manual_alerts_convert_israel_time_to_utc_and_preserve_trade_fields():
    alerts = build_manual_tree_golden_alerts(
        manual_alert_inputs(),
        created_at=FIXED_TIME,
        source_timezone="Asia/Jerusalem",
    ).to_payload()

    assert alerts["alert_count"] == 2
    assert alerts["source_timezone"] == "Asia/Jerusalem"
    assert alerts["alerts"][0]["alert_local_time"] == "2026-08-31T08:58:00+03:00"
    assert alerts["alerts"][0]["alert_utc_time"] == "2026-08-31T05:58:00Z"
    assert alerts["alerts"][1]["alert_utc_time"] == "2026-09-04T08:05:00Z"
    assert alerts["alerts"][1]["outcome_status"] == "BELOW_THRESHOLD"
    assert alerts["alerts"][1]["raw_symbol"] == "XAUUSD"


def test_manual_alert_ids_are_stable_across_generation_time():
    first = build_manual_tree_golden_alerts(
        manual_alert_inputs(),
        created_at=FIXED_TIME,
        source_timezone="Asia/Jerusalem",
    ).to_payload()
    second = build_manual_tree_golden_alerts(
        manual_alert_inputs(),
        created_at=datetime(2026, 9, 8, 1, 15, tzinfo=UTC),
        source_timezone="Asia/Jerusalem",
    ).to_payload()

    assert first["created_at"] != second["created_at"]
    assert first["golden_set_id"] == second["golden_set_id"]


def test_alignment_report_blocks_replay_against_current_gc_dataset():
    alerts = build_manual_tree_golden_alerts(
        manual_alert_inputs(),
        created_at=FIXED_TIME,
        source_timezone="Asia/Jerusalem",
    ).to_payload()
    report = build_manual_tree_replay_alignment_report(
        alerts,
        gc_manifest(),
        symbol_map={"GC"},
        tree_gate_audit_id="a" * 64,
        created_at=FIXED_TIME,
    ).to_payload()

    assert report["status"] == "REPLAY_BLOCKED_SOURCE_DATA_GAP"
    assert report["manual_alert_count"] == 2
    assert report["tree_gate_audit_id"] == "a" * 64
    assert report["current_dataset_symbol"] == "GC"
    assert report["manual_alert_symbol"] == "XAUUSD"
    assert report["eligible_for_current_replay_count"] == 0
    assert "SYMBOL_MISMATCH_XAUUSD_VS_GC" in report["blocked_reasons"]
    assert "ALERT_RANGE_AFTER_CURRENT_DATASET_END" in report["blocked_reasons"]
    assert report["replay_ready"] is False
    assert report["model_training_allowed"] is False
    assert report["recommended_next_phase"] == "PHASE_59_XAUUSD_REPLAY_DATA_ONBOARDING_OR_PROXY_DECISION"


def test_alignment_report_id_is_stable_across_generation_time():
    alerts = build_manual_tree_golden_alerts(
        manual_alert_inputs(),
        created_at=FIXED_TIME,
        source_timezone="Asia/Jerusalem",
    ).to_payload()
    first = build_manual_tree_replay_alignment_report(
        alerts,
        gc_manifest(),
        symbol_map={"GC"},
        tree_gate_audit_id="a" * 64,
        created_at=FIXED_TIME,
    ).to_payload()
    second = build_manual_tree_replay_alignment_report(
        alerts,
        gc_manifest(),
        symbol_map={"GC"},
        tree_gate_audit_id="a" * 64,
        created_at=datetime(2026, 9, 8, 1, 15, tzinfo=UTC),
    ).to_payload()

    assert first["created_at"] != second["created_at"]
    assert first["report_id"] == second["report_id"]


def test_alignment_schema_rejects_replay_ready_when_blocked():
    alerts = build_manual_tree_golden_alerts(
        manual_alert_inputs(),
        created_at=FIXED_TIME,
        source_timezone="Asia/Jerusalem",
    ).to_payload()
    run = build_manual_tree_replay_alignment_report(
        alerts,
        gc_manifest(),
        symbol_map={"GC"},
        tree_gate_audit_id="a" * 64,
        created_at=FIXED_TIME,
    )
    payload = run.to_payload()
    payload["replay_ready"] = True

    with pytest.raises(Exception):
        run.__class__(payload).to_payload()
