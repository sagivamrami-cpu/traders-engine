# Human Decision Record

Decision:
APPROVED_V1_NOT_DATASET_AUTHORIZED

Decision id:
D3_TIMESTAMP_POLICY_V1

Approver:
Human Data Owner

Recorded by:
Codex

Recorded at:
2026-09-01T18:10:00Z

Scope:
Approve timestamp interpretation for the first GC v1 research pipeline only.

Approved interpretation:
- OHLCV `ts_event` is treated as the start of the 1-second interval.
- Order-flow `minute` is treated as the start of the 1-minute interval.
- Naive timestamps in the long order-flow series are localized as UTC wall-clock.

Evidence:
- Phase 30 observed OHLCV `ts_event` as `timestamp[ns, tz=UTC]`.
- Phase 30 observed long order-flow `minute` as `timestamp[ns]`.
- The order-flow README states that naive timestamps are UTC wall-clock.

Explicit non-approval:
- Does not approve bar-boundary policy.
- Does not approve CME session calendar policy.
- Does not approve `available_at` beyond the blocked candidate.
- Does not approve missing-bar handling.
- Does not approve order-flow/OHLCV joins.
- Does not approve resampling.
- Does not approve dataset construction.
- Does not approve label building.
- Does not approve training.
- Does not approve model promotion, live trading, broker execution, or capital allocation.

Remaining gates:
- `BAR_BOUNDARY`
- `SESSION_CALENDAR`
- `AVAILABLE_AT_POLICY`
- `MISSING_BAR_POLICY`
- `ROLL_POLICY`
- `ORDER_FLOW_ERA_MAP`
- `CUMULATIVE_FEATURE_POLICY`
- `LABEL_CONTRACT`
- `SPLIT_AND_EMBARGO_POLICY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`
