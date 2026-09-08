from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def require_keys(label: str, data: dict, keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise ValueError(f"{label} missing required keys: {', '.join(missing)}")


def validate_unique_ids(label: str, rows: list[dict], key: str = "id") -> None:
    seen = set()
    for row in rows:
        value = row.get(key)
        if value in seen:
            raise ValueError(f"{label} duplicate id: {value}")
        seen.add(value)


def validate_research_parameter(parameter: dict) -> None:
    require_keys(
        "parameter",
        parameter,
        ["parameter_id", "hypothesis", "allowed_range", "source", "status"],
    )
    if parameter["status"] not in {"OPEN", "APPROVED", "REJECTED"}:
        raise ValueError(f"parameter invalid status: {parameter['status']}")


def validate_json_schemas() -> None:
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def validate_node_registry(path: Path) -> None:
    data = load_yaml(path)
    require_keys("node registry", data, ["version", "layers", "tr_runtime_stages", "nodes"])
    validate_unique_ids("node registry layers", data["layers"])
    validate_unique_ids("node registry nodes", data["nodes"])
    if len(data["layers"]) != 22:
        raise ValueError("node registry must contain 22 layers")
    if len(data["tr_runtime_stages"]) != 14:
        raise ValueError("node registry must contain 14 TR runtime stages")


def validate_feature_catalog(path: Path) -> None:
    data = load_yaml(path)
    require_keys("feature catalog", data, ["version", "null_semantics", "feature_families"])
    validate_unique_ids("feature families", data["feature_families"])
    for family in data["feature_families"]:
        require_keys("feature family", family, ["id", "owner", "features"])
        validate_unique_ids(f"features in {family['id']}", family["features"])


def validate_label_contracts(path: Path) -> None:
    data = load_yaml(path)
    require_keys("label contracts", data, ["version", "candidate_snapshot", "trade_contracts", "outcome_labels"])
    validate_unique_ids("trade contracts", data["trade_contracts"], key="contract_version")
    validate_unique_ids("outcome labels", data["outcome_labels"], key="label_version")


def validate_priority_register(path: Path) -> None:
    data = load_yaml(path)
    require_keys("priority register", data, ["version", "research_parameters", "human_decisions"])
    for parameter in data["research_parameters"]:
        validate_research_parameter(parameter)


def validate_required_files() -> None:
    required = [
        "configs/graphs/node-registry.yaml",
        "configs/features/feature-catalog.yaml",
        "configs/contracts/label-contracts.yaml",
        "configs/features/feature-dependency-graph.yaml",
        "configs/features/freshness-policy.yaml",
        "configs/graphs/critical-dependency-matrix.yaml",
        "configs/history/historical-match-policy.yaml",
        "configs/decision/conflict-policy.yaml",
        "configs/risk/portfolio-sizing-policy.yaml",
        "configs/execution/cost-fill-policy.yaml",
        "configs/runtime/degraded-mode-policy.yaml",
        "configs/runtime/kill-switch-policy.yaml",
        "research/priority-register.yaml",
        "research/experiment-ledger/README.md",
    ]
    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        raise ValueError(f"missing Phase 0 files: {', '.join(missing)}")


def main() -> int:
    validate_json_schemas()
    validate_required_files()
    validate_node_registry(ROOT / "configs/graphs/node-registry.yaml")
    validate_feature_catalog(ROOT / "configs/features/feature-catalog.yaml")
    validate_label_contracts(ROOT / "configs/contracts/label-contracts.yaml")
    validate_priority_register(ROOT / "research/priority-register.yaml")
    print("Phase 0 artifacts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
