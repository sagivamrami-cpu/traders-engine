# Phase 0 Specification Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 0 specification-freeze artifacts for the TR Hybrid Intelligence trading system before any data ingestion, feature engine, labeling, runtime, or model training work begins.

**Architecture:** Keep the existing content engine untouched. Add a separate specification layer made of versioned JSON schemas, YAML contracts, policy skeletons, validation tooling, tests, and a Phase 0 implementation report. The validator is deterministic and checks structure, versions, open research parameters, and artifact cross-references without assigning trading thresholds.

**Tech Stack:** Python 3.9+, pytest, PyYAML, jsonschema, JSON Schema Draft 2020-12, YAML config artifacts.

**Spec:** `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`

## Global Constraints

- Codex owns architecture and task routing.
- No model training starts before Phase 0 artifacts are approved.
- No feature may use data with `feature_observed_at > observation_time`.
- Null, zero, false, stale, unavailable, not applicable, and unknown are separate states.
- Hard gates are deterministic code or policies, not learned model weights.
- Candidate generation and candidate rejection are both logged.
- A training row is a Candidate Snapshot, not a candle.
- If target and stop are both touched in the same bar without tick path, the label is `AMBIGUOUS`.
- Touching a price is not proof of fill.
- No random split is allowed for time-series training or evaluation.
- LLMs may explain, audit, summarize, and detect assumptions; they may not directly place orders, set size, override hard gates, or approve promotion.
- LangGraph is a control-plane state machine, not the data plane, feature engine, ML trainer, backtest engine, broker state, or low-latency execution adapter.
- Every schema, label, contract, policy, graph, model, dataset, and report is versioned.
- No edge claim is accepted without out-of-sample evidence, calibrated probabilities, costs, stability checks, and multiple-testing awareness.
- Every phase ends with an implementation report listing files, tests, decisions, unresolved risks, and next phase.

---

## File Structure

Create or modify these files only:

- `requirements.txt`: add test and schema-validation dependencies.
- `pytest.ini`: configure pytest discovery.
- `schemas/feature_value.schema.json`: FeatureValue contract.
- `schemas/unified_market_state.schema.json`: UnifiedMarketState contract.
- `schemas/candidate_action.schema.json`: CandidateAction contract.
- `schemas/trade_contract.schema.json`: TradeContract contract.
- `schemas/outcome_label.schema.json`: OutcomeLabel contract.
- `schemas/prediction.schema.json`: Prediction contract.
- `schemas/final_decision.schema.json`: FinalDecision contract.
- `schemas/llm-meta-output.schema.json`: constrained LLM audit output contract.
- `configs/graphs/node-registry.yaml`: 22 layers, 14 TR runtime stages, node taxonomy, graph nodes.
- `configs/features/feature-catalog.yaml`: feature families and v1 feature contracts.
- `configs/contracts/label-contracts.yaml`: label, candidate snapshot, and trade contract definitions for the first graph candidate.
- `configs/features/feature-dependency-graph.yaml`: dependency and loop mapping by feature family.
- `configs/features/freshness-policy.yaml`: freshness status contract and research-owned TTL entries.
- `configs/graphs/critical-dependency-matrix.yaml`: graph-level required and optional dependencies.
- `configs/history/historical-match-policy.yaml`: historical probability output contract and fallback hierarchy.
- `configs/decision/conflict-policy.yaml`: conflict inputs and allowed outputs.
- `configs/risk/portfolio-sizing-policy.yaml`: sizing family contract and open sizing decision.
- `configs/execution/cost-fill-policy.yaml`: execution cost and fill concepts.
- `configs/runtime/degraded-mode-policy.yaml`: degraded mode behavior.
- `configs/runtime/kill-switch-policy.yaml`: kill switch taxonomy.
- `research/priority-register.yaml`: open research and human decision register.
- `research/experiment-ledger/README.md`: experiment ledger format.
- `tools/validate_phase0.py`: deterministic artifact validator.
- `tests/specification/test_phase0_schemas.py`: schema examples and rejection tests.
- `tests/specification/test_phase0_configs.py`: YAML artifact tests.
- `tests/specification/test_phase0_validator.py`: validator behavior tests.
- `docs/implementation-reports/phase-0-specification-freeze.md`: Phase 0 report.

Do not modify:

- `engine/`
- `brand.py`
- `run_daily.py`
- Notion or Telegram delivery code

---

### Task 1: Test and Validation Tooling

**Files:**
- Modify: `requirements.txt`
- Create: `pytest.ini`
- Create: `tests/specification/test_phase0_tooling.py`

**Interfaces:**
- Consumes: existing Python environment.
- Produces: pytest discovery and imports for `yaml` and `jsonschema`.

- [ ] **Step 1: Write the failing test**

Create `tests/specification/test_phase0_tooling.py`:

```python
def test_phase0_validation_dependencies_import():
    import jsonschema
    import yaml

    assert jsonschema.Draft202012Validator.META_SCHEMA["$schema"].endswith("/schema")
    assert yaml.safe_load("phase: 0\n") == {"phase": 0}
```

- [ ] **Step 2: Run the test to verify it fails before dependencies are installed**

Run: `python -m pytest tests/specification/test_phase0_tooling.py -v`

Expected before dependency update: import failure for `pytest`, `jsonschema`, or `yaml` in a clean environment.

- [ ] **Step 3: Add dependencies and pytest configuration**

