# Codex Status

Status:
ACCEPTED_BY_CODEX

Phase:
28

Subject:
Groq review intake for GC bar/session/timestamp policy candidate

Review:
`agent-exchange/reviews/2026-09-01T213200Z-groq-review-phase-28-bar-session-timestamp-policy.md`

Verdict:
ACCEPT_WITH_CHANGES

Codex decision:
Accepted as technically valid. Phase 28 remains a blocked policy candidate only. It is not D1-D3 approval, not a complete CME session calendar, not confirmed timestamp evidence, not gap-detection approval, not resampling approval, and not training authorization.

Implemented changes:
- Candidate timeframe, interval, timezone, interval semantics, and `available_at` now carry candidate/not-gate-satisfied tokens.
- Calendar id now remains `cme-globex-metals-research-pending-v1`.
- Session policy now names unsatisfied UTC/CT membership, trade-date roll, and unresolved CME source scope.
- OHLCV 1s timestamp role now requires archive evidence.
- `blocked_reasons` is populated from unsatisfied gates and source/evidence blockers.
- `MISSING_BAR_POLICY` remains a required gate before gap detection.
- Phase 24/25-style denied actions were added to the Phase 28 blocked-action list.
- Phase 28 validator now asserts these guards.

Verification:
- `python -m pytest tests\research\test_gc_bar_session_timestamp_policy.py tests\research\test_phase28_validator.py -q`: PASS, 4 passed.
- `python tools\validate_phase28.py`: PASS, `Phase 28 artifacts validated`.

Remaining blockers:
- Human D1: UTC-fixed vs session-anchored bar-boundary decision.
- Human D2: CME calendar id, holiday/maintenance/early-close overlay, trade-date roll, and UTC/CT membership policy.
- Human D3: timestamp-role confirmation and archive/vendor evidence.
- D4 missing-bar/gap policy remains blocked until D1-D3 and `AVAILABLE_AT_POLICY` are resolved.
- Dataset construction and training remain blocked.

Commit/push:
Not performed by user instruction.
