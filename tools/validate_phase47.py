from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_system.data_foundation.manifests import load_json, validate_json_payload

BUILD_MANIFEST_PATH = ROOT / "configs/datasets/gc-30m-real-dataset-build-manifest.json"
ROWS_ROOT = ROOT / "market-data/gc-30m-real"
TRAINING_RUN_PATH = ROOT / "configs/models/gc-majority-baseline-training-run.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)


def _contains_local_path(value: object) -> bool:
    if isinstance(value, dict):
        return any(_contains_local_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_local_path(item) for item in value)
    if isinstance(value, str):
        return "C:\\" in value or "/Users/" in value
    return False


def main() -> None:
    _run([sys.executable, str(ROOT / "tools/validate_phase46.py")])
    _run([sys.executable, "-m", "pytest", "tests/research/test_gc_pretraining_readiness.py", "-q"])
    validate_json_payload(ROOT / "schemas/model_training_run.schema.json", load_json(TRAINING_RUN_PATH))

    result = _run(
        [
            sys.executable,
            str(ROOT / "tools/gc_pretraining_readiness.py"),
            "--contract",
            str(ROOT / "configs/datasets/gc-30m-real-dataset-contract.yaml"),
            "--decisions",
            str(ROOT / "agent-exchange/decisions/databento-gc-real-data-decisions.yaml"),
            "--checklist",
            str(ROOT / "configs/research/real-data-readiness-checklist.yaml"),
            "--training-policy",
            str(ROOT / "configs/models/baseline-training-policy.yaml"),
            "--groq-phase24-review",
            str(ROOT / "agent-exchange/reviews/2026-09-01T185200Z-groq-review-phase-24-dataset-contract.md"),
            "--groq-phase24-intake",
            str(ROOT / "agent-exchange/status/2026-09-01T170300Z-codex-groq-phase-23-to-26-review-intake.md"),
            "--build-manifest",
            str(BUILD_MANIFEST_PATH),
            "--rows-root",
            str(ROWS_ROOT),
            "--variant",
            "order_flow",
        ]
    )
    readiness = json.loads(result.stdout)
    validate_json_payload(ROOT / "schemas/gc_pretraining_readiness_report.schema.json", readiness)
    _require(readiness["status"] == "READY", "pre-training readiness must be READY after the real dataset build")
    _require(readiness["training_start_allowed"] is True, "training start must be allowed for the baseline gate")
    _require(readiness["dataset_construction_allowed"] is True, "dataset construction authorization must remain recorded")
    _require(readiness["model_promotion_allowed"] is False, "model promotion must remain blocked")
    _require(readiness["required_pretraining_gates"] == [], "no pre-training gate may remain open")
    _require(readiness["blocking_reviews"] == [], "external review blockers must be closed")
    _require(readiness["pending_process_steps"] == [], "no pending pre-training process step may remain")
    _require(not _contains_local_path(readiness), "readiness report must not contain local machine paths")

    training = load_json(TRAINING_RUN_PATH)
    _require(training["status"] == "TRAINED", "majority baseline training run must be trained")
    _require(training["model_type"] == "MAJORITY_CLASS_BASELINE", "Phase 47 only validates the baseline model")
    _require(training["baseline_class"] == "STOP_FIRST", "baseline class changed")
    _require(training["promotion_allowed"] is False, "baseline model promotion must remain blocked")
    _require(training["dataset_id"] == readiness["built_dataset_id"], "training run must use the ready dataset")
    _require(
        training["split_summary"] == readiness["training_readiness"]["split_summary"],
        "training split summary must match readiness",
    )
    _require(
        training["class_distribution"] == readiness["training_readiness"]["class_distribution"],
        "training class distribution must match readiness",
    )
    _require(training["split_summary"] == {"TRAIN": 238398, "VALIDATION": 45074, "TEST": 57584}, "trainable splits changed")
    _require(
        training["class_distribution"] == {"EXPIRED": 47922, "STOP_FIRST": 146567, "TARGET_FIRST": 146567},
        "trainable class distribution changed",
    )
    _require(
        training["metrics"] == {
            "validation_accuracy": 0.4223499134756179,
            "test_accuracy": 0.4404522089469297,
        },
        "baseline metrics changed",
    )
    _require(not _contains_local_path(training), "training run must not contain local machine paths")

    print("Phase 47 artifacts validated")


if __name__ == "__main__":
    main()