Append to `requirements.txt`:

```text
pytest>=8.0
PyYAML>=6.0
jsonschema>=4.22
```

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 4: Install dependencies**

Run: `python -m pip install -r requirements.txt`

Expected: command exits 0.

- [ ] **Step 5: Run the tooling test**

Run: `python -m pytest tests/specification/test_phase0_tooling.py -v`

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini tests/specification/test_phase0_tooling.py
git commit -m "test: add phase 0 validation tooling"
```

---

### Task 2: Core JSON Schemas

**Files:**
- Create: `schemas/feature_value.schema.json`
- Create: `schemas/unified_market_state.schema.json`
- Create: `schemas/candidate_action.schema.json`
- Create: `schemas/trade_contract.schema.json`
- Create: `schemas/outcome_label.schema.json`
- Create: `schemas/prediction.schema.json`
- Create: `schemas/final_decision.schema.json`
- Create: `schemas/llm-meta-output.schema.json`
- Create: `tests/specification/test_phase0_schemas.py`

**Interfaces:**
- Consumes: JSON Schema Draft 2020-12.
- Produces: schema files used by `tools/validate_phase0.py`.

- [ ] **Step 1: Write schema tests with valid examples**

Create `tests/specification/test_phase0_schemas.py`:

```python
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def assert_valid(schema_name: str, payload: dict) -> None:
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def assert_invalid(schema_name: str, payload: dict) -> None:
    schema = load_schema(schema_name)
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert errors


def test_feature_value_valid_contract():
    assert_valid(
        "feature_value.schema.json",
        {
            "name": "tr.vector.recovery_pct",
            "value": 0.48,
            "dtype": "float",
            "status": "VALID",
            "observed_at": "2026-08-30T12:42:00Z",
            "computed_at": "2026-08-30T12:42:01Z",
            "source": "market-feed-v2",
            "engine_version": "vector-engine-1.0.0",
            "confidence": 0.91,
        },
    )


def test_feature_value_rejects_unknown_null_semantics():
    assert_invalid(
        "feature_value.schema.json",
        {
            "name": "tr.vector.recovery_pct",
            "value": 0,
            "dtype": "float",
            "status": "UNKNOWN",
            "observed_at": "2026-08-30T12:42:00Z",
            "computed_at": "2026-08-30T12:42:01Z",
            "source": "market-feed-v2",
            "engine_version": "vector-engine-1.0.0",
            "confidence": 0.91,
        },
    )


def test_unified_market_state_valid_contract():
    assert_valid(
        "unified_market_state.schema.json",
        {
            "snapshot_id": "ums-GC-20260830T124200Z",
            "symbol": "GC",
            "observation_time": "2026-08-30T12:42:00Z",
            "schema_version": "ums-1.0.0",
            "data_quality": "VALID",
            "feature_values": {},
            "availability": {"tr": True, "order_flow": True, "options": False},
            "regime": {
                "primary": "EXPANSION",
                "probabilities": {
                    "TREND": 0.31,
                    "RANGE": 0.09,
                    "EXPANSION": 0.56,
                    "EVENT": 0.04,
                },
            },
        },
    )


def test_candidate_action_valid_contract():
    assert_valid(
        "candidate_action.schema.json",
        {
            "candidate_id": "c-001",
            "snapshot_id": "ums-GC-20260830T124200Z",
            "producer": "TR",
            "graph_id": "tr-vshape-retest-long",
            "graph_version": "1.0.0",
            "direction": "LONG",
            "status": "ELIGIBLE",
            "created_at": "2026-08-30T12:42:00Z",
            "expires_at": "2026-08-30T13:02:00Z",
            "reasons": ["V_SHAPE_COMPLETE", "RETEST_CONFIRMED"],
        },
    )


def test_trade_contract_valid_contract():
    assert_valid(
        "trade_contract.schema.json",
        {
            "contract_version": "tr-contract-1.0.0",
            "entry_policy": "TRIGGER_CLOSE",
            "entry_price": 2410.0,
            "stop_policy": "STRUCTURE_INVALIDATION",
            "stop_price": 2400.0,
            "target_policy": "NEXT_NAMED_LEVEL",
            "target_price": 2432.0,
            "expiry_policy": "MAX_20_BARS",
            "max_holding_bars": 20,
            "commission": 2.4,
            "slippage_model_version": "slippage-1.0.0",
            "fill_policy_version": "fill-1.0.0",
        },
    )


def test_outcome_label_accepts_ambiguous():
    assert_valid(
        "outcome_label.schema.json",
        {
            "candidate_id": "c-001",
            "label_version": "outcome-1.0.0",
            "outcome_class": "AMBIGUOUS",
            "target_before_stop": 0,
            "stop_before_target": 0,
            "expired": 0,
            "net_return_r": None,
            "mae_r": -0.35,
            "mfe_r": 2.4,
            "time_to_outcome_bars": 1,
            "filled": True,
            "realized_slippage_ticks": None,
            "label_quality": "EXCLUDED_FROM_TRAINING",
        },
    )


def test_prediction_valid_contract():
    assert_valid(
        "prediction.schema.json",
        {
            "candidate_id": "c-001",
            "model_id": "candidate-outcome-gbdt",
            "model_version": "0.3.0",
            "feature_schema_version": "ums-1.0.0",
            "p_target_first": 0.74,
            "p_stop_first": 0.21,
            "p_expired": 0.05,
            "expected_net_return_r": 0.82,
            "expected_mae_r": -0.46,
            "expected_mfe_r": 1.88,
            "uncertainty": 0.09,
            "coverage_status": "IN_DISTRIBUTION",
            "calibration_version": "cal-0.2.0",
        },
    )


