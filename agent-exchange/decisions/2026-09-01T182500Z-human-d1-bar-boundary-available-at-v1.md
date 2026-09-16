# Human Decision Record

Decision:
APPROVED_V1_NOT_DATASET_AUTHORIZED

Decision id:
D1_BAR_BOUNDARY_AVAILABLE_AT_V1

Approver:
Human Data Owner

Recorded by:
Codex

Recorded at:
2026-09-01T18:25:00Z

Scope:
Approve the first GC v1 baseline bar-boundary and availability policy only.

Approved interpretation:
- First training baseline timeframe is 30 minutes.
- Bar boundaries are UTC-fixed on minute `00` and `30`.
- Intervals are half-open: `[bar_start_utc, bar_end_utc)`.
- Row availability for closed-bar features is `bar_end_utc`.
- CME session membership is metadata and must not shift v1 bar boundaries.

Explicit non-approval:
- Does not approve the CME session calendar.
- Does not approve holiday, early-close, maintenance, weekend, DST, trade-date-roll, or UTC/CT session-membership logic.
- Does not approve missing-bar handling.
- Does not approve order-flow/OHLCV joins.
- Does not approve resampling implementation.
- Does not approve dataset construction.
- Does not approve label building.
- Does not approve training.
- Does not approve model promotion, live trading, broker execution, or capital allocation.

Remaining gates:
- `SESSION_CALENDAR`
- `MISSING_BAR_POLICY`
- `ROLL_POLICY`
- `ORDER_FLOW_ERA_MAP`
- `CUMULATIVE_FEATURE_POLICY`
- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`
