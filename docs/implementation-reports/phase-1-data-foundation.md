# Phase 1 Data Foundation Report

## Scope

Phase 1 creates a deterministic fixture-backed data foundation for the TR
Hybrid Intelligence trading system. It covers source inventory, source hashes,
timestamp and symbol normalization, session resolution, availability intervals,
point-in-time filtering, replay fingerprinting, and metadata validation.

It does not implement model training, backtesting, candidate generation,
feature engines, broker integration, live execution, or production data vendor
connectivity.

## Files

- schemas: raw source and dataset manifest contracts
- configs/data: source inventory, session calendar, symbol map, normalization policy
- trading_system/data_foundation: Phase 1 package modules
- tests/data_foundation: behavior and contract tests
- tests/fixtures/data_foundation: synthetic raw OHLCV fixture and expected replay manifest
- tools/validate_phase1.py: deterministic Phase 1 validator
- research/priority-register.yaml: open Phase 1 human data decisions

## Tests

- `python -m pytest tests/data_foundation -v`
- `python -m pytest tests/specification tests/data_foundation -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`

## Decisions

- Phase 1 uses only synthetic fixture data until real data sources are approved.
- Real OHLCV, order-flow, and options sources remain `OPEN_HUMAN_DECISION`.
- `available_at` is required for all historical records.
- Point-in-time filtering excludes records with `available_at > observation_time`.
- Missing volume is represented as `MISSING`, not zero.
- Delayed records beyond the configured stale threshold are represented as `STALE`.
- Corrected records preserve `CORRECTED` provenance instead of silently replacing prior state.
- Replay manifests use a fixed Phase 1 fixture timestamp for byte-stable validation.

## Unresolved Risks

- No production OHLCV vendor is approved.
- No production order-flow vendor is approved.
- No production options vendor is approved.
- No first real vertical-slice symbol is approved.
- No first real historical interval is approved.
- No external raw-data storage and license policy is approved.

## Next Phase

After the human data decisions are resolved, Phase 1 can be extended from the
synthetic fixture to one real symbol, one graph, and one bounded historical
interval. Phase 2 should not start until replay of that vertical slice is stable
and point-in-time checks pass.