def test_final_decision_valid_contract():
    assert_valid(
        "final_decision.schema.json",
        {
            "decision": "LONG",
            "candidate_id": "c-001",
            "decision_policy_version": "policy-0.2.0",
            "hard_gates_passed": True,
            "expected_value_r": 0.82,
            "risk_size": 0.25,
            "reasons": [
                "POSITIVE_EXPECTED_VALUE",
                "CALIBRATED_CONFIDENCE",
                "RISK_WITHIN_LIMIT",
            ],
        },
    )


def test_llm_meta_output_rejects_order_action():
    assert_invalid(
        "llm-meta-output.schema.json",
        {
            "thesis": "looks strong",
            "supported_state_paths": ["tr.vector.recovery_pct"],
            "assumptions": [],
            "contradictions": [],
            "recommended_action": "SUBMIT_ORDER",
            "confidence": 0.61,
            "schema_version": "llm-meta-0.1.0",
        },
    )
```

- [ ] **Step 2: Run schema tests to verify missing schemas fail**

Run: `python -m pytest tests/specification/test_phase0_schemas.py -v`

Expected: FAIL because schema files do not exist.

- [ ] **Step 3: Create the schema files**

Each schema must include:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false
}
```

Required enum values:

- FeatureValue `status`: `VALID`, `MISSING`, `STALE`, `UNAVAILABLE`, `NOT_APPLICABLE`
- FeatureValue `dtype`: `float`, `integer`, `string`, `boolean`, `categorical`, `object`, `array`, `null`
- UnifiedMarketState `data_quality`: `VALID`, `DEGRADED`, `STALE_BLOCKING`, `INVALID`
- CandidateAction `producer`: `TR`, `ORDER_FLOW`, `OPTIONS`
- CandidateAction `direction`: `LONG`, `SHORT`
- CandidateAction `status`: `ELIGIBLE`, `REJECTED`, `EXPIRED`, `BLOCKED`
- OutcomeLabel `outcome_class`: `TARGET_FIRST`, `STOP_FIRST`, `EXPIRED`, `AMBIGUOUS`
- OutcomeLabel `label_quality`: `HIGH`, `MEDIUM`, `LOW`, `EXCLUDED_FROM_TRAINING`
- Prediction `coverage_status`: `IN_DISTRIBUTION`, `LOW_COVERAGE`, `OUT_OF_DISTRIBUTION`, `MODEL_UNAVAILABLE`
- FinalDecision `decision`: `LONG`, `SHORT`, `WAIT`, `NO_TRADE`
- LLM meta `recommended_action`: `LONG`, `SHORT`, `WAIT`, `NO_TRADE`

Numeric probability fields must use:

```json
{"type": "number", "minimum": 0, "maximum": 1}
```

Timestamp fields must use:

```json
{"type": "string", "format": "date-time"}
```

- [ ] **Step 4: Run schema tests**

Run: `python -m pytest tests/specification/test_phase0_schemas.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add schemas tests/specification/test_phase0_schemas.py
git commit -m "feat: add phase 0 core schemas"
```

---

### Task 3: Phase 0 Artifact Validator

**Files:**
- Create: `tools/validate_phase0.py`
- Create: `tests/specification/test_phase0_validator.py`

**Interfaces:**
- Consumes: schema files under `schemas/`; YAML files under `configs/` and `research/`.
- Produces: CLI command `python tools/validate_phase0.py` with exit code 0 on valid Phase 0 artifacts.

- [ ] **Step 1: Write validator tests**

Create `tests/specification/test_phase0_validator.py`:

```python
from pathlib import Path

import pytest

from tools.validate_phase0 import (
    load_yaml,
    require_keys,
    validate_unique_ids,
    validate_research_parameter,
)


def test_require_keys_reports_missing_key():
    with pytest.raises(ValueError, match="missing required keys: version"):
        require_keys("sample", {"name": "x"}, ["name", "version"])


def test_validate_unique_ids_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicate id: tr.vector"):
        validate_unique_ids("features", [{"id": "tr.vector"}, {"id": "tr.vector"}])


def test_validate_research_parameter_requires_status():
    with pytest.raises(ValueError, match="parameter missing required keys: status"):
        validate_research_parameter(
            {
                "parameter_id": "tr.vector.threshold",
                "hypothesis": "vector threshold requires evidence",
                "allowed_range": {"min": 0, "max": 1},
                "source": "research",
            }
        )


def test_load_yaml_reads_mapping(tmp_path: Path):
    path = tmp_path / "artifact.yaml"
    path.write_text("version: phase0-0.1.0\n", encoding="utf-8")
    assert load_yaml(path) == {"version": "phase0-0.1.0"}
```

- [ ] **Step 2: Run validator tests to verify they fail**

Run: `python -m pytest tests/specification/test_phase0_validator.py -v`

Expected: FAIL because `tools.validate_phase0` does not exist.

- [ ] **Step 3: Create the validator module**

Create `tools/validate_phase0.py` with these exact public functions:

```python
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
```

- [ ] **Step 4: Run validator unit tests**

