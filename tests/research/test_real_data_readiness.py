import json
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.research.readiness import (
    build_real_data_readiness_report,
    load_real_data_readiness_checklist,
)

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST_PATH = ROOT / "configs/research/real-data-readiness-checklist.yaml"


def validate_payload(schema_name: str, payload: dict) -> None:
    schema = json.loads((ROOT / f"schemas/{schema_name}").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def report():
    return build_real_data_readiness_report(
        load_real_data_readiness_checklist(CHECKLIST_PATH),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def test_real_data_readiness_checklist_config_validates_against_schema():
    payload = yaml.safe_load(CHECKLIST_PATH.read_text(encoding="utf-8"))

    validate_payload("real_data_readiness_report.schema.json", report().to_payload())
    assert payload["version"] == "real-data-readiness-checklist-0.1.0"
    assert len(payload["required_items"]) >= 6


def test_default_real_data_readiness_report_remains_blocked():
    payload = report().to_payload()

    assert payload["status"] == "BLOCKED"
    assert payload["satisfied_count"] == 0
    assert payload["open_count"] == payload["required_count"]
    assert "BUILD_PRODUCTION_TRAINING_DATASET" in payload["blocked_actions"]
    assert "TRAIN_PRODUCTION_MODEL" in payload["blocked_actions"]
    assert "LIVE_TRADING" in payload["blocked_actions"]


def test_required_human_inputs_are_explicit():
    payload = report().to_payload()
    item_ids = {item["item_id"] for item in payload["required_items"]}

    assert "REAL_HISTORICAL_OHLCV_CSV" in item_ids
    assert "FIRST_REAL_SYMBOL" in item_ids
    assert "FIRST_HISTORICAL_INTERVAL" in item_ids
    assert "RAW_DATA_STORAGE_LICENSE_APPROVAL" in item_ids
    assert "ORDER_FLOW_SOURCE_DECISION" in item_ids
    assert "OPTIONS_SOURCE_DECISION" in item_ids
    assert "PRODUCTION_OHLCV_VENDOR_DECISION" in item_ids


def test_no_required_item_is_satisfied_by_default():
    payload = report().to_payload()

    assert all(item["status"] == "OPEN_HUMAN_DECISION" for item in payload["required_items"])
