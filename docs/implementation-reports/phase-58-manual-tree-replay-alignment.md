# Phase 58: Manual Tree Replay Alignment

## Purpose

Phase 58 converts the user-provided manual XAUUSD trade summary for 2026-08-31 through 2026-09-04 into a structured golden alert set.

This phase does not train a model. It checks whether the current local data can replay the manual tree alerts.

## Inputs

- Source: user-provided trade summary screenshot.
- Asset: `XAUUSD`.
- Timestamp meaning: alert time.
- Timezone: `Asia/Jerusalem`.
- Year: `2026`.
- Alerts transcribed: `15`.

## Method

The intake converts every alert from Israel time to UTC and preserves:

- local alert timestamp
- UTC alert timestamp
- side: `BUY` or `SELL`
- entry price
- outcome category from the screenshot
- maximum move when available
- target dots when visually available
- transcription confidence

The replay alignment report then compares the manual alert set against the current registered dataset and symbol map.

## Main Result

Golden set ID: `a3e4622f166e4e9be08baac5ee16e3ec26c308bbb4120067c0d90f22405461b5`

Alignment report ID: `f6d8e565716d8a6c44c293d3ad2cb4874ab557c4b2e596dd80aec0a0881689af`

Manual alert range:

- local: `2026-08-31 08:58` through `2026-09-04 20:45`
- UTC: `2026-08-31T05:58:00Z` through `2026-09-04T17:45:00Z`

Current dataset:

- symbol: `GC`
- range: `2010-06-07T00:00:00Z` through `2026-08-05T23:30:00Z`

## Replay Decision

Replay status: `REPLAY_BLOCKED_SOURCE_DATA_GAP`

Eligible alerts for current replay: `0`

Reasons:

- `SYMBOL_MISMATCH_XAUUSD_VS_GC`
- `XAUUSD_NOT_REGISTERED_IN_SYMBOL_MAP`
- `ALERT_RANGE_AFTER_CURRENT_DATASET_END`
- `TREE_GATES_NOT_IMPLEMENTED_FOR_MANUAL_REPLAY`

## Trading Interpretation

The manual tree may be working, but the current training data cannot yet test these alerts.

The manual alerts are XAUUSD alerts from 2026-08-31 through 2026-09-04. The current local dataset is GC futures and ends at 2026-08-05. That means there is no point-in-time XAUUSD market data in the repo for the exact alert window.

So the correct conclusion is not that the tree failed. The correct conclusion is that replay is blocked until we load matching XAUUSD data, or explicitly approve a separate GC proxy study.

## Blocked Actions

- `RUN_MANUAL_TREE_REPLAY`
- `TRAIN_MODEL_FROM_MANUAL_ALERTS`
- `MAP_XAUUSD_TO_GC_WITHOUT_PROXY_STUDY`
- `MODEL_PROMOTION`
- `LIVE_TRADING`
- `BROKER_EXECUTION`
- `CAPITAL_ALLOCATION`
- `CLAIM_EDGE`

## Required Next Inputs

- Register `XAUUSD` as a separate replay symbol, or record a human-approved GC proxy study.
- Obtain XAUUSD OHLCV for 2026-08-31 through 2026-09-04 with point-in-time timestamps.
- Obtain matching order-flow source, or explicitly mark order-flow unavailable for this replay.
- Implement typed tree gates before scoring replay alignment.

## Recommended Next Phase

`PHASE_59_XAUUSD_REPLAY_DATA_ONBOARDING_OR_PROXY_DECISION`

## Artifacts

- Input: `configs/research/xauusd-manual-tree-alerts-2026w36.input.json`
- Golden alerts schema: `schemas/manual_tree_golden_alerts.schema.json`
- Alignment report schema: `schemas/manual_tree_replay_alignment_report.schema.json`
- Module: `trading_system/research/manual_tree_replay_alignment.py`
- CLI: `tools/manual_tree_replay_alignment.py`
- Validator: `tools/validate_phase58.py`
- Golden alerts: `configs/research/xauusd-manual-tree-golden-alerts-2026w36.json`
- Alignment report: `configs/research/manual-tree-replay-alignment-report.json`
- Tests:
  - `tests/research/test_manual_tree_replay_alignment.py`
  - `tests/research/test_manual_tree_replay_alignment_cli.py`
  - `tests/research/test_phase58_validator.py`

## Verification

```powershell
python -m pytest tests\research\test_manual_tree_replay_alignment.py tests\research\test_manual_tree_replay_alignment_cli.py tests\research\test_phase58_validator.py -q
python tools\validate_phase58.py
python -m py_compile trading_system\research\manual_tree_replay_alignment.py tools\manual_tree_replay_alignment.py tools\validate_phase58.py
```

Result:

- 5 tests passed.
- Phase 58 validator passed.
- Python compile check passed.