Run: `python -m pytest tests/specification/test_phase0_validator.py -v`

Expected: all tests pass.

- [ ] **Step 5: Run the full validator to verify artifact files are still missing**

Run: `python tools/validate_phase0.py`

Expected: FAIL with `missing Phase 0 files`.

- [ ] **Step 6: Commit**

```bash
git add tools/validate_phase0.py tests/specification/test_phase0_validator.py
git commit -m "feat: add phase 0 artifact validator"
```

---

### Task 4: Node Registry

**Files:**
- Create: `configs/graphs/node-registry.yaml`
- Create: `tests/specification/test_phase0_configs.py`

**Interfaces:**
- Consumes: `tools.validate_phase0.validate_node_registry`.
- Produces: node registry with 22 layers, 14 TR runtime stages, taxonomy, and first graph node set.

- [ ] **Step 1: Write node registry tests**

Create `tests/specification/test_phase0_configs.py`:

```python
from pathlib import Path

from tools.validate_phase0 import load_yaml, validate_node_registry

ROOT = Path(__file__).resolve().parents[2]


def test_node_registry_has_required_layers_and_runtime_stages():
    path = ROOT / "configs/graphs/node-registry.yaml"
    validate_node_registry(path)
    registry = load_yaml(path)
    assert [layer["id"] for layer in registry["layers"]] == [f"L{i}" for i in range(22)]
    assert registry["tr_runtime_stages"] == [
        "DATA",
        "POSITION",
        "SESSION",
        "LOCATION",
        "CYCLE",
        "CONTEXT",
        "PATTERN",
        "VECTOR",
        "TRAP",
        "RETEST",
        "TARGET_RISK",
        "TRIGGER",
        "SCALE_IN",
        "INVALIDATION",
    ]


def test_node_registry_keeps_hard_gates_deterministic():
    registry = load_yaml(ROOT / "configs/graphs/node-registry.yaml")
    hard_gate_types = {"GLOBAL_HARD_GATE", "GRAPH_ELIGIBILITY_GATE"}
    for node in registry["nodes"]:
        if node["type"] in hard_gate_types:
            assert node["learned"] is False
```

- [ ] **Step 2: Run config tests to verify missing node registry fails**

Run: `python -m pytest tests/specification/test_phase0_configs.py -v`

Expected: FAIL because `node-registry.yaml` does not exist.

- [ ] **Step 3: Create node registry artifact**

Create `configs/graphs/node-registry.yaml` with:

```yaml
version: node-registry-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
taxonomy:
  - FEATURE_ENGINE
  - GLOBAL_HARD_GATE
  - GRAPH_ELIGIBILITY_GATE
  - CANDIDATE_RULE
  - OUTCOME_CONTRACT
  - ALPHA_EVIDENCE
layers:
  - {id: L0, domain: Data & Provenance, role: quality_source_time_session_freshness_version}
  - {id: L1, domain: Market Context, role: shared_context}
  - {id: L2, domain: Trend / MTF, role: trend_multi_timeframe_structure}
  - {id: L3, domain: TR / Vector Intelligence, role: tr_hybrid_state}
  - {id: L4, domain: Location / Levels, role: location_levels_premium_discount}
  - {id: L5, domain: Session Intelligence, role: phase_daily_open_brinks_ny}
  - {id: L6, domain: Cycle Intelligence, role: peak_l1_l2_l3_pushes_age_reset}
  - {id: L7, domain: Pattern Intelligence, role: w_m_vshape_tattoo_rvc_gvc_block}
  - {id: L8, domain: Vector Intelligence, role: vector_type_recovery_first_vector}
  - {id: L9, domain: Trap / Retest, role: trap_retest_reclaim_rejection}
  - {id: L10, domain: Order Flow, role: executed_flow_delta_cvd_footprint_dom_mbo}
  - {id: L11, domain: Options, role: chain_greeks_exposures_walls_expected_move}
  - {id: L12, domain: Cross-Asset / Events, role: correlations_news_event_macro_context}
  - {id: L13, domain: Unified Market State, role: typed_versioned_snapshot}
  - {id: L14, domain: Regime, role: trend_range_expansion_contraction_event_volatility}
  - {id: L15, domain: Historical Probability, role: conditional_probability_and_coverage}
  - {id: L16, domain: Candidate Generation, role: candidates_from_each_producer}
  - {id: L17, domain: Conflict & Ranking, role: conflict_confirmation_ranking_comparison}
  - {id: L18, domain: Timing / Trigger, role: trigger_wait_expiry_entry_timing}
  - {id: L19, domain: Risk / Execution, role: stop_target_costs_size_fill_order_policy}
  - {id: L20, domain: Final Decision, role: long_short_wait_no_trade_trade_contract}
  - {id: L21, domain: Feedback / Learning, role: outcome_logging_replay_research_promotion}
tr_runtime_stages:
  - DATA
  - POSITION
  - SESSION
  - LOCATION
  - CYCLE
  - CONTEXT
  - PATTERN
  - VECTOR
  - TRAP
  - RETEST
  - TARGET_RISK
  - TRIGGER
  - SCALE_IN
  - INVALIDATION
nodes:
  - id: data.quality_gate
    layer: L0
    type: GLOBAL_HARD_GATE
    learned: false
    dependencies: []
    output_contract: data_quality_gate_result
  - id: tr.location
    layer: L4
    type: FEATURE_ENGINE
    learned: false
    dependencies: [data.ohlcv]
    output_contract: feature_family.tr.location
  - id: tr.vshape
    layer: L7
    type: FEATURE_ENGINE
    learned: false
    dependencies: [data.ohlcv, tr.location]
    output_contract: feature_family.tr.pattern
  - id: tr.retest
    layer: L9
    type: FEATURE_ENGINE
    learned: false
    dependencies: [data.ohlcv, tr.vshape]
    output_contract: feature_family.tr.retest
  - id: graph.tr-vshape-retest-long
    layer: L16
    type: CANDIDATE_RULE
    learned: false
    dependencies: [tr.location, tr.vshape, tr.retest]
    output_contract: candidate_action.schema.json
  - id: contract.tr-vshape-retest-long
    layer: L20
    type: OUTCOME_CONTRACT
    learned: false
    dependencies: [graph.tr-vshape-retest-long]
    output_contract: trade_contract.schema.json
```

