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
