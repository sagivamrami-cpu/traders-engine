import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.manifests import load_json

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/data/gc-bar-session-timestamp-policy.yaml"
SCHEMA_PATH = ROOT / "schemas/gc_bar_session_timestamp_policy.schema.json"
CREATED_AT = datetime(2026, 9, 1, 21, 30, tzinfo=UTC)


def validate_policy_payload(payload: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def minimal_valid_policy_payload() -> dict:
    return {
        "report_id": "a" * 64,
        "policy_version": "gc-bar-session-timestamp-policy-0.1.0",
        "mode": "GC_BAR_SESSION_TIMESTAMP_POLICY",
        "created_at": "2026-09-01T21:30:00Z",
        "status": "POLICY_APPROVED_MISSING_BAR_RESOLVED_CONSTRUCTION_AUTHORIZED",
        "canonical_symbol": "GC",
        "candidate_timeframe": "30m_UTC_FIXED_BASELINE_APPROVED_V1",
        "bar_boundary_policy": {
            "status": "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED",
            "decision_ref": "agent-exchange/decisions/2026-09-01T182500Z-human-d1-bar-boundary-available-at-v1.md",
            "interval": "30m_UTC_FIXED_BASELINE_APPROVED_V1",
            "timezone": "UTC_FIXED_APPROVED_V1",
            "boundary_minutes": [0, 30],
            "interval_semantics": "HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE_APPROVED_V1",
            "available_at": "BAR_END_UTC_APPROVED_V1",
        },
        "session_calendar_policy": {
            "status": "SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH",
            "decision_ref": "agent-exchange/decisions/2026-09-02T052000Z-human-d2-final-session-calendar-implementation.md",
            "source_strategy_ref": "configs/data/gc-session-calendar-source-strategy.yaml",
            "calendar_id": "cme-globex-metals-research-v1",
            "exchange_timezone": "America/Chicago",
            "utc_session_reconciliation_status": "SATISFIED_RESEARCH_CALENDAR_V1",
            "utc_bar_session_membership_status": "IMPLEMENTED_RESEARCH_V1",
            "trade_date_roll_status": "IMPLEMENTED_RESEARCH_V1",
            "cme_source_scope_status": "GC_GLOBEX_NORMAL_HOURS_RESEARCH_V1",
            "open_reconciliation_questions": [],
            "reconciliation_answers": {
                "UTC_30M_BARS_THAT_STRADDLE_CME_DAILY_BREAK": "DROP_AND_COUNT_STRADDLES_SESSION_BOUNDARY_ZERO_EXPECTED_FOR_GC",
                "SESSION_CLOSED_BARS_DROP_MARK_OR_KEEP_WITH_SESSION_FLAG": "DROP_AND_COUNT_OUT_OF_SESSION_BARS",
                "DST_SHIFT_OF_CT_SESSION_BOUNDARIES_AGAINST_UTC_BARS": "CT_BOUNDARIES_ALIGN_TO_30M_UTC_GRID_IN_CST_AND_CDT_VERIFIED",
            },
            "normal_session": {
                "days": "SUNDAY_TO_FRIDAY",
                "open_time_ct": "17:00",
                "close_time_ct": "16:00",
                "daily_break_start_ct": "16:00",
                "daily_break_end_ct": "17:00",
            },
            "source_urls": [
                "https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html",
                "https://www.cmegroup.com/trading-hours.html",
            ],
            "holiday_overlay_status": "TRANSFERRED_TO_MISSING_BAR_POLICY_OBSERVED_GAP_EXCLUSION_V1",
        },
        "timestamp_policy": {
            "status": "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED",
            "decision_ref": "agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md",
            "ohlcv_1s_timestamp_role": "TS_EVENT_INTERVAL_START_APPROVED_V1",
            "ohlcv_1s_evidence_status": "ARCHIVE_SCHEMA_UTC_AWARE_PLUS_HUMAN_APPROVAL",
            "order_flow_minute_role": "MINUTE_START_APPROVED_V1",
            "naive_minute_timezone_policy": "LOCALIZE_AS_UTC_WALL_CLOCK_APPROVED_V1",
        },
        "dataset_construction_allowed": True,
        "resampling_allowed": True,
        "training_allowed": False,
        "required_remaining_gates": [],
        "blocked_actions": [
            "TRAIN_PRODUCTION_MODEL",
            "MODEL_PROMOTION",
            "LIVE_TRADING",
            "BROKER_EXECUTION",
            "CAPITAL_ALLOCATION",
            "CLAIM_EDGE",
            "USE_ARCHIVED_CVD_COLUMN",
            "MAP_GC_TO_XAUUSD",
            "INGEST_ORDERFLOW_4H_CSV",
            "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES",
        ],
        "blocked_reasons": [],
    }


def test_gc_bar_session_timestamp_policy_schema_accepts_source_backed_candidate():
    payload = minimal_valid_policy_payload()
    validate_policy_payload(payload)
    assert payload["candidate_timeframe"] == "30m_UTC_FIXED_BASELINE_APPROVED_V1"
    assert payload["bar_boundary_policy"]["status"] == "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert payload["bar_boundary_policy"]["available_at"] == "BAR_END_UTC_APPROVED_V1"
    assert payload["timestamp_policy"]["status"] == "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert payload["timestamp_policy"]["ohlcv_1s_timestamp_role"] == "TS_EVENT_INTERVAL_START_APPROVED_V1"
    assert payload["session_calendar_policy"]["calendar_id"] == "cme-globex-metals-research-v1"
    assert payload["session_calendar_policy"]["holiday_overlay_status"] == (
        "TRANSFERRED_TO_MISSING_BAR_POLICY_OBSERVED_GAP_EXCLUSION_V1"
    )
    assert payload["dataset_construction_allowed"] is True
    assert payload["training_allowed"] is False
    assert payload["blocked_reasons"] == []


def test_gc_bar_session_timestamp_policy_config_and_report_remain_blocked():
    from trading_system.research.gc_bar_session_timestamp_policy import (
        build_gc_bar_session_timestamp_policy_report,
    )

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert config["candidate_timeframe"] == "30m_UTC_FIXED_BASELINE_APPROVED_V1"
    assert config["bar_boundary_policy"]["status"] == "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert config["bar_boundary_policy"]["boundary_minutes"] == [0, 30]
    assert config["bar_boundary_policy"]["available_at"] == "BAR_END_UTC_APPROVED_V1"
    assert config["session_calendar_policy"]["calendar_id"] == "cme-globex-metals-research-v1"
    assert config["session_calendar_policy"]["status"] == (
        "SATISFIED_RESEARCH_CALENDAR_V1_NOT_EXECUTION_TRUTH"
    )
    assert config["session_calendar_policy"]["decision_ref"].endswith(
        "human-d2-final-session-calendar-implementation.md"
    )
    assert config["session_calendar_policy"]["source_strategy_ref"] == (
        "configs/data/gc-session-calendar-source-strategy.yaml"
    )
    assert config["session_calendar_policy"]["normal_session"]["open_time_ct"] == "17:00"
    assert config["session_calendar_policy"]["holiday_overlay_status"] == (
        "TRANSFERRED_TO_MISSING_BAR_POLICY_OBSERVED_GAP_EXCLUSION_V1"
    )
    assert config["missing_bar_policy_ref"] == "configs/data/gc-missing-bar-policy.yaml"
    assert config["construction_authorization_ref"].endswith("dataset-construction-authorization-gc-30m-f9d3c1b0.md")
    assert config["session_calendar_policy"]["utc_session_reconciliation_status"] == (
        "SATISFIED_RESEARCH_CALENDAR_V1"
    )
    assert config["session_calendar_policy"]["utc_bar_session_membership_status"] == "IMPLEMENTED_RESEARCH_V1"
    assert config["session_calendar_policy"]["trade_date_roll_status"] == "IMPLEMENTED_RESEARCH_V1"
    assert config["timestamp_policy"]["status"] == "HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED"
    assert config["timestamp_policy"]["decision_ref"].endswith("human-d3-timestamp-policy-v1.md")
    assert config["timestamp_policy"]["ohlcv_1s_timestamp_role"] == "TS_EVENT_INTERVAL_START_APPROVED_V1"
    assert config["timestamp_policy"]["order_flow_minute_role"] == "MINUTE_START_APPROVED_V1"
    assert config["timestamp_policy"]["naive_minute_timezone_policy"] == (
        "LOCALIZE_AS_UTC_WALL_CLOCK_APPROVED_V1"
    )

    payload = build_gc_bar_session_timestamp_policy_report(
        CONFIG_PATH,
        created_at=CREATED_AT,
    ).to_payload()

    validate_policy_payload(payload)
    assert payload["status"] == "POLICY_APPROVED_MISSING_BAR_RESOLVED_CONSTRUCTION_AUTHORIZED"
    assert payload["training_allowed"] is False
    assert payload["dataset_construction_allowed"] is True
    assert payload["resampling_allowed"] is True
    assert payload["required_remaining_gates"] == []
    assert payload["blocked_reasons"] == []
    assert "RESAMPLE_REAL_BARS" not in payload["blocked_actions"]
    assert "CLAIM_EDGE" in payload["blocked_actions"]
    assert "INGEST_CONTINUOUS_OR_STITCHED_GC_SERIES" in payload["blocked_actions"]
    assert "HOLIDAY_OVERLAY_REQUIRED_NOT_ENCODED" not in payload["blocked_reasons"]
    assert "TIMESTAMP_ROLE_GATE_UNSATISFIED" not in payload["blocked_reasons"]
    assert "VENDOR_TIMESTAMP_EVIDENCE_PENDING" not in payload["blocked_reasons"]
    assert "BAR_BOUNDARY_GATE_UNSATISFIED" not in payload["blocked_reasons"]
    assert "AVAILABLE_AT_POLICY_GATE_UNSATISFIED" not in payload["blocked_reasons"]
    assert "MISSING_BAR_POLICY_GATE_UNSATISFIED" not in payload["blocked_reasons"]
    assert payload["session_calendar_policy"]["open_reconciliation_questions"] == []
    assert payload["session_calendar_policy"]["reconciliation_answers"][
        "UTC_30M_BARS_THAT_STRADDLE_CME_DAILY_BREAK"
    ] == "DROP_AND_COUNT_STRADDLES_SESSION_BOUNDARY_ZERO_EXPECTED_FOR_GC"
    assert "C:\\" not in json.dumps(payload, sort_keys=True)


def test_gc_bar_session_timestamp_policy_cli_outputs_sanitized_json():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_gc_bar_session_timestamp_policy.py",
            "--policy",
            "configs/data/gc-bar-session-timestamp-policy.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    validate_policy_payload(payload)
    assert payload["status"] == "POLICY_APPROVED_MISSING_BAR_RESOLVED_CONSTRUCTION_AUTHORIZED"
    assert payload["training_allowed"] is False
    assert "C:\\" not in result.stdout
    assert "/Users/" not in result.stdout
    assert result.stderr == ""
