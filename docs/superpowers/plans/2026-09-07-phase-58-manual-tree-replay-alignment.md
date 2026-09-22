# Phase 58: Manual Tree Replay Alignment

## Goal

Turn the user-provided manual tree trade summary into a versioned golden alert set and determine whether the current dataset can replay it.

## Inputs

- User-provided trade summary screenshot for `2026-08-31` through `2026-09-04`
- Human clarifications:
  - year: `2026`
  - timezone: `Asia/Jerusalem`
  - symbol: `XAUUSD`
  - timestamp meaning: alert time
- `configs/datasets/gc-30m-real-dataset-build-manifest.json`
- `configs/data/symbol-map.yaml`
- `configs/models/gc-tree-gate-baseline-audit.json`

## Outputs

- `schemas/manual_tree_golden_alerts.schema.json`
- `schemas/manual_tree_replay_alignment_report.schema.json`
- `trading_system/research/manual_tree_replay_alignment.py`
- `tools/manual_tree_replay_alignment.py`
- `tools/validate_phase58.py`
- `configs/research/xauusd-manual-tree-golden-alerts-2026w36.json`
- `configs/research/manual-tree-replay-alignment-report.json`
- `docs/implementation-reports/phase-58-manual-tree-replay-alignment.md`
- `agent-exchange/status/2026-09-07-phase-58-manual-tree-replay-alignment.md`

## Test Plan

1. Add unit tests for converting manual Israel-time alerts to UTC.
2. Add tests that current GC data cannot replay XAUUSD alerts outside its date range.
3. Add schema rejection tests for replay-ready claims when blockers exist.
4. Add CLI and validator tests.
5. Generate the real golden set and alignment report.
6. Verify focused tests, validator, compile checks, secret scan, raw-data staging guard, and git diff checks.

## Acceptance Criteria

- Alert timestamps are stored in both local `Asia/Jerusalem` time and UTC.
- The manual alert set contains the visible XAUUSD/gold alerts from the screenshot.
- Current replay is blocked because the registered dataset is `GC`, not `XAUUSD`, and ends before the alert week.
- No proxy mapping from GC to XAUUSD is silently approved.
- Model training and promotion remain blocked.