- [ ] **Step 4: Run node registry tests**

Run: `python -m pytest tests/specification/test_phase0_configs.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add configs/graphs/node-registry.yaml tests/specification/test_phase0_configs.py
git commit -m "feat: add phase 0 node registry"
```

---

### Task 5: Feature Catalog

**Files:**
- Create: `configs/features/feature-catalog.yaml`
- Modify: `tests/specification/test_phase0_configs.py`

**Interfaces:**
- Consumes: `tools.validate_phase0.validate_feature_catalog`.
- Produces: feature family contracts for data provenance, shared context, TR, order flow, options, regime, and risk.

- [ ] **Step 1: Add feature catalog tests**

Append to `tests/specification/test_phase0_configs.py`:

```python
from tools.validate_phase0 import validate_feature_catalog


def test_feature_catalog_has_null_semantics_and_required_families():
    path = ROOT / "configs/features/feature-catalog.yaml"
    validate_feature_catalog(path)
    catalog = load_yaml(path)
    assert catalog["null_semantics"] == [
        "zero",
        "false",
        "missing",
        "unknown",
        "unavailable",
        "not_applicable",
        "stale",
    ]
    family_ids = {family["id"] for family in catalog["feature_families"]}
    assert {
        "data.provenance",
        "shared.context",
        "tr.location",
        "tr.pattern",
        "tr.vector",
        "tr.retest",
        "order_flow.master",
        "options.prior",
        "regime.market",
        "risk.geometry",
    }.issubset(family_ids)
```

- [ ] **Step 2: Run the new test to verify missing catalog fails**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_feature_catalog_has_null_semantics_and_required_families -v`

Expected: FAIL because `feature-catalog.yaml` does not exist.

- [ ] **Step 3: Create feature catalog artifact**

Create `configs/features/feature-catalog.yaml` with `version:
feature-catalog-0.1.0`, the exact `null_semantics` list from the test, and
feature families. Each feature entry must include:

```yaml
id: tr.vector.recovery_pct
dtype: float
unit: percent
status_values: [VALID, MISSING, STALE, UNAVAILABLE, NOT_APPLICABLE]
source: deterministic_feature_engine
observed_at_required: true
computed_at_required: true
engine_version_required: true
confidence_required: true
research_parameters:
  - tr.vector.recovery_pct.thresholds
```

Minimum feature entries:

- `data.symbol`
- `data.timeframe`
- `data.closed_bar`
- `data.freshness_status`
- `shared.vwap.distance_atr`
- `shared.level.type`
- `shared.premium_discount.percentile`
- `tr.location.distance_atr`
- `tr.pattern.type`
- `tr.pattern.quality`
- `tr.vector.type`
- `tr.vector.strength`
- `tr.vector.recovery_pct`
- `tr.retest.state`
- `tr.retest.quality`
- `order_flow.delta`
- `order_flow.cvd_slope`
- `order_flow.absorption`
- `options.gamma_regime`
- `options.expected_move`
- `options.prior.confidence`
- `regime.primary`
- `regime.probabilities`
- `risk.stop_distance`
- `risk.target_distance`
- `risk.rr`

- [ ] **Step 4: Run feature catalog test**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_feature_catalog_has_null_semantics_and_required_families -v`

Expected: pass.

- [ ] **Step 5: Run all config tests**

Run: `python -m pytest tests/specification/test_phase0_configs.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add configs/features/feature-catalog.yaml tests/specification/test_phase0_configs.py
git commit -m "feat: add phase 0 feature catalog"
```

---

### Task 6: Label Contracts

**Files:**
- Create: `configs/contracts/label-contracts.yaml`
- Modify: `tests/specification/test_phase0_configs.py`

**Interfaces:**
- Consumes: `tools.validate_phase0.validate_label_contracts`.
- Produces: v1 candidate snapshot, trade contract, and outcome label contracts.

- [ ] **Step 1: Add label contract tests**

Append to `tests/specification/test_phase0_configs.py`:

```python
from tools.validate_phase0 import validate_label_contracts


def test_label_contracts_define_candidate_snapshot_and_ambiguous_policy():
    path = ROOT / "configs/contracts/label-contracts.yaml"
    validate_label_contracts(path)
    contracts = load_yaml(path)
    assert contracts["candidate_snapshot"]["granularity"] == [
        "observation_time",
        "symbol",
        "producer",
        "graph_id",
        "candidate_direction",
        "contract_version",
    ]
    label = contracts["outcome_labels"][0]
    assert "AMBIGUOUS" in label["outcome_classes"]
    assert label["same_bar_target_and_stop_policy"] == "AMBIGUOUS_EXCLUDED_FROM_TRAINING"
```

