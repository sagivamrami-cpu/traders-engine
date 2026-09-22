# Phase 4 Fixture Dataset Factory Report

## Scope

Phase 4 creates fixture-only candidate training rows by joining UnifiedMarketState,
CandidateAction, TradeContract, and OutcomeLabel artifacts.

It does not implement model training, prediction, backtesting, broker
integration, live execution, or production data vendor connectivity.

## Files

- schemas/candidate_training_row.schema.json: candidate row contract
- configs/datasets/fixture-dataset-policy.yaml: fixture dataset and chronological split policy
- trading_system/datasets: row contract, row factory, and split helper
- tests/datasets: contract, factory, split, and validator tests
- tools/validate_phase4.py: deterministic Phase 4 validator

## Tests

- `python -m pytest tests/datasets -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`

## Decisions

- Dataset rows are candidate snapshots, not candles.
- Rejected candidates remain present and excluded from training.
- Ambiguous labels remain present and excluded from training.
- Chronological split assignment is deterministic and has no random state.
- Source hashes are carried into each row for provenance.

## Unresolved Risks

- No production data source is approved.
- No production graph rule is approved.
- No time-series evaluation protocol beyond split assignment exists.
- No model baseline exists.

## Next Phase

Phase 5 should add baseline offline model training only after dataset row
validation, chronological split enforcement, leakage checks, and metric
contracts are in place. The first model must remain research-only.
