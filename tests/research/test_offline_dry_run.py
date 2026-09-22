import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
import pytest

from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.models.readiness import load_training_policy
from trading_system.research.offline_dry_run import build_local_csv_research_dry_run

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"
METADATA_PATH = ROOT / "configs/data/local-csv-onboarding-template.yaml"
RETENTION_POLICY_PATH = ROOT / "configs/data/raw-data-retention-policy.yaml"


def metadata() -> dict:
    return yaml.safe_load(METADATA_PATH.read_text(encoding="utf-8"))


def dry_run():
    return build_local_csv_research_dry_run(
        FIXTURE_CSV,
        metadata(),
        load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
        load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
        load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml"),
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )


def validate_payload(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/offline_research_run.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_local_csv_dry_run_payload_validates_against_schema():
    payload = dry_run().to_payload()

    validate_payload(payload)
    assert payload["run_version"] == "offline-research-run-0.1.0"
    assert payload["mode"] == "LOCAL_CSV_DRY_RUN"


def test_local_csv_dry_run_keeps_source_and_training_blocked():
    payload = dry_run().to_payload()

    assert payload["raw_source_manifest"]["source_status"] == "OPEN_HUMAN_DECISION"
    assert payload["training_run"]["status"] == "BLOCKED"
    assert payload["training_run"]["promotion_allowed"] is False
    assert payload["safety_status"] == "BLOCKED_FOR_RESEARCH_ONLY"
    assert "PRODUCTION_SOURCE_NOT_APPROVED" in payload["blocked_reasons"]


def test_fixture_counts_are_deterministic():
    payload = dry_run().to_payload()

    assert payload["normalized_bar_count"] == 6
    assert payload["snapshot_count"] == 6
    assert payload["candidate_count"] == 6
    assert payload["training_row_count"] == 6
    assert payload["included_training_row_count"] == 1


def test_non_fixture_metadata_cannot_use_fixture_dry_run_identity():
    non_fixture_metadata = metadata()
    non_fixture_metadata["source_id"] = "local-csv-ohlcv-real-spy"

    try:
        build_local_csv_research_dry_run(
            FIXTURE_CSV,
            non_fixture_metadata,
            load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
            load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
            load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml"),
            created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        )
    except ValueError as error:
        assert "FIXTURE_SYMBOL_FORBIDDEN_FOR_REAL_SOURCE" in str(error)
    else:
        raise AssertionError("non-fixture metadata must not use fixture dry-run identity")


def test_dry_run_rejects_real_source_without_existing_human_decision_record():
    real_metadata = metadata()
    real_metadata["source_id"] = "real-ohlcv-spy-1m"
    real_metadata["canonical_symbol"] = "SPY.US"
    real_metadata["human_decision_ref"] = "agent-exchange/decisions/example.md"

    with pytest.raises(ValueError, match="HUMAN_DECISION_REF_NOT_FOUND"):
        build_local_csv_research_dry_run(
            FIXTURE_CSV,
            real_metadata,
            load_normalization_policy(ROOT / "configs/data/normalization-policy.yaml"),
            load_symbol_map(ROOT / "configs/data/symbol-map.yaml"),
            load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml"),
            created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
        )


def test_dry_run_cli_requires_retention_policy_gate():
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_local_csv_dry_run.py",
            "--csv",
            str(FIXTURE_CSV),
            "--metadata",
            str(METADATA_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "retention" in result.stderr.lower()


def test_dry_run_cli_runs_after_bundle_validation_gate():
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_local_csv_dry_run.py",
            "--csv",
            str(FIXTURE_CSV),
            "--metadata",
            str(METADATA_PATH),
            "--retention-policy",
            str(RETENTION_POLICY_PATH),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "LOCAL_CSV_DRY_RUN"
    assert payload["safety_status"] == "BLOCKED_FOR_RESEARCH_ONLY"
