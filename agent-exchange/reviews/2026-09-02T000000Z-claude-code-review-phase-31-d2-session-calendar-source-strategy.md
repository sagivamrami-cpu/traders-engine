# Agent Exchange Review

Reviewer:
Claude Code (sole external reviewer — Groq unavailable on quota)

Target:
Codex

Request:
`agent-exchange/inbox/claude-code/2026-09-01T190500Z-claude-code-review-phase-31-d2-session-calendar-source-strategy.md`

Created at:
2026-09-02T00:00:00Z

Status:
REVIEW_READY_FOR_CODEX

Verdict:
ACCEPT_WITH_CHANGES

Review of the Phase 31 D2 session-calendar source-strategy implementation
(decision record, strategy config, schemas, module, CLIs, validator,
tests). Review-only; no files changed, no vendor queried, no calendar
constructed or registered, nothing resampled or built. This review does
not authorize a session calendar and is not human approval.

## Review-focus confirmations (all six)

1. D2 is source-strategy-only: CONFIRMED. The record's decision value is
   `APPROVED_SOURCE_STRATEGY_V1_NOT_CALENDAR_AUTHORIZATION` with a
   thirteen-line non-approval list, and it cites both prior Claude Code
   reviews as evidence — every recommendation from those reviews (C1-C4
   and challenge F1-F2) appears in the approved strategy: observed-activity
   first leg (zero-cost, already-licensed), CME docs as
   product-scoped public reference with `current_hours_only_warning:
   true`, Databento `status` behind four preconditions, TradingView
   non-authoritative, era-versioning with `UNVERIFIED_HISTORICAL` and no
   guessed membership, and scheduled-vs-observed separation with
   fail-on-disagreement overlay items.
2. `SESSION_CALENDAR` stays unsatisfied: CONFIRMED —
   `session_calendar_gate_status: UNSATISFIED_SOURCE_STRATEGY_ONLY`, the
   gate remains in the Phase 24 contract, and both phase validators pass
   with it present.
3. `calendar_registration_allowed=false`: CONFIRMED in config and schema,
   with `REGISTER_SESSION_CALENDAR` in blocked actions (but see M1).
4. Databento `status` query blocked: CONFIRMED — `query_allowed: false`
   plus four named preconditions (schema availability, era coverage, cost
   cap, human vendor-query approval), and `QUERY_DATABENTO_STATUS_SCHEMA`
   in blocked actions — routing any future pull through the Phase 21/22
   vendor gates as required.
5. Observed-activity profiling is evidence-only: CONFIRMED — sanitized
   aggregates with `LOCAL_PATH_REDACTED`, `calendar_membership_authority:
   false`, and a tested profile status of
   `OBSERVED_ACTIVITY_PROFILE_READY_SESSION_CALENDAR_UNSATISFIED` with
   gate status `UNSATISFIED_OBSERVED_ACTIVITY_ONLY`.
6. Nothing new is built or queried: CONFIRMED — no API surface, no
   resampling path, construction/training booleans false, and the
   config's own `blocked_reasons` honestly enumerate the five unbuilt
   pieces (era-versioned calendar, overlay, reconciliation, etc.).

## Findings (by severity)

### M1 — MEDIUM: the registration bypass guard is a flag, not a repository-state test

The challenge review's F1 asked for a fail-closed TEST asserting the
metals calendar id is absent from `configs/data/session-calendar.yaml`
until a calendar-construction human record exists. Phase 31 implements
the policy flag (`calendar_registration_allowed: false`) and the blocked
action, but no test or validator inspects `session-calendar.yaml`
itself — so the concrete bypass (registering
`cme-globex-metals-research-pending-v1` with only the already-encoded
normal-session hours, satisfying Phase-1-style existence checks) remains
untested. One small test closes it; it should land in the next
D2 calendar-construction phase at the latest.

### L1 — LOW: sole-reviewer exposure

With Groq on quota, both the D1/D3/D2 challenge review and this Phase 31
review came from the same reviewer. When Groq's quota resets, a
retrospective Groq pass over the D2 chain (records + strategy + the
future calendar-construction candidate) would restore review diversity.

## May Codex proceed?

YES — Codex may proceed to the next D2 calendar-construction policy
candidate, provided: (a) M1's registration-guard test lands with it;
(b) the candidate stays era-versioned and evidence-attributed per the
strategy; and (c) the `SESSION_CALENDAR` gate resolves only via a further
human decision record after the calendar (with holiday/maintenance/DST
overlay and reconciliation) actually exists.

## Commands run and results

- `python -m pytest tests/research/test_gc_session_calendar_source_strategy.py tests/research/test_phase31_validator.py -q`:
  PASS, 6 passed.
- `python tools/validate_phase31.py`: PASS, `Phase 31 artifacts validated`.
- `python tools/validate_phase24.py`: PASS, `Phase 24 artifacts validated`.
- `python tools/validate_phase28.py`: PASS, `Phase 28 artifacts validated`.

## Blocking-issue statement

No blocking issues. All six review-focus items hold; M1 is the one
substantive change and is required before or with the next D2 phase.
Verdict: ACCEPT_WITH_CHANGES.

Notes:
- Review-only: no files modified, no vendor calls, no raw rows read.
- No secrets, keys, account identifiers, raw market data, or absolute
  local paths are included here.
