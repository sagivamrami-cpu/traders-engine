# Phase 3 Candidate and Label Factory Report

## Scope

Phase 3 creates fixture-only CandidateAction, TradeContract, and OutcomeLabel
factories over Phase 2 UnifiedMarketState snapshots and Phase 1 normalized bars.

It does not implement model training, prediction, backtesting, broker
integration, live execution, or production data vendor connectivity.

## Files

- configs/candidates/fixture-graph-rules.yaml: fixture graph and contract rules
- trading_system/candidates: contracts, deterministic candidate generation, and labeling
- tests/candidates: contract, generation, labeling, and validator tests
- tools/validate_phase3.py: deterministic Phase 3 validator

## Tests

- `python -m pytest tests/candidates -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`

## Decisions

- Phase 3 remains fixture-only.
- Candidate generation emits eligible and rejected candidates.
- Fixture LONG contracts use close entry, bar-low stop, and 2R target.
- Rejected candidates are labeled as unfilled and excluded from training.
- Same-bar target and stop touch is labeled `AMBIGUOUS` and excluded from training.

## Unresolved Risks

- Production graph rules are not approved.
- Production stop, target, expiry, commission, slippage, and fill policies are not approved.
- No real vertical-slice symbol or historical interval is approved.
- No model dataset has been produced.

## Next Phase

Phase 4 should build a fixture-backed Dataset Factory that joins UnifiedMarketState,
CandidateAction, TradeContract, and OutcomeLabel payloads into candidate training
rows. Training must remain blocked until dataset validation and time-series split
rules are implemented.
