# Phase 0 Specification Freeze Report

## Scope

Phase 0 creates versioned specification artifacts for the TR Hybrid Intelligence
trading system. It does not implement data ingestion, feature engines, labels,
model training, LangGraph runtime, execution adapters, or live trading.

## Files

- schemas: core JSON contracts
- configs: node registry, feature catalog, label contracts, and policy contracts
- research: priority register and experiment ledger format
- tools: Phase 0 validator
- tests: schema, config, and validator tests

## Tests

- `python -m pytest tests/specification -v`
- `python tools/validate_phase0.py`

## Decisions

- Codex remains Architecture Lead.
- Phase 0 artifacts precede model training.
- The first graph candidate is represented as `tr-vshape-retest-long` for
  contract freezing only; human approval is still required before dataset work.
- Options v1 mode remains an open human decision.
- LLM v1 mode remains an open human decision.
- Default sizing family remains an open human decision.

## Unresolved Risks

- No raw market data inventory exists yet.
- No approved label horizon exists yet.
- No approved sizing family exists yet.
- No approved first vertical-slice graph exists yet.
- No out-of-sample evidence exists yet.

## Next Phase

Phase 1 begins only after human approval of Phase 0 artifacts. Phase 1 should
build raw source inventory, source hashing, timestamp/session normalization,
availability eras, and point-in-time storage.
