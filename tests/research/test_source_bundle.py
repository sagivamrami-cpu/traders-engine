import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from trading_system.research.source_bundle import validate_local_source_bundle

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
METADATA_PATH = ROOT / "configs/data/local-csv-onboarding-template.yaml"
RETENTION_POLICY_PATH = ROOT / "configs/data/raw-data-retention-policy.yaml"


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/source_bundle_validation.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def bundle(metadata_path: Path = METADATA_PATH):
    return validate_local_source_bundle(
        FIXTURE_CSV,
        metadata_path,
        RETENTION_POLICY_PATH,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def test_fixture_source_bundle_payload_validates_against_schema():
    payload = bundle().to_payload()

    validate_payload(payload)
    assert payload["validation_version"] == "source-bundle-validation-0.1.0"
    assert payload["mode"] == "LOCAL_SOURCE_BUNDLE_VALIDATION"


def test_fixture_source_bundle_is_accepted_for_dry_run_only():
    payload = bundle().to_payload()

    assert payload["status"] == "ACCEPTED_FOR_DRY_RUN"
    assert payload["retention_decision"]["retention_approved"] is False
    assert payload["dry_run_summary"]["promotion_allowed"] is False
    assert payload["dry_run_summary"]["safety_status"] == "BLOCKED_FOR_RESEARCH_ONLY"
    assert "MODEL_PROMOTION" in payload["blocked_actions"]


def test_non_open_metadata_source_status_blocks_bundle(tmp_path: Path):
    metadata = yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))
    metadata["source_status"] = "APPROVED_FIXTURE"
    metadata_path = tmp_path / "metadata.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=True), encoding="utf-8")

    payload = bundle(metadata_path).to_payload()

    assert payload["status"] == "BLOCKED"
    assert "RETENTION_POLICY_BLOCKED" in payload["blocked_reasons"]
    assert "SOURCE_STATUS_NOT_OPEN_HUMAN_DECISION" in payload["retention_decision"]["blocked_reasons"]


def test_missing_metadata_file_fails_explicitly(tmp_path: Path):
    missing_metadata = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        bundle(missing_metadata)


def test_source_bundle_validation_does_not_depend_on_process_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    payload = bundle().to_payload()

    assert payload["status"] == "ACCEPTED_FOR_DRY_RUN"
