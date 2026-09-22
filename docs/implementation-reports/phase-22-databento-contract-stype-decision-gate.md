# Phase 22 Databento Contract Stype Decision Gate

## Summary

Phase 22 adds a human-reviewed contract/stype decision gate before any real-key
Databento online cost preflight. This prevents Codex from querying Databento
with ambiguous `GC`/`raw_symbol` assumptions.

## Added

- `docs/superpowers/plans/2026-09-01-phase-22-databento-contract-stype-decision-gate.md`
- `schemas/databento_gc_contract_stype_decision.schema.json`
- `trading_system/research/databento_contract_stype_decision.py`
- `tools/validate_databento_gc_contract_stype_decision.py`
- `tests/research/test_databento_contract_stype_decision.py`

## Modified

- `tools/preflight_databento_gc_vendor.py`
- `tools/validate_phase21.py`
- `configs/data/databento-gc-contract-stype-decision-template.yaml`
- `docs/implementation-reports/phase-21-databento-access-cost-preflight.md`

## Safety Guarantees

- The open template validates but does not approve online cost preflight.
- Approved decisions are scoped to `COST_PREFLIGHT_ONLY`.
- Approved decisions require human metadata: approver, timestamp, evidence,
  selected mode, and selected symbols.
- `XAUUSD` and `GLD` are rejected.
- Online cost preflight requires `--contract-stype-decision`.
- No Databento API call is made by validators or tests.
- Purchase, download, training, live trading, broker execution, and capital
  allocation remain blocked.

## Verification

- `python -m pytest tests/research/test_databento_contract_stype_decision.py -q`: PASS, 6 passed.
- `python -m pytest tests/research/test_databento_vendor_preflight.py tests/research/test_databento_contract_stype_decision.py tests/research/test_phase21_validator.py -q`: PASS, 22 passed.
- `python tools/validate_phase21.py`: PASS, Phase 21 artifacts validated.

## Remaining Human Choice

Before any real-key online cost estimate, the human must choose one Databento
symbol mode:

- `dated_raw_symbol`, for example `GCZ6`
- `parent_futures`, for example `GC.FUT`
- `continuous_front_month`, for example `GC.v.0`

This choice is still not approval to buy data or train a model.
