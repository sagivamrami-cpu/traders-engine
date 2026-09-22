# Phase 9 Local CSV Research Dry-Run Report

## Scope

Phase 9 adds a local-only research dry-run that connects CSV onboarding through
normalization, market-state snapshots, fixture candidate generation, labeling,
candidate training rows, and the majority baseline training readiness gate.

It does not approve a data vendor, fetch network data, write persistent
artifacts, backtest, integrate a broker, run live execution, promote a model, or
allocate capital.

## Files

- schemas/offline_research_run.schema.json: dry-run summary contract
- trading_system/research/offline_dry_run.py: offline orchestration module
- trading_system/research/__init__.py: research package marker
- tools/run_local_csv_dry_run.py: CLI that prints dry-run JSON
- tools/validate_phase9.py: deterministic Phase 9 validator
- tests/research/test_offline_dry_run.py: dry-run behavior tests
- tests/research/test_phase9_validator.py: validator smoke test

## Tests

- `python -m pytest tests/research/test_offline_dry_run.py -v`
- `python -m pytest tests/research/test_phase9_validator.py -v`
- `python -m pytest tests/specification tests/data_foundation tests/features tests/candidates tests/datasets tests/models tests/evaluation tests/governance tests/research -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`
- `python tools/validate_phase3.py`
- `python tools/validate_phase4.py`
- `python tools/validate_phase5.py`
- `python tools/validate_phase6.py`
- `python tools/validate_phase7.py`
- `python tools/validate_phase8.py`
- `python tools/validate_phase9.py`

## Decisions

- The dry-run accepts local CSV input only.
- The source status remains `OPEN_HUMAN_DECISION`.
- The output is a summary payload, not a persisted training artifact.
- Promotion remains false through the nested training run payload.
- Blocked actions explicitly include vendor approval, model promotion, live
  trading, broker execution, and capital allocation.

## Unresolved Risks

- No production data vendor has been approved.
- No production storage policy exists for user-provided raw CSV files.
- Fixture-sized inputs are insufficient training evidence.
- Candidate rules, labels, costs, fills, and splits remain fixture policies.
- No real out-of-sample, shadow, or paper trading evidence exists.

## Next Phase

The next phase should either onboard a real historical OHLCV CSV through the
dry-run or define the production raw-data storage and licensing policy required
before retaining user-provided market data.