- [ ] **Step 2: Run the new test to verify missing contracts fail**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_label_contracts_define_candidate_snapshot_and_ambiguous_policy -v`

Expected: FAIL because `label-contracts.yaml` does not exist.

- [ ] **Step 3: Create label contracts artifact**

Create `configs/contracts/label-contracts.yaml`:

```yaml
version: label-contracts-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
candidate_snapshot:
  id_strategy: sha256_symbol_observation_time_producer_graph_direction_contract_version
  granularity:
    - observation_time
    - symbol
    - producer
    - graph_id
    - candidate_direction
    - contract_version
  rejected_candidates_logged: true
trade_contracts:
  - contract_version: tr-contract-0.1.0
    graph_id: tr-vshape-retest-long
    direction: LONG
    entry_policy: TRIGGER_CLOSE
    stop_policy: STRUCTURE_INVALIDATION
    target_policy: NEXT_NAMED_LEVEL
    expiry_policy: MAX_BARS_OPEN_RESEARCH_PARAMETER
    costs_policy_ref: configs/execution/cost-fill-policy.yaml
    fill_policy_ref: configs/execution/cost-fill-policy.yaml
    live_thresholds_approved: false
outcome_labels:
  - label_version: outcome-0.1.0
    outcome_classes: [TARGET_FIRST, STOP_FIRST, EXPIRED, AMBIGUOUS]
    primary_training_label: outcome_class
    binary_projection_allowed: true
    same_bar_target_and_stop_policy: AMBIGUOUS_EXCLUDED_FROM_TRAINING
    secondary_labels:
      - net_return_r
      - mae_r
      - mfe_r
      - time_to_outcome_bars
      - filled
      - realized_slippage_ticks
      - thesis_invalidated_before_outcome
```

- [ ] **Step 4: Run label contract test**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_label_contracts_define_candidate_snapshot_and_ambiguous_policy -v`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add configs/contracts/label-contracts.yaml tests/specification/test_phase0_configs.py
git commit -m "feat: add phase 0 label contracts"
```

---

### Task 7: Operational Policy Skeletons

**Files:**
- Create: `configs/features/feature-dependency-graph.yaml`
- Create: `configs/features/freshness-policy.yaml`
- Create: `configs/graphs/critical-dependency-matrix.yaml`
- Create: `configs/history/historical-match-policy.yaml`
- Create: `configs/decision/conflict-policy.yaml`
- Create: `configs/risk/portfolio-sizing-policy.yaml`
- Create: `configs/execution/cost-fill-policy.yaml`
- Create: `configs/runtime/degraded-mode-policy.yaml`
- Create: `configs/runtime/kill-switch-policy.yaml`
- Create: `research/priority-register.yaml`
- Create: `research/experiment-ledger/README.md`
- Modify: `tests/specification/test_phase0_configs.py`

**Interfaces:**
- Consumes: `tools.validate_phase0.validate_required_files` and `validate_priority_register`.
- Produces: all non-model policy contracts required by Phase 0.

- [ ] **Step 1: Add policy file tests**

Append to `tests/specification/test_phase0_configs.py`:

```python
from tools.validate_phase0 import validate_priority_register, validate_required_files


def test_phase0_required_policy_files_exist():
    validate_required_files()


def test_priority_register_keeps_research_parameters_open():
    path = ROOT / "research/priority-register.yaml"
    validate_priority_register(path)
    register = load_yaml(path)
    statuses = {p["status"] for p in register["research_parameters"]}
    assert statuses == {"OPEN"}
    priorities = {p["priority"] for p in register["research_parameters"]}
    assert "P0_BLOCKS_DATASET" in priorities
    assert "P0_BLOCKS_LIVE" in priorities
```

- [ ] **Step 2: Run the new tests to verify missing files fail**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_phase0_required_policy_files_exist tests/specification/test_phase0_configs.py::test_priority_register_keeps_research_parameters_open -v`

Expected: FAIL because policy files do not exist.

- [ ] **Step 3: Create `feature-dependency-graph.yaml`**

Use this structure:

```yaml
version: feature-dependency-graph-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
feature_families:
  - feature_family: tr.vector
    inputs: [normalized_bars, volume_provenance]
    update_trigger: bar_close
    loop: fast
    max_compute_ms: OPEN_RESEARCH
    ttl_ms: OPEN_RESEARCH
    fallback: UNAVAILABLE
    consumers: [tr_graphs, unified_state]
    skip_rule: null
```

Include entries for `data.provenance`, `shared.context`, `tr.location`,
`tr.pattern`, `tr.vector`, `tr.retest`, `order_flow.master`,
`options.prior`, `regime.market`, and `risk.geometry`.

- [ ] **Step 4: Create `freshness-policy.yaml`**

Use this structure:

```yaml
version: freshness-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
status_values: [FRESH, STALE_USABLE, STALE_BLOCKING, UNAVAILABLE, NOT_APPLICABLE]
ttl_policy:
  - feature_family: tr.vector
    instrument: GC
    timeframe: OPEN_RESEARCH
    session: OPEN_RESEARCH
    source_latency_ms: OPEN_RESEARCH
    market_status: OPEN_RESEARCH
    ttl_ms: OPEN_RESEARCH
    owner: Data Provenance Agent
```

