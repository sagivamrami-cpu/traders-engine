# Phases 43-47: GC 30m Real Dataset to Training Start

Owner: Claude Code (human-delegated decisions, see decision records).
Goal: `gc_pretraining_readiness` reports `training_start_allowed: true` for the
first real GC 30m research dataset, with the majority-class baseline actually
trained as proof. Model promotion, live trading, broker execution, and capital
allocation stay blocked throughout.

Starting state (post Phase 42): remaining gates `MISSING_BAR_POLICY`,
`DATASET_IDENTITY`, `DATASET_CONSTRUCTION_AUTHORIZATION`,
`REAL_DATASET_NOT_BUILT`.

## Fixed inputs

- OHLCV: local Databento GC 1s ZIP, 195 monthly parquet members
  (`gc_1s/gc_1s_YYYY-MM.parquet`), index `ts_event` (UTC, interval start),
  columns `gc_open gc_high gc_low gc_close gc_volume`; sha256
  `b59a9dd0...c3d1`, 984,191,105 bytes, 2010-06-07 .. 2026-08-05.
- Order flow: local Databento GC ZIP member `gc/GCext_of_1m.parquet`, index
  `minute` (naive, localize as UTC wall clock), columns
  `volume delta trades`; sha256 `34f82b1b...3155`, 2011-01-02 .. 2026-07-17.
- Calendar: `cme-globex-metals-research-v1` via `resolve_session()`.
- Governing decisions: D1 (30m UTC half-open, available_at = bar end), D3
  (timestamp roles), D4-final (fail-closed exclusion), D5-final (research-only
  identity), D6-final (order flow volume/delta/trades only, 2017 window
  excluded), D7-final (outcome-contract label), D8-final (walk-forward +
  purge + embargo 8), D9-final (authorization bound to identity hash).

## Rules encoded (v1)

Bar grid: 30m UTC, `[start, start+30m)`. Resample 1s -> 30m: open first,
high max, low min, close last, volume sum, `seconds_with_trades` count.
`available_at = bar_end`.

Session membership: a grid bar is `IN_SESSION` iff both `bar_start` and
`bar_end - 1s` resolve `in_session=True`. Exactly one endpoint in session ->
`STRADDLES_SESSION_BOUNDARY` (expected 0 for GC; kept as a guard). Bars not in
session are dropped, not counted as missing. The expected grid is every
in-session bar between the first and last observed in-session bar; an expected
bar with no 1s rows is an `OHLCV_MISSING_BAR`. Session-sequence index counts
only expected in-session bars, so weekends and daily breaks are not gaps.

Row exclusion (D4, fail-closed; every reason recorded, counts by reason and
split emitted in the manifest):
- `OHLCV_MISSING_BAR`: expected bar absent (no row can exist).
- `OHLCV_GAP_IN_FEATURE_LOOKBACK`: any of the previous 14 session bars missing.
- `INSUFFICIENT_LOOKBACK`: fewer than 14 prior session bars.
- `OHLCV_GAP_IN_LABEL_HORIZON`: any of session bars t+1..t+8 missing.
- `INSUFFICIENT_HORIZON`: fewer than 8 session bars after t.
- `DAMAGED_2017_WINDOW`: decision bar in `[2017-01-01, 2017-06-01)` UTC,
  applied to ALL variants (D8) through
  `apply_gc_order_flow_training_mask`.
- `AMBIGUOUS_LABEL`: target and stop touched in the same bar (D7).
- `PURGED_HORIZON_CROSSES_SPLIT_BOUNDARY`, `EMBARGO_AFTER_SPLIT_BOUNDARY`
  (D8, embargo = 8 session bars).
- Order-flow variant only: `ORDER_FLOW_OUTSIDE_COVERAGE` (bar outside the
  order-flow archive span), `ORDER_FLOW_MISSING_FOR_ACTIVE_BAR` (OHLCV volume
  > 0 but zero order-flow minutes in the bar), `ORDER_FLOW_GAP_IN_FEATURE_LOOKBACK`
  (any of the previous 14 session bars order-flow-missing).
No forward fill anywhere.

Features (closed bars only, available at bar end): `close`, `atr_14`,
returns over 1/4/8/14 bars, range/ATR, `volume_30m`, `seconds_with_trades`;
order-flow variant adds `of_volume`, `of_delta`, `of_trades`,
`of_minutes_present`, and 14-bar rolling sums of volume/delta/trades. No CVD,
no cumulative carry across bars beyond the explicit 14-bar rolling window.

Label (D7): R = simple mean of true range over the 14 closed bars ending at
t (`ATR_14_30M_CLOSED_BARS_AT_DECISION`). Entry = open of bar t+1. Long:
target entry+R, stop entry-R; short mirrored. Horizon = bars t+1..t+8
inclusive. First bar touching target -> `TARGET_FIRST`; stop -> `STOP_FIRST`;
both in one bar -> `AMBIGUOUS` (excluded); none -> `EXPIRED`. Zero cost, not
execution truth. One row per (bar, direction).

Split (D8): chronological. TRAIN decision_time < 2022-01-01Z, VALIDATION
< 2024-01-01Z, TEST otherwise. Purge rows whose horizon crosses a boundary;
embargo the first 8 session bars after each boundary. No random state.

Dataset identity: sha256 of both archives (recomputed at build and required to
equal the canonical manifests), sha256 of every governing config and schema,
builder version, rule constants -> `dataset_id = sha256(stable_json)`.

## Phases

43. `MISSING_BAR_POLICY`: builder module with the rules above, fixture tests,
    policy yaml + schema + CLI validator, contract/label-split/timestamp
    policy wiring, validators 24/25/28/29 retargeted.
44. `DATASET_IDENTITY`: identity manifest module + config + CLI; contract
    wiring; validators retargeted.
45. `DATASET_CONSTRUCTION_AUTHORIZATION`: delegated human record bound to the
    identity hash; contract `construction_authorized_by` + allow-flag; schema
    and readiness updated so `required_pretraining_gates ==
    [REAL_DATASET_NOT_BUILT]`.
46. Build: `tools/build_gc_30m_real_dataset.py` writes rows parquet under
    gitignored `market-data/` and a sanitized build manifest (counts, hashes,
    exclusion counts by reason and split, dataset_id) into the repo.
47. Training start: readiness consumes the build manifest, checks identity
    match and `evaluate_training_readiness` on the built rows, reports
    `status: READY`, `training_start_allowed: true`; run
    `train_majority_baseline` and record the run manifest.

Each phase leaves a `status/` result for Codex; decisions go to `decisions/`.
