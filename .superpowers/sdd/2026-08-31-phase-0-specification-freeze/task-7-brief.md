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
