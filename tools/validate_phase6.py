from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.datasets.contracts import CandidateTrainingRow  # noqa: E402
from trading_system.evaluation.predictions import prediction_from_majority_baseline  # noqa: E402
from trading_system.evaluation.walk_forward import (  # noqa: E402
    evaluate_majority_baseline_walk_forward,
    load_walk_forward_policy,
)


def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def validate(schema_name: str, payload: dict[str, Any]) -> None:
    schema = load_json(f"schemas/{schema_name}")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def row(index: int, outcome_class: str) -> CandidateTrainingRow:
    return CandidateTrainingRow(
        row_id=f"row-{index}",
        dataset_id="fixture-candidate-dataset",
        dataset_version="fixture-candidate-dataset-0.1.0",
        snapshot_id=f"snapshot-{index}",
        candidate_id=f"candidate-{index}",
        symbol="TR_FIXTURE_SPY",
        observation_time=datetime(2026, 8, 28, 13, 30, tzinfo=UTC) + timedelta(minutes=index),
        graph_id="tr-vshape-retest-long",
        graph_version="fixture-graph-rules-0.1.0",
        direction="LONG",
        candidate_status="ELIGIBLE",
        features={"price.return_pct": 0.001},
        feature_schema_version="feature-catalog-0.1.0",
        contract_version="fixture-tr-contract-0.1.0",
        label_version="fixture-outcome-0.1.0",
        outcome_class=outcome_class,
        label_quality="HIGH",
        included_in_training=True,
        exclusion_reasons=(),
        split="TRAIN",
        source_hashes={"ohlcv-fixture-v1": "a" * 64},
    )


def main() -> None:
    policy = load_walk_forward_policy(ROOT / "configs/evaluation/walk-forward-policy.yaml")
    prediction = prediction_from_majority_baseline(
        "candidate-1",
        baseline_class="TARGET_FIRST",
        model_version="majority-class-baseline-0.1.0",
        feature_schema_version="feature-catalog-0.1.0",
    )
    validate("prediction.schema.json", prediction.to_payload())

    blocked_report = evaluate_majority_baseline_walk_forward(
        [row(0, "TARGET_FIRST")],
        policy,
        training_run_id="run-blocked",
        model_version="majority-class-baseline-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    trained_report = evaluate_majority_baseline_walk_forward(
        [
            row(0, "STOP_FIRST"),
            row(1, "TARGET_FIRST"),
            row(2, "STOP_FIRST"),
            row(3, "STOP_FIRST"),
            row(4, "TARGET_FIRST"),
        ],
        policy,
        training_run_id="run-trained",
        model_version="majority-class-baseline-0.1.0",
        created_at=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )
    for report in [blocked_report, trained_report]:
        if report.promotion_allowed:
            raise ValueError("Phase 6 promotion must remain blocked")
        validate("model_evaluation_report.schema.json", report.to_payload())
    print("Phase 6 artifacts validated")


if __name__ == "__main__":
    main()
