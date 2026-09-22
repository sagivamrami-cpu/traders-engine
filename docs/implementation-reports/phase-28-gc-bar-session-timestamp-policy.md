# Phase 28 GC Bar Session Timestamp Policy Implementation Report

## Summary

Implemented a source-backed GC bar/session/timestamp policy candidate. Phase 28 records the approved v1 UTC-fixed 30m bar boundary and timestamp conventions, while preserving unresolved CME session-calendar and missing-bar gates before real resampling.

This phase does not resample real bars, encode a yearly CME holiday overlay, approve timestamp evidence, construct a dataset, train a model, query vendors, promote models, live trade, execute broker actions, or allocate capital.

## Files

- `configs/data/gc-bar-session-timestamp-policy.yaml`
- `schemas/gc_bar_session_timestamp_policy.schema.json`
- `trading_system/research/gc_bar_session_timestamp_policy.py`
- `tools/validate_gc_bar_session_timestamp_policy.py`
- `tools/validate_phase28.py`
- `tests/research/test_gc_bar_session_timestamp_policy.py`
- `tests/research/test_phase28_validator.py`

## Policy Candidate

- `candidate_timeframe=30m_UTC_FIXED_BASELINE_APPROVED_V1`
- UTC fixed bar boundaries at minute `00` and `30`
- half-open intervals `[bar_start_utc, bar_end_utc)`
- `available_at=BAR_END_UTC_APPROVED_V1`
- D1 decision ref: `agent-exchange/decisions/2026-09-01T182500Z-human-d1-bar-boundary-available-at-v1.md`
- CME Globex metals normal session candidate:
  - calendar id: `cme-globex-metals-research-pending-v1`
  - exchange timezone: `America/Chicago`
  - Sunday-Friday
  - open `17:00` CT
  - close `16:00` CT
  - daily break `16:00`-`17:00` CT
- source references:
  - `https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html`
  - `https://www.cmegroup.com/trading-hours.html`
- `holiday_overlay_status=REQUIRED_NOT_ENCODED`
- `utc_session_reconciliation_status=OPEN_REQUIRES_GATE_DECISION`
- `utc_bar_session_membership_status=REQUIRED_NOT_ENCODED`
- `trade_date_roll_status=REQUIRED_NOT_ENCODED`
- `cme_source_scope_status=CLEARPORT_VS_GLOBEX_GC_PRODUCT_HOURS_UNRESOLVED`
- D2 source strategy is approved through `agent-exchange/decisions/2026-09-01T185500Z-human-d2-session-calendar-source-strategy-v1.md`, but calendar implementation remains required.
- open reconciliation questions:
  - `UTC_30M_BARS_THAT_STRADDLE_CME_DAILY_BREAK`
  - `SESSION_CLOSED_BARS_DROP_MARK_OR_KEEP_WITH_SESSION_FLAG`
  - `DST_SHIFT_OF_CT_SESSION_BOUNDARIES_AGAINST_UTC_BARS`
- timestamp policy is now `HUMAN_APPROVED_V1_NOT_DATASET_AUTHORIZED`
- decision ref: `agent-exchange/decisions/2026-09-01T181000Z-human-d3-timestamp-policy-v1.md`
- OHLCV 1s timestamp role is now `TS_EVENT_INTERVAL_START_APPROVED_V1`
- Order-flow minute role is now `MINUTE_START_APPROVED_V1`
- Naive long order-flow minute timestamps are now `LOCALIZE_AS_UTC_WALL_CLOCK_APPROVED_V1`

## Gates Preserved

- `SESSION_CALENDAR`
- `MISSING_BAR_POLICY`
- `DATASET_CONSTRUCTION_AUTHORIZATION`

## Blocked Reasons

- `SESSION_CALENDAR_GATE_UNSATISFIED`
- `MISSING_BAR_POLICY_GATE_UNSATISFIED`
- `DATASET_CONSTRUCTION_AUTHORIZATION_GATE_UNSATISFIED`
- `HOLIDAY_OVERLAY_REQUIRED_NOT_ENCODED`
- `UTC_BAR_SESSION_MEMBERSHIP_REQUIRED_NOT_ENCODED`

## Verification

- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_phase28_validator.py -q`: PASS, 4 passed.
- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`: PASS, 12 passed.
- `python tools\validate_phase28.py`: PASS, `Phase 28 artifacts validated`.

## Review Intake

- Claude Code Phase 28: `ACCEPT`.
- Claude Code L1: implemented by adding explicit UTC-vs-CT session reconciliation questions to the policy and schema.
- Groq Phase 28: `ACCEPT_WITH_CHANGES`.
- Groq F1-F5: implemented by making 30m/UTC/available_at/calendar/timestamp values visibly candidate or evidence-pending, adding UTC/CT membership and trade-date-roll blockers, populating `blocked_reasons`, carrying `MISSING_BAR_POLICY`, and broadening blocked actions.
- Claude D1/D3 follow-up review: accepted with changes; Codex implemented the fail-closed metals-calendar registration guard, moved the top-level policy status to reviewed/partially approved/still blocked, and kept D2 session-calendar unresolved.
- D2 source-strategy approval: accepted as source strategy only; no calendar registration, Databento `status` query, resampling, dataset construction, or training is authorized.

## Remaining Blockers

- D2 source strategy is chosen, but the full authoritative era-versioned calendar still must be implemented before any metals calendar can be registered.
- Official CME holiday/maintenance overlay and observed-activity reconciliation must be encoded and reviewed before session calendar is usable for real resampling.
- Timestamp-role, 30m UTC-fixed bar boundary, and `available_at=bar_end_utc` are approved for v1 only; all downstream construction remains blocked.
- Real resampling remains blocked.
- Dataset construction remains blocked.
- Training remains blocked.

## Next

Next non-training gate: D2 session-calendar source strategy and implementation policy.
