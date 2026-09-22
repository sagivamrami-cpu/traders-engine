# Phase 2 Deterministic Feature Engines Report

## Scope

Phase 2 converts Phase 1 normalized, point-in-time fixture records into
schema-compatible FeatureValue payloads and UnifiedMarketState snapshots.

It does not implement candidate generation, labels, backtesting, model
training, broker integration, live execution, or production data vendor
connectivity.

## Files

- configs/features/feature-catalog.yaml: Phase 2 fixture feature ids
- configs/features/feature-engine-registry.yaml: deterministic engine registry
- trading_system/features: feature contracts, registry, price-action features, and UMS builder
- tests/features: contract, feature, market-state, and validator tests
- tools/validate_phase2.py: deterministic Phase 2 validator

## Tests

- `python -m pytest tests/features -v`
- `python -m pytest tests/specification tests/data_foundation tests/features -v`
- `python tools/validate_phase0.py`
- `python tools/validate_phase1.py`
- `python tools/validate_phase2.py`

## Decisions

- Phase 2 uses the existing synthetic OHLCV fixture from Phase 1.
- Price action features are deterministic and use only point-in-time available bars.
- `CORRECTED` source rows map to valid Phase 0 feature status while retaining source provenance upstream.
- Invalid and unknown source rows map to `UNAVAILABLE` feature status.
- UMS data quality is `VALID` only when required fixture features are valid.

## Unresolved Risks

- Real OHLCV, order-flow, and options sources remain unapproved.
- Feature formulas are intentionally minimal fixture formulas, not researched alpha claims.
- No TR graph candidate or label factory exists yet.

## Next Phase

Phase 3 should build candidate snapshot and label factory contracts for one
fixture-backed graph. It must continue to record rejected candidates and keep
ambiguous labels out of training until a conservative policy is approved.
