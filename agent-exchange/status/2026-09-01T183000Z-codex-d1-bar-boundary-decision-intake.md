# Agent Exchange Status

Sender:
Codex

Status:
ACCEPTED_BY_CODEX

Scope:
D1 human decision intake for GC v1 bar boundary, timeframe baseline, and available-at policy.

Decision Record:
`agent-exchange/decisions/2026-09-01T182500Z-human-d1-bar-boundary-available-at-v1.md`

Accepted Policy:
- `candidate_timeframe=30m_UTC_FIXED_BASELINE_APPROVED_V1`
- `interval_semantics=HALF_OPEN_UTC_START_INCLUSIVE_END_EXCLUSIVE_APPROVED_V1`
- `bar_boundary.timezone=UTC_FIXED_APPROVED_V1`
- `bar_boundary.available_at=BAR_END_UTC_APPROVED_V1`
- `available_at_policy.policy=BAR_END_UTC_APPROVED_V1`

What Changed:
- Removed `BAR_BOUNDARY` and `AVAILABLE_AT_POLICY` from unsatisfied Phase 28 and Phase 24 gates.
- Removed `BAR_BOUNDARY_GATE_UNSATISFIED` and `AVAILABLE_AT_POLICY_GATE_UNSATISFIED` blockers.
- Kept `SESSION_CALENDAR`, `MISSING_BAR_POLICY`, and `DATASET_CONSTRUCTION_AUTHORIZATION` blocked.
- Kept dataset construction and training disallowed.

Verification:
- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_gc_real_dataset_contract.py tests\research\test_gc_pretraining_readiness.py -q`: PASS, 12 passed.
- `python tools\validate_phase24.py`: PASS.
- `python tools\validate_phase25.py`: PASS.
- `python tools\validate_phase28.py`: PASS.
- `python tools\validate_phase29.py`: PASS.
- `python tools\validate_phase30.py`: PASS.

Next Human-Dependent Gate:
`SESSION_CALENDAR`: choose authoritative source and construction policy for CME Globex metals session membership, holidays, maintenance breaks, and DST handling.
