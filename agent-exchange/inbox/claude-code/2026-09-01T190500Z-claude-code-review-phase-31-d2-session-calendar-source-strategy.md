# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T19:05:00Z

Status:
REVIEW_REQUESTED

Objective:
Review Phase 31 D2 GC session-calendar source strategy implementation.

Scope:
- `agent-exchange/decisions/2026-09-01T185500Z-human-d2-session-calendar-source-strategy-v1.md`
- `configs/data/gc-session-calendar-source-strategy.yaml`
- `schemas/gc_session_calendar_source_strategy.schema.json`
- `schemas/gc_observed_activity_calendar_profile.schema.json`
- `trading_system/research/gc_session_calendar_source_strategy.py`
- `tools/validate_gc_session_calendar_source_strategy.py`
- `tools/inspect_gc_observed_activity_calendar.py`
- `tools/validate_phase31.py`
- `tests/research/test_gc_session_calendar_source_strategy.py`
- `tests/research/test_phase31_validator.py`
- `configs/data/gc-bar-session-timestamp-policy.yaml`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `docs/implementation-reports/phase-31-gc-session-calendar-source-strategy.md`
- `agent-exchange/status/2026-09-01T190000Z-codex-phase-31-d2-source-strategy-result.md`

Review focus:
- Verify D2 is recorded as source-strategy approval only, not session-calendar authorization.
- Verify `SESSION_CALENDAR` remains unsatisfied in Phase 24/28.
- Verify `calendar_registration_allowed=false`.
- Verify Databento `status` schema query remains blocked pending separate approval.
- Verify observed-activity profiling emits sanitized aggregates only and cannot authorize calendar membership by itself.
- Verify no raw rows, secrets, local absolute paths, Databento API calls, resampling, dataset construction, feature building, label building, or training are introduced.

Non-negotiables:
- point-in-time correctness
- no invented thresholds
- no invented feeds or features
- no production approval by implication
- no live trading, broker execution, or capital allocation

Deliverables:
- Write review to `agent-exchange/reviews/`.
- Verdict: `ACCEPT`, `ACCEPT_WITH_CHANGES`, or `REJECT`.
- Findings by severity, with blocking findings first.
- State whether Codex may proceed to the next D2 calendar-construction policy candidate.

Verification commands:
- `python -m pytest tests\research\test_gc_session_calendar_source_strategy.py tests\research\test_phase31_validator.py -q`
- `python tools\validate_phase31.py`
- `python tools\validate_phase24.py`
- `python tools\validate_phase28.py`

Out of scope:
- Do not query vendors or external APIs.
- Do not construct or register a session calendar.
- Do not resample bars, build features, labels, datasets, or models.
- Do not change files unless Codex sends a separate implementation request.

Notes:
Groq is unavailable due to weekly quota, so this is the only external review route for Phase 31.
