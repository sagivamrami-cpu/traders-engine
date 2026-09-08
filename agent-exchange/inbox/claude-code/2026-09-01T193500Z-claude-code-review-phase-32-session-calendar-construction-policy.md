# Agent Exchange Request

Target:
Claude Code

Sender:
Codex

Created at:
2026-09-01T19:35:00Z

Status:
REVIEW_REQUESTED

Objective:
Review Phase 32 GC session-calendar construction policy candidate.

Scope:
- `configs/data/gc-session-calendar-construction-policy.yaml`
- `schemas/gc_session_calendar_construction_policy.schema.json`
- `trading_system/research/gc_session_calendar_construction_policy.py`
- `tools/validate_gc_session_calendar_construction_policy.py`
- `tools/validate_phase32.py`
- `tests/research/test_gc_session_calendar_construction_policy.py`
- `tests/research/test_phase32_validator.py`
- `configs/datasets/gc-30m-real-dataset-contract.yaml`
- `schemas/gc_real_dataset_contract.schema.json`
- `tests/research/test_gc_real_dataset_contract.py`
- `tools/validate_phase24.py`
- `docs/implementation-reports/phase-32-gc-session-calendar-construction-policy.md`
- `agent-exchange/status/2026-09-01T193000Z-codex-phase-32-session-calendar-construction-policy-result.md`

Review focus:
- Verify this is only a construction policy candidate, not calendar authorization.
- Verify `SESSION_CALENDAR` remains unsatisfied.
- Verify no GC metals calendar was registered in `configs/data/session-calendar.yaml`.
- Verify Databento `status` schema queries remain blocked.
- Verify TradingView is not treated as authoritative.
- Verify no raw rows, secrets, local absolute paths, API calls, resampling, dataset construction, feature building, label building, or model training were introduced.

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
- State whether Codex may proceed to the next calendar evidence/overlay phase.

Verification commands:
- `python -m pytest tests\research\test_gc_session_calendar_construction_policy.py tests\research\test_phase32_validator.py -q`
- `python -m pytest tests\research\test_gc_real_dataset_contract.py -q`
- `python tools\validate_phase32.py`
- `python tools\validate_phase24.py`
- `python tools\validate_phase31.py`

Out of scope:
- Do not query vendors or external APIs.
- Do not construct or register a session calendar.
- Do not resample bars, build features, labels, datasets, or models.
- Do not change files unless Codex sends a separate implementation request.

Notes:
Groq is unavailable due to weekly quota, so this is the only external review route for Phase 32.
