from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.datasets.contracts import CandidateTrainingRow  # noqa: E402
from trading_system.models.baseline import train_majority_baseline  # noqa: E402
from trading_system.models.readiness import load_training_policy  # noqa: E402


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def validate_run(payload: dict[str, Any]) -> None:
    schema = load_json("schemas/model_training_run.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def row(row_id: str, outcome_class: str, split: str, *, included: bool = True) -> CandidateTrainingRow:
    return CandidateTrainingRow(
        row_id=row_id,
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        snapshot_id=f"snapshot-{row_id}",
        candidate_id=f"candidate-{row_id}",
        symbol="TR_FIXTURE_SPY",
        observation_time=datetime(2026, 8, 28, 13, 31, tzinfo=UTC),
        graph_id="tr-vshape-retest-long",
        graph_version="fixture-graph-rules-0.1.0",
        direction="LONG",
        candidate_status="ELIGIBLE" if included else "REJECTED",
        features={"price.return_pct": 0.001},
        feature_schema_version="feature-catalog-0.1.0",
        contract_version="fixture-tr-contract-0.1.0" if included else None,
        label_version="fixture-outcome-0.1.0" if included else None,
        outcome_class=outcome_class if included else None,
        label_quality="HIGH" if included else "EXCLUDED_FROM_TRAINING",
        included_in_training=included,
        exclusion_reasons=() if included else ("CANDIDATE_REJECTED",),
        split=split,
        source_hashes={"ohlcv-fixture-v1": "a" * 64},
    )


def main() -> None:
    policy = load_training_policy(ROOT / "configs/models/baseline-training-policy.yaml")
    blocked_run = train_majority_baseline(
        [row("1", "TARGET_FIRST", "TRAIN")],
        policy,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    trained_run = train_majority_baseline(
        [
            row("1", "STOP_FIRST", "TRAIN"),
            row("2", "TARGET_FIRST", "TRAIN"),
            row("3", "STOP_FIRST", "TRAIN"),
            row("4", "STOP_FIRST", "VALIDATION"),
            row("5", "TARGET_FIRST", "TEST"),
        ],
        policy,
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    if blocked_run.status != "BLOCKED":
        raise ValueError("fixture-sized dataset should be blocked")
    if trained_run.status != "TRAINED":
        raise ValueError("synthetic trainable rows should train the baseline")
    if blocked_run.promotion_allowed or trained_run.promotion_allowed:
        raise ValueError("Phase 5 promotion must remain disabled")
    validate_run(blocked_run.to_payload())
    validate_run(trained_run.to_payload())
    print("Phase 5 artifacts validated")


if __name__ == "__main__":
    main()
