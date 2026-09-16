import json
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.csv_onboarding import build_raw_source_manifest_for_csv
from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.data_foundation.storage_policy import (
    evaluate_raw_data_retention,
    load_raw_data_retention_policy,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs/data/raw-data-retention-policy.yaml"
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def validate_policy_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/raw_data_retention_policy.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def manifest(status: str = "OPEN_HUMAN_DECISION") -> dict:
    metadata = yaml.safe_load((ROOT / "configs/data/local-csv-onboarding-template.yaml").read_text(encoding="utf-8"))
    metadata["source_status"] = status
    return build_raw_source_manifest_for_csv(
        FIXTURE_CSV,
        metadata,
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        ingested_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def test_raw_data_retention_policy_payload_validates_against_schema():
    payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))

    validate_policy_payload(payload)
    assert payload["mode"] == "MANIFEST_ONLY_LOCAL_CSV"
    assert payload["raw_copy_allowed"] is False


def test_manifest_only_local_csv_decision_blocks_raw_retention_actions():
    policy = load_raw_data_retention_policy(POLICY_PATH)
    decision = evaluate_raw_data_retention(policy, manifest())
    payload = decision.to_payload()

    assert payload["status"] == "MANIFEST_ONLY_ALLOWED"
    assert payload["retention_approved"] is False
    assert payload["manifest_output_allowed"] is True
    assert payload["dry_run_output_allowed"] is True
    assert payload["raw_copy_allowed"] is False
    assert payload["raw_mutation_allowed"] is False
    assert payload["network_upload_allowed"] is False
    assert "COPY_RAW_CSV" in payload["forbidden_actions"]
    assert "RAW_RETENTION_REQUIRES_HUMAN_APPROVAL" in payload["blocked_reasons"]


def test_non_open_source_status_is_blocked():
    policy = load_raw_data_retention_policy(POLICY_PATH)
    decision = evaluate_raw_data_retention(policy, manifest(status="APPROVED_FIXTURE"))

    assert decision.status == "BLOCKED"
    assert "SOURCE_STATUS_NOT_OPEN_HUMAN_DECISION" in decision.blocked_reasons


def test_edited_policy_with_storage_roots_blocks_manifest_only_mode(tmp_path: Path):
    payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    payload["approved_storage_roots"] = ["C:/market-data/raw"]
    path = tmp_path / "edited-retention-policy.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    decision = evaluate_raw_data_retention(load_raw_data_retention_policy(path), manifest())

    assert decision.status == "BLOCKED"
    assert "APPROVED_STORAGE_ROOTS_MUST_BE_EMPTY_UNTIL_APPROVAL" in decision.blocked_reasons