- [ ] **Step 5: Create `critical-dependency-matrix.yaml`**

Use this structure:

```yaml
version: critical-dependency-matrix-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
graphs:
  - graph_id: tr-vshape-retest-long
    required: [data.ohlcv, tr.location, tr.vshape, tr.retest]
    optional: [order_flow.absorption, options.prior]
    degraded_policy:
      order_flow.absorption: LOWER_CONFIDENCE
      options.prior: UNKNOWN_PRIOR
    blocking_policy:
      tr.location: REJECT_GRAPH
```

- [ ] **Step 6: Create remaining policy files**

Each file must contain `version`, `status`, `owner_agent`, and a contract body:

`configs/history/historical-match-policy.yaml`:

```yaml
version: historical-match-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
owner_agent: Leakage and Validation Agent
output_contract:
  required_fields: [probability, effective_n, interval_low, interval_high, match_level, coverage, policy_version]
fallback_hierarchy:
  - GRAPH_REGIME_SYMBOL
  - GRAPH_REGIME_ASSET_CLASS
  - GRAPH_BROAD_REGIME
  - GLOBAL_CALIBRATED_MODEL_PRIOR
  - INSUFFICIENT_EVIDENCE
research_parameters:
  - historical.minimum_effective_n
  - historical.distance_metric
```

`configs/decision/conflict-policy.yaml`:

```yaml
version: conflict-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
owner_agent: Decision Policy Agent
allowed_outputs: [SELECT_CANDIDATE, WAIT, NO_TRADE, LOWER_SIZE, REQUIRE_CONFIRMATION, SPECIAL_SETUP]
forbidden_rules: [TWO_OUT_OF_THREE_VOTE]
required_inputs:
  - candidate_producer
  - graph_id
  - direction
  - calibrated_probability
  - expected_value_r
  - regime
  - producer_reliability
  - data_quality
  - disagreement_type
  - portfolio_exposure
```

`configs/risk/portfolio-sizing-policy.yaml`:

```yaml
version: portfolio-sizing-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
owner_agent: Risk and Execution Agent
approved_sizing_family: OPEN_HUMAN_DECISION
allowed_families: [FIXED_FRACTIONAL, VOLATILITY_TARGETED, CAPPED_MODEL]
forbidden_families: [UNCAPPED_KELLY]
required_caps: [per_trade, per_symbol, per_direction, portfolio, event_exposure]
```

`configs/execution/cost-fill-policy.yaml`:

```yaml
version: cost-fill-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
owner_agent: Risk and Execution Agent
cost_components: [commission, spread, slippage, market_impact, queue_fill_probability, partial_fill, cancel_replace_cost, adverse_selection]
priority_order: [EMPIRICAL_FILLS, EMPIRICAL_PROXY, CONSERVATIVE_THEORETICAL_FALLBACK]
touch_price_is_fill: false
```

`configs/runtime/degraded-mode-policy.yaml`:

```yaml
version: degraded-mode-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
owner_agent: Architecture Lead
safe_degraded_behaviors: [LOWER_CONFIDENCE, UNKNOWN_PRIOR, REJECT_GRAPH, NO_TRADE]
unsafe_global_defaults: [OPTIONS_UNAVAILABLE_BLOCKS_TR, TR_WEAK_BLOCKS_OF, REGIME_WEAK_SKIPS_ALL_SETUPS]
```

`configs/runtime/kill-switch-policy.yaml`:

```yaml
version: kill-switch-policy-0.1.0
status: SPECIFICATION_FREEZE_DRAFT
owner_agent: Risk and Execution Agent
kill_types:
  - {type: DATA, scope: producer_or_global, required_action: block_affected_scope}
  - {type: RISK, scope: account_or_portfolio, required_action: block_new_risk_manage_exits}
  - {type: EXECUTION, scope: broker_or_venue, required_action: cancel_reconcile_block}
  - {type: MODEL, scope: model_or_graph, required_action: fallback_or_disable_model}
  - {type: SYSTEMIC, scope: global, required_action: global_safe_mode}
  - {type: MANUAL, scope: configured_scope, required_action: immediate_policy_action}
audit_required: true
idempotent: true
recovery_acknowledgement_required: true
```

`research/priority-register.yaml`:

```yaml
version: priority-register-0.1.0
research_parameters:
  - parameter_id: tr.vector.thresholds
    hypothesis: Vector thresholds require out-of-sample evidence by graph and regime.
    allowed_range: {min: 0, max: 1}
    source: research
    status: OPEN
    priority: P0_BLOCKS_DATASET
  - parameter_id: label.max_holding_bars
    hypothesis: Expiry horizon changes target-first and stop-first class balance.
    allowed_range: {min: 1, max: 200}
    source: research
    status: OPEN
    priority: P0_BLOCKS_DATASET
  - parameter_id: risk.default_sizing_family
    hypothesis: Default sizing family affects live risk and must be human approved.
    allowed_range: [FIXED_FRACTIONAL, VOLATILITY_TARGETED, CAPPED_MODEL]
    source: human_decision
    status: OPEN
    priority: P0_BLOCKS_LIVE
human_decisions:
  - decision_id: first_vertical_slice_graph
    status: OPEN
    allowed_values: [tr-vshape-retest-long]
  - decision_id: options_v1_mode
    status: OPEN
    allowed_values: [PRIOR_ONLY, CONFIRMATION_ONLY, CANDIDATE_PRODUCER, DISABLED]
  - decision_id: llm_v1_mode
    status: OPEN
    allowed_values: [EXPLANATION_AUDIT_ONLY]
```

