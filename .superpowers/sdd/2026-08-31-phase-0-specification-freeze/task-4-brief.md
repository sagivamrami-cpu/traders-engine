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
