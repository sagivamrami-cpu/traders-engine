import json
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from trading_system.data_foundation.normalization import load_normalization_policy, load_symbol_map
from trading_system.models.readiness import load_training_policy
from trading_system.research.offline_dry_run import build_local_csv_research_dry_run

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CSV = ROOT / "tests/fixtures/data_foundation/raw/ohlcv_fixture.csv"


def metadata() -> dict:
    return yaml.safe_load((ROOT / "configs/data/local-csv-onboarding-template.yaml").read_text(encoding="utf-8"))


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