`research/experiment-ledger/README.md`:

```markdown
# Experiment Ledger

Every research experiment is recorded, including rejected experiments.

Required fields:

- experiment_id
- hypothesis
- features_graphs_parameters
- dataset_manifest
- train_period
- validation_period
- test_period
- number_of_prior_trials
- metrics
- costs
- accepted_or_rejected
- decision_reason
```

- [ ] **Step 7: Run policy tests**

Run: `python -m pytest tests/specification/test_phase0_configs.py -v`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add configs research tests/specification/test_phase0_configs.py
git commit -m "feat: add phase 0 policy contracts"
```

---

### Task 8: Full Phase 0 Validation Command

**Files:**
- Modify: `tests/specification/test_phase0_configs.py`

**Interfaces:**
- Consumes: `tools.validate_phase0.main`.
- Produces: one full validation check covering schemas and required Phase 0 artifacts.

- [ ] **Step 1: Add full validation test**

Append to `tests/specification/test_phase0_configs.py`:

```python
from tools.validate_phase0 import main as validate_phase0_main


def test_full_phase0_validation_command(capsys):
    assert validate_phase0_main() == 0
    assert "Phase 0 artifacts validated" in capsys.readouterr().out
```

- [ ] **Step 2: Run the full validation test**

Run: `python -m pytest tests/specification/test_phase0_configs.py::test_full_phase0_validation_command -v`

Expected: pass.

- [ ] **Step 3: Run all specification tests**

Run: `python -m pytest tests/specification -v`

Expected: all tests pass.

- [ ] **Step 4: Run validator CLI**

Run: `python tools/validate_phase0.py`

Expected:

```text
Phase 0 artifacts validated
```

- [ ] **Step 5: Commit**

```bash
git add tests/specification/test_phase0_configs.py
git commit -m "test: validate complete phase 0 artifact set"
```

---

### Task 9: Phase 0 Implementation Report

**Files:**
- Create: `docs/implementation-reports/phase-0-specification-freeze.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all Phase 0 artifacts and test output.
- Produces: user-facing Phase 0 report and README pointer.

- [ ] **Step 1: Create implementation report**

Create `docs/implementation-reports/phase-0-specification-freeze.md`:

```markdown
# Phase 0 Specification Freeze Report

## Scope

Phase 0 creates versioned specification artifacts for the TR Hybrid Intelligence
trading system. It does not implement data ingestion, feature engines, labels,
model training, LangGraph runtime, execution adapters, or live trading.

## Files

- schemas: core JSON contracts
- configs: node registry, feature catalog, label contracts, and policy contracts
- research: priority register and experiment ledger format
- tools: Phase 0 validator
- tests: schema, config, and validator tests

## Tests

- `python -m pytest tests/specification -v`
- `python tools/validate_phase0.py`

## Decisions

- Codex remains Architecture Lead.
- Phase 0 artifacts precede model training.
- The first graph candidate is represented as `tr-vshape-retest-long` for
  contract freezing only; human approval is still required before dataset work.
- Options v1 mode remains an open human decision.
- LLM v1 mode remains an open human decision.
- Default sizing family remains an open human decision.

## Unresolved Risks

- No raw market data inventory exists yet.
- No approved label horizon exists yet.
- No approved sizing family exists yet.
- No approved first vertical-slice graph exists yet.
- No out-of-sample evidence exists yet.

## Next Phase

Phase 1 begins only after human approval of Phase 0 artifacts. Phase 1 should
build raw source inventory, source hashing, timestamp/session normalization,
availability eras, and point-in-time storage.
```

- [ ] **Step 2: Add README pointer**

Append this section to `README.md`:

```markdown
## TR Hybrid Intelligence Planning

The trading-system implementation plan is tracked separately from the content
engine.

- Architecture blueprint: `docs/architecture/TR-TREE-TO-TRAINED-MODEL-IMPLEMENTATION-PLAN.md`
- Multi-tool operating model: `docs/superpowers/specs/2026-08-31-multi-tool-agent-operating-model-design.md`
- Phase 0 implementation plan: `docs/superpowers/plans/2026-08-31-phase-0-specification-freeze.md`
- Phase 0 report: `docs/implementation-reports/phase-0-specification-freeze.md`
```

- [ ] **Step 3: Run all checks**

Run:

```bash
python -m pytest tests/specification -v
python tools/validate_phase0.py
```

Expected: pytest passes and validator prints `Phase 0 artifacts validated`.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/implementation-reports/phase-0-specification-freeze.md
git commit -m "docs: add phase 0 specification freeze report"
```

---

## Final Verification

- [ ] Run all specification tests:

```bash
python -m pytest tests/specification -v
```

Expected: all tests pass.

- [ ] Run Phase 0 validator:

```bash
python tools/validate_phase0.py
```

Expected:

```text
Phase 0 artifacts validated
```

- [ ] Check Git state:

```bash
git status --short --branch
```

Expected: clean working tree on the implementation branch.

- [ ] Produce final implementation summary containing:

- files created
- tests run
- open human decisions
- unresolved risks
- recommended Phase 1 entry criteria
