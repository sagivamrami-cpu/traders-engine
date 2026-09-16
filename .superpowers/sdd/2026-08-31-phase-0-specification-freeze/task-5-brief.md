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
