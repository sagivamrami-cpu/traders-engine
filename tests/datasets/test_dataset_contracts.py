import json
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

from trading_system.datasets.contracts import CandidateTrainingRow

ROOT = Path(__file__).resolve().parents[2]


def validate_row(payload: dict) -> None:
    schema = json.loads((ROOT / "schemas/candidate_training_row.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_candidate_training_row_payload_matches_schema():
    row = CandidateTrainingRow(
        row_id="row-1",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        snapshot_id="snapshot-1",
        candidate_id="candidate-1",
        symbol="TR_FIXTURE_SPY",
        observation_time=datetime(2026, 8, 28, 13, 31, tzinfo=UTC),
        graph_id="tr-vshape-retest-long",
        graph_version="fixture-graph-rules-0.1.0",
        direction="LONG",
        candidate_status="ELIGIBLE",
        features={"price.return_pct": 0.001},
        feature_schema_version="feature-catalog-0.1.0",
        contract_version="fixture-tr-contract-0.1.0",
        label_version="fixture-outcome-0.1.0",
        outcome_class="TARGET_FIRST",
        label_quality="HIGH",
        included_in_training=True,
        exclusion_reasons=[],
        split="TRAIN",
        source_hashes={"ohlcv-fixture-v1": "a" * 64},
    )

    validate_row(row.to_payload())
