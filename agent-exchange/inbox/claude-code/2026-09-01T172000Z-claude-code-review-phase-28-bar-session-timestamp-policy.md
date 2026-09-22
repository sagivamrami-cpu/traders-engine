# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T17:20:00Z

Status:
REVIEW_REQUESTED

Priority:
HIGH

Objective:
Review Phase 28 GC bar/session/timestamp policy candidate.

Scope:
- `configs/data/gc-bar-session-timestamp-policy.yaml`
- `schemas/gc_bar_session_timestamp_policy.schema.json`
- `trading_system/research/gc_bar_session_timestamp_policy.py`
- `tools/validate_gc_bar_session_timestamp_policy.py`
- `tools/validate_phase28.py`
- `tests/research/test_gc_bar_session_timestamp_policy.py`
- `tests/research/test_phase28_validator.py`
- `docs/implementation-reports/phase-28-gc-bar-session-timestamp-policy.md`

Review focus:
- Verify UTC-fixed 30m bar-boundary policy is represented as a candidate only, not dataset authorization.
- Verify CME Globex metals normal-session policy is source-backed but keeps `holiday_overlay_status=REQUIRED_NOT_ENCODED`.
- Verify timestamp role remains pending human confirmation/vendor evidence.
- Verify no real resampling, dataset construction, or training is authorized.
- Verify CLI output is sanitized and does not leak local paths.

Forbidden assumptions:
- Do not mark `BAR_BOUNDARY`, `SESSION_CALENDAR`, `TIMESTAMP_ROLE`, or `AVAILABLE_AT_POLICY` satisfied.
- Do not encode guessed holidays.
- Do not build a dataset, labels, features, or model.
- Do not query vendors or external APIs.
- Do not write secrets, raw market rows, local absolute paths, or large artifacts.

Verification command:
- `python tools/validate_phase28.py`

Expected output:
Write review to `agent-exchange/reviews/` with verdict, findings by severity, commands run, and whether Codex may accept Phase 28 as a blocked policy candidate.
