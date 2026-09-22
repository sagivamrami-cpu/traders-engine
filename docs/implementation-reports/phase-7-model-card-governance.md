# Phase 7 Model Card Governance Report

## Scope

Phase 7 adds research-only model card governance artifacts that summarize model
training, evaluation, known limitations, blocked promotion reasons, supported
scope, and rollback target.

It does not implement approval workflow automation, live deployment, broker
integration, shadow trading, paper trading, or capital allocation.

## Files

- schemas/model_card.schema.json: model card contract
- configs/governance/model-card-policy.yaml: blocked approval policy
- trading_system/governance: model card dataclass and builder
- tests/governance: model card and validator tests
- tools/validate_phase7.py: deterministic Phase 7 validator

## Tests

- `python -m pytest tests/governance -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`
- `python tools/validate_phase6.py`
- `python tools/validate_phase7.py`

## Decisions

- Model card approval status remains `BLOCKED`.
- `approver` remains null until explicit human approval exists.
- `promotion_allowed` remains false at schema and code levels.
- Known limitations explicitly state fixture-only evidence and missing shadow, paper, and cost/fill evidence.
- Rollback target is `NO_LIVE_MODEL`.

## Unresolved Risks

- No production data source is approved.
- No real out-of-sample evidence exists.
- No shadow or paper trading evidence exists.
- No cost/fill evidence exists.
- No human promotion approval exists.

## Next Phase

The next meaningful phase requires real vertical-slice inputs: production data
source, symbol, timeframe, date range, and raw-data storage policy. Without those
inputs, additional implementation should remain governance, validation, or
simulation-only.
